from __future__ import annotations
"""
app.py — Tiresias OCR · API Flask
Porta: 5090  |  Auth: Atlas IAM (localhost:5010)
"""
import json
import logging
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import timedelta
from pathlib import Path

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

import auth
import database as db
import worker
import atlas_client as ac

ac.SISTEMA_FOLDER = "Tiresias – OCR"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("tiresias.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(BASE_DIR, "tiresias.key")

if os.path.exists(KEY_FILE):
    _key = open(KEY_FILE, "rb").read()[:32]
else:
    _key = os.urandom(32)
    with open(KEY_FILE, "wb") as f:
        f.write(_key)

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
app.secret_key = _key
app.permanent_session_lifetime = timedelta(hours=12)
CORS(app, supports_credentials=True)

_ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}


def _err(msg, code=400):
    return jsonify({"error": msg}), code


def _ok(data=None, **kwargs):
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    payload.update(kwargs)
    return jsonify(payload)


# ── SSO ───────────────────────────────────────────────────────────────────────

def _sso_login(token: str):
    ac.sso_login_from_token(token)


# ── Static ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    token = request.args.get("atlas_token", "").strip()
    if token and not ac.is_atlas_authenticated():
        _sso_login(token)
    resp = send_from_directory(BASE_DIR, "tiresias.html")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.route("/api/ping")
def ping():
    return _ok(message="pong")


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def login():
    data     = request.json or {}
    email    = data.get("email", data.get("username", "")).strip().lower()
    password = data.get("password", "")
    atlas_user = ac.login_with_credentials(email, password)
    if atlas_user:
        return _ok({
            "nome":       atlas_user.get("nome"),
            "email":      atlas_user.get("email"),
            "role_atlas": ac.get_atlas_role(),
            "escopo":     ac.get_atlas_escopo(),
        }, message="Login realizado com sucesso.")
    return _err("E-mail ou senha inválidos, ou acesso ao Tiresias não autorizado.", 401)


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    auth.logout_user()
    return _ok(message="Sessão encerrada.")


@app.route("/api/auth/status")
def auth_status():
    return _ok({
        "authenticated": ac.is_atlas_authenticated(),
        "user":          ac.get_atlas_user(),
        "role_atlas":    ac.get_atlas_role(),
        "escopo":        ac.get_atlas_escopo(),
    })


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.route("/api/stats")
@auth.require_auth
def stats():
    s = db.get_stats()
    s["ocr_status"] = worker.ocr_status()
    s["fila_size"]  = worker.doc_queue.qsize()
    return _ok(s)


# ── Documentos ────────────────────────────────────────────────────────────────

@app.route("/api/docs")
@auth.require_auth
def list_docs():
    status = request.args.get("status", "")
    tipo   = request.args.get("tipo", "")
    q      = request.args.get("q", "")
    limit  = min(int(request.args.get("limit", 100)), 500)
    offset = int(request.args.get("offset", 0))
    return _ok(db.list_docs(status=status, tipo=tipo, q=q, limit=limit, offset=offset))


@app.route("/api/docs/<int:doc_id>")
@auth.require_auth
def get_doc(doc_id):
    doc = db.get_doc(doc_id)
    if not doc:
        return _err("Documento não encontrado.", 404)
    return _ok(doc)


@app.route("/api/docs/check-hash", methods=["POST"])
@auth.require_auth
def check_hash():
    """Recebe {'hash': '<sha256>'} e informa se já existe na base."""
    h = (request.json or {}).get("hash", "").strip()
    if not h:
        return _err("Hash ausente.")
    existing = db.find_by_hash(h)
    if existing:
        return _ok({
            "duplicate": True,
            "doc_id":    existing["id"],
            "nome":      existing["nome_original"],
            "status":    existing["status"],
            "criado_em": existing["criado_em"],
        })
    return _ok({"duplicate": False})


@app.route("/api/docs/upload", methods=["POST"])
@auth.require_auth
def upload_doc():
    files = request.files.getlist("file")
    if not files or all(not f.filename for f in files):
        return _err("Nenhum arquivo enviado.")

    tipo_hint  = request.form.get("tipo", "")
    observacao = request.form.get("observacao", "")
    ignorar_dup = request.form.get("ignorar_duplicata", "0") == "1"
    cfg  = db.get_config()
    lang = cfg.get("idioma_ocr", "por")

    results = []
    for f in files:
        if not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in _ALLOWED_EXT:
            results.append({"nome": f.filename, "ok": False,
                            "error": f"Extensão não suportada: {ext}"})
            continue

        safe_name = f"{int(time.time() * 1000)}_{Path(f.filename).name}"
        dest = os.path.join(db.UPLOADS_DIR, safe_name)
        f.save(dest)

        file_hash = db.sha256_file(dest)
        duplicata_de = None
        existing = db.find_by_hash(file_hash)
        if existing and not ignorar_dup:
            os.remove(dest)
            results.append({
                "nome": f.filename, "ok": False, "duplicate": True,
                "doc_id": existing["id"], "nome_existente": existing["nome_original"],
            })
            continue
        if existing:
            duplicata_de = existing["id"]

        doc_id = db.add_doc(
            nome_original   = f.filename,
            caminho_entrada = dest,
            tipo            = tipo_hint or "desconhecido",
            observacao      = observacao,
            hash_sha256     = file_hash,
            duplicata_de    = duplicata_de,
        )
        worker.enqueue(doc_id, dest, tipo_hint, lang)
        results.append({"nome": f.filename, "ok": True, "doc_id": doc_id,
                        "duplicate": bool(duplicata_de), "duplicata_de": duplicata_de})

    enviados  = [r for r in results if r.get("ok")]
    rejeitados = [r for r in results if not r.get("ok")]
    msg = f"{len(enviados)} arquivo(s) enviado(s) para processamento."
    if rejeitados:
        msg += f" {len(rejeitados)} ignorado(s) por duplicata."
    return _ok({"results": results, "enviados": len(enviados),
                "rejeitados": len(rejeitados)}, message=msg)


@app.route("/api/docs/<int:doc_id>/retry", methods=["POST"])
@auth.require_auth
def retry_doc(doc_id):
    doc = db.get_doc(doc_id)
    if not doc:
        return _err("Documento não encontrado.", 404)
    path = doc.get("caminho_final") or doc.get("caminho_entrada") or ""
    if not path or not os.path.exists(path):
        return _err("Arquivo original não encontrado no disco.")
    cfg = db.get_config()
    db.update_doc(doc_id, status="pendente", observacao="Re-processando...")
    worker.enqueue(doc_id, path, doc.get("tipo", ""), cfg.get("idioma_ocr", "por"))
    return _ok(message="Documento adicionado à fila novamente.")


@app.route("/api/docs/<int:doc_id>", methods=["DELETE"])
@auth.require_auth
def delete_doc(doc_id):
    if not db.get_doc(doc_id):
        return _err("Documento não encontrado.", 404)
    db.delete_doc(doc_id)
    return _ok(message="Documento removido.")


# ── Regras ────────────────────────────────────────────────────────────────────

@app.route("/api/regras")
@auth.require_auth
def list_regras():
    return _ok(db.list_regras())


@app.route("/api/regras", methods=["POST"])
@auth.require_auth
def add_regra():
    data = request.json or {}
    nome = data.get("nome", "").strip()
    if not nome:
        return _err("Nome é obrigatório.")
    regra_id = db.add_regra(
        nome            = nome,
        tipo_doc        = data.get("tipo_doc", "generico"),
        palavras_chave  = json.dumps(data.get("palavras_chave", [])),
        pasta_destino   = data.get("pasta_destino", ""),
        prefixo_nome    = data.get("prefixo_nome", ""),
        exportar_sqlite = int(bool(data.get("exportar_sqlite", False))),
    )
    return _ok({"id": regra_id}, message="Regra criada.")


@app.route("/api/regras/<int:regra_id>", methods=["PUT"])
@auth.require_auth
def update_regra(regra_id):
    data, kwargs = request.json or {}, {}
    for k in ("nome", "tipo_doc", "pasta_destino", "prefixo_nome"):
        if k in data: kwargs[k] = data[k]
    if "palavras_chave" in data:
        kwargs["palavras_chave"] = json.dumps(data["palavras_chave"])
    if "exportar_sqlite" in data:
        kwargs["exportar_sqlite"] = int(bool(data["exportar_sqlite"]))
    if "ativo" in data:
        kwargs["ativo"] = int(bool(data["ativo"]))
    if kwargs:
        db.update_regra(regra_id, **kwargs)
    return _ok(message="Regra atualizada.")


@app.route("/api/regras/<int:regra_id>", methods=["DELETE"])
@auth.require_auth
def delete_regra(regra_id):
    db.delete_regra(regra_id)
    return _ok(message="Regra removida.")


# ── Config ────────────────────────────────────────────────────────────────────

@app.route("/api/config")
@auth.require_auth
def get_config():
    return _ok(db.get_config())


@app.route("/api/config", methods=["POST"])
@auth.require_auth
def set_config():
    data = request.json or {}
    allowed = {"pasta_entrada", "pasta_saida", "idioma_ocr",
               "validar_cpf_cnpj", "renomear_arquivos",
               "exportar_sqlite", "ocr_engine", "monitorar_pasta"}
    cfg = {k: v for k, v in data.items() if k in allowed}
    db.set_config(cfg)
    full = db.get_config()
    if full.get("monitorar_pasta") == "1" and full.get("pasta_entrada"):
        worker.start_watchdog(full["pasta_entrada"])
    return _ok(message="Configurações salvas.")


# ── Instalação Tesseract ──────────────────────────────────────────────────────

@app.route("/api/install/tesseract", methods=["POST"])
@auth.require_auth
def install_tesseract():
    import shutil, subprocess, sys as _sys
    _tess_paths = ("/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract")
    if shutil.which("tesseract") or any(os.path.isfile(p) for p in _tess_paths):
        return _ok(message="Tesseract já está instalado.")
    if _sys.platform == "darwin":
        brew = (shutil.which("brew") or
                next((p for p in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew") if os.path.isfile(p)), None))
        if brew:
            try:
                r = subprocess.run([brew, "install", "tesseract"],
                                   capture_output=True, text=True, timeout=360)
                if r.returncode == 0:
                    worker.probe_tesseract()
                    return _ok(message="Tesseract instalado com sucesso! Atualizando status...")
                return _err(f"Falha na instalação:\n{(r.stderr or r.stdout)[:300]}")
            except subprocess.TimeoutExpired:
                return _err("Timeout (6 min). A instalação pode ter continuado em segundo plano — recarregue a página.")
            except Exception as e:
                return _err(str(e))
        # Homebrew não instalado — cria .command e abre com open (sempre funciona no macOS)
        import tempfile, stat
        script = (
            '#!/bin/bash\n'
            'echo "=== Instalando Homebrew + Tesseract ==="\n'
            '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"\n'
            'BREW=$(command -v brew || echo /opt/homebrew/bin/brew)\n'
            '$BREW install tesseract\n'
            'echo ""\n'
            'echo ">>> Concluido. Volte ao Tiresias e clique em Verificar status."\n'
            'read -p "Pressione Enter para fechar..."\n'
        )
        tmp = tempfile.NamedTemporaryFile(suffix=".command", delete=False, mode="w")
        tmp.write(script)
        tmp.flush()
        os.chmod(tmp.name, os.stat(tmp.name).st_mode | stat.S_IXUSR | stat.S_IXGRP)
        tmp.close()
        try:
            subprocess.Popen(["open", tmp.name])
            return _ok(message="Terminal aberto com o instalador. Siga as instruções e clique em 'Verificar status' ao concluir.")
        except Exception as e:
            return _err(f"Não foi possível abrir o Terminal: {e}")
    if _sys.platform == "win32":
        for mgr, cmd in [
            ("winget", ["winget", "install", "--id", "UB-Mannheim.TesseractOCR", "-e", "--silent", "--accept-package-agreements"]),
            ("choco",  ["choco",  "install",  "tesseract", "-y"]),
        ]:
            if shutil.which(mgr):
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=360)
                    if r.returncode == 0:
                        return _ok(message="Tesseract instalado com sucesso! Atualizando status...")
                    return _err(f"Falha ({mgr}):\n{(r.stderr or r.stdout)[:300]}")
                except subprocess.TimeoutExpired:
                    return _err("Timeout — recarregue a página após a instalação concluir.")
                except Exception as e:
                    return _err(str(e))
        return _err("winget e choco não encontrados. Instale manualmente: https://github.com/UB-Mannheim/tesseract/wiki")
    return _err(f"Instalação automática não suportada neste sistema ({_sys.platform}).")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    worker.start_worker()
    cfg = db.get_config()
    if cfg.get("monitorar_pasta") == "1" and cfg.get("pasta_entrada"):
        worker.start_watchdog(cfg["pasta_entrada"])
    logger.info("Tiresias iniciado na porta 5090")
    app.run(host="127.0.0.1", port=5090, debug=False, use_reloader=False)
