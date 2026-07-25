import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.constants import ACTIVE_STATUSES
from app.database import async_session
from app.models.application import Application, ApplicationStatusHistory

logger = logging.getLogger("ats.scheduled")


async def _flag_stale_applications_async():
    cutoff = datetime.utcnow() - timedelta(days=settings.STALE_APPLICATION_DAYS)

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
            logger.warning(
                f"Stale application {app_id}: stuck in '{status}' since {last_changed} "
                f"(>{settings.STALE_APPLICATION_DAYS} days)"
            )

        logger.info(f"Stale application sweep complete: {len(stale)} flagged")
        return len(stale)


@celery_app.task(name="app.tasks.scheduled_tasks.flag_stale_applications")
def flag_stale_applications():
    asyncio.run(_flag_stale_applications_async())
