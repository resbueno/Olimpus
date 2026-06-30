from __future__ import annotations
"""
scheduler_manager.py — Orquestrador de jobs APScheduler
"""

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_job_registry: dict[int, str] = {}   # monitor_id → job_id


# ── Inicialização ────────────────────────────────────────────────────────────

def init_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    _scheduler.add_listener(_on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    _scheduler.start()
    logger.info("Scheduler iniciado.")
    _load_all_active_monitors()


def shutdown_scheduler():
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler encerrado.")


# ── Gerenciamento de jobs ────────────────────────────────────────────────────

def _job_id(monitor_id: int) -> str:
    return f"monitor_{monitor_id}"


def add_job(monitor_id: int, interval_minutes: int):
    """Registra ou substitui o job de um monitor."""
    if not _scheduler:
        return
    jid = _job_id(monitor_id)
    if _scheduler.get_job(jid):
        _scheduler.remove_job(jid)
    _scheduler.add_job(
        func=_run_safe,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id=jid,
        args=[monitor_id],
        replace_existing=True,
        misfire_grace_time=60,
        max_instances=1,
        name=f"Monitor #{monitor_id} — {interval_minutes}min",
    )
    _job_registry[monitor_id] = jid
    logger.info(f"Job adicionado: monitor_id={monitor_id}, intervalo={interval_minutes}min")


def remove_job(monitor_id: int):
    if not _scheduler:
        return
    jid = _job_id(monitor_id)
    if _scheduler.get_job(jid):
        _scheduler.remove_job(jid)
    _job_registry.pop(monitor_id, None)
    logger.info(f"Job removido: monitor_id={monitor_id}")


def pause_job(monitor_id: int):
    if not _scheduler:
        return
    jid = _job_id(monitor_id)
    if _scheduler.get_job(jid):
        _scheduler.pause_job(jid)
        logger.info(f"Job pausado: monitor_id={monitor_id}")


def resume_job(monitor_id: int):
    if not _scheduler:
        return
    jid = _job_id(monitor_id)
    if _scheduler.get_job(jid):
        _scheduler.resume_job(jid)
        logger.info(f"Job retomado: monitor_id={monitor_id}")


def run_now(monitor_id: int):
    """Executa o job imediatamente (fora do ciclo normal)."""
    if not _scheduler:
        return
    _run_safe(monitor_id)


def list_jobs() -> list[dict]:
    if not _scheduler:
        return []
    jobs = []
    for job in _scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "job_id": job.id,
            "name": job.name,
            "next_run": next_run.isoformat() if next_run else None,
            "pending": job.pending,
        })
    return jobs


def get_job_info(monitor_id: int) -> dict | None:
    if not _scheduler:
        return None
    jid = _job_id(monitor_id)
    job = _scheduler.get_job(jid)
    if not job:
        return None
    next_run = job.next_run_time
    return {
        "job_id": job.id,
        "name": job.name,
        "next_run": next_run.isoformat() if next_run else None,
        "pending": job.pending,
    }


# ── Carregamento inicial ─────────────────────────────────────────────────────

def _load_all_active_monitors():
    from database import list_monitors
    monitors = list_monitors(active_only=True)
    for m in monitors:
        add_job(m["id"], m["interval_minutes"])
    logger.info(f"{len(monitors)} monitor(es) carregado(s) no scheduler.")


# ── Execução segura ──────────────────────────────────────────────────────────

def _run_safe(monitor_id: int):
    """Wrapper que garante que uma falha não derruba o scheduler."""
    try:
        from worker import run_journey
        result = run_journey(monitor_id)
        status = result.get("status", "UNKNOWN")
        logger.info(f"[monitor_id={monitor_id}] Jornada concluída — status={status}")
    except Exception as exc:
        logger.error(f"[monitor_id={monitor_id}] Erro inesperado no worker: {exc}")


# ── Listener de eventos ──────────────────────────────────────────────────────

def _on_job_event(event):
    if event.exception:
        logger.error(f"Job {event.job_id} falhou: {event.exception}")
    else:
        logger.debug(f"Job {event.job_id} executado com sucesso.")
