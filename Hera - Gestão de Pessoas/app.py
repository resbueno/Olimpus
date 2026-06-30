from __future__ import annotations
"""
app.py — Hera: Gestão de Pessoas (porta 5041)
Autenticação delegada ao Atlas (http://localhost:5010).

Tipos de acesso (RBAC v5.0):
  Tipo 1 (USER/SELF)    — ver diretório (sem edição), dashboard, onboarding próprio,
                           solicitar férias próprias, avaliações/feedbacks/PDI próprios,
                           kudos de todos, enviar feedbacks/kudos, inscrever em treinamentos
  Tipo 2 (GESTOR/TEAM)  — tudo do tipo 1 + ver equipe, feedbacks ao gestor,
                           onboarding da equipe, aprovar férias da equipe, relatórios da equipe
  Tipo 3 (ADMIN/COMPANY)— acesso total à ferramenta e visualização de tudo
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
from ferias_calc import FeriasCalculador

ac.SISTEMA_FOLDER = "Hera - Gestão de Pessoas"

ATLAS_URL      = ac.ATLAS_URL
SISTEMA_FOLDER = ac.SISTEMA_FOLDER
PORT           = 5041

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(BASE_DIR, "hera.key")

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

# Mapeamento RBAC → role local do Hera
ROLE_MAP = {
    "ADMIN_GERAL": "admin",
    "ADMIN": "admin",
    "GESTOR": "rh",
    "USER": "colaborador",
}


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


def _visible_uids(u):
    """
    Retorna lista de IDs visíveis conforme escopo RBAC, ou None (= todos).
      COMPANY/GLOBAL → todos da empresa (ou todos)
      TEAM           → si mesmo + colaboradores do mesmo departamento
      SELF           → apenas si mesmo
    """
    escopo = ac.get_atlas_escopo()
    if escopo in ("COMPANY", "GLOBAL"):
        emp_id = u.get("empresa_id")
        if not emp_id or escopo == "GLOBAL":
            return None
        return [x["id"] for x in db.list_users(empresa_id=emp_id)]
    if escopo == "TEAM":
        ids = [u["id"]]
        dept = u.get("departamento_id")
        if dept:
            for x in db.list_users(departamento_id=dept):
                if x["id"] not in ids:
                    ids.append(x["id"])
        # Também inclui subordinados diretos (gestor_id = u.id)
        for sub in db.list_users(gestor_id=u["id"]):
            if sub["id"] not in ids:
                ids.append(sub["id"])
        return ids
    # SELF
    return [u["id"]]


def _can_see_user(u, target_uid):
    """Verifica se u tem permissão para ver dados de target_uid."""
    if u["id"] == target_uid:
        return True
    vids = _visible_uids(u)
    return vids is None or target_uid in vids


def require_role(*roles):
    """Exige role local (admin, rh, colaborador)."""
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
    """Sincroniza o usuário Atlas com o banco local do Hera."""
    atlas_user["_role_sistema"] = ac.map_role_to_local(atlas_user, ROLE_MAP)
    return db.get_or_create_user_from_atlas(atlas_user)


def _sso_login(token: str):
    ac.sso_login_from_token(token, db_sync_fn=_sync_atlas_user)


# ── Atlas Sync ────────────────────────────────────────────────────────────────

def _atlas_sync(email: str, senha: str) -> dict:
    import http.cookiejar
    stats = {"departamentos": 0, "colaboradores": 0, "erros": []}
    if not ac._atlas_running():
        return stats

    cj     = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    body = json.dumps({"email": email, "senha": senha}).encode()
    req  = urllib.request.Request(
        f"{ATLAS_URL}/api/auth/login", data=body,
        headers={"Content-Type": "application/json"}, method="POST"
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
                role_sistema = ""
                try:
                    pid = p.get("id")
                    if pid:
                        folder_enc = urllib.parse.quote(SISTEMA_FOLDER, safe="")
                        with opener.open(
                            f"{ATLAS_URL}/api/acessos/resolve/{pid}/{folder_enc}", timeout=3
                        ) as r2:
                            resolve_data = json.loads(r2.read()).get("data", {})
                            role_sistema = resolve_data.get("role") or resolve_data.get("role_sistema", "")
                except Exception:
                    pass
                atlas_user = {
                    "id":            p.get("id"),
                    "nome":          p["nome"],
                    "email":         p["email"],
                    "cargo":         p.get("cargo", ""),
                    "funcoes":       funcoes,
                    "tipos_acesso":  p.get("tipos_acesso") or [],
                    "empresa_id":    p.get("empresa_id"),
                    "empresa_nome":  p.get("empresa_nome") or "",
                    "_role_sistema": role_sistema,
                    "salario":       p.get("salario", 0) or 0,
                    "gestor_id":     p.get("gestor_id"),
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
    return send_from_directory(BASE_DIR, "hera.html")


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
                "role": u["role"], "cargo": u.get("cargo", ""),
                "departamento_id": u.get("departamento_id"),
                "departamento_nome": u.get("departamento_nome", ""),
                "gestor_id": u.get("gestor_id"),
                "is_gestor": db.is_gestor(u["id"]),
                "foto_url": u.get("foto_url", ""),
                "escopo": ac.get_atlas_escopo(),
                "role_atlas": ac.get_atlas_role()})


# ── Atlas Sync ────────────────────────────────────────────────────────────────

@app.route("/api/atlas/sync", methods=["POST"])
@require_role("admin", "rh")
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


# ── Colaboradores ─────────────────────────────────────────────────────────────

@app.route("/api/users")
@require_auth
def list_users():
    u      = current_user()
    dept   = request.args.get("departamento_id")
    escopo = ac.get_atlas_escopo()

    if escopo in ("COMPANY", "GLOBAL"):
        dept_filter = int(dept) if dept else None
        emp_id = None if escopo == "GLOBAL" else u.get("empresa_id")
        return _ok(db.list_users(empresa_id=emp_id, departamento_id=dept_filter))

    if escopo == "TEAM":
        dept_filter = int(dept) if dept else u.get("departamento_id")
        return _ok(db.list_users(departamento_id=dept_filter))

    # SELF: apenas si mesmo (diretório somente leitura)
    vids = _visible_uids(u)
    return _ok(db.list_users(ids=vids))


@app.route("/api/users/<int:uid>")
@require_auth
def get_user(uid):
    u = current_user()
    if not _can_see_user(u, uid):
        return _err("Sem permissão.", 403)
    target = db.get_user(uid)
    if not target:
        return _err("Colaborador não encontrado.", 404)
    return _ok(target)


@app.route("/api/users/<int:uid>", methods=["PUT"])
@require_auth
def update_user(uid):
    u = current_user()
    if not u:
        return _err("Não autenticado.", 401)
    d = request.json or {}
    escopo = ac.get_atlas_escopo()
    if escopo in ("COMPANY", "GLOBAL"):
        # ADMIN: edita qualquer colaborador visível
        if not _can_see_user(u, uid):
            return _err("Sem permissão.", 403)
        db.update_user(uid, d)
    elif escopo == "TEAM" and _can_see_user(u, uid):
        # GESTOR: edita colaboradores da equipe
        db.update_user(uid, d)
    elif u["id"] == uid:
        # USER/SELF: só edita cargo e foto do próprio perfil
        allowed = {k: d[k] for k in ["cargo", "foto_url"] if k in d}
        if allowed:
            db.update_user(uid, allowed)
    else:
        return _err("Sem permissão.", 403)
    return _ok()


# ── Departamentos ─────────────────────────────────────────────────────────────

@app.route("/api/departments")
@require_auth
def list_departments():
    u      = current_user()
    escopo = ac.get_atlas_escopo()
    if escopo in ("COMPANY", "GLOBAL"):
        emp_id = None if escopo == "GLOBAL" else u.get("empresa_id")
        return _ok(db.list_departamentos(empresa_id=emp_id))
    if escopo == "TEAM":
        dept = db.get_departamento(u.get("departamento_id")) if u.get("departamento_id") else None
        return _ok([dept] if dept else [])
    # SELF: apenas o próprio departamento
    dept = db.get_departamento(u.get("departamento_id")) if u.get("departamento_id") else None
    return _ok([dept] if dept else [])


@app.route("/api/departments", methods=["POST"])
@require_role("admin", "rh")
def create_department():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    new_id = db.create_departamento(d)
    return _ok({"id": new_id}), 201


@app.route("/api/departments/<int:did>", methods=["PUT"])
@require_role("admin", "rh")
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


# ── Onboarding ─────────────────────────────────────────────────────────────────

@app.route("/api/onboarding/etapas")
@require_auth
def list_etapas():
    return _ok(db.list_onboarding_etapas(ativo_only=False))


@app.route("/api/onboarding/etapas", methods=["POST"])
@require_role("admin", "rh")
def create_etapa():
    d = request.json or {}
    if not d.get("titulo"):
        return _err("Título é obrigatório.")
    new_id = db.create_onboarding_etapa(d)
    return _ok({"id": new_id}), 201


@app.route("/api/onboarding/etapas/<int:eid>", methods=["PUT"])
@require_role("admin", "rh")
def update_etapa(eid):
    db.update_onboarding_etapa(eid, request.json or {})
    return _ok()


@app.route("/api/onboarding/<int:uid>")
@require_auth
def get_onboarding(uid):
    u = current_user()
    if not _can_see_user(u, uid):
        return _err("Sem permissão.", 403)
    return _ok(db.get_onboarding_progresso(uid))


@app.route("/api/onboarding/<int:uid>/etapa/<int:eid>", methods=["PUT"])
@require_auth
def update_progresso(uid, eid):
    u      = current_user()
    escopo = ac.get_atlas_escopo()
    # USER/SELF: só edita o próprio onboarding (status das etapas, não as etapas em si)
    if escopo == "SELF" and uid != u["id"]:
        return _err("Sem permissão.", 403)
    if not _can_see_user(u, uid):
        return _err("Sem permissão.", 403)
    d = request.json or {}
    db.update_onboarding_progresso(uid, eid, d.get("concluida", False),
                                   d.get("observacao", ""))
    return _ok()


# ── Férias ────────────────────────────────────────────────────────────────────

@app.route("/api/ferias")
@require_auth
def list_ferias():
    u      = current_user()
    uid    = request.args.get("user_id")
    stat   = request.args.get("status")
    escopo = ac.get_atlas_escopo()

    if escopo == "SELF":
        # USER/SELF: vê só as próprias solicitações
        return _ok(db.list_ferias(user_id=u["id"], status=stat))

    # TEAM/COMPANY/GLOBAL: limita ao escopo visível
    vids = _visible_uids(u)
    if uid:
        target_uid = int(uid)
        if vids is not None and target_uid not in vids:
            return _err("Sem permissão.", 403)
        return _ok(db.list_ferias(user_id=target_uid, status=stat))

    if vids is None:
        return _ok(db.list_ferias(status=stat))
    return _ok(db.list_ferias(user_ids=vids, status=stat))


@app.route("/api/ferias/equipe")
@require_auth
def list_ferias_equipe():
    u      = current_user()
    escopo = ac.get_atlas_escopo()

    if escopo == "SELF":
        return _err("Sem permissão para ver equipe.", 403)

    # TEAM: vê férias da equipe do departamento
    # COMPANY/GLOBAL: vê de qualquer gestor
    gid = request.args.get("gestor_id")
    if gid:
        gid_int = int(gid)
        if not _can_see_user(u, gid_int):
            return _err("Sem permissão.", 403)
        return _ok(db.list_ferias_equipe(gid_int))
    return _ok(db.list_ferias_equipe(u["id"]))



@app.route("/api/ferias/resumo/<int:uid>")
@require_auth
def get_ferias_resumo(uid):
    u = current_user()
    if not _can_see_user(u, uid):
        # Também permite se for gestor direto do uid
        colab = db.get_user(uid)
        if not (colab and colab.get("gestor_id") and int(colab["gestor_id"]) == int(u["id"])):
            return _err("Sem permissão para ver detalhes deste colaborador.", 403)

    user = db.get_user(uid)
    if not user: return _err("Usuário não encontrado.", 404)

    historico = db.list_ferias(user_id=uid)
    status_clt = FeriasCalculador.classificar_status_ferias(user.get("data_admissao"), historico)
    
    # Cálculo financeiro baseado em 30 dias (padrão)
    financeiro = None
    if user.get("salario_mensal") and user["salario_mensal"] > 0:
        financeiro = FeriasCalculador.calcular_valor_ferias(user["salario_mensal"], 30)

    return _ok({
        "user": {
            "id": user["id"],
            "nome": user["nome"],
            "data_admissao": user.get("data_admissao"),
            "cargo": user.get("cargo"),
            "salario_mensal": user.get("salario_mensal", 0)
        },
        "status_clt": status_clt,
        "historico": historico,
        "financeiro": financeiro
    })


@app.route("/api/ferias", methods=["POST"])
@require_auth
def create_ferias():
    u = current_user()
    d = request.json or {}
    for f in ["data_inicio", "data_fim"]:
        if not d.get(f):
            return _err(f"Campo obrigatório: {f}")
    # USER/SELF só pode solicitar para si mesmo
    escopo = ac.get_atlas_escopo()
    if escopo == "SELF":
        d["user_id"] = u["id"]
    elif not d.get("user_id"):
        d["user_id"] = u["id"]
    elif not _can_see_user(u, int(d["user_id"])):
        return _err("Sem permissão.", 403)
    # Calcula dias úteis (simplificado: dias corridos)
    try:
        di = datetime.strptime(d["data_inicio"], "%Y-%m-%d")
        df = datetime.strptime(d["data_fim"],    "%Y-%m-%d")
        d["dias"] = max(1, (df - di).days + 1)
        if d["dias"] > 30:
            return _err("O período de férias não pode exceder 30 dias (CLT).")
    except Exception:
        d["dias"] = 0
    new_id = db.create_ferias(d)
    return _ok({"id": new_id}), 201


@app.route("/api/ferias/<int:fid>")
@require_auth
def get_ferias(fid):
    f = db.get_ferias(fid)
    if not f: return _err("Não encontrado", 404)
    u = current_user()
    if _can_see_user(u, f["user_id"]):
        return _ok(f)
    # Também permite gestor direto
    colab = db.get_user(f["user_id"])
    if colab and colab.get("gestor_id") and int(colab["gestor_id"]) == int(u["id"]):
        return _ok(f)
    return _err("Sem permissão", 403)


@app.route("/api/ferias/<int:fid>/status", methods=["PUT"])
@require_auth
def update_ferias_status(fid):
    u = current_user()
    d = request.json or {}
    status = d.get("status")
    if status not in ("aprovada", "recusada"):
        return _err("Status deve ser 'aprovada' ou 'recusada'.")
    
    ferias = db.get_ferias(fid)
    if not ferias:
        return _err("Solicitação não encontrada.", 404)
        
    # Verificação de permissão: deve poder ver o usuário das férias ou ser seu gestor direto
    if not _can_see_user(u, ferias["user_id"]):
        colab = db.get_user(ferias["user_id"])
        if not (colab and colab.get("gestor_id") and int(colab["gestor_id"]) == int(u["id"])):
            return _err("Sem permissão para alterar o status desta solicitação.", 403)
        
    db.update_ferias_status(fid, status, u["id"])
    return _ok()


@app.route("/api/ferias/<int:uid>/calcular", methods=["POST"])
@require_auth
def calcular_ferias(uid):
    """Calcula valor das férias baseado em salário e dias."""
    u = current_user()
    if not _can_see_user(u, uid):
        return _err("Sem permissão.", 403)

    user = db.get_user(uid)
    if not user:
        return _err("Colaborador não encontrado.", 404)

    if not user.get("salario_mensal") or user["salario_mensal"] <= 0:
        return _err("Salário mensal não configurado para este colaborador.")

    d = request.json or {}
    dias = d.get("dias", 30)

    if dias <= 0 or dias > 30:
        return _err("Dias deve estar entre 1 e 30.")

    valores = FeriasCalculador.calcular_valor_ferias(
        user["salario_mensal"], dias, incluir_adicional=True
    )

    return _ok({
        "usuario": {"id": user["id"], "nome": user["nome"]},
        "ferias": valores
    })


@app.route("/api/ferias/opcoes-fracionamento", methods=["GET"])
@require_auth
def listar_opcoes_fracionamento():
    """Lista todas as opções válidas de fracionamento de férias."""
    dias = request.args.get("dias", 30, type=int)
    opcoes = FeriasCalculador.gerar_opcoes_fracionamento(dias)
    return _ok({"opcoes": opcoes})


@app.route("/api/ferias/<int:fid>/periodos", methods=["POST"])
@require_auth
def adicionar_periodos_ferias(fid):
    """Adiciona períodos fracionados a uma solicitação de férias."""
    ferias = db.get_ferias(fid)
    if not ferias:
        return _err("Solicitação não encontrada.", 404)
    
    u = current_user()
    if not _can_see_user(u, ferias["user_id"]):
        colab = db.get_user(ferias["user_id"])
        if not (colab and colab.get("gestor_id") and int(colab["gestor_id"]) == int(u["id"])):
            return _err("Sem permissão para fracionar esta solicitação.", 403)

    d = request.json or {}
    periodos = d.get("periodos", [])

    if not periodos:
        return _err("Nenhum período fornecido.")

    # Valida fracionamento
    duracao_dias = [p.get("duracao_dias", 0) for p in periodos]
    valido, mensagem = FeriasCalculador.validar_fracionamento(duracao_dias)

    if not valido:
        return _err(f"Fracionamento inválido: {mensagem}")

    # Cria períodos
    db.create_ferias_periodos(fid, periodos)

    return _ok({"periodos_adicionados": len(periodos)})


# ── Avaliações ─────────────────────────────────────────────────────────────────

@app.route("/api/ciclos")
@require_auth
def list_ciclos():
    return _ok(db.list_ciclos())


@app.route("/api/ciclos", methods=["POST"])
@require_role("admin", "rh")
def create_ciclo():
    d = request.json or {}
    for f in ["titulo", "data_inicio", "data_fim"]:
        if not d.get(f):
            return _err(f"Campo obrigatório: {f}")
    new_id = db.create_ciclo(d)
    return _ok({"id": new_id}), 201


@app.route("/api/ciclos/<int:cid>", methods=["PUT"])
@require_role("admin", "rh")
def update_ciclo(cid):
    if not db.get_ciclo(cid):
        return _err("Ciclo não encontrado.", 404)
    db.update_ciclo(cid, request.json or {})
    return _ok()


@app.route("/api/ciclos/<int:cid>/avaliacoes")
@require_auth
def list_avaliacoes(cid):
    u         = current_user()
    avaliador = request.args.get("avaliador_id")
    avaliado  = request.args.get("avaliado_id")
    escopo    = ac.get_atlas_escopo()

    if escopo == "SELF":
        # USER/SELF: só vê as próprias avaliações (como avaliado)
        avaliado = str(u["id"])
    else:
        # TEAM/COMPANY/GLOBAL: valida visibilidade
        if avaliador and not _can_see_user(u, int(avaliador)):
            return _err("Sem permissão.", 403)
        if avaliado and not _can_see_user(u, int(avaliado)):
            return _err("Sem permissão.", 403)

    return _ok(db.list_avaliacoes(
        ciclo_id=cid,
        avaliador_id=int(avaliador) if avaliador else None,
        avaliado_id=int(avaliado)   if avaliado  else None,
    ))


@app.route("/api/ciclos/<int:cid>/avaliacoes", methods=["POST"])
@require_auth
def upsert_avaliacao(cid):
    u = current_user()
    d = request.json or {}
    d["ciclo_id"] = cid
    for f in ["avaliado_id", "avaliador_id"]:
        if not d.get(f):
            return _err(f"Campo obrigatório: {f}")
    # USER/SELF só pode enviar avaliações em seu próprio nome
    if ac.get_atlas_escopo() == "SELF" and d["avaliador_id"] != u["id"]:
        return _err("Sem permissão.", 403)
    new_id = db.upsert_avaliacao(d)
    return _ok({"id": new_id})


# ── Feedbacks ─────────────────────────────────────────────────────────────────

@app.route("/api/feedbacks")
@require_auth
def list_feedbacks():
    u      = current_user()
    para   = request.args.get("para_user_id")
    de     = request.args.get("de_user_id")
    escopo = ac.get_atlas_escopo()

    if escopo == "SELF":
        # USER/SELF: só vê feedbacks próprios (enviados para ele ou por ele)
        if not para and not de:
            para = str(u["id"])
    elif escopo == "TEAM":
        # GESTOR/TEAM: vê feedbacks próprios + feedbacks visíveis ao gestor (da equipe)
        if para and not _can_see_user(u, int(para)):
            return _err("Sem permissão.", 403)
        if de and not _can_see_user(u, int(de)):
            return _err("Sem permissão.", 403)
    else:
        # COMPANY/GLOBAL: validação ampla
        if para and not _can_see_user(u, int(para)):
            return _err("Sem permissão.", 403)
        if de and not _can_see_user(u, int(de)):
            return _err("Sem permissão.", 403)

    return _ok(db.list_feedbacks(
        para_user_id=int(para) if para else None,
        de_user_id=int(de)     if de   else None,
    ))


@app.route("/api/feedbacks", methods=["POST"])
@require_auth
def create_feedback():
    u = current_user()
    d = request.json or {}
    if not d.get("para_user_id"):
        return _err("para_user_id é obrigatório.")
    if not d.get("texto", "").strip():
        return _err("Texto é obrigatório.")
    d["de_user_id"] = u["id"]
    new_id = db.create_feedback(d)
    return _ok({"id": new_id}), 201


@app.route("/api/feedbacks/<int:fid>", methods=["DELETE"])
@require_role("admin", "rh")
def delete_feedback(fid):
    db.delete_feedback(fid)
    return _ok()


# ── Kudos ─────────────────────────────────────────────────────────────────────

@app.route("/api/kudos/feed")
@require_auth
def kudos_feed():
    return _ok(db.list_kudos_feed())


@app.route("/api/kudos")
@require_auth
def list_kudos():
    para = request.args.get("para_user_id")
    return _ok(db.list_kudos(para_user_id=int(para) if para else None))


@app.route("/api/kudos", methods=["POST"])
@require_auth
def create_kudos():
    u = current_user()
    d = request.json or {}
    if not d.get("para_user_id"):
        return _err("para_user_id é obrigatório.")
    if not d.get("mensagem", "").strip():
        return _err("Mensagem é obrigatória.")
    if d["para_user_id"] == u["id"]:
        return _err("Não é possível enviar kudos para si mesmo.")
    d["de_user_id"] = u["id"]
    new_id = db.create_kudos(d)
    return _ok({"id": new_id}), 201


# ── PDI ───────────────────────────────────────────────────────────────────────

@app.route("/api/pdi")
@require_auth
def list_pdi():
    u      = current_user()
    uid    = request.args.get("user_id")
    escopo = ac.get_atlas_escopo()

    if escopo == "SELF":
        # USER/SELF: só vê o próprio PDI
        return _ok(db.list_pdi(user_id=u["id"]))

    if uid:
        if not _can_see_user(u, int(uid)):
            return _err("Sem permissão.", 403)
        return _ok(db.list_pdi(user_id=int(uid)))

    # TEAM/COMPANY/GLOBAL: PDIs dos usuários visíveis
    vids = _visible_uids(u)
    if vids is None:
        return _ok(db.list_pdi())
    all_pdi = []
    for vid in vids:
        all_pdi.extend(db.list_pdi(user_id=vid))
    all_pdi.sort(key=lambda x: x.get("criado_em", ""), reverse=True)
    return _ok(all_pdi)


@app.route("/api/pdi/<int:pid>")
@require_auth
def get_pdi(pid):
    p = db.get_pdi(pid)
    if not p:
        return _err("PDI não encontrado.", 404)
    u = current_user()
    if not _can_see_user(u, p["user_id"]):
        return _err("Sem permissão.", 403)
    return _ok(p)


@app.route("/api/pdi", methods=["POST"])
@require_auth
def create_pdi():
    u = current_user()
    d = request.json or {}
    for f in ["titulo", "periodo_inicio", "periodo_fim"]:
        if not d.get(f):
            return _err(f"Campo obrigatório: {f}")
    if ac.get_atlas_escopo() == "SELF":
        d["user_id"] = u["id"]
    elif not d.get("user_id"):
        d["user_id"] = u["id"]
    elif not _can_see_user(u, int(d["user_id"])):
        return _err("Sem permissão.", 403)
    new_id = db.create_pdi(d)
    return _ok({"id": new_id}), 201


@app.route("/api/pdi/<int:pid>", methods=["PUT"])
@require_auth
def update_pdi(pid):
    p = db.get_pdi(pid)
    if not p:
        return _err("PDI não encontrado.", 404)
    u = current_user()
    if not _can_see_user(u, p["user_id"]):
        return _err("Sem permissão.", 403)
    db.update_pdi(pid, request.json or {})
    return _ok()


@app.route("/api/pdi/<int:pid>/acoes", methods=["POST"])
@require_auth
def create_acao(pid):
    p = db.get_pdi(pid)
    if not p:
        return _err("PDI não encontrado.", 404)
    u = current_user()
    if not _can_see_user(u, p["user_id"]):
        return _err("Sem permissão.", 403)
    d = request.json or {}
    for f in ["descricao", "prazo"]:
        if not d.get(f):
            return _err(f"Campo obrigatório: {f}")
    d["pdi_id"] = pid
    new_id = db.create_pdi_acao(d)
    return _ok({"id": new_id}), 201


@app.route("/api/pdi/acoes/<int:aid>", methods=["PUT"])
@require_auth
def update_acao(aid):
    db.update_pdi_acao(aid, request.json or {})
    return _ok()


@app.route("/api/pdi/acoes/<int:aid>", methods=["DELETE"])
@require_role("admin", "rh")
def delete_acao(aid):
    db.delete_pdi_acao(aid)
    return _ok()


# ── Treinamentos ──────────────────────────────────────────────────────────────

@app.route("/api/treinamentos")
@require_auth
def list_treinamentos():
    return _ok(db.list_treinamentos())


@app.route("/api/treinamentos", methods=["POST"])
@require_role("admin", "rh")
def create_treinamento():
    d = request.json or {}
    if not d.get("titulo"):
        return _err("Título é obrigatório.")
    new_id = db.create_treinamento(d)
    return _ok({"id": new_id}), 201


@app.route("/api/treinamentos/<int:tid>", methods=["PUT"])
@require_role("admin", "rh")
def update_treinamento(tid):
    if not db.get_treinamento(tid):
        return _err("Treinamento não encontrado.", 404)
    db.update_treinamento(tid, request.json or {})
    return _ok()


@app.route("/api/treinamentos/<int:tid>", methods=["DELETE"])
@require_role("admin")
def delete_treinamento(tid):
    db.delete_treinamento(tid)
    return _ok()


@app.route("/api/treinamentos/<int:tid>/inscricoes")
@require_auth
def list_inscricoes(tid):
    return _ok(db.list_inscricoes(treinamento_id=tid))


@app.route("/api/treinamentos/<int:tid>/inscrever", methods=["POST"])
@require_auth
def inscrever(tid):
    if not db.get_treinamento(tid):
        return _err("Treinamento não encontrado.", 404)
    u   = current_user()
    d   = request.json or {}
    uid = d.get("user_id", u["id"])
    if not _can_see_user(u, uid):
        return _err("Sem permissão.", 403)
    db.inscrever_treinamento(tid, uid)
    return _ok()


@app.route("/api/treinamentos/<int:tid>/inscricoes/<int:uid>", methods=["PUT"])
@require_auth
def update_inscricao(tid, uid):
    u = current_user()
    if not _can_see_user(u, uid):
        return _err("Sem permissão.", 403)
    db.update_inscricao(tid, uid, request.json or {})
    return _ok()


@app.route("/api/meus-treinamentos")
@require_auth
def meus_treinamentos():
    u = current_user()
    return _ok(db.list_inscricoes(user_id=u["id"]))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
@require_auth
def dashboard():
    u      = current_user()
    escopo = ac.get_atlas_escopo()
    if escopo in ("COMPANY", "GLOBAL"):
        emp_id = None if escopo == "GLOBAL" else u.get("empresa_id")
        return _ok(db.get_dashboard_stats(empresa_id=emp_id))
    if escopo == "TEAM":
        return _ok(db.get_dashboard_stats(empresa_id=None, departamento_id=u.get("departamento_id")))
    # SELF: stats do próprio departamento
    return _ok(db.get_dashboard_stats(empresa_id=None, departamento_id=u.get("departamento_id")))


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    print(f"\n  HERA rodando em http://localhost:{PORT}\n")
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)
