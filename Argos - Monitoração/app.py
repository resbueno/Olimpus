from __future__ import annotations
"""
app.py — API REST Flask + servidor do painel Argos

Tipos de acesso (RBAC v5.0):
  Tipo 1 (USER)   — Visualização das monitorações da empresa
  Tipo 2 (GESTOR+) — Edição, criação e exclusão de monitorações da empresa
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

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

import database as db
import scheduler_manager as sched
import auth
import atlas_client as ac

ac.SISTEMA_FOLDER = "Argos - Monitoração"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("monitor.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
app.secret_key = open(os.path.join(BASE_DIR, "secret.key"), "rb").read()[:32] if os.path.exists(os.path.join(BASE_DIR, "secret.key")) else os.urandom(32)
app.permanent_session_lifetime = timedelta(hours=12)
CORS(app, supports_credentials=True)

ALLOWED_INTERVALS = {1, 5, 15, 30, 60}


def _err(msg, code=400):
    return jsonify({"error": msg}), code


def _ok(data=None, **kwargs):
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    payload.update(kwargs)
    return jsonify(payload)


# ── Static ────────────────────────────────────────────────────────────────────

def _sso_login(token: str):
    """Tenta criar sessão Argos a partir de token Atlas (SSO)."""
    ac.sso_login_from_token(token)


@app.route("/")
def index():
    token = request.args.get("atlas_token", "").strip()
    if token and not ac.is_atlas_authenticated():
        _sso_login(token)
    return send_from_directory(BASE_DIR, "dashboard.html")


@app.route("/screenshots/<path:filename>")
def serve_screenshot(filename):
    return send_from_directory(db.SCREENSHOTS_DIR, filename)


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
            "role_atlas": ac.get_atlas_role(),
            "escopo": ac.get_atlas_escopo(),
        }, message="Login realizado com sucesso.")
    return _err("E-mail ou senha inválidos, ou acesso ao Argos não autorizado.", 401)


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return _ok(message="Sessao encerrada.")


@app.route("/api/auth/status", methods=["GET"])
def auth_status():
    u = ac.get_atlas_user()
    return _ok({
        "authenticated": ac.is_atlas_authenticated(),
        "user": u,
        "role_atlas": ac.get_atlas_role(),
        "escopo": ac.get_atlas_escopo(),
    })


@app.route("/api/auth/change-password", methods=["POST"])
@auth.require_auth
def change_password():
    """Redireciona para o Atlas — senhas são gerenciadas centralmente."""
    return _err(
        "Altere sua senha em http://localhost:5010 (Atlas — Gestão de Acessos).",
        400,
    )


@app.route("/api/auth/change-username", methods=["POST"])
@auth.require_auth
def change_username():
    """Redireciona para o Atlas — usuários são gerenciados centralmente."""
    return _err(
        "Gerencie seus dados em http://localhost:5010 (Atlas — Gestão de Acessos).",
        400,
    )


# ── Config e-mail ─────────────────────────────────────────────────────────────

@app.route("/api/config/email", methods=["GET"])
@auth.require_auth
def get_email_config():
    return _ok(auth.get_email_config())


@app.route("/api/config/email", methods=["POST"])
@auth.require_auth
def save_email_config():
    data = request.json or {}
    gmail_user = data.get("gmail_user", "").strip()
    gmail_app_password = data.get("gmail_app_password") or None
    auth.save_email_config(gmail_user, gmail_app_password)
    return _ok(message="Configurações de e-mail salvas.")


@app.route("/api/config/email/test", methods=["POST"])
@auth.require_auth
def test_email():
    import notifier
    data = request.json or {}
    to_email = data.get("to_email", "").strip()
    if not to_email:
        return _err("Informe um e-mail de destino para o teste.")
    cfg = auth.load_config()
    gmail_user = cfg.get("gmail_user", "")
    gmail_app_password = cfg.get("gmail_app_password", "")
    if not gmail_user or not gmail_app_password:
        return _err("Configure o Gmail antes de testar.")
    try:
        notifier.send_test_email(gmail_user, gmail_app_password, to_email)
        return _ok(message=f"E-mail de teste enviado para {to_email}.")
    except Exception as e:
        return _err(f"Falha ao enviar: {str(e)}")


# ── Monitors ──────────────────────────────────────────────────────────────────

@app.route("/api/monitors", methods=["GET"])
def get_monitors():
    monitors = db.list_monitors()
    result = []
    for m in monitors:
        m_copy = dict(m)
        m_copy.pop("password_enc", None)
        m_copy["last_execution"] = db.get_last_execution(m["id"])
        m_copy["stats"] = db.get_stats(m["id"])
        m_copy["job"] = sched.get_job_info(m["id"])
        result.append(m_copy)
    return _ok(result)


@app.route("/api/monitors/<int:mid>", methods=["GET"])
def get_monitor(mid):
    m = db.get_monitor(mid)
    if not m:
        return _err("Monitor nao encontrado.", 404)
    m.pop("password_enc", None)
    m["stats"] = db.get_stats(mid)
    m["job"] = sched.get_job_info(mid)
    return _ok(m)


@app.route("/api/monitors", methods=["POST"])
@auth.require_auth
def create_monitor():
    data = request.json or {}
    required = ["name", "url", "username", "password", "target_menu_selector", "interval_minutes"]
    for f in required:
        if not data.get(f):
            return _err(f"Campo obrigatorio ausente: {f}")
    if int(data["interval_minutes"]) not in ALLOWED_INTERVALS:
        return _err(f"Intervalo invalido. Permitidos: {sorted(ALLOWED_INTERVALS)}")
    new_id = db.create_monitor(data)
    if data.get("active", 1):
        sched.add_job(new_id, int(data["interval_minutes"]))
    return _ok({"id": new_id}, message="Monitor criado."), 201


@app.route("/api/monitors/<int:mid>", methods=["PUT"])
@auth.require_auth
def update_monitor(mid):
    if not db.get_monitor(mid):
        return _err("Monitor nao encontrado.", 404)
    data = request.json or {}
    if "interval_minutes" in data and int(data["interval_minutes"]) not in ALLOWED_INTERVALS:
        return _err(f"Intervalo invalido. Permitidos: {sorted(ALLOWED_INTERVALS)}")
    db.update_monitor(mid, data)
    m = db.get_monitor(mid)
    if m["active"]:
        sched.add_job(mid, m["interval_minutes"])
    else:
        sched.remove_job(mid)
    return _ok(message="Monitor atualizado.")


@app.route("/api/monitors/<int:mid>", methods=["DELETE"])
@auth.require_auth
def delete_monitor(mid):
    if not db.get_monitor(mid):
        return _err("Monitor nao encontrado.", 404)
    sched.remove_job(mid)
    db.delete_monitor(mid)
    return _ok(message="Monitor removido.")


@app.route("/api/monitors/<int:mid>/toggle", methods=["POST"])
@auth.require_auth
def toggle_monitor(mid):
    m = db.get_monitor(mid)
    if not m:
        return _err("Monitor nao encontrado.", 404)
    active = not bool(m["active"])
    db.toggle_monitor(mid, active)
    if active:
        sched.add_job(mid, m["interval_minutes"])
    else:
        sched.remove_job(mid)
    return _ok({"active": active})


@app.route("/api/monitors/<int:mid>/run", methods=["POST"])
@auth.require_auth
def run_now(mid):
    if not db.get_monitor(mid):
        return _err("Monitor nao encontrado.", 404)
    sched.run_now(mid)
    return _ok(message="Execucao iniciada.")


# ── History ───────────────────────────────────────────────────────────────────

@app.route("/api/monitors/<int:mid>/history", methods=["GET"])
def get_history(mid):
    limit = int(request.args.get("limit", 50))
    return _ok(db.get_history(mid, limit))


@app.route("/api/history", methods=["GET"])
def get_history_all():
    limit = int(request.args.get("limit", 200))
    return _ok(db.get_history_all(limit))


# ── Stats / Scheduler ─────────────────────────────────────────────────────────

@app.route("/api/stats", methods=["GET"])
def global_stats():
    monitors = db.list_monitors()
    total = len(monitors)
    active = sum(1 for m in monitors if m["active"])
    history = db.get_history_all(limit=500)
    success = sum(1 for h in history if h["status"] == "SUCCESS")
    fail = sum(1 for h in history if h["status"] == "FAIL")
    ms_vals = [h["total_journey_ms"] for h in history if h.get("total_journey_ms") and h["status"] == "SUCCESS"]
    avg_ms = round(sum(ms_vals) / len(ms_vals)) if ms_vals else None
    return _ok({
        "total_monitors": total,
        "active_monitors": active,
        "total_executions": len(history),
        "success_executions": success,
        "fail_executions": fail,
        "avg_journey_ms": avg_ms,
        "availability": round(success / (success + fail) * 100, 1) if (success + fail) > 0 else None,
    })


@app.route("/api/scheduler/jobs", methods=["GET"])
@auth.require_auth
def scheduler_jobs():
    return _ok(sched.list_jobs())


@app.route("/api/test/ping", methods=["GET"])
@app.route("/api/ping", methods=["GET"])
def ping():
    return _ok({"timestamp": datetime.now().isoformat()})


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def _on_shutdown(sig, frame):
    logger.info("Encerrando Argos...")
    sched.shutdown_scheduler()
    sys.exit(0)


if __name__ == "__main__":
    db.init_db()
    # garante que a secret.key existe antes de usá-la
    from database import _get_or_create_key
    _get_or_create_key()
    app.secret_key = _get_or_create_key()[:32]
    sched.init_scheduler()
    signal.signal(signal.SIGINT, _on_shutdown)
    signal.signal(signal.SIGTERM, _on_shutdown)
    logger.info("Argos iniciado em http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
