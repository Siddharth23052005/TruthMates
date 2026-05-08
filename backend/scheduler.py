from __future__ import annotations

from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.logging import get_logger, log_event
import trending_pipeline

logger = get_logger("truthmates.scheduler")
_scheduler: AsyncIOScheduler | None = None


async def _run_trending_job() -> None:
    log_event(logger, "trending_job_started")
    try:
        payload = await trending_pipeline.run()
        log_event(logger, "trending_job_completed", **payload)
    except Exception as exc:
        log_event(logger, "trending_job_failed", level="error", error=str(exc))


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _run_trending_job,
        trigger="date",
        run_date=datetime.now(timezone.utc),
        id="trending_service_bootstrap_job",
        replace_existing=True,
    )
    _scheduler.add_job(
        _run_trending_job,
        trigger="interval",
        hours=6,
        id="trending_service_job",
        replace_existing=True,
    )
    _scheduler.start()
    log_event(logger, "scheduler_started", interval_hours=6)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    log_event(logger, "scheduler_stopped")
