from __future__ import annotations
"""
app.py — Atlas: Gestão de Acessos / IAM (porta 5010)
Versão 4.0 — DDD / RBAC

Modelo de acesso:
  - Roles: USER, GESTOR, ADMIN, ADMIN_GERAL
  - Escopo: SELF, TEAM, COMPANY, GLOBAL
  - Permissões granulares por sistema
  - Multi-tenant com isolamento por empresa_id
"""
import io
import json
import os
import sys
from datetime import timedelta
from functools import wraps

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

try:
    import openpyxl
    _XLSX_OK = True
except ImportError:
    _XLSX_OK = False

import database as db
import token_utils as tu

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OLIMPUS_DIR = os.path.dirname(BASE_DIR)
ATLAS_FOLDER = "Atlas - Gestão de Acessos"

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
app.permanent_session_lifetime = timedelta(hours=12)
CORS(app, supports_credentials=True)


def _load_secret():
    return tu._get_key()[:32]


app.secret_key = _load_secret()


def _ok(data=None, **kw):
    p = {"ok": True}
    if data is not None:
        p["data"] = data
    p.update(kw)
    return jsonify(p)


def _err(msg, code=400):
    return jsonify({"error": msg}), code


def _ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr)


# ── Auth helpers ─────────────────────────────────────────────────────────────

def current_user():
    uid = session.get("pessoa_id")
    return db.get_pessoa(uid) if uid else None


def _max_role_nivel(user):
    """Retorna o nível máximo de role do usuário."""
    roles = user.get("roles") or []
    if not roles:
        return -1
    return max(r.get("role_nivel", 0) for r in roles)


def _is_admin_geral(user=None):
    """Verifica se o usuário é ADMIN_GERAL (nível 3 — acesso global)."""
    if user is None:
        user = current_user()
    if not user:
        return False
    return any(r.get("role_nome") == "ADMIN_GERAL" for r in (user.get("roles") or []))


def _is_admin(user=None):
    """Verifica se o usuário é ADMIN ou ADMIN_GERAL."""
    if user is None:
        user = current_user()
    if not user:
        return False
    return _max_role_nivel(user) >= 2  # ADMIN=2, ADMIN_GERAL=3


def _is_gestor(user=None):
    """Verifica se o usuário é pelo menos GESTOR."""
    if user is None:
        user = current_user()
    if not user:
        return False
    return _max_role_nivel(user) >= 1


def require_auth(f):
    @wraps(f)
    def wrapped(*a, **kw):
        if not session.get("pessoa_id"):
            return _err("Não autenticado.", 401)
        return f(*a, **kw)
    return wrapped


def require_admin(f):
    @wraps(f)
    def wrapped(*a, **kw):
        u = current_user()
        if not u:
            return _err("Não autenticado.", 401)
        if not _is_admin(u):
            return _err("Apenas administradores.", 403)
        return f(*a, **kw)
    return wrapped


def require_admin_geral(f):
    @wraps(f)
    def wrapped(*a, **kw):
        u = current_user()
        if not u:
            return _err("Não autenticado.", 401)
        if not _is_admin_geral(u):
            return _err("Apenas Admin Geral.", 403)
        return f(*a, **kw)
    return wrapped


def _audit(acao, entidade=None, entidade_id=None, detalhe=None, user=None):
    """Helper para auditoria com empresa_id automático."""
    if user is None:
        user = current_user()
    db.add_audit(
        acao, entidade, entidade_id, detalhe,
        pessoa_id=user["id"] if user else None,
        ip=_ip(),
        empresa_id=user.get("empresa_id") if user else None,
    )


# ── Static ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "atlas.html")


@app.route("/api/ping")
def api_ping():
    from datetime import datetime
    return jsonify({"ok": True, "ts": datetime.now().isoformat()})


@app.route("/login")
def login_page():
    return send_from_directory(BASE_DIR, "atlas.html")


# ── Auth ─────────────────────────────────────────────────────────────────────

def _build_user_response(p, include_token=False):
    """Monta o payload de resposta do usuário."""
    roles = p.get("roles") or []
    funcoes_legadas = db._roles_to_funcoes(roles)
    sistemas = db.get_sistemas_permitidos(p["id"])

    # Roles por sistema (para o token)
    roles_por_sistema = {}
    for r in roles:
        roles_por_sistema[r["sistema_folder"]] = {
            "role": r["role_nome"],
            "escopo": r["escopo"],
        }

    resp = {
        "id":                p["id"],
        "nome":              p["nome"],
        "email":             p["email"],
        "cargo":             p.get("cargo") or "",
        "telefone":          p.get("telefone") or "",
        "departamento_id":   p.get("departamento_id"),
        "departamento_nome": p.get("departamento_nome") or "",
        "empresa_id":        p.get("empresa_id"),
        "empresa_nome":      p.get("empresa_nome"),
        "funcoes":           funcoes_legadas,
        "roles":             roles,
        "sistemas":          sistemas,
        "trocar_senha":      bool(p.get("trocar_senha")),
    }

    if include_token:
        token = tu.create_token({
            "sub":        p["id"],
            "email":      p["email"],
            "nome":       p["nome"],
            "cargo":      p.get("cargo") or "",
            "empresa_id": p.get("empresa_id"),
            "funcoes":    funcoes_legadas,
            "roles":      roles_por_sistema,
            "sistemas":   sistemas,
        })
        resp["token"] = token

    return resp


@app.route("/api/auth/login", methods=["POST"])
def login():
    d = request.json or {}
    email = d.get("email", "").strip().lower()
    senha = d.get("senha", "")
    if not db.check_password(email, senha):
        return _err("E-mail ou senha inválidos.", 401)
    p = db.get_pessoa_by_email(email)
    session["pessoa_id"] = p["id"]
    session.permanent = True
    _audit("login", "pessoa", p["id"], "Login realizado", p)
    return _ok(_build_user_response(p, include_token=True))


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    u = current_user()
    if u:
        _audit("logout", "pessoa", u["id"], "Logout", u)
    session.clear()
    return _ok()


@app.route("/api/auth/me")
@require_auth
def me():
    p = current_user()
    resp = _build_user_response(p)
    resp["salario"] = p.get("salario", 0) or 0
    return _ok(resp)


@app.route("/api/auth/sso", methods=["POST"])
def sso_login():
    d = request.json or {}
    token = d.get("token", "")
    payload = tu.validate_token(token)
    if not payload:
        return _err("Token inválido ou expirado.", 401)
    p = db.get_pessoa(payload.get("sub"))
    if not p or not p.get("ativo"):
        return _err("Usuário não encontrado ou inativo.", 401)
    session["pessoa_id"] = p["id"]
    session.permanent = True
    return _ok({
        "id":           p["id"],
        "nome":         p["nome"],
        "email":        p["email"],
        "empresa_id":   p.get("empresa_id"),
        "empresa_nome": p.get("empresa_nome"),
        "funcoes":      db._roles_to_funcoes(p.get("roles") or []),
        "roles":        p.get("roles") or [],
    })


@app.route("/api/auth/validate")
def validate():
    token = (request.args.get("token") or
             request.headers.get("X-Atlas-Token") or
             (request.json or {}).get("token", ""))
    payload = tu.validate_token(token)
    if not payload:
        return _err("Token inválido ou expirado.", 401)
    return _ok(payload)


@app.route("/api/auth/change-password", methods=["POST"])
@require_auth
def change_password():
    u = current_user()
    d = request.json or {}
    ok, msg = db.change_password(u["id"], d.get("atual", ""), d.get("nova", ""))
    if ok:
        _audit("change_password", "pessoa", u["id"], "Senha alterada", u)
    return _ok(message=msg) if ok else _err(msg)


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
@require_auth
def dashboard():
    u = current_user()
    empresa_id = None if _is_admin_geral(u) else u.get("empresa_id")
    return _ok(db.get_dashboard(empresa_id=empresa_id))


# ── Departamentos ────────────────────────────────────────────────────────────

@app.route("/api/departamentos")
@require_auth
def list_departamentos():
    u = current_user()
    empresa_id = request.args.get("empresa_id")
    if empresa_id:
        empresa_id = int(empresa_id)
    elif not _is_admin_geral(u):
        empresa_id = u.get("empresa_id")
    return _ok(db.list_departamentos(empresa_id=empresa_id))


@app.route("/api/departamentos", methods=["POST"])
@require_admin
def create_departamento():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    new_id = db.create_departamento(d)
    u = current_user()
    _audit("criar", "departamento", new_id, f"Departamento '{d['nome']}' criado", u)
    return _ok({"id": new_id}), 201


@app.route("/api/departamentos/<int:did>")
@require_auth
def get_departamento(did):
    dep = db.get_departamento(did)
    if not dep:
        return _err("Departamento não encontrado.", 404)
    return _ok(dep)


@app.route("/api/departamentos/<int:did>", methods=["PUT"])
@require_admin
def update_departamento(did):
    if not db.get_departamento(did):
        return _err("Departamento não encontrado.", 404)
    d = request.json or {}
    db.update_departamento(did, d)
    u = current_user()
    _audit("editar", "departamento", did, "Departamento atualizado", u)
    return _ok()


@app.route("/api/departamentos/<int:did>", methods=["DELETE"])
@require_admin
def delete_departamento(did):
    if not db.get_departamento(did):
        return _err("Departamento não encontrado.", 404)
    db.delete_departamento(did)
    u = current_user()
    _audit("excluir", "departamento", did, "Departamento excluído", u)
    return _ok()


# ── Empresas ─────────────────────────────────────────────────────────────────

@app.route("/api/empresas")
@require_auth
def list_empresas():
    u = current_user()
    ativo = request.args.get("ativo") == "1"
    if _is_admin_geral(u):
        return _ok(db.list_empresas(ativo_only=ativo))
    if u.get("empresa_id"):
        e = db.get_empresa(u["empresa_id"])
        if e:
            e["total_pessoas"] = len(db.list_pessoas(empresa_id=e["id"]))
            return _ok([e])
    return _ok([])


@app.route("/api/empresas", methods=["POST"])
@require_admin_geral
def create_empresa():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    new_id = db.create_empresa(d)
    u = current_user()
    _audit("criar", "empresa", new_id, f"Empresa '{d['nome']}' criada", u)
    return _ok({"id": new_id}), 201


@app.route("/api/empresas/<int:eid>")
@require_auth
def get_empresa(eid):
    u = current_user()
    if not _is_admin_geral(u) and u.get("empresa_id") != eid:
        return _err("Acesso negado.", 403)
    e = db.get_empresa(eid)
    if not e:
        return _err("Empresa não encontrada.", 404)
    return _ok(e)


@app.route("/api/empresas/<int:eid>", methods=["PUT"])
@require_admin
def update_empresa(eid):
    u = current_user()
    if not _is_admin_geral(u) and u.get("empresa_id") != eid:
        return _err("Acesso negado.", 403)
    if not db.get_empresa(eid):
        return _err("Empresa não encontrada.", 404)
    d = request.json or {}
    db.update_empresa(eid, d)
    _audit("editar", "empresa", eid, "Empresa atualizada", u)
    return _ok()


@app.route("/api/empresas/<int:eid>", methods=["DELETE"])
@require_admin_geral
def delete_empresa(eid):
    if not db.get_empresa(eid):
        return _err("Empresa não encontrada.", 404)
    db.delete_empresa(eid)
    u = current_user()
    _audit("desativar", "empresa", eid, "Empresa desativada", u)
    return _ok()


# ── Pessoas ──────────────────────────────────────────────────────────────────

@app.route("/api/pessoas")
@require_auth
def list_pessoas():
    u = current_user()
    ativo = request.args.get("ativo", "1") == "1"
    emp_id = request.args.get("empresa_id")
    dept_id = request.args.get("departamento_id")

    if emp_id:
        emp_id = int(emp_id)
    elif not _is_admin_geral(u):
        emp_id = u.get("empresa_id")

    pessoas = db.list_pessoas(
        ativo_only=ativo,
        empresa_id=emp_id,
        departamento_id=int(dept_id) if dept_id else None,
    )
    return _ok(pessoas)


@app.route("/api/pessoas", methods=["POST"])
@require_admin
def create_pessoa():
    d = request.json or {}
    for f in ["nome", "email", "senha"]:
        if not d.get(f):
            return _err(f"Campo obrigatório: {f}")
    if db.get_pessoa_by_email(d["email"]):
        return _err("E-mail já cadastrado.")
    u = current_user()
    d["criado_por"] = u["id"]
    new_id = db.create_pessoa(d)
    _audit("criar", "pessoa", new_id, f"Pessoa '{d['nome']}' criada", u)
    return _ok({"id": new_id}), 201


@app.route("/api/pessoas/importar", methods=["POST"])
@require_admin
def importar_pessoas():
    if not _XLSX_OK:
        return _err("openpyxl não instalado. Execute: pip install openpyxl", 500)

    file = request.files.get("arquivo")
    if not file or not file.filename.lower().endswith((".xlsx", ".xls")):
        return _err("Envie um arquivo .xlsx válido.")

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file.read()), read_only=True, data_only=True)
        ws = wb.active
        rows_raw = list(ws.iter_rows(values_only=True))
    except Exception as e:
        return _err(f"Erro ao ler o arquivo: {e}")

    if not rows_raw:
        return _err("Planilha vazia.")

    header = [str(c).strip().lower() if c else "" for c in rows_raw[0]]
    COL_MAP = {
        "nome":    ["nome", "name"],
        "email":   ["email", "e-mail"],
        "cargo":   ["cargo", "função", "funcao", "position"],
        "empresa": ["empresa", "company"],
        "role":    ["role", "perfil", "papel", "funcao_atlas", "funcao atlas"],
    }

    def col(key):
        for alias in COL_MAP[key]:
            if alias in header:
                return header.index(alias)
        return None

    idx = {k: col(k) for k in COL_MAP}
    if idx["nome"] is None or idx["email"] is None:
        return _err("A planilha precisa ter colunas 'Nome' e 'Email'.")

    empresas = {e["nome"].lower(): e["id"] for e in db.list_empresas()}
    roles = {r["nome"].lower(): r["id"] for r in db.list_roles()}

    rows = []
    for raw in rows_raw[1:]:
        def cell(i):
            return str(raw[i]).strip() if i is not None and i < len(raw) and raw[i] is not None else ""

        nome = cell(idx["nome"])
        email = cell(idx["email"]).lower()
        if not nome or not email:
            continue

        cargo = cell(idx["cargo"])
        empresa_nm = cell(idx["empresa"]).lower()
        role_nm = cell(idx["role"]).lower()

        empresa_id = empresas.get(empresa_nm) if empresa_nm else None
        role_id = roles.get(role_nm) if role_nm else None

        rows.append({
            "nome":       nome,
            "email":      email,
            "cargo":      cargo,
            "empresa_id": empresa_id,
            "role_id":    role_id,
        })

    if not rows:
        return _err("Nenhuma linha válida encontrada na planilha.")

    u = current_user()
    result = db.bulk_import_pessoas(rows, criado_por=u["id"])
    _audit("importar", "pessoa", None,
           f"{result['criados']} criados, {result['ignorados']} ignorados via Excel", u)
    return _ok(result)


@app.route("/api/pessoas/<int:pid>")
@require_auth
def get_pessoa(pid):
    u = current_user()
    p = db.get_pessoa(pid)
    if not p:
        return _err("Pessoa não encontrada.", 404)
    if not _is_admin_geral(u) and p.get("empresa_id") != u.get("empresa_id"):
        return _err("Acesso negado.", 403)
    p.pop("senha_hash", None)
    return _ok(p)


@app.route("/api/pessoas/<int:pid>/sistemas")
@require_auth
def get_pessoa_sistemas(pid):
    if not db.get_pessoa(pid):
        return _err("Pessoa não encontrada.", 404)
    sistemas = db.get_sistemas_permitidos(pid)
    return _ok(sistemas)


@app.route("/api/pessoas/<int:pid>/roles")
@require_auth
def get_pessoa_roles(pid):
    """Retorna as roles atribuídas a uma pessoa."""
    if not db.get_pessoa(pid):
        return _err("Pessoa não encontrada.", 404)
    sf = request.args.get("sistema_folder")
    roles = db.get_usuario_roles(pid, sistema_folder=sf)
    return _ok(roles)


@app.route("/api/pessoas/<int:pid>/roles", methods=["POST"])
@require_admin
def set_pessoa_role(pid):
    """Define a role de uma pessoa para um sistema."""
    if not db.get_pessoa(pid):
        return _err("Pessoa não encontrada.", 404)
    d = request.json or {}
    sf = d.get("sistema_folder", "").strip()
    role_id = d.get("role_id")
    escopo = d.get("escopo", "SELF").upper()
    if not sf:
        return _err("sistema_folder é obrigatório.")
    if not role_id:
        return _err("role_id é obrigatório.")
    if escopo not in db.ESCOPOS:
        return _err(f"Escopo inválido. Use: {', '.join(db.ESCOPOS)}")

    u = current_user()

    # Regra: Gestor não cria outro gestor
    role = db.get_role(role_id)
    if role and role["nivel"] >= 1 and not _is_admin(u):
        return _err("Apenas administradores podem atribuir roles de gestor ou superior.", 403)

    # Regra: Usuário nunca altera próprio papel
    if pid == u["id"] and not _is_admin_geral(u):
        return _err("Não é possível alterar seu próprio papel.", 403)

    db.set_usuario_role(pid, int(role_id), sf, escopo=escopo, criado_por=u["id"])
    role_nome = role["nome"] if role else "?"
    _audit("atribuir_role", "usuario_role", pid,
           f"Role {role_nome} ({escopo}) → sistema {sf}", u)
    return _ok()


@app.route("/api/pessoas/<int:pid>/roles", methods=["DELETE"])
@require_admin
def delete_pessoa_role(pid):
    """Remove a role de uma pessoa para um sistema."""
    sf = request.args.get("sistema_folder") or (request.json or {}).get("sistema_folder", "")
    if not sf:
        return _err("sistema_folder é obrigatório.")
    if sf == ATLAS_FOLDER:
        return _err("Não é possível remover acesso ao Atlas.", 403)
    u = current_user()
    db.delete_usuario_role(pid, sf)
    _audit("remover_role", "usuario_role", pid, f"Role removida do sistema {sf}", u)
    return _ok()


@app.route("/api/pessoas/<int:pid>", methods=["PUT"])
@require_admin
def update_pessoa(pid):
    if not db.get_pessoa(pid):
        return _err("Pessoa não encontrada.", 404)
    d = request.json or {}
    db.update_pessoa(pid, d)
    u = current_user()
    _audit("editar", "pessoa", pid, "Pessoa atualizada", u)
    return _ok()


@app.route("/api/pessoas/<int:pid>", methods=["DELETE"])
@require_admin
def delete_pessoa(pid):
    u = current_user()
    if pid == u["id"]:
        return _err("Não é possível desativar seu próprio usuário.")
    if not db.get_pessoa(pid):
        return _err("Pessoa não encontrada.", 404)
    db.delete_pessoa(pid)
    _audit("desativar", "pessoa", pid, "Pessoa desativada", u)
    return _ok()


# ── Sistemas ─────────────────────────────────────────────────────────────────

@app.route("/api/sistemas")
@require_auth
def list_sistemas():
    return _ok(db.list_sistemas())


@app.route("/api/sistemas/sync", methods=["POST"])
@require_admin
def sync_sistemas():
    apps = []
    try:
        for entry in os.scandir(OLIMPUS_DIR):
            if not entry.is_dir():
                continue
            if entry.name.startswith(".") or entry.name.startswith("_"):
                continue
            meta_file = os.path.join(entry.path, "olimpus.json")
            nome = entry.name
            if os.path.isfile(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    nome = meta.get("name", entry.name)
                except Exception:
                    pass
            apps.append({"folder": entry.name, "name": nome})
        db.sync_sistemas(apps)
        u = current_user()
        _audit("sync", "sistemas", None, f"{len(apps)} sistemas sincronizados", u)
        return _ok({"sincronizados": len(apps)})
    except Exception as e:
        return _err(f"Erro ao sincronizar: {str(e)}")


# ── Roles ────────────────────────────────────────────────────────────────────

@app.route("/api/roles")
@require_auth
def list_roles():
    return _ok(db.list_roles())


@app.route("/api/roles/<int:rid>")
@require_auth
def get_role(rid):
    r = db.get_role(rid)
    if not r:
        return _err("Role não encontrada.", 404)
    r["permissoes"] = db.get_role_permissoes(rid)
    return _ok(r)


@app.route("/api/roles", methods=["POST"])
@require_admin_geral
def create_role():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    new_id = db.create_role(d)
    u = current_user()
    _audit("criar", "role", new_id, f"Role '{d['nome']}' criada", u)
    return _ok({"id": new_id}), 201


@app.route("/api/roles/<int:rid>", methods=["PUT"])
@require_admin_geral
def update_role(rid):
    if not db.get_role(rid):
        return _err("Role não encontrada.", 404)
    d = request.json or {}
    db.update_role(rid, d)
    u = current_user()
    _audit("editar", "role", rid, "Role atualizada", u)
    return _ok()


# ── Permissões ───────────────────────────────────────────────────────────────

@app.route("/api/permissoes")
@require_auth
def list_permissoes():
    return _ok(db.list_permissoes())


@app.route("/api/permissoes/disponiveis")
@require_auth
def list_permissoes_disponiveis():
    return _ok(db.PERMISSOES_DISPONIVEIS)


# ── Role ↔ Permissões por sistema ────────────────────────────────────────────

@app.route("/api/role-permissoes/<int:role_id>")
@require_auth
def get_role_permissoes(role_id):
    """Retorna as permissões de uma role, opcionalmente filtrado por sistema."""
    if not db.get_role(role_id):
        return _err("Role não encontrada.", 404)
    sf = request.args.get("sistema_folder")
    perms = db.get_role_permissoes(role_id, sistema_folder=sf)
    return _ok(perms)


@app.route("/api/role-permissoes/<int:role_id>", methods=["POST"])
@require_admin_geral
def set_role_permissoes(role_id):
    """Define as permissões de uma role para um sistema.
    Body: {sistema_folder: "...", permissoes: ["visualizar", "criar", ...]}
    """
    if not db.get_role(role_id):
        return _err("Role não encontrada.", 404)
    d = request.json or {}
    sf = d.get("sistema_folder", "").strip()
    perms = d.get("permissoes", [])
    if not sf:
        return _err("sistema_folder é obrigatório.")
    db.set_role_permissoes(role_id, sf, perms)
    u = current_user()
    _audit("editar", "role_permissoes", role_id,
           f"Permissões da role atualizadas para {sf}: {', '.join(perms)}", u)
    return _ok()


# ── Resolução de Acesso ─────────────────────────────────────────────────────

@app.route("/api/acessos/resolve/<int:pessoa_id>/<path:sistema_folder>")
@require_auth
def resolve_acesso(pessoa_id, sistema_folder):
    result = db.resolve_acesso_completo(pessoa_id, sistema_folder)
    return _ok(result)


@app.route("/api/acessos/matriz/empresa/<int:eid>")
@require_auth
def matriz_empresa(eid):
    return _ok(db.get_matriz_empresa(eid))


@app.route("/api/acessos/matriz/pessoa/<int:pid>")
@require_auth
def matriz_pessoa(pid):
    return _ok(db.get_matriz_pessoa(pid))


@app.route("/api/acessos/usuario-roles")
@require_auth
def list_usuario_roles_por_sistema():
    """Lista vínculos usuário-role para um sistema."""
    sf = request.args.get("sistema_folder")
    empresa_id = request.args.get("empresa_id")
    if not sf:
        return _err("sistema_folder é obrigatório.")
    return _ok(db.list_usuario_roles_por_sistema(
        sf, empresa_id=int(empresa_id) if empresa_id else None,
    ))


# ── Escopos (referência) ────────────────────────────────────────────────────

@app.route("/api/escopos")
@require_auth
def list_escopos():
    return _ok(db.ESCOPOS)


# ── Compatibilidade: Tipos de Acesso (aliases para Roles) ───────────────

@app.route("/api/tipos-acesso")
@require_auth
def list_tipos_acesso():
    """Alias para /api/roles (compatibilidade)."""
    roles = db.list_roles()
    result = []
    for r in roles:
        role_nome = r.pop("role_nome", r.get("nome"))
        total = db.count_usuarios_com_role(r["id"])
        result.append({
            "id": r["id"],
            "nome": role_nome,
            "descricao": r.get("descricao", ""),
            "permissoes": r.get("permissoes", {}),
            "nivel": r.get("nivel", 0),
            "total_usuarios": total,
        })
    return _ok(result)


@app.route("/api/tipos-acesso/<int:rid>")
@require_auth
def get_tipo_acesso(rid):
    """Alias para /api/roles/{id}."""
    r = db.get_role(rid)
    if not r:
        return _err("Tipo de acesso não encontrado.", 404)
    r["nome"] = r.pop("role_nome", r.get("nome"))
    r["descricao"] = r.get("descricao", "")
    r["permissoes"] = db.get_role_permissoes(rid)
    return _ok(r)


@app.route("/api/tipos-acesso", methods=["POST"])
@require_admin_geral
def create_tipo_acesso():
    """Alias para /api/roles."""
    return create_role()


@app.route("/api/tipos-acesso/<int:rid>", methods=["PUT"])
@require_admin_geral
def update_tipo_acesso(rid):
    """Alias para /api/roles/{id}."""
    return update_role(rid)


@app.route("/api/tipos-acesso/<int:rid>", methods=["DELETE"])
@require_admin_geral
def delete_tipo_acesso(rid):
    """Remove tipo de acesso."""
    if not db.get_role(rid):
        return _err("Tipo de acesso não encontrado.", 404)
    u = current_user()
    _audit("excluir", "role", rid, "Tipo de acesso removido", u)
    db.delete_role(rid)
    return _ok()


@app.route("/api/tipos-acesso/permissoes")
@require_auth
def list_tipos_acesso_permissoes():
    """Alias para /api/permissoes."""
    return list_permissoes()


# ── Compatibilidade: Pessoa Tipos de Acesso ───────────────────────────────

@app.route("/api/pessoas/<int:pid>/tipos-acesso")
@require_auth
def get_pessoa_tipos_acesso(pid):
    """Retorna os tipos de acesso de uma pessoa (alias para /api/pessoas/{id}/roles)."""
    sf = request.args.get("sistema_folder")
    roles = db.get_usuario_roles(pid, sistema_folder=sf)
    return _ok([{
        "tipo_acesso_id": r["role_id"],
        "role_nome": r["role_nome"],
        "escopo": r["escopo"],
        "sistema_folder": r["sistema_folder"],
    } for r in roles])


@app.route("/api/pessoas/<int:pid>/tipos-acesso", methods=["POST"])
@require_admin
def set_pessoa_tipos_acesso(pid):
    """Define tipos de acesso de uma pessoa (alias para /api/pessoas/{id}/roles)."""
    return set_pessoa_role(pid)


@app.route("/api/pessoas/<int:pid>/tipos-acesso", methods=["DELETE"])
@require_admin
def delete_pessoa_tipos_acesso(pid):
    """Remove tipo de acesso de uma pessoa."""
    sf = request.args.get("sistema_folder") or (request.json or {}).get("sistema_folder", "")
    if not sf:
        return _err("sistema_folder é obrigatório.")
    db.delete_usuario_role(pid, sf)
    return _ok()


# ── Auditoria ────────────────────────────────────────────────────────────────

@app.route("/api/audit")
@require_auth
def list_audit():
    u = current_user()
    limit = min(int(request.args.get("limit", 200)), 1000)
    pessoa_id = request.args.get("pessoa_id")
    entidade = request.args.get("entidade")
    empresa_id = request.args.get("empresa_id")

    if not _is_admin_geral(u) and not empresa_id:
        empresa_id = u.get("empresa_id")

    return _ok(db.list_audit(
        limit=limit,
        pessoa_id=int(pessoa_id) if pessoa_id else None,
        entidade=entidade or None,
        empresa_id=int(empresa_id) if empresa_id else None,
    ))


# ── Bootstrap ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    app.secret_key = _load_secret()
    print("\n ATLAS rodando em http://localhost:5010\n")
    print("  Admin padrão: admin@olimpus.local / Atlas@2024\n")
    print("  Modelo: RBAC v4.0 (USER -> GESTOR -> ADMIN -> ADMIN_GERAL)\n")
    app.run(host="127.0.0.1", port=5010, debug=False, threaded=True)
