import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select, func

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.constants import ACTIVE_STATUSES
from app.database import async_session
from app.models.application import Application, ApplicationStatusHistory

log = structlog.get_logger("ats.scheduled")


async def _flag_stale_applications_async():
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.STALE_APPLICATION_DAYS)

    async with async_session() as db:
        subq = (
            select(
                ApplicationStatusHistory.application_id,
                func.max(ApplicationStatusHistory.changed_at).label("last_changed"),
            )
            .group_by(ApplicationStatusHistory.application_id)
            .subquery()
        )

        query = (
            select(Application.id, Application.current_status, subq.c.last_changed)
            .join(subq, Application.id == subq.c.application_id)
            .where(Application.current_status.in_(ACTIVE_STATUSES))
            .where(subq.c.last_changed < cutoff)
        )

        result = await db.execute(query)
        stale = result.all()

        for app_id, status, last_changed in stale:
            log.warn(
                "application.stale",
                application_id=str(app_id),
                status=status,
                last_changed=str(last_changed),
                stale_days=settings.STALE_APPLICATION_DAYS,
            )

        log.info("stale_sweep.complete", flagged=len(stale))
        return len(stale)


@celery_app.task(name="app.tasks.scheduled_tasks.flag_stale_applications")
def flag_stale_applications():
    asyncio.run(_flag_stale_applications_async())
