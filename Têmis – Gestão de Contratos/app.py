from __future__ import annotations
"""
app.py — API REST Flask + servidor do Têmis — Gestão de Contratos
Fases 1-4: contratos, fiscal, IA (Claude), alertas por e-mail
"""

import json
import logging
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

# pythonw sem console → stdout/stderr são None; protege contra crash
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from werkzeug.utils import secure_filename

import auth
import database as db
import notifier
import scheduler
import atlas_client as ac

ac.SISTEMA_FOLDER = "Têmis – Gestão de Contratos"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("temis.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
app.permanent_session_lifetime = timedelta(hours=12)
app.config["SESSION_COOKIE_NAME"]     = "temis_session"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"]   = False
CORS(app, supports_credentials=True)

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "odt", "txt"}

_key_path = os.path.join(BASE_DIR, "temis.key")
app.secret_key = (
    open(_key_path, "rb").read()[:32]
    if os.path.exists(_key_path)
    else os.urandom(32)
)


def _err(msg, code=400):
    return jsonify({"error": msg}), code


def _ok(data=None, **kwargs):
    payload = {"ok": True}
    if data is not None:
        payload["data"] = data
    payload.update(kwargs)
    return jsonify(payload)


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── SSO ───────────────────────────────────────────────────────────────────────

def _sso_login(token: str):
    ac.sso_login_from_token(token)


# ── Static ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    token = request.args.get("atlas_token", "").strip()
    if token and not ac.is_atlas_authenticated():
        _sso_login(token)
    return send_from_directory(BASE_DIR, "temis.html")


@app.route("/contratos/<path:filename>")
@auth.require_auth
def serve_file(filename):
    return send_from_directory(db.FILES_DIR, filename)


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def login():
    data     = request.json or {}
    email    = data.get("email", data.get("username", "")).strip().lower()
    password = data.get("password", "")
    atlas_user = ac.login_with_credentials(email, password)
    if atlas_user:
        return _ok({"nome": atlas_user.get("nome"), "email": atlas_user.get("email"),
                    "role_atlas": ac.get_atlas_role(), "escopo": ac.get_atlas_escopo()},
                   message="Login realizado.")
    return _err("E-mail ou senha inválidos, ou acesso ao Têmis não autorizado.", 401)


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    auth.logout_user()
    return _ok(message="Sessão encerrada.")


@app.route("/api/auth/status", methods=["GET"])
def auth_status():
    return _ok({
        "authenticated": ac.is_atlas_authenticated(),
        "user":          ac.get_atlas_user(),
        "role_atlas":    ac.get_atlas_role(),
        "escopo":        ac.get_atlas_escopo(),
    })


# ── Contracts ─────────────────────────────────────────────────────────────────

@app.route("/api/contracts", methods=["GET"])
@auth.require_auth
def list_contracts():
    return _ok(db.list_contracts(
        status=request.args.get("status") or None,
        search=request.args.get("q") or None,
    ))


@app.route("/api/contracts/<int:cid>", methods=["GET"])
@auth.require_auth
def get_contract(cid):
    c = db.get_contract(cid)
    if not c:
        return _err("Contrato não encontrado.", 404)
    c["signatarios"] = db.list_signatories(cid)
    c["versoes"]     = db.list_versions(cid)
    c["audit_log"]   = db.get_audit_log(cid)
    return _ok(c)


@app.route("/api/contracts", methods=["POST"])
@auth.require_auth
def create_contract():
    data = request.json or {}
    if not data.get("titulo", "").strip():
        return _err("O título do contrato é obrigatório.")
    cid = db.create_contract(data, auth.get_user_name())
    return _ok({"id": cid}, message="Contrato criado."), 201


@app.route("/api/contracts/<int:cid>", methods=["PUT"])
@auth.require_auth
def update_contract(cid):
    if not db.get_contract(cid):
        return _err("Contrato não encontrado.", 404)
    data = request.json or {}
    if "status" in data and data["status"] not in db.STATUSES:
        return _err(f"Status inválido.")
    db.update_contract(cid, data, auth.get_user_name())
    return _ok(message="Contrato atualizado.")


@app.route("/api/contracts/<int:cid>", methods=["DELETE"])
@auth.require_auth
def delete_contract(cid):
    if not db.get_contract(cid):
        return _err("Contrato não encontrado.", 404)
    db.delete_contract(cid, auth.get_user_name())
    return _ok(message="Contrato excluído.")


@app.route("/api/contracts/<int:cid>/status", methods=["POST"])
@auth.require_auth
def change_status(cid):
    if not db.get_contract(cid):
        return _err("Contrato não encontrado.", 404)
    novo = (request.json or {}).get("status", "").strip()
    if novo not in db.STATUSES:
        return _err(f"Status inválido.")
    db.advance_status(cid, novo, auth.get_user_name())
    return _ok(message=f"Status → '{novo}'.")


# ── Upload ────────────────────────────────────────────────────────────────────

@app.route("/api/contracts/<int:cid>/upload", methods=["POST"])
@auth.require_auth
def upload_file(cid):
    if not db.get_contract(cid):
        return _err("Contrato não encontrado.", 404)
    if "file" not in request.files:
        return _err("Nenhum arquivo enviado.")
    f = request.files["file"]
    if not f.filename or not _allowed_file(f.filename):
        return _err(f"Tipo não permitido. Use: {', '.join(ALLOWED_EXTENSIONS)}")
    safe  = secure_filename(f.filename)
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{cid}_{ts}_{safe}"
    f.save(os.path.join(db.FILES_DIR, fname))
    obs   = request.form.get("observacoes", "")
    db.update_contract(cid, {"arquivo_path": fname, "arquivo_nome": f.filename}, auth.get_user_name())
    db.add_version(cid, fname, f.filename, obs, auth.get_user_name())
    return _ok({"arquivo_path": fname, "arquivo_nome": f.filename}, message="Arquivo enviado.")


# ── Signatários ───────────────────────────────────────────────────────────────

@app.route("/api/contracts/<int:cid>/signatories", methods=["GET"])
@auth.require_auth
def list_signatories(cid):
    return _ok(db.list_signatories(cid))


@app.route("/api/contracts/<int:cid>/signatories", methods=["POST"])
@auth.require_auth
def add_signatory(cid):
    if not db.get_contract(cid):
        return _err("Contrato não encontrado.", 404)
    data = request.json or {}
    if not data.get("nome") or not data.get("email"):
        return _err("Nome e e-mail são obrigatórios.")
    sid = db.add_signatory(cid, data, auth.get_user_name())
    return _ok({"id": sid}, message="Signatário adicionado."), 201


@app.route("/api/signatories/<int:sid>", methods=["DELETE"])
@auth.require_auth
def remove_signatory(sid):
    db.remove_signatory(sid, auth.get_user_name())
    return _ok(message="Signatário removido.")


@app.route("/api/sign/<token>", methods=["GET", "POST"])
def sign_by_token(token):
    result = db.sign_contract(token)
    if result["ok"]:
        return _ok(result, message=f"Assinado com sucesso por {result['nome']}.")
    return _err(result["error"], 400)


# ── Fiscal — Tributos ─────────────────────────────────────────────────────────

@app.route("/api/contracts/<int:cid>/fiscal", methods=["GET"])
@auth.require_auth
def get_fiscal(cid):
    if not db.get_contract(cid):
        return _err("Contrato não encontrado.", 404)
    return _ok(db.get_fiscal_summary(cid))


@app.route("/api/contracts/<int:cid>/taxes", methods=["GET"])
@auth.require_auth
def list_taxes(cid):
    return _ok(db.list_taxes(cid))


@app.route("/api/contracts/<int:cid>/taxes", methods=["POST"])
@auth.require_auth
def add_tax(cid):
    if not db.get_contract(cid):
        return _err("Contrato não encontrado.", 404)
    data = request.json or {}
    if not data.get("tributo"):
        return _err("Tributo é obrigatório.")
    tid = db.add_tax(cid, data, auth.get_user_name())
    return _ok({"id": tid}, message="Tributo adicionado."), 201


@app.route("/api/taxes/<int:tid>", methods=["PUT"])
@auth.require_auth
def update_tax(tid):
    db.update_tax(tid, request.json or {}, auth.get_user_name())
    return _ok(message="Tributo atualizado.")


@app.route("/api/taxes/<int:tid>", methods=["DELETE"])
@auth.require_auth
def delete_tax(tid):
    db.delete_tax(tid, auth.get_user_name())
    return _ok(message="Tributo removido.")


# ── Fiscal — Eventos ──────────────────────────────────────────────────────────

@app.route("/api/contracts/<int:cid>/fiscal/events", methods=["GET"])
@auth.require_auth
def list_fiscal_events(cid):
    return _ok(db.list_fiscal_events(cid))


@app.route("/api/contracts/<int:cid>/fiscal/events", methods=["POST"])
@auth.require_auth
def add_fiscal_event(cid):
    if not db.get_contract(cid):
        return _err("Contrato não encontrado.", 404)
    data = request.json or {}
    if not data.get("tipo") or not data.get("data_prevista"):
        return _err("Tipo e data prevista são obrigatórios.")
    eid = db.add_fiscal_event(cid, data, auth.get_user_name())
    return _ok({"id": eid}, message="Evento fiscal adicionado."), 201


@app.route("/api/fiscal/events/<int:eid>", methods=["PUT"])
@auth.require_auth
def update_fiscal_event(eid):
    db.update_fiscal_event(eid, request.json or {}, auth.get_user_name())
    return _ok(message="Evento atualizado.")


@app.route("/api/fiscal/events/<int:eid>", methods=["DELETE"])
@auth.require_auth
def delete_fiscal_event(eid):
    db.delete_fiscal_event(eid, auth.get_user_name())
    return _ok(message="Evento removido.")


@app.route("/api/fiscal/events/<int:eid>/concluir", methods=["POST"])
@auth.require_auth
def concluir_fiscal_event(eid):
    data = request.json or {}
    db.update_fiscal_event(eid, {
        "status": "realizado",
        "data_realizada": data.get("data_realizada") or datetime.now().date().isoformat(),
        "valor_realizado": data.get("valor_realizado"),
        "observacoes": data.get("observacoes", ""),
    }, auth.get_user_name())
    return _ok(message="Evento marcado como realizado.")


# ── IA — Análise de Cláusulas ─────────────────────────────────────────────────

@app.route("/api/contracts/<int:cid>/analysis", methods=["GET"])
@auth.require_auth
def get_analysis(cid):
    return _ok(db.get_analysis(cid))


@app.route("/api/contracts/<int:cid>/analyze", methods=["POST"])
@auth.require_auth
def analyze_contract(cid):
    c = db.get_contract(cid)
    if not c:
        return _err("Contrato não encontrado.", 404)

    cfg = notifier.load_config()
    api_key = cfg.get("anthropic_api_key", "").strip()
    if not api_key:
        return _err("Chave da API Anthropic não configurada. Acesse Configurações → IA.", 400)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        return _err("Biblioteca 'anthropic' não instalada. Execute: pip install anthropic", 500)

    # Monta contexto do contrato para análise
    taxes  = db.list_taxes(cid)
    events = db.list_fiscal_events(cid)
    tributos_str = ", ".join(t["tributo"] for t in taxes) if taxes else "Nenhum cadastrado"

    prompt = f"""Você é um especialista jurídico e fiscal brasileiro. Analise o contrato abaixo e retorne um JSON estruturado.

DADOS DO CONTRATO:
- Título: {c.get('titulo')}
- Tipo: {c.get('tipo')}
- Número: {c.get('numero_contrato') or 'Não informado'}
- Objeto: {c.get('objeto') or 'Não informado'}
- Contraparte: {c.get('contraparte') or 'Não informado'} (CNPJ: {c.get('contraparte_cnpj') or 'N/I'})
- Valor: R$ {c.get('valor') or 'Não informado'}
- Vigência: {c.get('data_inicio') or 'N/I'} até {c.get('data_fim') or 'N/I'}
- Status: {c.get('status')}
- Tributos vinculados: {tributos_str}
- Eventos fiscais: {len(events)} cadastrados

Retorne EXATAMENTE este JSON (sem markdown, sem texto extra):
{{
  "score_risco": <inteiro de 1 a 10, onde 10 é risco máximo>,
  "resumo": "<resumo executivo de 2-3 frases>",
  "riscos": [
    {{"titulo": "<risco>", "descricao": "<explicação>", "severidade": "<alto|medio|baixo>"}}
  ],
  "clausulas_faltantes": [
    "<cláusula importante ausente ou não mencionada>"
  ],
  "recomendacoes": [
    "<recomendação prática e objetiva>"
  ]
}}

Considere legislação brasileira (CLT, Código Civil, tributação federal/estadual/municipal)."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Remove markdown se presente
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        analysis = json.loads(raw)
        analysis["raw_response"] = raw
        db.save_analysis(cid, analysis)
        db._audit(cid, "análise de IA realizada", auth.get_user_name(),
                  f"Score de risco: {analysis.get('score_risco')}/10")
        return _ok(analysis, message="Análise concluída.")
    except json.JSONDecodeError:
        db.save_analysis(cid, {"score_risco": None, "resumo": raw,
                                "riscos": [], "clausulas_faltantes": [], "recomendacoes": [],
                                "raw_response": raw})
        return _ok({"resumo": raw, "raw_response": raw}, message="Análise salva (resposta livre).")
    except Exception as e:
        logger.error(f"Erro na análise IA: {e}")
        return _err(f"Erro ao chamar a API: {str(e)}", 500)


# ── Configurações ─────────────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
@auth.require_auth
def get_config():
    cfg = notifier.load_config()
    safe = {k: v for k, v in cfg.items() if k != "gmail_app_password"}
    safe["gmail_app_password_set"] = bool(cfg.get("gmail_app_password"))
    safe["anthropic_key_set"] = bool(cfg.get("anthropic_api_key"))
    return _ok(safe)


@app.route("/api/config", methods=["POST"])
@auth.require_auth
def save_config():
    data = request.json or {}
    cfg  = notifier.load_config()
    if "gmail_user" in data:
        cfg["gmail_user"] = data["gmail_user"]
    if "gmail_app_password" in data and data["gmail_app_password"]:
        cfg["gmail_app_password"] = data["gmail_app_password"]
    if "anthropic_api_key" in data and data["anthropic_api_key"]:
        cfg["anthropic_api_key"] = data["anthropic_api_key"]
    if "alertas" in data:
        cfg["alertas"] = data["alertas"]
    notifier.save_config(cfg)
    return _ok(message="Configurações salvas.")


@app.route("/api/config/email/test", methods=["POST"])
@auth.require_auth
def test_email():
    data     = request.json or {}
    to_email = data.get("to_email", "").strip()
    if not to_email:
        return _err("Informe um e-mail de destino.")
    cfg = notifier.load_config()
    if not cfg.get("gmail_user") or not cfg.get("gmail_app_password"):
        return _err("Configure o Gmail antes de testar.")
    ok = notifier.send_test_email(cfg, to_email)
    if ok:
        return _ok(message=f"E-mail de teste enviado para {to_email}.")
    return _err("Falha ao enviar. Verifique as credenciais Gmail.")


# ── Alertas ───────────────────────────────────────────────────────────────────

@app.route("/api/alerts", methods=["GET"])
@auth.require_auth
def get_alerts():
    days     = int(request.args.get("days", 60))
    expiring = db.get_expiring_contracts(days)
    expired  = db.get_expired_contracts()
    overdue  = db.get_overdue_fiscal_events()
    upcoming = db.get_upcoming_fiscal_events(15)
    pending  = db.get_pending_signatures()
    return _ok({
        "expiring": expiring, "expired": expired,
        "fiscal_overdue": overdue, "fiscal_upcoming": upcoming,
        "pending_signatures": pending,
        "total": len(expiring) + len(expired) + len(overdue) + len(pending),
    })


@app.route("/api/alerts/send", methods=["POST"])
@auth.require_auth
def send_alerts_now():
    try:
        scheduler.run_now()
        return _ok(message="Verificação de alertas disparada com sucesso.")
    except Exception as e:
        return _err(f"Erro: {str(e)}")


@app.route("/api/alerts/log", methods=["GET"])
@auth.require_auth
def get_alert_log():
    cid   = request.args.get("contract_id")
    limit = int(request.args.get("limit", 50))
    return _ok(db.get_alert_log(contract_id=int(cid) if cid else None, limit=limit))


# ── Audit Log ─────────────────────────────────────────────────────────────────

@app.route("/api/audit", methods=["GET"])
@auth.require_auth
def get_audit():
    return _ok(db.get_audit_log(limit=int(request.args.get("limit", 100))))


@app.route("/api/contracts/<int:cid>/audit", methods=["GET"])
@auth.require_auth
def get_contract_audit(cid):
    return _ok(db.get_audit_log(contract_id=cid))


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.route("/api/stats", methods=["GET"])
@auth.require_auth
def get_stats():
    return _ok(db.get_stats())


@app.route("/api/test/ping", methods=["GET"])
@app.route("/api/ping", methods=["GET"])
def ping():
    return _ok({"timestamp": datetime.now().isoformat()})


# ── Bootstrap ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    db.init_db()
    from database import _get_or_create_key
    app.secret_key = _get_or_create_key()[:32]
    scheduler.init_scheduler()
    logger.info("Têmis iniciado em http://localhost:5020")
    app.run(host="0.0.0.0", port=5020, debug=False, use_reloader=False)
