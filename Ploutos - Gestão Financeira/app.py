from __future__ import annotations
"""
app.py — Ploutos: Gestão Financeira (porta 5080)
Autenticação delegada ao Atlas (http://localhost:5010).
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from functools import wraps

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

import database as db
import atlas_client as ac

ac.SISTEMA_FOLDER = "Ploutos - Gestão Financeira"

ATLAS_URL      = ac.ATLAS_URL
SISTEMA_FOLDER = ac.SISTEMA_FOLDER
PORT           = 5080

ROLE_MAP = {
    "ADMIN_GERAL": "admin",
    "ADMIN": "admin",
    "GESTOR": "financeiro",
    "USER": "colaborador",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(BASE_DIR, "ploutos.key")

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
    atlas_user["_role_sistema"] = ac.map_role_to_local(atlas_user, ROLE_MAP)
    return db.get_or_create_user_from_atlas(atlas_user)


def _sso_login(token: str):
    ac.sso_login_from_token(token, db_sync_fn=_sync_atlas_user)


# ── Atlas Sync ────────────────────────────────────────────────────────────────

def _atlas_sync(email: str, senha: str) -> dict:
    stats = {"departamentos": 0, "colaboradores": 0, "erros": []}
    if not ac._atlas_running():
        return stats

    import http.cookiejar
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
            emp_data = json.loads(resp.read()).get("data", [])
        for emp in emp_data:
            if emp.get("ativo", 1):
                db.get_or_create_dept_from_atlas(emp["id"], emp["nome"])
                stats["departamentos"] += 1
    except Exception as e:
        stats["erros"].append(f"empresas: {e}")

    try:
        with opener.open(f"{ATLAS_URL}/api/pessoas", timeout=5) as resp:
            pess_data = json.loads(resp.read()).get("data", [])
        for p in pess_data:
            if not p.get("ativo", True):
                continue
            try:
                funcoes_raw = p.get("funcoes_nomes") or ""
                funcoes = [f.strip() for f in funcoes_raw.split(",") if f.strip()]
                atlas_user = {
                    "id":           p.get("id"),
                    "nome":         p["nome"],
                    "email":        p["email"],
                    "cargo":        p.get("cargo", ""),
                    "funcoes":      funcoes,
                    "empresa_id":   p.get("empresa_id"),
                    "empresa_nome": p.get("empresa_nome") or "",
                }
                db.get_or_create_user_from_atlas(atlas_user)
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
    return send_from_directory(BASE_DIR, "ploutos.html")


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

    # Fallback local
    local_u = db.get_user_by_email(email)
    if local_u and local_u.get("atlas_id") is None and db.check_password(email, senha):
        session["user_id"] = local_u["id"]
        session.permanent  = True
        return _ok({"id": local_u["id"], "nome": local_u["nome"], "email": local_u["email"],
                    "role": local_u["role"], "cargo": local_u.get("cargo", "")})

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
                "role": u["role"], "cargo": u.get("cargo", ""),
                "departamento_id": u.get("departamento_id"),
                "departamento_nome": u.get("departamento_nome", ""),
                "escopo": ac.get_atlas_escopo(),
                "role_atlas": ac.get_atlas_role()})


# ── Atlas Sync ────────────────────────────────────────────────────────────────

@app.route("/api/atlas/sync", methods=["POST"])
@require_role("admin", "financeiro")
def atlas_sync():
    d     = request.json or {}
    email = d.get("email", "").strip().lower()
    senha = d.get("senha", "")
    if not email or not senha:
        return _err("Informe e-mail e senha do Atlas para sincronizar.")
    if not ac._atlas_running():
        return _err("Atlas não está acessível em localhost:5010.")
    stats = _atlas_sync(email, senha)
    if stats["departamentos"] == 0 and stats["colaboradores"] == 0:
        return _err("Credenciais inválidas ou nenhum dado encontrado no Atlas.")
    return _ok(stats)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
@require_auth
def dashboard():
    hoje      = datetime.now().strftime("%Y-%m-%d")
    ano       = datetime.now().year
    mes       = datetime.now().month
    inicio_mes = f"{ano}-{str(mes).zfill(2)}-01"
    # Último dia do mês
    if mes == 12:
        fim_mes = f"{ano}-12-31"
    else:
        fim_mes = (datetime(ano, mes + 1, 1) - timedelta(days=1)).strftime("%Y-%m-%d")
    return _ok(db.get_dashboard(hoje, inicio_mes, fim_mes))


# ── Lançamentos ───────────────────────────────────────────────────────────────

@app.route("/api/lancamentos")
@require_auth
def list_lancamentos():
    tipo        = request.args.get("tipo")
    status      = request.args.get("status")
    cat_id      = request.args.get("categoria_id")
    data_inicio = request.args.get("data_inicio")
    data_fim    = request.args.get("data_fim")
    limit       = int(request.args.get("limit", 200))
    offset      = int(request.args.get("offset", 0))
    return _ok(db.list_lancamentos(
        tipo=tipo,
        status=status,
        categoria_id=int(cat_id) if cat_id else None,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit,
        offset=offset,
    ))


@app.route("/api/lancamentos/<int:lid>")
@require_auth
def get_lancamento(lid):
    l = db.get_lancamento(lid)
    if not l:
        return _err("Lançamento não encontrado.", 404)
    return _ok(l)


@app.route("/api/lancamentos", methods=["POST"])
@require_role("admin", "financeiro")
def create_lancamento():
    d = request.json or {}
    for f in ["descricao", "valor", "tipo", "data_vencimento"]:
        if not d.get(f) and d.get(f) != 0:
            return _err(f"Campo obrigatório: {f}")
    if d["tipo"] not in ("receita", "despesa"):
        return _err("tipo deve ser 'receita' ou 'despesa'.")
    try:
        float(d["valor"])
    except (ValueError, TypeError):
        return _err("valor deve ser numérico.")
    new_id = db.create_lancamento(d, current_user()["id"])
    return _ok({"id": new_id}), 201


@app.route("/api/lancamentos/<int:lid>", methods=["PUT"])
@require_role("admin", "financeiro")
def update_lancamento(lid):
    if not db.get_lancamento(lid):
        return _err("Lançamento não encontrado.", 404)
    db.update_lancamento(lid, request.json or {})
    return _ok()


@app.route("/api/lancamentos/<int:lid>", methods=["DELETE"])
@require_role("admin", "financeiro")
def delete_lancamento(lid):
    if not db.get_lancamento(lid):
        return _err("Lançamento não encontrado.", 404)
    db.delete_lancamento(lid)
    return _ok()


# ── Categorias ────────────────────────────────────────────────────────────────

@app.route("/api/categorias")
@require_auth
def list_categorias():
    tipo = request.args.get("tipo")
    return _ok(db.list_categorias(tipo=tipo))


@app.route("/api/categorias", methods=["POST"])
@require_role("admin", "financeiro")
def create_categoria():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    if d.get("tipo") not in ("receita", "despesa"):
        return _err("tipo deve ser 'receita' ou 'despesa'.")
    new_id = db.create_categoria(d)
    return _ok({"id": new_id}), 201


@app.route("/api/categorias/<int:cid>", methods=["PUT"])
@require_role("admin", "financeiro")
def update_categoria(cid):
    if not db.get_categoria(cid):
        return _err("Categoria não encontrada.", 404)
    db.update_categoria(cid, request.json or {})
    return _ok()


@app.route("/api/categorias/<int:cid>", methods=["DELETE"])
@require_role("admin")
def delete_categoria(cid):
    db.delete_categoria(cid)
    return _ok()


# ── Centro de Custos ──────────────────────────────────────────────────────────

@app.route("/api/centro-custos")
@require_auth
def list_centro_custos():
    return _ok(db.list_centro_custos())


@app.route("/api/centro-custos", methods=["POST"])
@require_role("admin", "financeiro")
def create_centro_custo():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    new_id = db.create_centro_custo(d)
    return _ok({"id": new_id}), 201


@app.route("/api/centro-custos/<int:cid>", methods=["PUT"])
@require_role("admin", "financeiro")
def update_centro_custo(cid):
    if not db.get_centro_custo(cid):
        return _err("Centro de custo não encontrado.", 404)
    db.update_centro_custo(cid, request.json or {})
    return _ok()


@app.route("/api/centro-custos/<int:cid>", methods=["DELETE"])
@require_role("admin")
def delete_centro_custo(cid):
    db.delete_centro_custo(cid)
    return _ok()


# ── Orçamentos ────────────────────────────────────────────────────────────────

@app.route("/api/orcamentos")
@require_auth
def list_orcamentos():
    ano = int(request.args.get("ano", datetime.now().year))
    mes = int(request.args.get("mes", datetime.now().month))
    return _ok(db.list_orcamentos(ano, mes))


@app.route("/api/orcamentos", methods=["POST"])
@require_role("admin", "financeiro")
def upsert_orcamento():
    d = request.json or {}
    for f in ["ano", "mes", "categoria_id", "valor"]:
        if d.get(f) is None:
            return _err(f"Campo obrigatório: {f}")
    db.upsert_orcamento(int(d["ano"]), int(d["mes"]),
                        int(d["categoria_id"]), float(d["valor"]))
    return _ok()


# ── Fluxo de Caixa ────────────────────────────────────────────────────────────

@app.route("/api/fluxo-caixa")
@require_auth
def fluxo_caixa():
    ano = int(request.args.get("ano", datetime.now().year))
    return _ok(db.get_fluxo_caixa(ano))


# ── Orçamento vs Realizado ────────────────────────────────────────────────────

@app.route("/api/orcamento-realizado")
@require_auth
def orcamento_realizado():
    ano = int(request.args.get("ano", datetime.now().year))
    mes = int(request.args.get("mes", datetime.now().month))
    return _ok(db.get_orcamento_realizado(ano, mes))


# ── Departamentos ─────────────────────────────────────────────────────────────

@app.route("/api/departments")
@require_auth
def list_departments():
    return _ok(db.list_departamentos())


@app.route("/api/departments", methods=["POST"])
@require_role("admin")
def create_department():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    new_id = db.create_departamento(d)
    return _ok({"id": new_id}), 201


@app.route("/api/departments/<int:did>", methods=["PUT"])
@require_role("admin")
def update_department(did):
    if not db.get_departamento(did):
        return _err("Departamento não encontrado.", 404)
    db.update_departamento(did, request.json or {})
    return _ok()


@app.route("/api/departments/<int:did>", methods=["DELETE"])
@require_role("admin")
def delete_department(did):
    db.delete_departamento(did)
    return _ok()


# ── Usuários ──────────────────────────────────────────────────────────────────

@app.route("/api/users")
@require_role("admin", "financeiro")
def list_users():
    dept = request.args.get("departamento_id")
    return _ok(db.list_users(departamento_id=int(dept) if dept else None))


@app.route("/api/users/<int:uid>", methods=["PUT"])
@require_role("admin")
def update_user(uid):
    db.update_user(uid, request.json or {})
    return _ok()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    print(f"\n  PLOUTOS rodando em http://localhost:{PORT}\n")
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)
