from __future__ import annotations
"""
scheduler.py — Verificação diária de alertas do Têmis (APScheduler)
"""

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

import database as db
import notifier

logger = logging.getLogger(__name__)
_scheduler = None


def _run_alerts():
    logger.info("Verificando alertas Têmis...")
    cfg = notifier.load_config()
    alertas_cfg = cfg.get("alertas", {})

    # ── 1. Vencimento de contratos ────────────────────────────────────────────
    vcfg = alertas_cfg.get("vencimento_contrato", {})
    if vcfg.get("ativo") and vcfg.get("emails"):
        emails = vcfg["emails"]
        for dias in vcfg.get("dias", [30, 60, 90]):
            for c in db.get_expiring_contracts(dias):
                dr = int(c.get("dias_restantes") or 0)
                if dr == dias:  # só envia no dia exato da janela
                    ok = notifier.send_contract_expiry_alert(c, dr, emails, cfg)
                    db.log_alert(
                        c["id"], "vencimento_contrato",
                        ", ".join(emails),
                        f"Vencimento em {dr} dias — {c['titulo']}",
                        "enviado" if ok else "falhou",
                    )
                    logger.info(f"Alerta vencimento {'OK' if ok else 'FALHOU'}: {c['titulo']}")

    # ── 2. Obrigações fiscais ─────────────────────────────────────────────────
    fcfg = alertas_cfg.get("obrigacao_fiscal", {})
    if fcfg.get("ativo") and fcfg.get("emails"):
        emails = fcfg["emails"]

        # Vencidos (atrasados)
        for ev in db.get_overdue_fiscal_events():
            c = db.get_contract(ev["contract_id"])
            if c:
                ok = notifier.send_fiscal_event_alert(c, ev, emails, cfg)
                db.log_alert(
                    ev["contract_id"], "fiscal_atrasado",
                    ", ".join(emails),
                    f"Fiscal atrasado: {ev.get('tipo')} — {c['titulo']}",
                    "enviado" if ok else "falhou",
                )

        # A vencer em breve
        for dias in fcfg.get("dias", [7, 15]):
            for ev in db.get_upcoming_fiscal_events(dias):
                c = db.get_contract(ev["contract_id"])
                if c:
                    ok = notifier.send_fiscal_event_alert(c, ev, emails, cfg)
                    db.log_alert(
                        ev["contract_id"], "obrigacao_fiscal",
                        ", ".join(emails),
                        f"Fiscal em {dias}d: {ev.get('tipo')} — {c['titulo']}",
                        "enviado" if ok else "falhou",
                    )

    # ── 3. Pendências de assinatura ───────────────────────────────────────────
    scfg = alertas_cfg.get("pendencia_assinatura", {})
    if scfg.get("ativo") and scfg.get("emails"):
        emails = scfg["emails"]
        pendentes = db.get_pending_signatures()
        # Agrupa por contract_id
        por_contrato: dict = {}
        for s in pendentes:
            cid = s["contract_id"]
            por_contrato.setdefault(cid, []).append(s)
        for cid, sigs in por_contrato.items():
            c = db.get_contract(cid)
            if c:
                ok = notifier.send_signature_pending_alert(c, sigs, emails, cfg)
                db.log_alert(
                    cid, "pendencia_assinatura",
                    ", ".join(emails),
                    f"Assinatura pendente — {c['titulo']}",
                    "enviado" if ok else "falhou",
                )

    logger.info("Verificação de alertas concluída.")


def init_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    _scheduler.add_job(_run_alerts, "cron", hour=8, minute=0, id="daily_alerts")
    _scheduler.start()
    logger.info("Scheduler de alertas iniciado (executa diariamente às 08:00).")


def shutdown_scheduler():
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


def run_now():
    """Dispara verificação manual de alertas."""
    _run_alerts()
