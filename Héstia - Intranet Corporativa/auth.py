from __future__ import annotations
"""
auth.py — Autenticação do Héstia via Atlas (IAM central)
"""

import json
import logging
import os
import socket
import urllib.error
import urllib.request
from functools import wraps

from flask import jsonify, session

logger = logging.getLogger(__name__)

CFG_PATH       = os.path.join(os.path.dirname(__file__), "hestia.cfg")
ATLAS_URL    = "http://localhost:5010"
SISTEMA_FOLDER = "Héstia - Intranet Corporativa"


def load_config() -> dict:
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, "r") as f:
            return json.load(f)
    cfg = {}
    save_config(cfg)
    return cfg


def save_config(cfg: dict):
    with open(CFG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def _atlas_running() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 5010), timeout=1):
            return True
    except OSError:
        return False


def _parse_sistemas(sistemas) -> tuple[list[str], dict]:
    """Normaliza 'sistemas' do Atlas: retorna (folders, roles_por_folder)."""
    if not isinstance(sistemas, list):
        return [], {}
    folders, roles = [], {}
    for s in sistemas:
        if isinstance(s, dict):
            f = s.get("folder", "")
            folders.append(f)
            roles[f] = s.get("role_sistema", "")
        elif isinstance(s, str):
            folders.append(s)
            roles[s] = ""
    return folders, roles


def check_credentials(email: str, password: str) -> dict | None:
    logger.info(f"Tentando login para: {email}")
    if not _atlas_running():
        logger.warning("Atlas não está rodando")
        return None
    try:
        body = json.dumps({"email": email, "senha": password}).encode()
        req  = urllib.request.Request(
            f"{ATLAS_URL}/api/auth/login",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data     = json.loads(resp.read())
            logger.info(f"Resposta do Atlas: {data}")
            user     = data.get("data", {})
            sistemas = user.get("sistemas")
            folders, roles = _parse_sistemas(sistemas)
            if isinstance(sistemas, list) and SISTEMA_FOLDER not in folders:
                logger.warning(f"Usuário não tem acesso a {SISTEMA_FOLDER}. Sistemas: {sistemas}")
                return None
            user["_role_sistema"] = roles.get(SISTEMA_FOLDER, "")
            logger.info(f"Login permitido para: {email}")
            return user
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP Error: {e.code} - {e.reason}")
        return None
    except urllib.error.URLError as e:
        logger.error(f"URL Error: {e.reason}")
        return None
    except Exception as e:
        logger.error(f"Erro: {e}")
        return None


def get_user_role() -> str:
    """Retorna a role do usuário atual na Héstia (conforme definido no Atlas)."""
    user = get_current_user()
    if not user:
        return ""
    return user.get("_role_sistema", "") or (
        "admin" if "admin" in (user.get("funcoes") or []) else ""
    )


def is_authenticated() -> bool:
    return session.get("atlas_authenticated") is True


def login_user(user_data: dict):
    session["atlas_authenticated"] = True
    session["atlas_user"]  = user_data
    session.permanent = True


def logout_user():
    session.clear()


def get_current_user() -> dict | None:
    return session.get("atlas_user")


def is_admin() -> bool:
    user = get_current_user()
    if not user:
        return False
    funcoes = user.get("funcoes", [])
    return "admin" in funcoes or "administrador" in funcoes


def is_authenticated() -> bool:
    return session.get("atlas_authenticated") is True


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_authenticated():
            return jsonify({"error": "Não autenticado.", "auth_required": True}), 401
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_authenticated():
            return jsonify({"error": "Não autenticado.", "auth_required": True}), 401
        if not is_admin():
            return jsonify({"error": "Acesso restrito a administradores."}), 403
        return f(*args, **kwargs)
    return decorated