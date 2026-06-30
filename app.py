from __future__ import annotations
"""
app.py — Olimpus Hub (porta 5100)
Autenticação via Atlas (porta 5010).
Exibe apenas os sistemas que o usuário tem permissão de ver.
"""
import json
import logging
import os
import socket
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import timedelta
from functools import wraps

# pythonw sem console → stdout/stderr são None; protege contra crash
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hub.log")
logging.basicConfig(level=logging.INFO,
    format='%(asctime)s [%(threadName)s] %(levelname)s %(message)s',
    handlers=[logging.FileHandler(_LOG_FILE, encoding="utf-8"),
              logging.StreamHandler()])

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

BASE           = os.path.dirname(os.path.abspath(__file__))
ATLAS_URL    = "http://localhost:5010"
ATLAS_PORT   = 5010

_CREATION_FLAGS = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0x08000000
_IS_WINDOWS = sys.platform == "win32"

app = Flask(__name__, static_folder=BASE, static_url_path="")
app.permanent_session_lifetime = timedelta(hours=12)
app.config['SESSION_COOKIE_NAME']     = 'olimpus_session'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE']   = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
CORS(app, supports_credentials=True)

# Chave de sessão persistente
_KEY_FILE = os.path.join(BASE, "olimpus.key")
if os.path.exists(_KEY_FILE):
    with open(_KEY_FILE, "rb") as f:
        app.secret_key = f.read()
else:
    _key = os.urandom(32)
    with open(_KEY_FILE, "wb") as f:
        f.write(_key)
    app.secret_key = _key


# ── Helpers ───────────────────────────────────────────────────────────────────

def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def _http_ready(port: int) -> bool:
    """Verifica se o servidor já responde HTTP (sem estado global — thread-safe)."""
    import http.client
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("GET", "/api/ping")
        resp = conn.getresponse()
        conn.close()
        return resp.status < 500
    except Exception:
        return False


def _atlas_running() -> bool:
    return _port_open(ATLAS_PORT)


def _find_launch_script(folder_path: str):
    """Returns path to the runnable launch script for the current OS, or None."""
    if not _IS_WINDOWS:
        for name in ("iniciar.command", "iniciar.sh"):
            p = os.path.join(folder_path, name)
            if os.path.isfile(p):
                return p
    bat = os.path.join(folder_path, "iniciar.bat")
    return bat if os.path.isfile(bat) else None


def _run_script(script_path: str, folder_path: str):
    if _IS_WINDOWS:
        subprocess.Popen(
            ["cmd", "/c", script_path],
            cwd=folder_path,
            creationflags=_CREATION_FLAGS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        subprocess.Popen(
            ["bash", script_path],
            cwd=folder_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _read_meta(folder_path: str) -> dict:
    meta_file = os.path.join(folder_path, "olimpus.json")
    if os.path.isfile(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _ok(data=None, **kw):
    p = {"ok": True}
    if data is not None:
        p["data"] = data
    p.update(kw)
    return jsonify(p)


def _err(msg, code=400):
    return jsonify({"error": msg}), code


def require_auth(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return _err("Não autenticado.", 401)
        return f(*args, **kwargs)
    return wrapped


# ── Static ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(BASE, "olimpus.html", max_age=0)


@app.route("/api/ping")
def ping():
    return jsonify({"ok": True})


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def login():
    d     = request.json or {}
    email = d.get("email", "").strip().lower()
    senha = d.get("senha", "")

    if not _atlas_running():
        return _err(
            "O Atlas (serviço de autenticação) não está no ar. "
            "Inicie-o antes de acessar o Olimpus.",
            503,
        )

    try:
        body = json.dumps({"email": email, "senha": senha}).encode()
        req  = urllib.request.Request(
            f"{ATLAS_URL}/api/auth/login",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            user = data.get("data", {})
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return _err("E-mail ou senha inválidos.", 401)
        return _err("Erro ao contactar o Atlas.", 502)
    except Exception:
        return _err("Não foi possível contactar o Atlas.", 502)

    session["authenticated"] = True
    session["user"] = {
        "id":         user.get("id"),
        "nome":       user.get("nome"),
        "email":      user.get("email"),
        "empresa_id": user.get("empresa_id"),
        "funcoes":    user.get("funcoes", []),
    }
    # Normaliza sistemas: o Atlas retorna [{folder, role_sistema}] ou None.
    # Guardamos a lista original e também um set de folders para checagem rápida.
    raw_sistemas = user.get("sistemas")
    session["sistemas"] = raw_sistemas
    if isinstance(raw_sistemas, list):
        session["sistemas_folders"] = [
            s["folder"] if isinstance(s, dict) else s for s in raw_sistemas
        ]
    else:
        session["sistemas_folders"] = None  # irrestrito
    session["atlas_token"] = user.get("token")   # token HMAC para SSO
    session.permanent = True
    return _ok({"nome": user.get("nome"), "email": user.get("email")})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return _ok()


@app.route("/api/auth/me")
def me():
    if not session.get("authenticated"):
        return _err("Não autenticado.", 401)
    return _ok(session.get("user"))


# ── Apps ──────────────────────────────────────────────────────────────────────

def _get_sistemas_folders():
    """
    Retorna lista de folders permitidos para o usuário logado.
    Lida com o formato antigo (lista de strings) e o novo (lista de dicts).
    Retorna None se irrestrito.
    """
    # Chave nova (gerada a partir da v2.0 do Atlas)
    if "sistemas_folders" in session:
        return session["sistemas_folders"]
    # Compatibilidade: sessão gerada por versão anterior
    raw = session.get("sistemas")
    if raw is None:
        return None
    if isinstance(raw, list):
        return [s["folder"] if isinstance(s, dict) else s for s in raw]
    return None


@app.route("/api/apps", methods=["GET"])
@require_auth
def list_apps():
    # sistemas_folders: None = irrestrito; list[str] = apenas esses folders
    sistemas_folders = _get_sistemas_folders()
    apps = []
    for entry in sorted(os.scandir(BASE), key=lambda e: e.name.lower()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name.startswith("_"):
            continue
        if entry.name.lower() in ("documentation", "tests"):
            continue
        folder_name = unicodedata.normalize("NFC", entry.name)
        script      = _find_launch_script(entry.path)
        # Apps sem script (Em Breve) sempre visíveis; disponíveis filtram por Atlas
        if script and isinstance(sistemas_folders, list) and folder_name not in sistemas_folders:
            continue
        meta = _read_meta(entry.path)
        apps.append({
            "folder":    folder_name,
            "available": script is not None,
            "name":      meta.get("name",  entry.name),
            "myth":      meta.get("myth",  ""),
            "cat":       meta.get("cat",   ""),
            "desc":      meta.get("desc",  ""),
            "color":     meta.get("color", "#2563eb"),
            "icon":      meta.get("icon",  "default"),
            "port":      meta.get("port",  None),
        })
    apps.sort(key=lambda a: (not a["available"], a["name"].lower()))
    return jsonify(apps)


@app.route("/api/launch/<path:folder>", methods=["POST"])
@require_auth
def launch(folder):
    folder_path = os.path.join(BASE, folder)

    if not os.path.abspath(folder_path).startswith(os.path.abspath(BASE)):
        return jsonify({"ok": False, "error": "Acesso negado"}), 403

    script = _find_launch_script(folder_path)
    if not script:
        return jsonify({"ok": False, "error": f"Script de inicialização não encontrado em '{folder}'"}), 404

    # Verifica acesso da sessão ao sistema solicitado
    sistemas_folders = _get_sistemas_folders()
    if isinstance(sistemas_folders, list) and folder not in sistemas_folders:
        return jsonify({"ok": False, "error": "Acesso a este sistema não autorizado."}), 403

    log = logging.getLogger("launch")
    log.info("START script=%s", script)
    try:
        _run_script(script, folder_path)
        log.info("Popen OK")
    except Exception as exc:
        log.exception("Popen FAILED: %s", exc)
        return jsonify({"ok": False, "error": f"Falha ao iniciar script: {exc}"}), 500

    meta  = _read_meta(folder_path)
    port  = meta.get("port")
    token = session.get("atlas_token")
    log.info("port=%s token=%s", port, bool(token))

    # Retorna imediatamente — o frontend faz polling em /api/ready/<port>
    if port:
        return jsonify({"ok": True, "port": int(port), "token": token})

    return jsonify({"ok": True})


@app.route("/api/ready/<int:port>")
@require_auth
def ready(port):
    """Verifica se o servidor na porta já responde HTTP (polling do frontend)."""
    if port < 1024 or port > 65535:
        return jsonify({"ok": False, "error": "Porta inválida"}), 400
    return jsonify({"ok": True, "ready": _http_ready(port)})


if __name__ == "__main__":
    port = 5100
    print(f"\n OLIMPUS rodando em http://localhost:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
