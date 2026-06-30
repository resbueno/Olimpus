from __future__ import annotations
"""
atlas_client.py — Módulo de integração com o Atlas (IAM) para outros apps.
Coloque este arquivo na raiz de cada app que precisa validar tokens Atlas.

Versão 5.0 — RBAC com escopos (SELF/TEAM/COMPANY/GLOBAL) e permissões granulares.

Uso em outro app Flask:
    from atlas_client import (
        atlas_sso_bp, require_atlas, get_atlas_user,
        get_atlas_role, get_atlas_escopo, get_atlas_permissoes,
        is_admin, is_gestor, can_see_team, can_see_company,
        require_role, require_permissao,
        SISTEMA_FOLDER,
    )

    SISTEMA_FOLDER = "Cronos - Ponto Eletrônico"   # definir ANTES de importar
    app.register_blueprint(atlas_sso_bp)

    @app.route("/rota-protegida")
    @require_atlas
    def rota():
        user = get_atlas_user()
        role  = get_atlas_role()       # "USER", "GESTOR", "ADMIN", "ADMIN_GERAL"
        escopo = get_atlas_escopo()    # "SELF", "TEAM", "COMPANY", "GLOBAL"
        ...

Hierarquia de roles (nível):
    USER (0) → GESTOR (1) → ADMIN (2) → ADMIN_GERAL (3)

Escopos:
    SELF    → apenas dados próprios
    TEAM    → equipe (departamento)
    COMPANY → toda empresa
    GLOBAL  → todas empresas
"""
import base64
import hashlib
import hmac
import json
import os
import socket
import time
import urllib.parse
import urllib.request
from functools import wraps

from flask import Blueprint, jsonify, redirect, request, session

ATLAS_URL  = "http://localhost:5010"
ATLAS_PORT = 5010

# Cada app deve sobrescrever esta variável com seu próprio folder
SISTEMA_FOLDER = ""

_KEY_FILE = None  # resolvido lazy

# Hierarquia de roles — nível numérico
ROLE_NIVEL = {
    "USER": 0,
    "GESTOR": 1,
    "ADMIN": 2,
    "ADMIN_GERAL": 3,
}

ESCOPOS = ["SELF", "TEAM", "COMPANY", "GLOBAL"]


# ── Key management ──────────────────────────────────────────────────────────

def _find_key_file() -> str | None:
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "atlas.key"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Atlas - Gestão de Acessos", "atlas.key"),
    ]
    env_path = os.environ.get("ATLAS_KEY")
    if env_path:
        candidates.insert(0, env_path)
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _get_key() -> bytes | None:
    global _KEY_FILE
    if _KEY_FILE is None:
        _KEY_FILE = _find_key_file()
    if _KEY_FILE and os.path.isfile(_KEY_FILE):
        with open(_KEY_FILE, "rb") as f:
            return f.read()
    return None


def _b64d(s: str) -> dict:
    pad = 4 - len(s) % 4
    raw = base64.urlsafe_b64decode(s + "=" * pad)
    return json.loads(raw)


# ── Token validation ────────────────────────────────────────────────────────

def validate_atlas_token(token: str) -> dict | None:
    try:
        key = _get_key()
        if not key:
            return None
        parts = token.split(".")
        if len(parts) != 2:
            return None
        b64p, sig = parts
        expected = hmac.new(key, b64p.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = _b64d(b64p)
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


# ── Session helpers ─────────────────────────────────────────────────────────

def get_atlas_user() -> dict | None:
    """Retorna o payload do usuário Atlas da sessão atual."""
    return session.get("atlas_user")


def get_atlas_role(sistema_folder: str = None) -> str | None:
    """Retorna a role do usuário para o sistema (ex: 'USER', 'GESTOR', 'ADMIN', 'ADMIN_GERAL').
    Se sistema_folder não for informado, usa SISTEMA_FOLDER global.
    """
    user = get_atlas_user()
    if not user:
        return None
    sf = sistema_folder or SISTEMA_FOLDER
    roles = user.get("roles") or {}
    if isinstance(roles, dict) and sf and sf in roles:
        return roles[sf].get("role")
    # Se ADMIN_GERAL em qualquer sistema, é global
    if isinstance(roles, dict):
        for info in roles.values():
            if info.get("role") == "ADMIN_GERAL":
                return "ADMIN_GERAL"
    # Fallback legado
    funcoes = user.get("funcoes") or []
    if "admin" in funcoes:
        return "ADMIN"
    if "gestor" in funcoes:
        return "GESTOR"
    return "USER" if funcoes else None


def get_atlas_escopo(sistema_folder: str = None) -> str:
    """Retorna o escopo do usuário para o sistema (ex: 'SELF', 'TEAM', 'COMPANY', 'GLOBAL').
    Default: 'SELF'.
    """
    user = get_atlas_user()
    if not user:
        return "SELF"
    sf = sistema_folder or SISTEMA_FOLDER
    roles = user.get("roles") or {}
    if isinstance(roles, dict):
        if sf and sf in roles:
            return roles[sf].get("escopo", "SELF")
        for info in roles.values():
            if info.get("role") == "ADMIN_GERAL":
                return "GLOBAL"
    return "SELF"


def get_role_nivel(role: str = None) -> int:
    """Retorna o nível numérico da role. Se não informada, usa a role atual."""
    if role is None:
        role = get_atlas_role()
    return ROLE_NIVEL.get(role or "", -1)


def get_atlas_permissoes(sistema_folder: str = None) -> list:
    """Retorna a lista de permissões do token para este sistema.
    Extraída do campo 'sistemas' do token.
    """
    user = get_atlas_user()
    if not user:
        return []
    sf = sistema_folder or SISTEMA_FOLDER
    # Se ADMIN_GERAL, todas as permissões
    role = get_atlas_role(sf)
    if role == "ADMIN_GERAL":
        return ["visualizar", "criar", "editar", "excluir", "aprovar",
                "exportar", "importar", "configurar", "admin"]
    # Buscar no campo 'sistemas' se disponível
    sistemas = user.get("sistemas") or []
    for s in sistemas:
        if isinstance(s, dict) and s.get("folder") == sf:
            return s.get("permissoes", [])
    return []


# ── Verificações de nível ───────────────────────────────────────────────────

def is_admin_geral() -> bool:
    """Verifica se o usuário é ADMIN_GERAL (acesso global)."""
    return get_atlas_role() == "ADMIN_GERAL"


def is_admin(sistema_folder: str = None) -> bool:
    """Verifica se o usuário é ADMIN ou superior para o sistema."""
    return get_role_nivel(get_atlas_role(sistema_folder)) >= 2


def is_gestor(sistema_folder: str = None) -> bool:
    """Verifica se o usuário é pelo menos GESTOR para o sistema."""
    return get_role_nivel(get_atlas_role(sistema_folder)) >= 1


def is_user(sistema_folder: str = None) -> bool:
    """Verifica se o usuário tem pelo menos role USER."""
    return get_role_nivel(get_atlas_role(sistema_folder)) >= 0


# ── Verificações de escopo ──────────────────────────────────────────────────

def can_see_self() -> bool:
    """Qualquer autenticado pode ver dados próprios."""
    return get_atlas_user() is not None


def can_see_team(sistema_folder: str = None) -> bool:
    """Verifica se o escopo permite ver dados da equipe (TEAM, COMPANY ou GLOBAL)."""
    esc = get_atlas_escopo(sistema_folder)
    return esc in ("TEAM", "COMPANY", "GLOBAL")


def can_see_company(sistema_folder: str = None) -> bool:
    """Verifica se o escopo permite ver dados da empresa inteira (COMPANY ou GLOBAL)."""
    esc = get_atlas_escopo(sistema_folder)
    return esc in ("COMPANY", "GLOBAL")


def can_see_global(sistema_folder: str = None) -> bool:
    """Verifica se o escopo é GLOBAL (todas as empresas)."""
    return get_atlas_escopo(sistema_folder) == "GLOBAL"


def is_atlas_authenticated() -> bool:
    return session.get("atlas_authenticated") is True


# ── Decorators ──────────────────────────────────────────────────────────────

def _atlas_running() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", ATLAS_PORT), timeout=1):
            return True
    except OSError:
        return False


def require_atlas(f):
    """
    Decorator: exige autenticação Atlas.
    Se o Atlas não está rodando, passa livre (modo degradado).
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        if is_atlas_authenticated():
            return f(*args, **kwargs)
        token = (request.args.get("atlas_token") or
                 request.headers.get("X-Atlas-Token") or
                 request.cookies.get("atlas_token"))
        if token:
            payload = validate_atlas_token(token)
            if payload:
                session["atlas_authenticated"] = True
                session["atlas_user"] = payload
                session["atlas_token"] = token
                session.permanent = True
                return f(*args, **kwargs)
        if not _atlas_running():
            return f(*args, **kwargs)
        this_url = request.url
        return redirect(f"{ATLAS_URL}/login?next={this_url}")
    return wrapped


def require_role(*roles):
    """
    Decorator: exige que o usuário tenha uma das roles listadas para SISTEMA_FOLDER.
    Roles válidas: 'USER', 'GESTOR', 'ADMIN', 'ADMIN_GERAL'.

    Exemplo:
        @require_role("ADMIN", "ADMIN_GERAL")
        def rota_admin():
            ...
    """
    def dec(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            role = get_atlas_role()
            if role is None:
                return jsonify({"error": "Não autenticado."}), 401
            if role not in roles:
                return jsonify({"error": "Sem permissão."}), 403
            return f(*args, **kwargs)
        return wrapped
    return dec


def require_min_role(min_role: str):
    """
    Decorator: exige role de nível mínimo.
    Exemplo:
        @require_min_role("GESTOR")  → GESTOR, ADMIN, ADMIN_GERAL passam
    """
    min_nivel = ROLE_NIVEL.get(min_role, 0)
    def dec(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            role = get_atlas_role()
            if role is None:
                return jsonify({"error": "Não autenticado."}), 401
            if get_role_nivel(role) < min_nivel:
                return jsonify({"error": "Sem permissão."}), 403
            return f(*args, **kwargs)
        return wrapped
    return dec


def require_permissao(*permissoes):
    """
    Decorator: exige que o usuário tenha uma das permissões listadas.
    Exemplo:
        @require_permissao("aprovar")
        def aprovar_ferias():
            ...
    """
    def dec(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user_perms = get_atlas_permissoes()
            if not user_perms:
                return jsonify({"error": "Não autenticado."}), 401
            if "admin" in user_perms:
                return f(*args, **kwargs)
            if not any(p in user_perms for p in permissoes):
                return jsonify({"error": "Sem permissão."}), 403
            return f(*args, **kwargs)
        return wrapped
    return dec


def require_escopo(*escopos):
    """
    Decorator: exige que o escopo do usuário seja um dos listados.
    Exemplo:
        @require_escopo("COMPANY", "GLOBAL")
        def rota_empresa():
            ...
    """
    def dec(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            esc = get_atlas_escopo()
            if esc not in escopos:
                return jsonify({"error": "Sem permissão para este escopo."}), 403
            return f(*args, **kwargs)
        return wrapped
    return dec


# ── Atlas API helpers ────────────────────────────────────────────────────────

def atlas_validate_token(token: str) -> dict | None:
    """Valida token chamando o Atlas via HTTP (fallback se não tem a key local)."""
    try:
        url = f"{ATLAS_URL}/api/auth/validate?token=" + urllib.parse.quote(token)
        with urllib.request.urlopen(urllib.request.Request(url), timeout=5) as resp:
            return json.loads(resp.read()).get("data")
    except Exception:
        return None


def atlas_login(email: str, senha: str) -> dict | None:
    """Autentica via Atlas API. Retorna payload do usuário ou None."""
    if not _atlas_running():
        return None
    try:
        body = json.dumps({"email": email, "senha": senha}).encode()
        req = urllib.request.Request(
            f"{ATLAS_URL}/api/auth/login", data=body,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("data")
    except Exception:
        return None


def parse_sistemas(sistemas) -> tuple[list[str], dict]:
    """
    Normaliza o campo 'sistemas' do Atlas.
    Retorna (folders: list[str], roles_map: dict[folder -> {role, escopo}]).
    """
    if not isinstance(sistemas, list):
        return [], {}
    folders, roles = [], {}
    for s in sistemas:
        if isinstance(s, dict):
            f = s.get("folder", "")
            folders.append(f)
            roles[f] = {
                "role": s.get("role", "USER"),
                "escopo": s.get("escopo", "SELF"),
            }
        elif isinstance(s, str):
            folders.append(s)
            roles[s] = {"role": "USER", "escopo": "SELF"}
    return folders, roles


def has_sistema_access(sistemas, sistema_folder: str = None) -> bool:
    """Verifica se o usuário tem acesso a este sistema."""
    sf = sistema_folder or SISTEMA_FOLDER
    folders, _ = parse_sistemas(sistemas)
    return sf in folders


def sso_login_from_token(token: str, db_sync_fn=None):
    """
    Realiza login SSO a partir do token Atlas.
    Configura a sessão e opcionalmente sincroniza o usuário no banco local.

    Args:
        token: token Atlas
        db_sync_fn: função(atlas_user_dict) -> local_user_dict (opcional)
                    Se fornecida, cria/atualiza o usuário local e seta session["user_id"]
    """
    # Primeiro tenta validação local (rápido)
    payload = validate_atlas_token(token)
    # Fallback: validação via API
    if not payload:
        payload = atlas_validate_token(token)
    if not payload:
        return None

    sistemas = payload.get("sistemas")
    if isinstance(sistemas, list) and not has_sistema_access(sistemas):
        return None

    # Montar roles_por_sistema do token
    roles_por_sistema = payload.get("roles") or {}
    # Se roles não está no payload direto, extrair de sistemas
    if not roles_por_sistema and isinstance(sistemas, list):
        _, roles_map = parse_sistemas(sistemas)
        roles_por_sistema = roles_map

    atlas_user = {
        "id": payload.get("sub"),
        "nome": payload.get("nome", ""),
        "email": payload.get("email", ""),
        "cargo": payload.get("cargo", ""),
        "funcoes": payload.get("funcoes", []),
        "empresa_id": payload.get("empresa_id"),
        "empresa_nome": payload.get("empresa_nome", ""),
        "departamento_id": payload.get("departamento_id"),
        "salario": payload.get("salario", 0) or 0,
        "roles": roles_por_sistema,
        "sistemas": sistemas,
    }

    # Configurar sessão Atlas
    session["atlas_authenticated"] = True
    session["atlas_user"] = {
        **atlas_user,
        "roles": roles_por_sistema,
    }
    session["atlas_token"] = token
    session.permanent = True

    # Sincronizar com banco local se função fornecida
    if db_sync_fn:
        local_user = db_sync_fn(atlas_user)
        if local_user:
            session["user_id"] = local_user["id"]

    return atlas_user


def login_with_credentials(email: str, senha: str, db_sync_fn=None):
    """
    Login via credenciais Atlas. Retorna atlas_user ou None.

    Args:
        email: e-mail do usuário
        senha: senha
        db_sync_fn: função(atlas_user_dict) -> local_user_dict (opcional)
    """
    data = atlas_login(email, senha)
    if not data:
        return None

    sistemas = data.get("sistemas")
    if isinstance(sistemas, list) and not has_sistema_access(sistemas):
        return None

    # Extrair role para este sistema
    _, roles_map = parse_sistemas(sistemas or [])
    roles_por_sistema = data.get("roles") or {}
    if not roles_por_sistema:
        roles_por_sistema = roles_map

    atlas_user = {
        "id": data.get("id"),
        "nome": data.get("nome", ""),
        "email": data.get("email", ""),
        "cargo": data.get("cargo", ""),
        "funcoes": data.get("funcoes", []),
        "empresa_id": data.get("empresa_id"),
        "empresa_nome": data.get("empresa_nome", ""),
        "departamento_id": data.get("departamento_id"),
        "salario": data.get("salario", 0) or 0,
        "token": data.get("token", ""),
        "roles": roles_por_sistema,
        "sistemas": sistemas,
    }

    # Configurar sessão Atlas
    session["atlas_authenticated"] = True
    session["atlas_user"] = {
        **atlas_user,
        "roles": roles_por_sistema,
    }
    if data.get("token"):
        session["atlas_token"] = data["token"]
    session.permanent = True

    if db_sync_fn:
        local_user = db_sync_fn(atlas_user)
        if local_user:
            session["user_id"] = local_user["id"]

    return atlas_user


# ── Map para roles locais legadas ────────────────────────────────────────────

def map_role_to_local(atlas_user: dict, role_map: dict = None) -> str:
    """
    Mapeia a role RBAC do Atlas para a role local do app.

    Args:
        atlas_user: dict com 'roles', 'funcoes'
        role_map: dict customizado {RBAC_ROLE -> local_role}
                  Default: ADMIN_GERAL/ADMIN→'admin', GESTOR→'gestor', USER→'colaborador'

    Returns:
        string com a role local
    """
    if role_map is None:
        role_map = {
            "ADMIN_GERAL": "admin",
            "ADMIN": "admin",
            "GESTOR": "gestor",
            "USER": "colaborador",
        }

    sf = SISTEMA_FOLDER
    roles = atlas_user.get("roles") or {}

    # roles pode ser dict {folder: {role, escopo}} ou pode vir de parse_sistemas
    if isinstance(roles, dict) and sf in roles:
        info = roles[sf]
        rbac_role = info.get("role", "USER") if isinstance(info, dict) else str(info)
        if rbac_role in role_map:
            return role_map[rbac_role]

    # Check ADMIN_GERAL em qualquer sistema
    if isinstance(roles, dict):
        for info in roles.values():
            if isinstance(info, dict) and info.get("role") == "ADMIN_GERAL":
                return role_map.get("ADMIN_GERAL", "admin")

    # Fallback legado via funcoes
    funcoes = atlas_user.get("funcoes") or []
    if "admin" in funcoes:
        return role_map.get("ADMIN", "admin")
    if any(f in funcoes for f in ("gestor", "editor", "operador")):
        return role_map.get("GESTOR", "gestor")

    return role_map.get("USER", "colaborador")


def map_escopo_to_local(atlas_user: dict) -> str:
    """Extrai o escopo RBAC do Atlas para este sistema."""
    sf = SISTEMA_FOLDER
    roles = atlas_user.get("roles") or {}
    if isinstance(roles, dict) and sf in roles:
        info = roles[sf]
        if isinstance(info, dict):
            return info.get("escopo", "SELF")
    # ADMIN_GERAL → GLOBAL
    if isinstance(roles, dict):
        for info in roles.values():
            if isinstance(info, dict) and info.get("role") == "ADMIN_GERAL":
                return "GLOBAL"
    return "SELF"


# ── Blueprint SSO ────────────────────────────────────────────────────────────

atlas_sso_bp = Blueprint("atlas_sso", __name__)


@atlas_sso_bp.route("/api/auth/atlas-callback")
def atlas_callback():
    token = request.args.get("token", "")
    next_url = request.args.get("next", "/")
    payload = validate_atlas_token(token)
    if not payload:
        return redirect(f"{ATLAS_URL}/login?error=token_invalido&next={request.host_url}")
    session["atlas_authenticated"] = True
    session["atlas_user"] = payload
    session["atlas_token"] = token
    session.permanent = True
    return redirect(next_url)


@atlas_sso_bp.route("/api/auth/atlas-status")
def atlas_status():
    return jsonify({
        "authenticated": is_atlas_authenticated(),
        "atlas_running": _atlas_running(),
        "user": get_atlas_user(),
    })
