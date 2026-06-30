from __future__ import annotations
"""
auth.py — Autenticação do Têmis via Atlas (IAM central)
"""

import json
import os
import socket
import urllib.error
import urllib.request
from functools import wraps

from flask import jsonify, session

ATLAS_URL    = "http://localhost:5010"
SISTEMA_FOLDER = "Têmis – Gestão de Contratos"


# ── Atlas ───────────────────────────────────────────────────────────────────

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
    if not _atlas_running():
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
            user     = data.get("data", {})
            sistemas = user.get("sistemas")
            folders, roles = _parse_sistemas(sistemas)
            if isinstance(sistemas, list) and SISTEMA_FOLDER not in folders:
                return None
            user["_role_sistema"] = roles.get(SISTEMA_FOLDER, "")
            return user
    except (urllib.error.HTTPError, urllib.error.URLError, Exception):
        return None


def get_user_role() -> str:
    """Retorna a role do usuário atual no Têmis (conforme definido no Atlas)."""
    user = get_current_user()
    if not user:
        return ""
    return user.get("_role_sistema", "") or (
        "admin" if "admin" in (user.get("funcoes") or []) else ""
    )


# ── Sessão ────────────────────────────────────────────────────────────────────

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


def get_user_name() -> str:
    u = get_current_user()
    return u.get("nome", u.get("email", "sistema")) if u else "sistema"


# ── Decorator ─────────────────────────────────────────────────────────────────

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_authenticated():
            return jsonify({"error": "Não autenticado.", "auth_required": True}), 401
        return f(*args, **kwargs)
    return decorated
