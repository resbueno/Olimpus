from __future__ import annotations
"""
app.py — API REST Flask + servidor do painel Héstia
Intranet Corporativa
"""

import json
import logging
import os
import signal
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from flask import Flask, jsonify, request, send_from_directory, session, send_file
from werkzeug.utils import secure_filename
from flask_cors import CORS

import database as db
import auth
import atlas_client as ac

ac.SISTEMA_FOLDER = "Héstia - Intranet Corporativa"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("hestia.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
app.secret_key = open(os.path.join(BASE_DIR, "secret.key"), "rb").read()[:32] if os.path.exists(os.path.join(BASE_DIR, "secret.key")) else os.urandom(32)
app.permanent_session_lifetime = timedelta(hours=12)
CORS(app, supports_credentials=True)


def _err(msg, code=400):
    return jsonify({"error": msg}), code


def _ok(data=None, **kwargs):
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    payload.update(kwargs)
    return jsonify(payload)


@app.route("/api/settings", methods=["GET"])
def get_settings():
    settings = db.get_settings()
    return _ok(settings)


@app.route("/api/settings", methods=["POST"])
@auth.require_auth
def update_settings():
    user = auth.get_current_user()
    funcoes = user.get("funcoes", [])
    if "admin" not in funcoes and "administrador" not in funcoes:
        return _err("Apenas administradores podem alterar as configurações.")
    
    data = request.json
    for key, value in data.items():
        db.update_setting(key, value)
    return _ok(message="Configurações atualizadas.")


@app.route("/api/settings/logo", methods=["POST"])
@auth.require_auth
def upload_logo():
    user = auth.get_current_user()
    funcoes = user.get("funcoes", [])
    if "admin" not in funcoes and "administrador" not in funcoes:
        return _err("Apenas administradores podem alterar o logo.")
    
    if "file" not in request.files:
        return _err("Nenhum arquivo enviado.")
    file = request.files["file"]
    
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads", "branding")
    os.makedirs(upload_dir, exist_ok=True)
    
    filename = secure_filename(file.filename)
    safe_name = f"logo_{int(datetime.now().timestamp())}_{filename}"
    file_path = os.path.join(upload_dir, safe_name)
    file.save(file_path)
    
    # Gerar URL relativa para o frontend
    logo_url = f"/api/settings/logo/file?p={safe_name}"
    db.update_setting("header_logo_url", logo_url)
    
    return _ok({"url": logo_url}, message="Logo atualizado.")


@app.route("/api/settings/logo/file")
def get_logo_file():
    safe_name = request.args.get("p")
    if not safe_name:
        return _err("Arquivo não especificado.", 400)
    
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads", "branding")
    file_path = os.path.join(upload_dir, safe_name)
    
    if not os.path.exists(file_path):
        return _err("Arquivo não encontrado.", 404)
        
    return send_file(file_path)


# ── Static ────────────────────────────────────────────────────────────────────

def _sso_login(token: str):
    """Tenta criar sessão Héstia a partir de token Atlas (SSO)."""
    ac.sso_login_from_token(token)


@app.route("/")
def index():
    token = request.args.get("atlas_token", "").strip()
    if token and not ac.is_atlas_authenticated():
        _sso_login(token)
    return send_from_directory(BASE_DIR, "dashboard.html")


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    email    = data.get("email", data.get("username", "")).strip().lower()
    password = data.get("password", "")
    atlas_user = ac.login_with_credentials(email, password)
    if atlas_user:
        return _ok({
            "nome":   atlas_user.get("nome"),
            "email":  atlas_user.get("email"),
            "funcoes": atlas_user.get("funcoes", []),
            "is_admin": ac.is_admin(),
            "role_atlas": ac.get_atlas_role(),
            "escopo": ac.get_atlas_escopo(),
        }, message="Login realizado com sucesso.")
    return _err("E-mail ou senha inválidos, ou acesso à Héstia não autorizado.", 401)


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    auth.logout_user()
    return _ok(message="Sessão encerrada.")


@app.route("/api/auth/status", methods=["GET"])
def auth_status():
    u = ac.get_atlas_user()
    return _ok({
        "authenticated": ac.is_atlas_authenticated(),
        "is_admin": ac.is_admin(),
        "user": u,
        "role_atlas": ac.get_atlas_role(),
        "escopo": ac.get_atlas_escopo(),
    })


# ── News (Feed de Notícias) ──────────────────────────────────────────────────

@app.route("/api/news", methods=["GET"])
def get_news():
    limit = int(request.args.get("limit", 20))
    news = db.list_news(limit)
    return _ok(news)


@app.route("/api/news/<int:nid>", methods=["GET"])
def get_news_item(nid):
    item = db.get_news(nid)
    if not item:
        return _err("Notícia não encontrada.", 404)
    return _ok(item)


@app.route("/api/news", methods=["POST"])
@auth.require_auth
def create_news():
    data = request.json or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    if not title or not content:
        return _err("Título e conteúdo são obrigatórios.")
    user = auth.get_current_user()
    new_id = db.create_news(title, content, user.get("id"), user.get("nome"))
    return _ok({"id": new_id}, message="Notícia publicada."), 201


@app.route("/api/news/<int:nid>", methods=["PUT"])
@auth.require_auth
def update_news(nid):
    data = request.json or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    if not title or not content:
        return _err("Título e conteúdo são obrigatórios.")
    db.update_news(nid, title, content)
    return _ok(message="Notícia atualizada.")


@app.route("/api/news/<int:nid>", methods=["DELETE"])
@auth.require_auth
def delete_news(nid):
    db.delete_news(nid)
    return _ok(message="Notícia removida.")


@app.route("/api/news/<int:nid>/attachments", methods=["GET"])
def get_news_attachments(nid):
    attachments = db.list_news_attachments(nid)
    return _ok(attachments)


@app.route("/api/news/<int:nid>/attachments", methods=["POST"])
@auth.require_auth
def upload_news_attachment(nid):
    if "file" not in request.files:
        return _err("Nenhum arquivo enviado.")
    file = request.files["file"]
    if file.filename == "":
        return _err("Arquivo sem nome.")
    
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads", "news", str(nid))
    os.makedirs(upload_dir, exist_ok=True)
    
    filename = secure_filename(file.filename)
    safe_name = f"{int(datetime.now().timestamp())}_{filename}"
    file_path = os.path.join(upload_dir, safe_name)
    file.save(file_path)
    
    user = auth.get_current_user()
    db.add_news_attachment(
        nid, 
        filename, 
        file_path, 
        file.content_type, 
        os.path.getsize(file_path), 
        user.get("id")
    )
    return _ok(message="Anexo de notícia enviado.")


@app.route("/api/news/attachments/<int:aid>", methods=["GET"])
def download_news_attachment(aid):
    conn = db.get_conn()
    att = conn.execute("SELECT * FROM news_attachments WHERE id = ?", (aid,)).fetchone()
    conn.close()
    if not att:
        return _err("Anexo não encontrado.", 404)
    return send_file(att["file_path"], as_attachment=True, download_name=att["filename"])


# ── Documents (Documentos) ───────────────────────────────────────────────────

@app.route("/api/documents", methods=["GET"])
def get_documents():
    folder_id = request.args.get("folder_id")
    if folder_id == "" or folder_id == "null":
        folder_id = None
    docs = db.list_documents(folder_id)
    return _ok(docs)


@app.route("/api/documents/folders", methods=["GET"])
def get_folders():
    parent_id = request.args.get("parent_id")
    user = auth.get_current_user() or {}
    roles = user.get("funcoes", [])
    dept = user.get("departamento")
    folders = db.list_folders(parent_id, roles, dept)
    return _ok(folders)


@app.route("/api/documents/folders", methods=["POST"])
@auth.require_auth
def create_folder():
    data = request.json or {}
    name = data.get("name", "").strip()
    parent_id = data.get("parent_id")
    rules = data.get("rules", []) # Lista de {'role': '...', 'dept': '...'}
    
    if not name:
        return _err("Nome da pasta é obrigatório.")
    
    user = auth.get_current_user()
    new_id = db.create_folder(name, parent_id, user.get("id"))
    
    if rules:
        db.set_folder_access(new_id, rules)
        
    return _ok({"id": new_id}, message="Pasta criada.")


@app.route("/api/documents/folders/<int:fid>/access", methods=["PUT"])
@auth.require_auth
def set_folder_access(fid):
    data = request.json or {}
    rules = data.get("rules", [])
    db.set_folder_access(fid, rules)
    return _ok(message="Permissões atualizadas.")


@app.route("/api/departments", methods=["GET"])
def get_departments():
    depts = db.list_departments()
    return _ok(depts)


@app.route("/api/documents", methods=["POST"])
@auth.require_auth
def create_document():
    data = request.json or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    folder_id = data.get("folder_id")
    if folder_id == "" or folder_id == "null":
        folder_id = None
    if not title:
        return _err("Título é obrigatório.")
    user = auth.get_current_user()
    new_id = db.create_document(title, content, folder_id, user.get("id"), user.get("nome"))
    return _ok({"id": new_id}, message="Documento criado."), 201


@app.route("/api/documents/<int:did>", methods=["GET"])
def get_document(did):
    doc = db.get_document(did)
    if not doc:
        return _err("Documento não encontrado.", 404)
    return _ok(doc)


@app.route("/api/documents/<int:did>", methods=["PUT"])
@auth.require_auth
def update_document(did):
    data = request.json or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    if not title:
        return _err("Título é obrigatório.")
    user = auth.get_current_user()
    db.update_document(did, title, content, user.get("id"), user.get("nome"))
    return _ok(message="Documento atualizado.")


@app.route("/api/documents/<int:did>/versions", methods=["GET"])
def get_document_versions(did):
    versions = db.list_versions(did)
    return _ok(versions)


@app.route("/api/documents/<int:did>/attachments", methods=["GET"])
def get_document_attachments(did):
    attachments = db.list_attachments(did)
    return _ok(attachments)


@app.route("/api/documents/<int:did>/attachments", methods=["POST"])
@auth.require_auth
def upload_attachment(did):
    if "file" not in request.files:
        return _err("Nenhum arquivo enviado.")
    file = request.files["file"]
    if file.filename == "":
        return _err("Arquivo sem nome.")
    
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads", str(did))
    os.makedirs(upload_dir, exist_ok=True)
    
    filename = secure_filename(file.filename)
    # Evitar sobrescrever se o nome for igual? Talvez adicionar timestamp
    safe_name = f"{int(datetime.now().timestamp())}_{filename}"
    file_path = os.path.join(upload_dir, safe_name)
    file.save(file_path)
    
    user = auth.get_current_user()
    db.add_attachment(
        did, 
        filename, 
        file_path, 
        file.content_type, 
        os.path.getsize(file_path), 
        user.get("id")
    )
    return _ok(message="Anexo enviado com sucesso.")


@app.route("/api/attachments/<int:aid>", methods=["GET"])
def download_attachment(aid):
    conn = db.get_conn()
    att = conn.execute("SELECT * FROM document_attachments WHERE id = ?", (aid,)).fetchone()
    conn.close()
    if not att:
        return _err("Anexo não encontrado.", 404)
    
    return send_file(att["file_path"], as_attachment=True, download_name=att["filename"])


@app.route("/api/documents/<int:did>", methods=["DELETE"])
@auth.require_auth
def delete_document(did):
    db.delete_document(did)
    return _ok(message="Documento removido.")




# ── People (Pessoas/Diretório) ───────────────────────────────────────────────

@app.route("/api/people", methods=["GET"])
def get_people():
    search = request.args.get("search", "").strip()
    people = db.list_people(search)
    return _ok(people)


@app.route("/api/people/<int:pid>", methods=["GET"])
def get_person(pid):
    person = db.get_person(pid)
    if not person:
        return _err("Pessoa não encontrada.", 404)
    return _ok(person)


@app.route("/api/people/sync", methods=["POST"])
@auth.require_admin
def sync_people():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    senha = data.get("senha", "")
    if not email or not senha:
        return _err("Informe e-mail e senha do Atlas.")
    try:
        import http.cookiejar
        cj     = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

        # 1. Login no Atlas com as credenciais fornecidas
        body = json.dumps({"email": email, "senha": senha}).encode()
        req  = urllib.request.Request(
            f"{auth.ATLAS_URL}/api/auth/login",
            data=body, headers={"Content-Type": "application/json"}, method="POST",
        )
        with opener.open(req, timeout=5) as resp:
            login_resp = json.loads(resp.read())
        if not login_resp.get("ok"):
            return _err("Credenciais inválidas no Atlas.", 401)

        # 2. Busca lista de pessoas
        with opener.open(f"{auth.ATLAS_URL}/api/pessoas", timeout=10) as resp:
            people_resp = json.loads(resp.read())

        users = people_resp.get("data", [])
        synced = 0
        for u in users:
            if not u.get("ativo", True):
                continue
            db.upsert_person(
                user_id=str(u.get("id", "")),
                nome=u.get("nome", ""),
                email=u.get("email", ""),
                cargo=u.get("cargo", ""),
                departamento=u.get("empresa_nome", ""),
            )
            synced += 1
        return _ok({"synced": synced}, message=f"{synced} pessoas sincronizadas.")
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP Error sincronizando: {e.code}")
        return _err(f"Atlas retornou erro {e.code}.", 400)
    except urllib.error.URLError as e:
        logger.error(f"URL Error sincronizando: {e.reason}")
        return _err(f"Não foi possível acessar o Atlas: {e.reason}.", 400)
    except Exception as e:
        logger.error(f"Erro ao sincronizar: {e}")
        return _err(f"Erro: {str(e)}", 400)


@app.route("/api/people/birthdays", methods=["GET"])
def get_birthdays():
    days = int(request.args.get("days", 30))
    birthdays = db.get_birthdays(days)
    return _ok(birthdays)


@app.route("/api/people/kudos", methods=["GET"])
def get_kudos():
    limit = int(request.args.get("limit", 20))
    kudos = db.list_kudos(limit)
    return _ok(kudos)


@app.route("/api/people/kudos", methods=["POST"])
@auth.require_auth
def create_kudos():
    data = request.json or {}
    to_user_id = data.get("to_user_id")
    message = data.get("message", "").strip()
    if not to_user_id or not message:
        return _err("Usuário e mensagem são obrigatórios.")
    user = auth.get_current_user()
    new_id = db.create_kudos(to_user_id, user.get("id"), message)
    return _ok({"id": new_id}, message="Kudos enviado!"), 201


# ── Communities (Comunidades) ─────────────────────────────────────────────────

@app.route("/api/communities", methods=["GET"])
def get_communities():
    communities = db.list_communities()
    return _ok(communities)


@app.route("/api/communities/<int:cid>", methods=["GET"])
def get_community(cid):
    community = db.get_community(cid)
    if not community:
        return _err("Comunidade não encontrada.", 404)
    return _ok(community)


@app.route("/api/communities", methods=["POST"])
@auth.require_admin
def create_community():
    data = request.json or {}
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    if not name:
        return _err("Nome da comunidade é obrigatório.")
    user = auth.get_current_user()
    new_id = db.create_community(name, description, user.get("id"))
    return _ok({"id": new_id}, message="Comunidade criada."), 201


@app.route("/api/communities/<int:cid>/join", methods=["POST"])
@auth.require_auth
def join_community(cid):
    user = auth.get_current_user()
    db.join_community(cid, user.get("id"))
    return _ok(message="Você entrou na comunidade.")


@app.route("/api/communities/<int:cid>/leave", methods=["POST"])
@auth.require_auth
def leave_community(cid):
    user = auth.get_current_user()
    db.leave_community(cid, user.get("id"))
    return _ok(message="Você saiu da comunidade.")


@app.route("/api/communities/<int:cid>", methods=["PUT"])
@auth.require_admin
def update_community(cid):
    data = request.json or {}
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    if not name:
        return _err("Nome da comunidade é obrigatório.")
    db.update_community(cid, name, description)
    return _ok(message="Comunidade atualizada.")


@app.route("/api/communities/<int:cid>", methods=["DELETE"])
@auth.require_admin
def delete_community(cid):
    db.delete_community(cid)
    return _ok(message="Comunidade removida.")


@app.route("/api/communities/<int:cid>/messages", methods=["GET"])
def get_community_messages(cid):
    messages = db.list_community_messages(cid)
    return _ok(messages)


@app.route("/api/communities/<int:cid>/messages", methods=["POST"])
@auth.require_auth
def post_community_message(cid):
    data = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return _err("Mensagem é obrigatória.")
    user = auth.get_current_user()
    new_id = db.create_community_message(cid, user.get("id"), user.get("nome"), message)
    return _ok({"id": new_id}, message="Mensagem postada."), 201


# ── Events (Eventos/Calendário) ───────────────────────────────────────────────

@app.route("/api/events", methods=["GET"])
def get_events():
    start = request.args.get("start")
    end = request.args.get("end")
    events = db.list_events(start, end)
    return _ok(events)


@app.route("/api/events/<int:eid>", methods=["GET"])
def get_event(eid):
    event = db.get_event(eid)
    if not event:
        return _err("Evento não encontrado.", 404)
    return _ok(event)


@app.route("/api/events", methods=["POST"])
@auth.require_admin
def create_event():
    data = request.json or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    location = data.get("location", "").strip()
    meeting_link = data.get("meeting_link", "").strip()
    if not title or not start_date:
        return _err("Título e data de início são obrigatórios.")
    user = auth.get_current_user()
    new_id = db.create_event(title, description, start_date, end_date, location, meeting_link, user.get("id"))
    return _ok({"id": new_id}, message="Evento criado."), 201


@app.route("/api/events/<int:eid>", methods=["PUT"])
@auth.require_admin
def update_event(eid):
    data = request.json or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    location = data.get("location", "").strip()
    meeting_link = data.get("meeting_link", "").strip()
    if not title or not start_date:
        return _err("Título e data de início são obrigatórios.")
    db.update_event(eid, title, description, start_date, end_date, location, meeting_link)
    return _ok(message="Evento atualizado.")


@app.route("/api/events/<int:eid>", methods=["DELETE"])
@auth.require_admin
def delete_event(eid):
    db.delete_event(eid)
    return _ok(message="Evento removido.")


# ── Dashboard Stats ─────────────────────────────────────────────────────────

@app.route("/api/stats", methods=["GET"])
def global_stats():
    stats = db.get_global_stats()
    return _ok(stats)


# ── Ping ──────────────────────────────────────────────────────────────────────

@app.route("/api/ping", methods=["GET"])
def ping():
    return _ok({"timestamp": datetime.now().isoformat()})


# ── Bootstrap ────────────────────────────────────────────────────────────────

def _on_shutdown(sig, frame):
    logger.info("Encerrando Héstia...")
    sys.exit(0)


if __name__ == "__main__":
    db.init_db()
    from database import _get_or_create_key
    _get_or_create_key()
    app.secret_key = _get_or_create_key()[:32]
    signal.signal(signal.SIGINT, _on_shutdown)
    signal.signal(signal.SIGTERM, _on_shutdown)
    logger.info("Héstia iniciado em http://localhost:5020")
    app.run(host="0.0.0.0", port=5020, debug=False, use_reloader=False)
