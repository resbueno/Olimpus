from __future__ import annotations
"""
app.py — API REST Flask do Oráculo (porta 5030)
Autenticação delegada ao Atlas (http://localhost:5010).
Newsletter automática via APScheduler.
"""
import http.cookiejar
import json
import os
import smtplib
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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

ac.SISTEMA_FOLDER = "Oráculo - Hub de Notícias"

ATLAS_URL      = "http://localhost:5010"
SISTEMA_FOLDER = "Oráculo - Hub de Notícias"
PORT           = 5030

# Mapeamento role Atlas → role local do Oráculo
ROLE_MAP = {"ADMIN_GERAL": "admin", "ADMIN": "admin", "GESTOR": "editor", "USER": "leitor"}

# ── Feedparser (opcional) ─────────────────────────────────────────────────────
try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

# ── APScheduler (opcional) ────────────────────────────────────────────────────
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False


# ── Flask setup ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(BASE_DIR, "oraculo.key")

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

def _sync_atlas_user(atlas_user: dict):
    """Mapeia role Atlas → local e sincroniza usuário no banco."""
    local_role = ac.map_role_to_local(atlas_user, ROLE_MAP)
    atlas_user["_role_sistema"] = local_role
    return db.get_or_create_user_from_atlas(atlas_user)


def _sso_login(token: str):
    ac.sso_login_from_token(token, db_sync_fn=_sync_atlas_user)


# ── Atlas sync ────────────────────────────────────────────────────────────────

def _atlas_sync_request(path: str, email: str, senha: str):
    """
    Abre uma sessão HTTP com cookie jar, faz login no Atlas
    e retorna o JSON de 'path'. Retorna None em caso de falha.
    """
    if not ac._atlas_running():
        return None
    try:
        cj     = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        # Login
        body = json.dumps({"email": email, "senha": senha}).encode()
        req  = urllib.request.Request(
            f"{ATLAS_URL}/api/auth/login",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with opener.open(req, timeout=5) as resp:
            login_resp = json.loads(resp.read())
        if not login_resp.get("ok"):
            return None
        # Fetch resource
        with opener.open(f"{ATLAS_URL}{path}", timeout=5) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _do_atlas_sync(email: str, senha: str) -> dict:
    """
    Sincroniza empresas → departamentos e pessoas → usuários do Atlas.
    Retorna dict com contadores.
    """
    stats = {"departamentos": 0, "usuarios": 0, "erros": []}

    # 1. Empresas → Departamentos
    emp_resp = _atlas_sync_request("/api/empresas", email, senha)
    if emp_resp and emp_resp.get("data"):
        for emp in emp_resp["data"]:
            if emp.get("ativo", 1):
                db.get_or_create_dept_from_atlas_empresa(emp["id"], emp["nome"])
                stats["departamentos"] += 1

    # 2. Pessoas → Usuários
    pess_resp = _atlas_sync_request("/api/pessoas", email, senha)
    if pess_resp and pess_resp.get("data"):
        for p in pess_resp["data"]:
            if not p.get("ativo", True):
                continue
            try:
                funcoes_raw = p.get("funcoes_nomes") or ""
                funcoes = [f.strip() for f in funcoes_raw.split(",") if f.strip()]
                atlas_user = {
                    "nome":         p["nome"],
                    "email":        p["email"],
                    "funcoes":      funcoes,
                    "empresa_id":   p.get("empresa_id"),
                    "empresa_nome": p.get("empresa_nome") or "",
                }
                db.get_or_create_user_from_atlas(atlas_user)
                stats["usuarios"] += 1
            except Exception as e:
                stats["erros"].append(f"{p.get('email','?')}: {e}")

    return stats


# ── Static ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    token = request.args.get("atlas_token", "").strip()
    if token and not session.get("user_id"):
        _sso_login(token)
    return send_from_directory(BASE_DIR, "oraculo.html")


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
    return _ok({"id": u["id"], "nome": u["nome"], "email": u["email"],
                "role": u["role"], "role_atlas": ac.get_atlas_role(),
                "escopo": ac.get_atlas_escopo(),
                "departamento_id": u.get("departamento_id")})


# ── Users ─────────────────────────────────────────────────────────────────────

@app.route("/api/users")
@require_auth
def list_users():
    return _ok(db.list_users())


@app.route("/api/users", methods=["POST"])
@require_role("admin")
def create_user():
    return _err(
        "Usuários são gerenciados pelo Atlas. "
        "Cadastre a pessoa no Atlas (localhost:5010) e use Sincronizar para importá-la.",
        405
    )


@app.route("/api/users/<int:uid>", methods=["PUT"])
@require_role("admin")
def update_user(uid):
    # Permite apenas trocar o role local (mapeamento funcional interno)
    d = request.json or {}
    if not db.get_user(uid):
        return _err("Usuário não encontrado.", 404)
    allowed = {k: d[k] for k in ["role", "departamento_id"] if k in d}
    if allowed:
        db.update_user(uid, allowed)
    return _ok()


@app.route("/api/users/<int:uid>", methods=["DELETE"])
@require_role("admin")
def delete_user(uid):
    return _err(
        "Usuários são gerenciados pelo Atlas. "
        "Desative a pessoa no Atlas para revogar o acesso.",
        405
    )


# ── Atlas Sync ────────────────────────────────────────────────────────────────

@app.route("/api/atlas/sync", methods=["POST"])
@require_role("admin", "editor")
def atlas_sync():
    """Sincroniza empresas (→ departamentos) e pessoas (→ usuários) do Atlas."""
    d     = request.json or {}
    email = d.get("email", "").strip().lower()
    senha = d.get("senha", "")
    if not email or not senha:
        return _err("Informe e-mail e senha do Atlas para sincronizar.")
    if not ac._atlas_running():
        return _err("Atlas não está acessível em localhost:5010.")
    stats = _do_atlas_sync(email, senha)
    if stats["departamentos"] == 0 and stats["usuarios"] == 0:
        return _err("Credenciais inválidas no Atlas ou nenhum dado encontrado.")
    return _ok(stats)


# ── Departments ───────────────────────────────────────────────────────────────

@app.route("/api/departments")
@require_auth
def list_departments():
    return _ok(db.list_departments())


@app.route("/api/departments", methods=["POST"])
@require_role("admin", "editor")
def create_department():
    return _err(
        "Departamentos são herdados do Atlas (empresas). "
        "Crie a empresa no Atlas e use Sincronizar para importá-la.",
        405
    )


@app.route("/api/departments/<int:did>", methods=["PUT"])
@require_role("admin", "editor")
def update_department(did):
    if not db.get_department(did):
        return _err("Departamento não encontrado.", 404)
    d = request.json or {}
    # Apenas campos locais do Oráculo são editáveis; nome/empresa vêm do Atlas
    local_fields = {k: d[k] for k in ["horario_newsletter", "email_responsavel"] if k in d}
    if local_fields:
        db.update_department(did, local_fields)
    if "categorias" in d:
        db.set_department_categories(did, d["categorias"])
    return _ok()


@app.route("/api/departments/<int:did>", methods=["DELETE"])
@require_role("admin")
def delete_department(did):
    return _err(
        "Departamentos são herdados do Atlas. "
        "Desative a empresa no Atlas para removê-la.",
        405
    )


@app.route("/api/departments/<int:did>/categories")
@require_auth
def dept_categories(did):
    return _ok(db.get_department_categories(did))


# ── Categories ────────────────────────────────────────────────────────────────

@app.route("/api/categories")
@require_auth
def list_categories():
    return _ok(db.list_categories())


@app.route("/api/categories", methods=["POST"])
@require_role("admin", "editor")
def create_category():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    new_id = db.create_category(d)
    return _ok({"id": new_id}), 201


@app.route("/api/categories/<int:cid>", methods=["PUT"])
@require_role("admin", "editor")
def update_category(cid):
    if not db.get_category(cid):
        return _err("Categoria não encontrada.", 404)
    db.update_category(cid, request.json or {})
    return _ok()


@app.route("/api/categories/<int:cid>", methods=["DELETE"])
@require_role("admin")
def delete_category(cid):
    db.delete_category(cid)
    return _ok()


# ── News Sources ──────────────────────────────────────────────────────────────

@app.route("/api/sources")
@require_auth
def list_sources():
    return _ok(db.list_sources())


@app.route("/api/sources", methods=["POST"])
@require_role("admin", "editor")
def create_source():
    d = request.json or {}
    for f in ["nome", "url"]:
        if not d.get(f):
            return _err(f"Campo obrigatório: {f}")
    new_id = db.create_source(d)
    return _ok({"id": new_id}), 201


@app.route("/api/sources/<int:sid>", methods=["PUT"])
@require_role("admin", "editor")
def update_source(sid):
    if not db.get_source(sid):
        return _err("Fonte não encontrada.", 404)
    db.update_source(sid, request.json or {})
    return _ok()


@app.route("/api/sources/<int:sid>", methods=["DELETE"])
@require_role("admin")
def delete_source(sid):
    db.delete_source(sid)
    return _ok()


@app.route("/api/sources/<int:sid>/fetch", methods=["POST"])
@require_role("admin", "editor")
def fetch_source(sid):
    src = db.get_source(sid)
    if not src:
        return _err("Fonte não encontrada.", 404)
    count, err = _do_fetch_source(src)
    if err:
        return _err(err)
    return _ok({"coletadas": count})


@app.route("/api/sources/fetch-all", methods=["POST"])
@require_role("admin", "editor")
def fetch_all_sources():
    sources = [s for s in db.list_sources() if s["ativo"] and s["tipo"] == "rss"]
    total = 0
    for src in sources:
        count, _ = _do_fetch_source(src)
        total += count
    return _ok({"coletadas": total, "fontes": len(sources)})


def _do_fetch_source(src: dict) -> tuple[int, str | None]:
    if not HAS_FEEDPARSER:
        return 0, "feedparser não instalado. Execute: pip install feedparser"
    try:
        feed  = feedparser.parse(src["url"])
        count = 0
        for entry in feed.entries:
            url   = entry.get("link", "")
            if url and db.news_url_exists(url):
                continue
            titulo = entry.get("title", "Sem título")[:500]
            resumo = entry.get("summary", "")[:2000]
            pub    = entry.get("published", "") or entry.get("updated", "")
            nid    = db.create_news({
                "titulo":       titulo,
                "resumo":       resumo,
                "url":          url,
                "fonte_id":     src["id"],
                "publicado_em": pub[:10] if pub else None,
                "relevancia":   0.7,
            })
            count += 1
        db.update_source_last_fetch(src["id"])
        return count, None
    except Exception as e:
        return 0, str(e)


# ── News ──────────────────────────────────────────────────────────────────────

@app.route("/api/news")
@require_auth
def list_news():
    filters = {k: request.args.get(k) for k in
               ["categoria_id", "fonte_id", "min_relevancia", "desde"]}
    limit = int(request.args.get("limit", 100))
    return _ok(db.list_news(filters, limit))


@app.route("/api/news/<int:nid>")
@require_auth
def get_news(nid):
    n = db.get_news(nid)
    if not n:
        return _err("Notícia não encontrada.", 404)
    return _ok(n)


@app.route("/api/news", methods=["POST"])
@require_role("admin", "editor")
def create_news():
    d = request.json or {}
    if not d.get("titulo"):
        return _err("Título é obrigatório.")
    nid = db.create_news(d)
    if d.get("categorias"):
        db.set_news_categories(nid, d["categorias"])
    return _ok({"id": nid}), 201


@app.route("/api/news/<int:nid>", methods=["PUT"])
@require_role("admin", "editor")
def update_news(nid):
    if not db.get_news(nid):
        return _err("Notícia não encontrada.", 404)
    d = request.json or {}
    db.update_news(nid, d)
    if "categorias" in d:
        db.set_news_categories(nid, d["categorias"])
    return _ok()


@app.route("/api/news/<int:nid>", methods=["DELETE"])
@require_role("admin", "editor")
def delete_news(nid):
    if not db.get_news(nid):
        return _err("Notícia não encontrada.", 404)
    db.delete_news(nid)
    return _ok()


# ── KPIs ──────────────────────────────────────────────────────────────────────

@app.route("/api/kpis")
@require_auth
def list_kpis():
    dept = request.args.get("departamento_id")
    return _ok(db.list_kpis(dept))


@app.route("/api/kpis", methods=["POST"])
@require_role("admin", "editor")
def create_kpi():
    d = request.json or {}
    if not d.get("nome"):
        return _err("Nome é obrigatório.")
    new_id = db.create_kpi(d)
    return _ok({"id": new_id}), 201


@app.route("/api/kpis/<int:kid>", methods=["PUT"])
@require_role("admin", "editor")
def update_kpi(kid):
    if not db.get_kpi(kid):
        return _err("KPI não encontrado.", 404)
    db.update_kpi(kid, request.json or {})
    return _ok()


@app.route("/api/kpis/<int:kid>", methods=["DELETE"])
@require_role("admin")
def delete_kpi(kid):
    db.delete_kpi(kid)
    return _ok()


@app.route("/api/kpis/<int:kid>/values")
@require_auth
def kpi_values(kid):
    return _ok(db.list_kpi_values(kid))


@app.route("/api/kpis/<int:kid>/values", methods=["POST"])
@require_role("admin", "editor")
def add_kpi_value(kid):
    d = request.json or {}
    if d.get("valor") is None:
        return _err("Valor é obrigatório.")
    d["kpi_id"] = kid
    new_id = db.add_kpi_value(d)
    return _ok({"id": new_id}), 201


# ── Insights ──────────────────────────────────────────────────────────────────

@app.route("/api/insights")
@require_auth
def list_insights():
    dept = request.args.get("departamento_id")
    return _ok(db.list_insights(dept))


@app.route("/api/insights", methods=["POST"])
@require_role("admin", "editor")
def create_insight():
    d = request.json or {}
    for f in ["titulo", "descricao"]:
        if not d.get(f):
            return _err(f"Campo obrigatório: {f}")
    new_id = db.create_insight(d)
    return _ok({"id": new_id}), 201


@app.route("/api/insights/<int:iid>", methods=["PUT"])
@require_role("admin", "editor")
def update_insight(iid):
    if not db.get_insight(iid):
        return _err("Insight não encontrado.", 404)
    db.update_insight(iid, request.json or {})
    return _ok()


@app.route("/api/insights/<int:iid>", methods=["DELETE"])
@require_role("admin", "editor")
def delete_insight(iid):
    db.delete_insight(iid)
    return _ok()


# ── Newsletter ────────────────────────────────────────────────────────────────

@app.route("/api/newsletters")
@require_auth
def list_newsletters():
    dept = request.args.get("departamento_id")
    return _ok(db.list_newsletters(dept))


@app.route("/api/newsletters/<int:nlid>")
@require_auth
def get_newsletter(nlid):
    nl = db.get_newsletter(nlid)
    if not nl:
        return _err("Newsletter não encontrada.", 404)
    return _ok(nl)


@app.route("/api/newsletters/generate", methods=["POST"])
@require_role("admin", "editor")
def generate_newsletter():
    d    = request.json or {}
    did  = d.get("departamento_id")
    if not did:
        return _err("departamento_id é obrigatório.")
    dept = db.get_department(did)
    if not dept:
        return _err("Departamento não encontrado.", 404)

    since = (datetime.now() - timedelta(hours=24)).isoformat(timespec="seconds")

    insights = db.get_insights_for_newsletter(did, since)
    kpis     = db.get_kpi_values_for_newsletter(did, since)
    noticias = db.get_news_for_newsletter(did, since)

    # Regra: pelo menos 1 KPI ou 1 insight
    if not insights and not kpis:
        return _err("Sem KPIs ou Insights suficientes para gerar a newsletter.")

    conteudo = {
        "titulo":    f"Newsletter — {dept['nome']} — {datetime.now().strftime('%d/%m/%Y')}",
        "insights":  insights[:2],
        "kpis":      kpis[:3],
        "noticias":  noticias[:3],
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
    }

    nlid = db.create_newsletter(did, json.dumps(conteudo, ensure_ascii=False))
    return _ok({"id": nlid, "conteudo": conteudo}), 201


@app.route("/api/newsletters/<int:nlid>/send", methods=["POST"])
@require_role("admin", "editor")
def send_newsletter(nlid):
    nl = db.get_newsletter(nlid)
    if not nl:
        return _err("Newsletter não encontrada.", 404)

    smtp = db.get_smtp_config()
    if not smtp.get("ativo") or not smtp.get("host"):
        return _err("SMTP não configurado ou inativo. Configure em Configurações.")

    # Destinatários: usuários do departamento + email_responsavel do dept
    dept  = db.get_department(nl["departamento_id"]) or {}
    users = [u for u in db.list_users() if u.get("departamento_id") == nl["departamento_id"]]

    # Adiciona email_responsavel como destinatário extra (se não estiver já na lista)
    emails_na_lista = {u["email"] for u in users}
    responsavel     = (dept.get("email_responsavel") or "").strip()
    if responsavel and responsavel not in emails_na_lista:
        users = users + [{"email": responsavel, "nome": f"Responsável — {dept.get('nome','')}"}]

    if not users:
        return _err("Nenhum destinatário encontrado no departamento.")

    conteudo = json.loads(nl["conteudo_json"])
    html     = _build_email_html(conteudo)
    subject  = conteudo.get("titulo", "Newsletter Corporativa")

    try:
        _send_emails(smtp, users, subject, html)
        db.update_dispatch(nlid, "enviado", len(users))
        return _ok({"enviado_para": len(users)})
    except Exception as e:
        db.update_dispatch(nlid, "erro", 0, str(e))
        return _err(f"Falha ao enviar: {e}")


def _build_email_html(conteudo: dict) -> str:
    insights_html = ""
    for ins in conteudo.get("insights", []):
        cor = {"alto": "#dc2626", "medio": "#d97706", "baixo": "#16a34a"}.get(ins["impacto"], "#475569")
        insights_html += f"""
        <div style="border-left:3px solid {cor};padding:8px 14px;margin-bottom:10px;background:#f8fafc">
          <strong style="color:{cor}">[{ins['impacto'].upper()}]</strong>
          <strong>{ins['titulo']}</strong><br>
          <span style="color:#475569">{ins['descricao']}</span>
        </div>"""

    kpis_html = ""
    for kv in conteudo.get("kpis", []):
        kpis_html += f"""
        <div style="display:inline-block;border:1px solid #e2e8f0;border-radius:6px;
                    padding:12px 20px;margin:4px;text-align:center">
          <div style="font-size:1.3rem;font-weight:700;color:#0284c7">{kv['valor']} {kv.get('unidade','')}</div>
          <div style="font-size:.75rem;color:#94a3b8">{kv['nome']}</div>
        </div>"""

    noticias_html = ""
    for n in conteudo.get("noticias", []):
        noticias_html += f"""
        <div style="border-bottom:1px solid #e2e8f0;padding:10px 0">
          <a href="{n.get('url','#')}" style="color:#0284c7;font-weight:600;text-decoration:none">
            {n['titulo']}
          </a>
          <p style="color:#475569;margin:4px 0 0;font-size:.85rem">{n.get('resumo','')[:200]}</p>
        </div>"""

    return f"""
    <html><body style="font-family:'Segoe UI',Arial,sans-serif;max-width:640px;margin:0 auto;padding:24px">
      <div style="border-bottom:3px solid #0284c7;padding-bottom:16px;margin-bottom:24px">
        <h1 style="color:#0f172a;font-size:1.4rem;margin:0">{conteudo.get('titulo','Newsletter')}</h1>
        <span style="color:#94a3b8;font-size:.8rem">{conteudo.get('gerado_em','')}</span>
      </div>
      {'<h2 style="font-size:1rem;color:#0f172a">Insights</h2>' + insights_html if insights_html else ''}
      {'<h2 style="font-size:1rem;color:#0f172a">KPIs</h2><div>' + kpis_html + '</div>' if kpis_html else ''}
      {'<h2 style="font-size:1rem;color:#0f172a">Notícias</h2>' + noticias_html if noticias_html else ''}
      <div style="margin-top:32px;padding-top:16px;border-top:1px solid #e2e8f0;
                  color:#94a3b8;font-size:.75rem;text-align:center">
        Gerado automaticamente pelo Oráculo — Sistema Olimpus
      </div>
    </body></html>"""


def _send_emails(smtp_cfg: dict, users: list, subject: str, html: str):
    server = smtplib.SMTP(smtp_cfg["host"], smtp_cfg["porta"], timeout=10)
    if smtp_cfg.get("use_tls"):
        server.starttls()
    if smtp_cfg.get("usuario"):
        server.login(smtp_cfg["usuario"], smtp_cfg["senha"])
    for u in users:
        msg              = MIMEMultipart("alternative")
        msg["Subject"]   = subject
        msg["From"]      = smtp_cfg.get("remetente") or smtp_cfg["usuario"]
        msg["To"]        = u["email"]
        msg.attach(MIMEText(html, "html", "utf-8"))
        server.send_message(msg)
    server.quit()


# ── SMTP Config ───────────────────────────────────────────────────────────────

@app.route("/api/config/smtp")
@require_role("admin")
def get_smtp():
    cfg = db.get_smtp_config()
    # Não retorna senha
    cfg.pop("senha", None)
    return _ok(cfg)


@app.route("/api/config/smtp", methods=["PUT"])
@require_role("admin")
def update_smtp():
    d = request.json or {}
    # Só atualiza senha se foi enviada (não vazia)
    if not d.get("senha"):
        d.pop("senha", None)
    db.update_smtp_config(d)
    return _ok()


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
@require_auth
def dashboard():
    return _ok(db.get_dashboard_stats())


# ── Scheduler ─────────────────────────────────────────────────────────────────

def _job_fetch_rss():
    """Coleta RSS de todas as fontes ativas."""
    sources = [s for s in db.list_sources() if s["ativo"] and s["tipo"] == "rss"]
    for src in sources:
        try:
            _do_fetch_source(src)
        except Exception:
            pass


def _job_generate_newsletters():
    """Gera newsletters diárias para todos os departamentos."""
    since = (datetime.now() - timedelta(hours=24)).isoformat(timespec="seconds")
    for dept in db.list_departments():
        did = dept["id"]
        try:
            insights = db.get_insights_for_newsletter(did, since)
            kpis     = db.get_kpi_values_for_newsletter(did, since)
            noticias = db.get_news_for_newsletter(did, since)

            if not insights and not kpis:
                continue  # NewsletterSkipped

            conteudo = {
                "titulo":    f"Newsletter — {dept['nome']} — {datetime.now().strftime('%d/%m/%Y')}",
                "insights":  insights[:2],
                "kpis":      kpis[:3],
                "noticias":  noticias[:3],
                "gerado_em": datetime.now().isoformat(timespec="seconds"),
                "automatico": True,
            }
            nlid = db.create_newsletter(did, json.dumps(conteudo, ensure_ascii=False))

            # Tenta enviar se SMTP ativo
            smtp = db.get_smtp_config()
            if smtp.get("ativo") and smtp.get("host"):
                users = [u for u in db.list_users() if u.get("departamento_id") == did]
                # Adiciona email_responsavel do departamento como destinatário extra
                emails_na_lista = {u["email"] for u in users}
                responsavel     = (dept.get("email_responsavel") or "").strip()
                if responsavel and responsavel not in emails_na_lista:
                    users = users + [{"email": responsavel,
                                      "nome": f"Responsável — {dept['nome']}"}]
                if users:
                    html = _build_email_html(conteudo)
                    try:
                        _send_emails(smtp, users, conteudo["titulo"], html)
                        db.update_dispatch(nlid, "enviado", len(users))
                    except Exception as e:
                        db.update_dispatch(nlid, "erro", 0, str(e))
        except Exception:
            pass


def _setup_scheduler():
    if not HAS_SCHEDULER:
        return
    sched = BackgroundScheduler(timezone="America/Sao_Paulo")
    # Coleta RSS a cada 2 horas
    sched.add_job(_job_fetch_rss, "interval", hours=2, id="fetch_rss")
    # Newsletter diária às 08:00
    sched.add_job(_job_generate_newsletters, "cron", hour=8, minute=0, id="newsletter_daily")
    sched.start()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    _setup_scheduler()
    print(f"\n ORÁCULO rodando em http://localhost:{PORT}\n")
    if not HAS_FEEDPARSER:
        print(" AVISO: feedparser não instalado — coleta RSS desativada.")
    if not HAS_SCHEDULER:
        print(" AVISO: apscheduler não instalado — newsletter automática desativada.")
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)
