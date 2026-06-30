from __future__ import annotations
"""
auth.py — Tiresias OCR · Autenticação via Atlas IAM
Credenciais validadas no Atlas em http://localhost:5010.
"""
import json
import os
import socket
import urllib.error
import urllib.request
from functools import wraps

from flask import jsonify, session

ATLAS_URL      = "http://localhost:5010"
SISTEMA_FOLDER = "Tiresias – OCR"


def _atlas_running() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 5010), timeout=1):
            return True
    except OSError:
        return False


def _parse_sistemas(sistemas) -> tuple[list[str], dict]:
    """Normaliza sistemas do Atlas: lista de strings ou de {folder, role_sistema}."""
    folders, roles = [], {}
    for s in (sistemas or []):
        if isinstance(s, dict):
            f = s.get("folder", "")
            folders.append(f)
            roles[f] = s.get("role_sistema", "")
        elif isinstance(s, str):
            folders.append(s)
            roles[s] = ""
    return folders, roles


def check_credentials(email: str, password: str) -> dict | None:
    """Valida e-mail + senha no Atlas. Retorna dados do usuário ou None."""
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
            folders, _ = _parse_sistemas(sistemas)
            if isinstance(sistemas, list) and SISTEMA_FOLDER not in folders:
                return None
            return user
    except (urllib.error.HTTPError, urllib.error.URLError, Exception):
        return None


# ── Sessão ────────────────────────────────────────────────────────────────────

def is_authenticated() -> bool:
    return session.get("atlas_authenticated") is True


def login_user(user_data: dict):
    session["atlas_authenticated"] = True
    session["atlas_user"] = user_data
    session.permanent = True


def logout_user():
    session.clear()


def get_current_user() -> dict | None:
    return session.get("atlas_user")


# ── Decorator ─────────────────────────────────────────────────────────────────

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_authenticated():
            return jsonify({"error": "Não autenticado.", "auth_required": True}), 401
        return f(*args, **kwargs)
    return decorated
