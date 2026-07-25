from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import InterviewRound

INTERVIEW_DURATION = timedelta(hours=1)


async def check_interview_overlap(
    conducted_by: UUID,
    scheduled_at,
    db: AsyncSession,
    exclude_interview_id: UUID | None = None,
) -> None:
    start = scheduled_at.replace(tzinfo=None) if scheduled_at.tzinfo else scheduled_at
    end = start + INTERVIEW_DURATION

    query = select(InterviewRound).where(
        and_(
            InterviewRound.conducted_by == conducted_by,
            InterviewRound.scheduled_at.isnot(None),
        )
    )
    if exclude_interview_id:
        query = query.where(InterviewRound.id != exclude_interview_id)

    result = await db.execute(query)
    for existing in result.scalars():
        existing_start = (
            existing.scheduled_at.replace(tzinfo=None)
            if existing.scheduled_at.tzinfo
            else existing.scheduled_at
        )
        existing_end = existing_start + INTERVIEW_DURATION
        if start < existing_end and end > existing_start:
            raise HTTPException(
                status_code=409,
                detail=f"Interviewer has a conflicting interview at {existing.scheduled_at}",
            )
