from __future__ import annotations
"""
notifier.py — Envio de alertas por e-mail via Gmail SMTP
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def _build_alert_html(monitor: dict, result: dict, reasons: list[str]) -> str:
    name    = monitor.get("name", "—")
    url     = monitor.get("url", "—")
    ts      = result.get("executed_at", "—")
    error   = result.get("error_message") or "—"
    total   = result.get("total_journey_ms")
    dur_str = f"{total} ms" if total is not None else "—"
    status  = result.get("status", "—")

    reasons_html = "".join(
        f'<li style="margin-bottom:4px">{r}</li>' for r in reasons
    )

    status_color = "#dc2626" if status == "FAIL" else "#d97706"

    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:32px 0">
  <tr><td align="center">
    <table width="580" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px #0001">
      <!-- cabeçalho -->
      <tr>
        <td style="background:#0d1b2e;padding:20px 28px">
          <span style="color:{status_color};font-size:1.1rem;font-weight:700">&#9888; Alerta de Monitoramento</span>
          <span style="color:#94afc8;font-size:.8rem;margin-left:12px">Argos - Monitoração de Aplicações WEB</span>
        </td>
      </tr>
      <!-- motivos do alerta -->
      <tr>
        <td style="padding:20px 28px 8px 28px">
          <p style="margin:0 0 8px 0;font-size:.85rem;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:.05em">Motivo(s) do alerta</p>
          <ul style="margin:0;padding-left:18px;font-size:.88rem;color:{status_color};font-weight:600">
            {reasons_html}
          </ul>
        </td>
      </tr>
      <!-- corpo -->
      <tr>
        <td style="padding:16px 28px 28px 28px">
          <table width="100%" cellpadding="0" cellspacing="0" style="font-size:.88rem;color:#1e293b;border-top:1px solid #e2e8f0">
            <tr>
              <td style="padding:8px 0;color:#64748b;width:120px;vertical-align:top">Serviço</td>
              <td style="padding:8px 0;font-weight:700">{name}</td>
            </tr>
            <tr>
              <td style="padding:8px 0;color:#64748b;vertical-align:top">URL</td>
              <td style="padding:8px 0;word-break:break-all">{url}</td>
            </tr>
            <tr>
              <td style="padding:8px 0;color:#64748b;vertical-align:top">Status</td>
              <td style="padding:8px 0;font-weight:700;color:{status_color}">{status}</td>
            </tr>
            <tr>
              <td style="padding:8px 0;color:#64748b;vertical-align:top">Horário</td>
              <td style="padding:8px 0">{ts}</td>
            </tr>
            <tr>
              <td style="padding:8px 0;color:#64748b;vertical-align:top">Duração total</td>
              <td style="padding:8px 0">{dur_str}</td>
            </tr>
            <tr>
              <td style="padding:8px 0;color:#64748b;vertical-align:top">Erro</td>
              <td style="padding:8px 0;color:#dc2626;font-family:monospace;font-size:.82rem">{error}</td>
            </tr>
          </table>
        </td>
      </tr>
      <!-- rodapé -->
      <tr>
        <td style="background:#f8fafc;padding:14px 28px;font-size:.75rem;color:#94a3b8;border-top:1px solid #e2e8f0">
          Argos — Monitoração de Aplicações WEB &nbsp;|&nbsp; Este é um alerta automático, não responda a este e-mail.
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>
"""


def check_and_send_alert(monitor: dict, result: dict, gmail_user: str, gmail_app_password: str):
    """Avalia as regras de notificação do monitor e envia e-mail se alguma condição for satisfeita."""
    recipients = [e.strip() for e in monitor.get("notify_emails", "").split(",") if e.strip()]
    if not recipients:
        return
    if not gmail_user or not gmail_app_password:
        logger.warning(f"[{monitor.get('id')}] Alerta não enviado: Gmail não configurado.")
        return

    reasons = []

    # Regra 1: notificar em caso de falha
    if monitor.get("notify_on_fail", 1) and result.get("status") == "FAIL":
        reasons.append("Status da execução: <strong>FALHA</strong>")

    # Regra 2: notificar quando tempo total exceder o limite configurado
    slow_ms = monitor.get("notify_on_slow_ms")
    total_ms = result.get("total_journey_ms")
    if slow_ms and total_ms and total_ms > slow_ms:
        reasons.append(
            f"Tempo total da jornada ({total_ms} ms) excedeu o limite configurado ({slow_ms} ms)"
        )

    if not reasons:
        return

    status = result.get("status", "—")
    subject = f"[Argos] Alerta — {monitor.get('name', '?')} ({status})"

    _send(
        gmail_user=gmail_user,
        gmail_app_password=gmail_app_password,
        to=recipients,
        subject=subject,
        html=_build_alert_html(monitor, result, reasons),
        monitor_id=monitor.get("id"),
    )


def send_test_email(gmail_user: str, gmail_app_password: str, to_email: str):
    """Envia um e-mail de teste para validar as credenciais Gmail."""
    html = """
<!DOCTYPE html>
<html lang="pt-BR">
<body style="font-family:Arial,sans-serif;padding:32px;color:#1e293b">
  <h2 style="color:#1d6eea">Argos — Teste de E-mail</h2>
  <p>Se você recebeu esta mensagem, as configurações de e-mail estão funcionando corretamente.</p>
  <p style="color:#64748b;font-size:.8rem">Argos — Monitoração de Aplicações WEB</p>
</body>
</html>
"""
    _send(
        gmail_user=gmail_user,
        gmail_app_password=gmail_app_password,
        to=[to_email],
        subject="[Argos] Teste de configuração de e-mail",
        html=html,
    )


def _send(gmail_user: str, gmail_app_password: str, to: list,
          subject: str, html: str, monitor_id=None):
    tag = f"[{monitor_id}] " if monitor_id is not None else ""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Argos Monitoração de Aplicações WEB <{gmail_user}>"
        msg["To"]      = ", ".join(to)
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(gmail_user, gmail_app_password)
            smtp.sendmail(gmail_user, to, msg.as_string())

        logger.info(f"{tag}E-mail enviado para: {to}")
    except Exception as e:
        logger.error(f"{tag}Falha ao enviar e-mail: {e}")
        raise
