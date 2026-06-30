from __future__ import annotations
"""
notifier.py — Envio de alertas por e-mail (Gmail SMTP) para o Têmis
"""

import json
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temis.cfg")


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return _default_config()


def save_config(cfg: dict):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def _default_config() -> dict:
    cfg = {
        "gmail_user": "",
        "gmail_app_password": "",
        "anthropic_api_key": "",
        "alertas": {
            "vencimento_contrato": {
                "ativo": True,
                "dias": [30, 60, 90],
                "emails": []
            },
            "obrigacao_fiscal": {
                "ativo": True,
                "dias": [7, 15],
                "emails": []
            },
            "pendencia_assinatura": {
                "ativo": True,
                "dias": [3, 7],
                "emails": []
            }
        }
    }
    save_config(cfg)
    return cfg


# ── Envio ─────────────────────────────────────────────────────────────────────

def _send(subject: str, html_body: str, to_emails: list, cfg: dict) -> bool:
    gmail_user = cfg.get("gmail_user", "")
    gmail_pass = cfg.get("gmail_app_password", "")
    if not gmail_user or not gmail_pass or not to_emails:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Têmis · Gestão de Contratos <{gmail_user}>"
        msg["To"]      = ", ".join(to_emails)
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as s:
            s.login(gmail_user, gmail_pass)
            s.sendmail(gmail_user, to_emails, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail: {e}")
        return False


def send_test_email(cfg: dict, to_email: str) -> bool:
    subject = "✅ Têmis — Teste de Configuração de E-mail"
    body = _base_template(
        "Configuração de E-mail",
        "<p>Este é um e-mail de teste enviado pelo <strong>Têmis — Gestão de Contratos</strong>.</p>"
        "<p>As configurações de e-mail estão funcionando corretamente.</p>",
        "#7c3aed",
    )
    return _send(subject, body, [to_email], cfg)


# ── Templates ─────────────────────────────────────────────────────────────────

def _base_template(title: str, content: str, color: str = "#7c3aed") -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body style="margin:0;padding:0;background:#f8fafc;font-family:'Segoe UI',sans-serif">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:32px 16px">
<table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;overflow:hidden">
  <tr><td style="background:{color};padding:20px 28px">
    <span style="color:#fff;font-size:18px;font-weight:700;letter-spacing:.05em">⚖️ TÊMIS</span>
    <span style="color:#ffffff99;font-size:11px;margin-left:10px">Gestão de Contratos</span>
  </td></tr>
  <tr><td style="padding:24px 28px">
    <h2 style="margin:0 0 16px;color:#0f172a;font-size:16px">{title}</h2>
    <div style="color:#475569;font-size:14px;line-height:1.6">{content}</div>
  </td></tr>
  <tr><td style="padding:14px 28px;background:#f8fafc;border-top:1px solid #e2e8f0">
    <span style="color:#94a3b8;font-size:11px;font-family:monospace">Olimpus · Têmis — alerta automático · não responda este e-mail</span>
  </td></tr>
</table></td></tr></table></body></html>"""


def send_contract_expiry_alert(contract: dict, days_remaining: int, to_emails: list, cfg: dict) -> bool:
    criticidade = "🔴 CRÍTICO" if days_remaining <= 15 else ("🟡 ATENÇÃO" if days_remaining <= 30 else "🔵 AVISO")
    subject = f"{criticidade} — Contrato '{contract['titulo']}' vence em {days_remaining} dias"
    valor_str = f"R$ {contract['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if contract.get("valor") else "—"
    content = f"""
    <table width="100%" style="border:1px solid #e2e8f0;border-radius:6px;border-collapse:collapse;margin-bottom:16px">
      <tr style="background:#f8fafc"><td colspan="2" style="padding:10px 14px;font-weight:600;font-size:13px">Informações do Contrato</td></tr>
      <tr><td style="padding:8px 14px;color:#64748b;width:40%">Título</td><td style="padding:8px 14px"><strong>{contract['titulo']}</strong></td></tr>
      <tr style="background:#f8fafc"><td style="padding:8px 14px;color:#64748b">Nº Contrato</td><td style="padding:8px 14px">{contract.get('numero_contrato') or '—'}</td></tr>
      <tr><td style="padding:8px 14px;color:#64748b">Contraparte</td><td style="padding:8px 14px">{contract.get('contraparte') or '—'}</td></tr>
      <tr style="background:#f8fafc"><td style="padding:8px 14px;color:#64748b">Valor</td><td style="padding:8px 14px">{valor_str}</td></tr>
      <tr><td style="padding:8px 14px;color:#64748b">Data de Término</td><td style="padding:8px 14px"><strong style="color:#dc2626">{contract.get('data_fim') or '—'}</strong></td></tr>
    </table>
    <div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:6px;padding:12px 16px;margin-bottom:16px">
      <strong style="color:#dc2626">⏰ Este contrato vence em <span style="font-size:18px">{days_remaining}</span> dias.</strong><br>
      <span style="color:#7f1d1d;font-size:13px">Ação recomendada: verificar necessidade de renovação ou encerramento.</span>
    </div>
    <a href="http://localhost:5020" style="display:inline-block;background:#7c3aed;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;font-size:13px">Acessar Contrato →</a>
    """
    body = _base_template(f"Vencimento de Contrato em {days_remaining} dias", content, "#dc2626" if days_remaining <= 15 else "#d97706")
    return _send(subject, body, to_emails, cfg)


def send_fiscal_event_alert(contract: dict, event: dict, to_emails: list, cfg: dict) -> bool:
    is_overdue = event.get("status") == "pendente" and event.get("data_prevista", "") < __import__("datetime").datetime.today().date().isoformat()
    criticidade = "🔴 ATRASADO" if is_overdue else "🟡 PRÓXIMO"
    subject = f"{criticidade} — Obrigação fiscal: {event.get('tipo')} · {contract['titulo']}"
    content = f"""
    <table width="100%" style="border:1px solid #e2e8f0;border-radius:6px;border-collapse:collapse;margin-bottom:16px">
      <tr style="background:#f8fafc"><td colspan="2" style="padding:10px 14px;font-weight:600;font-size:13px">Evento Fiscal</td></tr>
      <tr><td style="padding:8px 14px;color:#64748b;width:40%">Tipo</td><td style="padding:8px 14px"><strong>{event.get('tipo')}</strong></td></tr>
      <tr style="background:#f8fafc"><td style="padding:8px 14px;color:#64748b">Descrição</td><td style="padding:8px 14px">{event.get('descricao') or '—'}</td></tr>
      <tr><td style="padding:8px 14px;color:#64748b">Contrato</td><td style="padding:8px 14px">{contract['titulo']}</td></tr>
      <tr style="background:#f8fafc"><td style="padding:8px 14px;color:#64748b">Data Prevista</td><td style="padding:8px 14px"><strong style="color:#dc2626">{event.get('data_prevista')}</strong></td></tr>
      <tr><td style="padding:8px 14px;color:#64748b">Competência</td><td style="padding:8px 14px">{event.get('competencia') or '—'}</td></tr>
    </table>
    <a href="http://localhost:5020" style="display:inline-block;background:#7c3aed;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;font-size:13px">Acessar Contrato →</a>
    """
    body = _base_template("Obrigação Fiscal Pendente", content, "#dc2626" if is_overdue else "#d97706")
    return _send(subject, body, to_emails, cfg)


def send_signature_pending_alert(contract: dict, signatarios_pendentes: list, to_emails: list, cfg: dict) -> bool:
    subject = f"✍️ Assinatura pendente — {contract['titulo']}"
    nomes = ", ".join(s["nome"] for s in signatarios_pendentes)
    content = f"""
    <p>O contrato <strong>{contract['titulo']}</strong> está aguardando assinatura de:</p>
    <ul style="margin:12px 0;padding-left:20px">
      {"".join(f"<li style='margin:4px 0'><strong>{s['nome']}</strong> &lt;{s['email']}&gt; — {s.get('papel','signatário')}</li>" for s in signatarios_pendentes)}
    </ul>
    <a href="http://localhost:5020" style="display:inline-block;background:#7c3aed;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;font-size:13px">Acessar Contrato →</a>
    """
    body = _base_template("Assinatura Pendente", content)
    return _send(subject, body, to_emails, cfg)
