from __future__ import annotations
"""
app.py — Cronos: Ponto Eletrônico (porta 5025)
Autenticação delegada ao Atlas (http://localhost:5010).

Tipos de acesso (RBAC v5.0):
  Tipo 1 (USER/SELF)    — bater ponto, ver histórico/espelho/banco próprio, solicitar ajustes próprios
  Tipo 2 (GESTOR/TEAM)  — tudo do tipo 1 + ver da equipe (departamento)
  Tipo 3 (ADMIN/COMPANY)— acesso total à ferramenta e visualização de tudo
"""
import csv
import io
import json
import os
import sys
from datetime import datetime, timedelta
from functools import wraps

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from flask import Flask, Response, jsonify, request, send_from_directory, session
from flask_cors import CORS

import database as db
import atlas_client as ac

ac.SISTEMA_FOLDER = "Cronos - Ponto Eletrônico"

ATLAS_URL      = ac.ATLAS_URL
SISTEMA_FOLDER = ac.SISTEMA_FOLDER
PORT           = 5025

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(BASE_DIR, "cronos.key")

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

# Mapeamento RBAC → role local do Cronos
ROLE_MAP = {
    "ADMIN_GERAL": "admin",
    "ADMIN": "admin",
    "GESTOR": "gestor",
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


def _visible_uids(u):
    """
    Retorna lista de user_ids visíveis conforme escopo RBAC:
      SELF    → apenas o próprio
      TEAM    → próprio + colaboradores do mesmo departamento
      COMPANY/GLOBAL → todos (None)
    """
    escopo = ac.get_atlas_escopo()
    if escopo in ("COMPANY", "GLOBAL"):
        return None  # todos
    if escopo == "TEAM":
        dept = u.get("departamento_id")
        if not dept:
            return [u["id"]]
        uids = [x["id"] for x in db.list_users(departamento_id=dept)]
        if u["id"] not in uids:
            uids.append(u["id"])
        return uids
    # SELF
    return [u["id"]]


def _can_see_uid(u, target_uid: int) -> bool:
    if u["id"] == target_uid:
        return True
    vids = _visible_uids(u)
    return vids is None or target_uid in vids


def require_auth(f):
    @wraps(f)
    def wrapped(*a, **kw):
        if not session.get("user_id"):
            return _err("Não autenticado.", 401)
        return f(*a, **kw)
    return wrapped


def require_role(*roles):
    """Exige role local (admin, gestor, colaborador)."""
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
    """Sincroniza o usuário Atlas com o banco local do Cronos."""
    atlas_user["_role_sistema"] = ac.map_role_to_local(atlas_user, ROLE_MAP)
    return db.get_or_create_user_from_atlas(atlas_user)


def _sso_login(token: str):
    ac.sso_login_from_token(token, db_sync_fn=_sync_atlas_user)


def _atlas_sync(email: str, senha: str) -> dict:
    import urllib.request
    import http.cookiejar
    stats = {"departamentos": 0, "colaboradores": 0, "erros": []}
    if not ac._atlas_running():
        return stats
    cj     = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body   = json.dumps({"email": email, "senha": senha}).encode()
    req    = urllib.request.Request(
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
            for emp in json.loads(resp.read()).get("data", []):
                if emp.get("ativo", 1):
                    db.get_or_create_dept(emp["id"], emp["nome"])
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
                        "cargo": p.get("cargo",""), "funcoes": funcoes,
                        "empresa_id": p.get("empresa_id"),
                        "empresa_nome": p.get("empresa_nome") or "",
                        "departamento_id": p.get("departamento_id"),
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
    return send_from_directory(BASE_DIR, "cronos.html")


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
            return _ok({"id": u["id"], "nome": u["nome"],
                        "email": u["email"], "role": u["role"]})
    if not ac._atlas_running() and db.check_password(email, senha):
        u = db.get_user_by_email(email)
        session["user_id"] = u["id"]
        session.permanent  = True
        return _ok({"id": u["id"], "nome": u["nome"],
                    "email": u["email"], "role": u["role"]})
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
                "role": u["role"], "cargo": u.get("cargo",""),
                "departamento_id": u.get("departamento_id"),
                "departamento_nome": u.get("departamento_nome",""),
                "jornada_id": u.get("jornada_id"),
                "jornada_nome": u.get("jornada_nome",""),
                "escopo": ac.get_atlas_escopo(),
                "role_atlas": ac.get_atlas_role()})


# ── Atlas Sync ────────────────────────────────────────────────────────────────

@app.route("/api/atlas/sync", methods=["POST"])
@require_role("admin", "rh")
def atlas_sync():
    d = request.json or {}
    email = d.get("email","").strip().lower()
    senha = d.get("senha","")
    if not email or not senha:
        return _err("Informe e-mail e senha do Atlas.")
    if not _atlas_running():
        return _err("Atlas não está acessível em localhost:5010.")
    stats = _atlas_sync(email, senha)
    if not stats["departamentos"] and not stats["colaboradores"]:
        return _err("Credenciais inválidas ou nenhum dado encontrado.")
    return _ok(stats)


# ── Ponto ────────────────────────────────────────────────────────────────────

@app.route("/api/ponto/bater", methods=["POST"])
@require_auth
def bater_ponto():
    u    = current_user()
    d    = request.json or {}
    hoje = datetime.now().strftime("%Y-%m-%d")
    prox = db.proximo_tipo(u["id"], hoje)
    if prox is None:
        return _err("Jornada já encerrada para hoje.")
    tipo = d.get("tipo") or prox
    # Valida que tipo solicitado é o esperado (colaborador não pode pular etapa)
    if u["role"] == "colaborador" and tipo != prox:
        return _err(f"Próximo registro esperado: {prox}.")
    nid = db.registrar_ponto(
        u["id"], tipo,
        observacao=d.get("observacao",""),
        latitude=d.get("latitude"),
        longitude=d.get("longitude"),
    )
    calc = db.calcular_dia(u["id"], hoje)
    return _ok({
        "id":      nid,
        "tipo":    tipo,
        "proximo": db.proximo_tipo(u["id"], hoje),
        "calc":    calc,
    })


@app.route("/api/ponto/hoje")
@require_auth
def ponto_hoje():
    u    = current_user()
    hoje = datetime.now().strftime("%Y-%m-%d")
    reg  = db.get_registros_dia(u["id"], hoje)
    calc = db.calcular_dia(u["id"], hoje)
    prox = db.proximo_tipo(u["id"], hoje)
    return _ok({"registros": reg, "calc": calc, "proximo": prox})


@app.route("/api/ponto/historico")
@require_auth
def historico():
    u        = current_user()
    uid_str  = request.args.get("user_id")
    data_ini = request.args.get("data_ini")
    data_fim = request.args.get("data_fim")

    if uid_str:
        target = int(uid_str)
        if not _can_see_uid(u, target):
            return _err("Sem permissão.", 403)
        registros = db.list_registros(user_id=target, data_ini=data_ini, data_fim=data_fim)
    else:
        vids = _visible_uids(u)
        registros = db.list_registros(data_ini=data_ini, data_fim=data_fim, user_ids=vids)
    return _ok(registros)


@app.route("/api/ponto/espelho")
@require_auth
def espelho():
    """Retorna totais por dia para um mês."""
    u   = current_user()
    uid = request.args.get("user_id")
    mes = int(request.args.get("mes", datetime.now().month))
    ano = int(request.args.get("ano", datetime.now().year))

    target = int(uid) if uid else u["id"]
    if not _can_see_uid(u, target):
        return _err("Sem permissão.", 403)

    resumo = db.resumo_mes(target, ano, mes)
    resumo["total_trab_fmt"]    = db._min_to_hhmm(resumo["total_min_trab"])
    resumo["total_extra_fmt"]   = db._min_to_hhmm(resumo["total_min_extra"])
    resumo["total_falta_fmt"]   = db._min_to_hhmm(resumo["total_min_falta"])
    resumo["total_noturno_fmt"] = db._min_to_hhmm(resumo["total_min_noturno"])
    for d in resumo["dias_detail"]:
        d["trab_fmt"]  = db._min_to_hhmm(d["min_trabalhados"])
        d["extra_fmt"] = db._min_to_hhmm(d["min_extra"])
        d["falta_fmt"] = db._min_to_hhmm(d["min_falta"])
    return _ok(resumo)


# ── Ajustes ───────────────────────────────────────────────────────────────────

@app.route("/api/ajustes")
@require_auth
def list_ajustes():
    u       = current_user()
    uid_str = request.args.get("user_id")
    status  = request.args.get("status")

    if uid_str:
        target = int(uid_str)
        if not _can_see_uid(u, target):
            return _err("Sem permissão.", 403)
        return _ok(db.list_ajustes(user_id=target, status=status))
    else:
        vids = _visible_uids(u)
        return _ok(db.list_ajustes(status=status, user_ids=vids))


@app.route("/api/ajustes", methods=["POST"])
@require_auth
def create_ajuste():
    u = current_user()
    d = request.json or {}
    for f in ["data", "tipo_ajuste", "timestamp_solicitado"]:
        if not d.get(f):
            return _err(f"Campo obrigatório: {f}")
    if u["role"] == "colaborador":
        d["user_id"] = u["id"]
    else:
        if not d.get("user_id"):
            d["user_id"] = u["id"]
        elif not _can_see_uid(u, int(d["user_id"])):
            return _err("Sem permissão.", 403)
    nid = db.create_ajuste(d)
    return _ok({"id": nid}), 201


@app.route("/api/ajustes/<int:aid>/status", methods=["PUT"])
@require_role("admin", "rh", "gestor")
def aprovar_ajuste(aid):
    u      = current_user()
    d      = request.json or {}
    status = d.get("status")
    if status not in ("aprovado", "reprovado"):
        return _err("Status deve ser 'aprovado' ou 'reprovado'.")
    aj = db.get_ajuste(aid)
    if aj and not _can_see_uid(u, aj["user_id"]):
        return _err("Sem permissão.", 403)
    db.aprovar_ajuste(aid, u["id"], status)
    return _ok()


# ── Jornadas ──────────────────────────────────────────────────────────────────

@app.route("/api/jornadas")
@require_auth
def list_jornadas():
    return _ok(db.list_jornadas())


@app.route("/api/jornadas", methods=["POST"])
@require_role("admin", "rh")
def create_jornada():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    nid = db.create_jornada(d)
    return _ok({"id": nid}), 201


@app.route("/api/jornadas/<int:jid>", methods=["PUT"])
@require_role("admin", "rh")
def update_jornada(jid):
    if not db.get_jornada(jid):
        return _err("Jornada não encontrada.", 404)
    db.update_jornada(jid, request.json or {})
    return _ok()


# ── Feriados ──────────────────────────────────────────────────────────────────

@app.route("/api/feriados")
@require_auth
def list_feriados():
    ano = request.args.get("ano")
    return _ok(db.list_feriados(ano=ano))


@app.route("/api/feriados", methods=["POST"])
@require_role("admin", "rh")
def create_feriado():
    d = request.json or {}
    for f in ["data", "descricao"]:
        if not d.get(f):
            return _err(f"Campo obrigatório: {f}")
    nid = db.create_feriado(d)
    return _ok({"id": nid}), 201


@app.route("/api/feriados/<int:fid>", methods=["DELETE"])
@require_role("admin", "rh")
def delete_feriado(fid):
    db.delete_feriado(fid)
    return _ok()


# ── Banco de Horas ─────────────────────────────────────────────────────────────

@app.route("/api/banco-horas")
@require_auth
def banco_horas():
    u       = current_user()
    uid_str = request.args.get("user_id")

    if uid_str:
        target = int(uid_str)
        if not _can_see_uid(u, target):
            return _err("Sem permissão.", 403)
    else:
        target = u["id"]
    
    banco = db.get_banco_horas(target)
    
    import sqlite3
    hera_db = os.path.join(os.path.dirname(BASE_DIR), "Hera - Gestão de Pessoas", "hera.db")
    salario = 0.0
    try:
        if os.path.exists(hera_db):
            t_user = db.get_user(target)
            if t_user and t_user.get("email"):
                conn = sqlite3.connect(hera_db)
                row = conn.execute("SELECT salario_mensal FROM users WHERE email=?", (t_user["email"],)).fetchone()
                if row and row[0]:
                    salario = float(row[0])
                conn.close()
    except Exception:
        pass
        
    valor_dinheiro = (banco["saldo_minutos"] / 60.0) * (salario / 220.0)
    banco["salario_mensal"] = salario
    banco["valor_dinheiro"] = valor_dinheiro

    return _ok({
        "banco":       banco,
        "lancamentos": db.list_lancamentos_banco(target),
    })


@app.route("/api/banco-horas/compensar", methods=["POST"])
@require_role("admin", "rh", "gestor")
def compensar():
    u = current_user()
    d = request.json or {}
    for f in ["user_id", "minutos", "data", "descricao"]:
        if not d.get(f):
            return _err(f"Campo obrigatório: {f}")
    target = int(d["user_id"])
    if not _can_see_uid(u, target):
        return _err("Sem permissão.", 403)
    db.compensar_banco_horas(target, int(d["minutos"]),
                             d["descricao"], u["id"], d["data"])
    return _ok()


# ── Fechamentos ───────────────────────────────────────────────────────────────

@app.route("/api/fechamentos")
@require_auth
def list_fechamentos():
    u       = current_user()
    uid_str = request.args.get("user_id")
    ano     = request.args.get("ano")

    if uid_str:
        target = int(uid_str)
        if not _can_see_uid(u, target):
            return _err("Sem permissão.", 403)
        return _ok(db.list_fechamentos(user_id=target, ano=int(ano) if ano else None))
    else:
        vids = _visible_uids(u)
        return _ok(db.list_fechamentos(ano=int(ano) if ano else None, user_ids=vids))


@app.route("/api/fechamentos/fechar", methods=["POST"])
@require_role("admin", "rh")
def fechar_periodo():
    u   = current_user()
    d   = request.json or {}
    uid = d.get("user_id")
    mes = d.get("mes")
    ano = d.get("ano")
    if not uid or not mes or not ano:
        return _err("user_id, mes e ano são obrigatórios.")
    target = int(uid)
    if not _can_see_uid(u, target):
        return _err("Sem permissão.", 403)
    result = db.fechar_periodo(target, int(mes), int(ano), u["id"])
    if result.get("erro"):
        return _err(result["erro"])
    return _ok(result)


@app.route("/api/fechamentos/exportar-csv")
@require_role("admin", "rh")
def exportar_csv():
    u       = current_user()
    uid_str = request.args.get("user_id")
    mes     = int(request.args.get("mes", datetime.now().month))
    ano     = int(request.args.get("ano", datetime.now().year))

    if uid_str:
        target = int(uid_str)
        if not _can_see_uid(u, target):
            return _err("Sem permissão.", 403)
        lista = db.list_fechamentos(user_id=target, ano=ano)
    else:
        vids  = _visible_uids(u)
        lista = db.list_fechamentos(ano=ano, user_ids=vids)
    lista_m = [f for f in lista if f["mes"] == mes]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Colaborador","Mês","Ano","Dias","Horas Trab",
                     "Horas Extras","Horas Falta","Status"])
    for f in lista_m:
        writer.writerow([
            f["user_nome"], f["mes"], f["ano"],
            f["total_dias"], f["total_trab_fmt"],
            f["total_extra_fmt"], f["total_falta_fmt"],
            f["status"],
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition":
                 f"attachment; filename=fechamento_{mes:02d}_{ano}.csv"}
    )


# ── Colaboradores ─────────────────────────────────────────────────────────────

@app.route("/api/users")
@require_auth
def list_users():
    u      = current_user()
    escopo = ac.get_atlas_escopo()

    if escopo in ("COMPANY", "GLOBAL"):
        # ADMIN: vê todos da empresa (ou todos se GLOBAL)
        emp_id = None if escopo == "GLOBAL" else u.get("empresa_id")
        return _ok(db.list_users(empresa_id=emp_id))
    if escopo == "TEAM":
        # GESTOR: vê colaboradores do mesmo departamento
        return _ok(db.list_users(departamento_id=u.get("departamento_id")))
    # SELF: apenas si mesmo
    return _ok([u])


@app.route("/api/users/<int:uid>", methods=["PUT"])
@require_role("admin", "rh")
def update_user(uid):
    u = current_user()
    if not _can_see_uid(u, uid):
        return _err("Sem permissão.", 403)
    db.update_user(uid, request.json or {})
    return _ok()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
@require_auth
def dashboard():
    u = current_user()
    stats = db.get_dashboard_stats(u["id"])
    
    banco = stats.get("banco_horas")
    if banco:
        import sqlite3
        hera_db = os.path.join(os.path.dirname(BASE_DIR), "Hera - Gestão de Pessoas", "hera.db")
        salario = 0.0
        try:
            if os.path.exists(hera_db):
                t_user = db.get_user(u["id"])
                if t_user and t_user.get("email"):
                    conn = sqlite3.connect(hera_db)
                    row = conn.execute("SELECT salario_mensal FROM users WHERE email=?", (t_user["email"],)).fetchone()
                    if row and row[0]:
                        salario = float(row[0])
                    conn.close()
        except Exception:
            pass
            
        valor_dinheiro = (banco["saldo_minutos"] / 60.0) * (salario / 220.0)
        banco["salario_mensal"] = salario
        banco["valor_dinheiro"] = valor_dinheiro
        
    return _ok(stats)


# ── Configurações ─────────────────────────────────────────────────────────────

@app.route("/api/config")
@require_auth
def get_config():
    return _ok(db.get_config())


@app.route("/api/config", methods=["PUT"])
@require_role("admin", "rh")
def update_config():
    db.update_config(request.json or {})
    return _ok()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    print(f"\n  CRONOS rodando em http://localhost:{PORT}\n")
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)
