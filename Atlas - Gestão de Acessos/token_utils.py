from __future__ import annotations
"""
token_utils.py — Criação e validação de tokens HMAC-SHA256 para o Atlas.
Formato: base64url(payload_json) + "." + hmac_hex
Sem dependências externas.
"""
import base64
import hashlib
import hmac
import json
import os
import time

KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "atlas.key")
TOKEN_TTL = 12 * 3600  # 12 horas


def _get_key() -> bytes:
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    key = os.urandom(32)
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key


def _b64e(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(s: str) -> dict:
    pad = 4 - len(s) % 4
    raw = base64.urlsafe_b64decode(s + "=" * pad)
    return json.loads(raw)


def create_token(payload: dict) -> str:
    key = _get_key()
    now = int(time.time())
    payload = {**payload, "iat": now, "exp": now + TOKEN_TTL}
    b64p = _b64e(payload)
    sig = hmac.new(key, b64p.encode(), hashlib.sha256).hexdigest()
    return f"{b64p}.{sig}"


def validate_token(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        b64p, sig = parts
        key = _get_key()
        expected = hmac.new(key, b64p.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = _b64d(b64p)
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
