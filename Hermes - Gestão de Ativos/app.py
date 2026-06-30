from __future__ import annotations
"""
app.py — Hermes: Gestão de Ativos (porta 5050)
Autenticação delegada ao Atlas (http://localhost:5010).
"""
import json
import os
import sys
from datetime import datetime, timedelta
from functools import wraps

# pythonw sem console → stdout/stderr são None; protege contra crash
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

import database as db
import atlas_client as ac

ac.SISTEMA_FOLDER = "Hermes - Gestão de Ativos"

ATLAS_URL      = ac.ATLAS_URL
SISTEMA_FOLDER = ac.SISTEMA_FOLDER
PORT           = 5050

# Mapeamento RBAC → role local do Hermes
ROLE_MAP = {
    "ADMIN_GERAL": "admin",
    "ADMIN": "admin",
    "GESTOR": "gestor",
    "USER": "colaborador",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(BASE_DIR, "hermes.key")

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
app.permanent_session_lifetime = timedelta(hours=12)
CORS(app, supports_credentials=True)

if os.path.exists(KEY_FILE):
    with open(KEY_FILE, "rb") as f:
        app.secret_key = f.read()
else:
    key = os.urandom(32)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    app.secret_key = key


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ok(data=None, **kw):
    p = {"ok": True}
    if data is not None:
        p["data"] = data
    p.update(kw)
    return jsonify(p)


def _err(msg, code=400):
    return jsonify({"error": msg}), code


def current_user():
    uid = session.get("user_id")
    return db.get_user(uid) if uid else None


def require_auth(f):
    @wraps(f)
    def wrapped(*a, **kw):
        if not session.get("user_id"):
            return _err("Não autenticado.", 401)
        return f(*a, **kw)
    return wrapped


def require_role(*roles):
    def dec(f):
        @wraps(f)
        def wrapped(*a, **kw):
            u = current_user()
            if not u:
                return _err("Não autenticado.", 401)
            if u["role"] not in roles:
                return _err("Sem permissão.", 403)
            return f(*a, **kw)
        return wrapped
    return dec


# ── Atlas SSO ─────────────────────────────────────────────────────────────────

def _sync_atlas_user(atlas_user: dict) -> dict | None:
    """Sincroniza o usuário Atlas com o banco local do Hermes."""
    atlas_user["_role_sistema"] = ac.map_role_to_local(atlas_user, ROLE_MAP)
    return db.get_or_create_user_from_atlas(atlas_user)


def _sso_login(token: str):
    ac.sso_login_from_token(token, db_sync_fn=_sync_atlas_user)


# ── Atlas Sync ────────────────────────────────────────────────────────────────

def _atlas_sync(email: str, senha: str) -> dict:
    import urllib.request
    import http.cookiejar
    stats = {"departamentos": 0, "colaboradores": 0, "erros": []}
    if not ac._atlas_running():
        return stats
    cj     = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    body = json.dumps({"email": email, "senha": senha}).encode()
    req  = urllib.request.Request(
        f"{ATLAS_URL}/api/auth/login", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with opener.open(req, timeout=5) as resp:
            if not json.loads(resp.read()).get("ok"):
                return stats
    except Exception:
        return stats

    try:
        with opener.open(f"{ATLAS_URL}/api/empresas", timeout=5) as resp:
            for emp in json.loads(resp.read()).get("data", []):
                if emp.get("ativo", 1):
                    db.get_or_create_dept_from_atlas(emp["id"], emp["nome"])
                    stats["departamentos"] += 1
    except Exception as e:
        stats["erros"].append(f"empresas: {e}")

    try:
        with opener.open(f"{ATLAS_URL}/api/pessoas", timeout=5) as resp:
            for p in json.loads(resp.read()).get("data", []):
                if not p.get("ativo", True):
                    continue
                try:
                    funcoes = [f.strip() for f in (p.get("funcoes_nomes") or "").split(",") if f.strip()]
                    db.get_or_create_user_from_atlas({
                        "id": p.get("id"), "nome": p["nome"], "email": p["email"],
                        "cargo": p.get("cargo", ""), "funcoes": funcoes,
                        "empresa_id": p.get("empresa_id"), "empresa_nome": p.get("empresa_nome") or "",
                    })
                    stats["colaboradores"] += 1
                except Exception as e:
                    stats["erros"].append(f"{p.get('email','?')}: {e}")
    except Exception as e:
        stats["erros"].append(f"pessoas: {e}")

    return stats


# ── Static ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    token = request.args.get("atlas_token", "").strip()
    if token and not session.get("user_id"):
        _sso_login(token)
    return send_from_directory(BASE_DIR, "hermes.html")


@app.route("/api/ping")
def ping():
    return _ok({"ts": datetime.now().isoformat()})


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def login():
    d     = request.json or {}
    email = d.get("email", "").strip().lower()
    senha = d.get("senha", "")

    atlas_user = ac.login_with_credentials(email, senha, db_sync_fn=_sync_atlas_user)
    if atlas_user:
        u = current_user()
        if u:
            return _ok({"id": u["id"], "nome": u["nome"], "email": u["email"],
                        "role": u["role"], "cargo": u.get("cargo", "")})

    if not ac._atlas_running() and db.check_password(email, senha):
        u = db.get_user_by_email(email)
        session["user_id"] = u["id"]
        session.permanent  = True
        return _ok({"id": u["id"], "nome": u["nome"], "email": u["email"],
                    "role": u["role"], "cargo": u.get("cargo", "")})

    return _err("E-mail ou senha inválidos.", 401)


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return _ok()


@app.route("/api/auth/me")
def me():
    u = current_user()
    if not u:
        return _err("Não autenticado.", 401)
    return _ok({"id": u["id"], "nome": u["nome"], "email": u["email"],
                "role": u["role"], "role_atlas": ac.get_atlas_role(),
                "escopo": ac.get_atlas_escopo(),
                "cargo": u.get("cargo", ""),
                "departamento_id": u.get("departamento_id"),
                "departamento_nome": u.get("departamento_nome", "")})


# ── Atlas Sync ────────────────────────────────────────────────────────────────

@app.route("/api/atlas/sync", methods=["POST"])
@require_role("admin", "gestor")
def atlas_sync():
    d     = request.json or {}
    email = d.get("email", "").strip().lower()
    senha = d.get("senha", "")
    if not email or not senha:
        return _err("Informe e-mail e senha do Atlas.")
    if not ac._atlas_running():
        return _err("Atlas não está acessível em localhost:5010.")
    stats = _atlas_sync(email, senha)
    if stats["departamentos"] == 0 and stats["colaboradores"] == 0:
        return _err("Credenciais inválidas ou nenhum dado encontrado.")
    return _ok(stats)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
@require_auth
def dashboard():
    return _ok(db.get_dashboard())


# ── Ativos ────────────────────────────────────────────────────────────────────

@app.route("/api/ativos")
@require_auth
def list_ativos():
    return _ok(db.list_ativos(
        status=request.args.get("status"),
        categoria_id=int(request.args.get("categoria_id")) if request.args.get("categoria_id") else None,
        localizacao_id=int(request.args.get("localizacao_id")) if request.args.get("localizacao_id") else None,
        q_text=request.args.get("q"),
        limit=int(request.args.get("limit", 300)),
        offset=int(request.args.get("offset", 0)),
    ))


@app.route("/api/ativos/<int:aid>")
@require_auth
def get_ativo(aid):
    a = db.get_ativo(aid)
    if not a:
        return _err("Ativo não encontrado.", 404)
    return _ok(a)


@app.route("/api/ativos", methods=["POST"])
@require_role("admin", "gestor")
def create_ativo():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    new_id = db.create_ativo(d, current_user()["id"])
    return _ok({"id": new_id}), 201


@app.route("/api/ativos/<int:aid>", methods=["PUT"])
@require_role("admin", "gestor")
def update_ativo(aid):
    if not db.get_ativo(aid):
        return _err("Ativo não encontrado.", 404)
    db.update_ativo(aid, request.json or {})
    return _ok()


@app.route("/api/ativos/<int:aid>", methods=["DELETE"])
@require_role("admin")
def delete_ativo(aid):
    if not db.get_ativo(aid):
        return _err("Ativo não encontrado.", 404)
    db.delete_ativo(aid)
    return _ok()


# ── Movimentações ─────────────────────────────────────────────────────────────

@app.route("/api/movimentacoes")
@require_auth
def list_movimentacoes():
    ativo_id = request.args.get("ativo_id")
    return _ok(db.list_movimentacoes(
        ativo_id=int(ativo_id) if ativo_id else None,
        limit=int(request.args.get("limit", 100)),
    ))


@app.route("/api/movimentacoes", methods=["POST"])
@require_role("admin", "gestor")
def create_movimentacao():
    d = request.json or {}
    if not d.get("ativo_id"):
        return _err("ativo_id é obrigatório.")
    if not d.get("para_localizacao_id") and not d.get("para_responsavel_id"):
        return _err("Informe o destino (localização ou responsável).")
    new_id = db.create_movimentacao(d, current_user()["id"])
    return _ok({"id": new_id}), 201


# ── Manutenções ───────────────────────────────────────────────────────────────

@app.route("/api/manutencoes")
@require_auth
def list_manutencoes():
    return _ok(db.list_manutencoes(
        ativo_id=int(request.args.get("ativo_id")) if request.args.get("ativo_id") else None,
        status=request.args.get("status"),
    ))


@app.route("/api/manutencoes", methods=["POST"])
@require_auth
def create_manutencao():
    d = request.json or {}
    if not d.get("ativo_id"):
        return _err("ativo_id é obrigatório.")
    new_id = db.create_manutencao(d, current_user()["id"])
    return _ok({"id": new_id}), 201


@app.route("/api/manutencoes/<int:mid>", methods=["PUT"])
@require_role("admin", "gestor")
def update_manutencao(mid):
    if not db.get_manutencao(mid):
        return _err("Manutenção não encontrada.", 404)
    db.update_manutencao(mid, request.json or {})
    return _ok()


# ── Depreciação ───────────────────────────────────────────────────────────────

@app.route("/api/ativos/<int:aid>/depreciacao")
@require_auth
def get_depreciacao(aid):
    if not db.get_ativo(aid):
        return _err("Ativo não encontrado.", 404)
    rows = db.get_depreciacao(aid)
    if not rows:
        rows = db.calcular_depreciacao(aid)
    return _ok(rows)


@app.route("/api/ativos/<int:aid>/depreciacao/recalcular", methods=["POST"])
@require_role("admin", "gestor")
def recalcular_depreciacao(aid):
    if not db.get_ativo(aid):
        return _err("Ativo não encontrado.", 404)
    rows = db.calcular_depreciacao(aid)
    return _ok(rows)


# ── Categorias ────────────────────────────────────────────────────────────────

@app.route("/api/categorias")
@require_auth
def list_categorias():
    return _ok(db.list_categorias())


@app.route("/api/categorias", methods=["POST"])
@require_role("admin", "gestor")
def create_categoria():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    new_id = db.create_categoria(d)
    return _ok({"id": new_id}), 201


@app.route("/api/categorias/<int:cid>", methods=["PUT"])
@require_role("admin", "gestor")
def update_categoria(cid):
    if not db.get_categoria(cid):
        return _err("Categoria não encontrada.", 404)
    db.update_categoria(cid, request.json or {})
    return _ok()


# ── Localizações ──────────────────────────────────────────────────────────────

@app.route("/api/localizacoes")
@require_auth
def list_localizacoes():
    return _ok(db.list_localizacoes())


@app.route("/api/localizacoes", methods=["POST"])
@require_role("admin", "gestor")
def create_localizacao():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    new_id = db.create_localizacao(d)
    return _ok({"id": new_id}), 201


@app.route("/api/localizacoes/<int:lid>", methods=["PUT"])
@require_role("admin", "gestor")
def update_localizacao(lid):
    if not db.get_localizacao(lid):
        return _err("Localização não encontrada.", 404)
    db.update_localizacao(lid, request.json or {})
    return _ok()


# ── Usuários ──────────────────────────────────────────────────────────────────

@app.route("/api/users")
@require_role("admin", "gestor")
def list_users():
    return _ok(db.list_users())


@app.route("/api/users/<int:uid>", methods=["PUT"])
@require_role("admin")
def update_user(uid):
    db.update_user(uid, request.json or {})
    return _ok()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    print(f"\n  HERMES rodando em http://localhost:{PORT}\n")
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)
