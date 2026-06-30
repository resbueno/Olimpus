from __future__ import annotations
"""
app.py — API REST Flask do Hércules (porta 5001)
Autenticação delegada ao Atlas (http://localhost:5010).
Fallback local caso o Atlas não esteja no ar.
"""
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

ac.SISTEMA_FOLDER = "Hércules - Gestão de Tarefas"

ROLE_MAP = {
    "ADMIN_GERAL": "admin",
    "ADMIN": "admin",
    "GESTOR": "gestor",
    "USER": "membro",
}


def _sync_atlas_user(atlas_user: dict):
    """Mapeia role Atlas → local e sincroniza usuário no banco."""
    atlas_user["_role_sistema"] = ac.map_role_to_local(atlas_user, ROLE_MAP)
    return db.get_or_create_user_from_atlas(atlas_user)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(BASE_DIR, "hercules.key")

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
app.permanent_session_lifetime = timedelta(hours=12)
CORS(app, supports_credentials=True)

# Chave persistente de sessão
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, "rb") as f:
        app.secret_key = f.read()
else:
    key = os.urandom(32)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    app.secret_key = key


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


def _ctx(u):
    """
    Retorna (empresa_id, departamento_id, user_id) para escopo de visibilidade.
    Usa escopo Atlas (GLOBAL/COMPANY/TEAM/SELF) quando disponível,
    com fallback para role local.
    """
    escopo = ac.get_atlas_escopo()
    if escopo in ("GLOBAL", "COMPANY"):
        emp = u.get("empresa_id")
        return (emp, None, None) if escopo == "COMPANY" else (None, None, None)
    if escopo == "TEAM":
        dept = u.get("departamento_id")
        return (None, dept, None) if dept else (None, None, None)
    # SELF ou fallback
    role = u.get("role", "membro")
    if role == "admin":
        emp = u.get("empresa_id")
        return (emp, None, None) if emp else (None, None, None)
    if role == "gestor":
        dept = u.get("departamento_id")
        return (None, dept, None) if dept else (None, None, None)
    return (None, None, u["id"])


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


# ── Static ────────────────────────────────────────────────────────────────────

def _sso_login(token: str):
    """Tenta criar sessão Hércules a partir de token Atlas (SSO)."""
    ac.sso_login_from_token(token, db_sync_fn=_sync_atlas_user)


@app.route("/")
def index():
    token = request.args.get("atlas_token", "").strip()
    if token and not session.get("user_id"):
        _sso_login(token)
    return send_from_directory(BASE_DIR, "hercules.html")


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
        u = _sync_atlas_user(atlas_user)
        session["user_id"] = u["id"]
        session.permanent  = True
        return _ok({"id": u["id"], "nome": u["nome"], "email": u["email"],
                    "role": u["role"], "role_atlas": ac.get_atlas_role(),
                    "escopo": ac.get_atlas_escopo()})

    # Fallback local — só funciona se Atlas não estiver no ar
    if not ac._atlas_running() and db.check_password(email, senha):
        u = db.get_user_by_email(email)
        session["user_id"] = u["id"]
        session.permanent  = True
        return _ok({"id": u["id"], "nome": u["nome"], "email": u["email"], "role": u["role"]})

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
    return _ok({
        "id": u["id"], "nome": u["nome"], "email": u["email"],
        "role": u["role"],
        "role_atlas": ac.get_atlas_role(),
        "escopo": ac.get_atlas_escopo(),
        "empresa_id": u.get("empresa_id"),
        "departamento_id": u.get("departamento_id"),
    })


@app.route("/api/auth/change-password", methods=["POST"])
@require_auth
def change_password():
    u = current_user()
    d = request.json or {}
    ok, msg = db.change_password(u["id"], d.get("atual", ""), d.get("nova", ""))
    return _ok(message=msg) if ok else _err(msg)


# ── Users ─────────────────────────────────────────────────────────────────────

@app.route("/api/users")
@require_auth
def list_users():
    return _ok(db.list_users())


@app.route("/api/users", methods=["POST"])
@require_role("admin")
def create_user():
    d = request.json or {}
    for f in ["nome", "email"]:
        if not d.get(f):
            return _err(f"Campo obrigatório: {f}")
    if db.get_user_by_email(d["email"]):
        return _err("E-mail já cadastrado.")
    # Senha não obrigatória — usuário deve logar via Atlas
    if not d.get("senha"):
        d["senha"] = ""  # db.create_user usará hash vazio
    new_id = db.create_user(d)
    return _ok({"id": new_id}), 201


@app.route("/api/users/<int:uid>", methods=["PUT"])
@require_role("admin")
def update_user(uid):
    if not db.get_user(uid):
        return _err("Usuário não encontrado.", 404)
    db.update_user(uid, request.json or {})
    return _ok()


@app.route("/api/users/<int:uid>", methods=["DELETE"])
@require_role("admin")
def delete_user(uid):
    u = current_user()
    if uid == u["id"]:
        return _err("Não é possível desativar seu próprio usuário.")
    db.delete_user(uid)
    return _ok()


# ── Projects ──────────────────────────────────────────────────────────────────

@app.route("/api/projects")
@require_auth
def list_projects():
    u = current_user()
    emp, dept, uid = _ctx(u)
    return _ok(db.list_projects(empresa_id=emp, departamento_id=dept, user_id=uid))


@app.route("/api/projects", methods=["POST"])
@require_role("admin", "gestor")
def create_project():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    u = current_user()
    emp, dept, _ = _ctx(u)
    new_id = db.create_project(d, u["id"], empresa_id=emp, departamento_id=dept)
    return _ok({"id": new_id}), 201


@app.route("/api/projects/<int:pid>", methods=["PUT"])
@require_role("admin", "gestor")
def update_project(pid):
    if not db.get_project(pid):
        return _err("Projeto não encontrado.", 404)
    db.update_project(pid, request.json or {})
    return _ok()


@app.route("/api/projects/<int:pid>", methods=["DELETE"])
@require_role("admin", "gestor")
def delete_project(pid):
    if not db.get_project(pid):
        return _err("Projeto não encontrado.", 404)
    db.delete_project(pid)
    return _ok()


# ── Tasks ─────────────────────────────────────────────────────────────────────

@app.route("/api/tasks")
@require_auth
def list_tasks():
    u = current_user()
    emp, dept, uid = _ctx(u)
    filters = {k: request.args.get(k) for k in ["projeto_id", "status", "prioridade", "responsavel_id"]}
    return _ok(db.list_tasks(filters, empresa_id=emp, departamento_id=dept, user_id=uid))


@app.route("/api/tasks/<int:tid>")
@require_auth
def get_task(tid):
    u = current_user()
    t = db.get_task(tid)
    if not t:
        return _err("Tarefa não encontrada.", 404)
    # Verifica visibilidade pelo escopo do usuário
    emp, dept, uid_scope = _ctx(u)
    if emp and t.get("empresa_id") != emp:
        return _err("Sem permissão.", 403)
    if dept:
        task_dept = t.get("departamento_id")
        resp_id = t.get("responsavel_id")
        if task_dept != dept:
            if resp_id:
                resp = db.get_user(resp_id)
                if not resp or resp.get("departamento_id") != dept:
                    return _err("Sem permissão.", 403)
            else:
                return _err("Sem permissão.", 403)
    if uid_scope is not None:
        if t.get("responsavel_id") != uid_scope and t.get("criado_por") != uid_scope:
            return _err("Sem permissão.", 403)
    t["comments"] = db.list_comments(tid)
    t["activities"] = db.list_activities(task_id=tid)
    return _ok(t)


@app.route("/api/tasks", methods=["POST"])
@require_auth
def create_task():
    d = request.json or {}
    if not d.get("titulo"):
        return _err("Título é obrigatório.")
    u = current_user()
    emp, dept, _ = _ctx(u)
    new_id = db.create_task(d, u["id"], empresa_id=emp, departamento_id=dept)
    db.add_activity("criou", f'Criou a tarefa "{d["titulo"]}"', new_id, u["id"])
    return _ok({"id": new_id}), 201


@app.route("/api/tasks/<int:tid>", methods=["PUT"])
@require_auth
def update_task(tid):
    u = current_user()
    t = db.get_task(tid)
    if not t:
        return _err("Tarefa não encontrada.", 404)
    # Verifica visibilidade antes de editar
    emp, dept, uid_scope = _ctx(u)
    if emp and t.get("empresa_id") != emp:
        return _err("Sem permissão.", 403)
    if dept:
        task_dept = t.get("departamento_id")
        resp_id = t.get("responsavel_id")
        if task_dept != dept:
            if resp_id:
                resp = db.get_user(resp_id)
                if not resp or resp.get("departamento_id") != dept:
                    return _err("Sem permissão.", 403)
            else:
                return _err("Sem permissão.", 403)
    if uid_scope is not None:
        if t.get("responsavel_id") != uid_scope and t.get("criado_por") != uid_scope:
            return _err("Sem permissão.", 403)
    d = request.json or {}
    if "status" in d and d["status"] != t["status"]:
        lbls = {"pendente": "Pendente", "em_andamento": "Em Andamento", "concluida": "Concluída"}
        db.add_activity(
            "status",
            f'Alterou status: "{lbls.get(t["status"], t["status"])}" → "{lbls.get(d["status"], d["status"])}"',
            tid, u["id"]
        )
    updated = db.update_task(tid, d)
    return _ok(updated)


@app.route("/api/tasks/<int:tid>", methods=["DELETE"])
@require_auth
def delete_task(tid):
    u = current_user()
    t = db.get_task(tid)
    if not t:
        return _err("Tarefa não encontrada.", 404)
    # Verifica visibilidade antes de excluir
    emp, dept, uid_scope = _ctx(u)
    if emp and t.get("empresa_id") != emp:
        return _err("Sem permissão.", 403)
    if dept:
        task_dept = t.get("departamento_id")
        resp_id = t.get("responsavel_id")
        if task_dept != dept:
            if resp_id:
                resp = db.get_user(resp_id)
                if not resp or resp.get("departamento_id") != dept:
                    return _err("Sem permissão.", 403)
            else:
                return _err("Sem permissão.", 403)
    if uid_scope is not None:
        if t.get("responsavel_id") != uid_scope and t.get("criado_por") != uid_scope:
            return _err("Sem permissão.", 403)
    db.delete_task(tid)
    return _ok()


# ── Comments ──────────────────────────────────────────────────────────────────

@app.route("/api/tasks/<int:tid>/comments")
@require_auth
def list_comments(tid):
    return _ok(db.list_comments(tid))


@app.route("/api/tasks/<int:tid>/comments", methods=["POST"])
@require_auth
def add_comment(tid):
    if not db.get_task(tid):
        return _err("Tarefa não encontrada.", 404)
    u = current_user()
    text = (request.json or {}).get("conteudo", "").strip()
    if not text:
        return _err("Comentário não pode ser vazio.")
    new_id = db.add_comment(tid, u["id"], text)
    db.add_activity("comentou", "Adicionou um comentário", tid, u["id"])
    return _ok({"id": new_id}), 201


@app.route("/api/comments/<int:cid>", methods=["DELETE"])
@require_auth
def delete_comment(cid):
    u = current_user()
    if not db.delete_comment(cid, u["id"], u["role"] == "admin"):
        return _err("Sem permissão para excluir este comentário.", 403)
    return _ok()


# ── Activities ────────────────────────────────────────────────────────────────

@app.route("/api/activities")
@require_auth
def list_activities():
    u = current_user()
    emp, dept, uid = _ctx(u)
    limit = int(request.args.get("limit", 50))
    return _ok(db.list_activities(limit=limit, empresa_id=emp, departamento_id=dept, user_id=uid))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
@require_auth
def dashboard():
    u = current_user()
    emp, dept, uid = _ctx(u)
    return _ok(db.get_dashboard_stats(empresa_id=emp, departamento_id=dept, user_id=uid))


if __name__ == "__main__":
    db.init_db()
    print("\n HÉRCULES rodando em http://localhost:5001\n")
    app.run(host="127.0.0.1", port=5001, debug=False, threaded=True)
