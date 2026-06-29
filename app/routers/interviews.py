import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.dependencies import get_current_recruiter
from app.models.recruiter import Recruiter
from app.models.application import Application
from app.models.job import Job
from app.models.interview import InterviewRound
from app.schemas.interview import InterviewCreate, InterviewOut, OutcomeUpdate

router = APIRouter(prefix="/interviews", tags=["interviews"])

INTERVIEW_DURATION = timedelta(hours=1)


async def _verify_ownership(app_id: uuid.UUID, recruiter: Recruiter, db) -> Application:
    application = await db.scalar(
        select(Application).where(Application.id == app_id).options(selectinload(Application.job))
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.job.created_by != recruiter.id:
        raise HTTPException(status_code=403, detail="Not your job posting")
    return application


@router.post("/", response_model=InterviewOut, status_code=status.HTTP_201_CREATED)
async def create_interview(
    body: InterviewCreate,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    await _verify_ownership(body.application_id, recruiter, db)

    # Validate round_number range
    if body.round_number < 1 or body.round_number > 100:
        raise HTTPException(
            status_code=422,
            detail="Round number must be between 1 and 100 inclusive"
        )

    # Validate conducted_by exists
    if body.conducted_by:
        interviewer = await db.get(Recruiter, body.conducted_by)
        if not interviewer:
            raise HTTPException(status_code=400, detail="Interviewer not found")

    # Check overlap for the interviewer
    if body.scheduled_at and body.conducted_by:
        start = body.scheduled_at.replace(tzinfo=None) if body.scheduled_at.tzinfo else body.scheduled_at
        end = start + INTERVIEW_DURATION
        result = await db.execute(
            select(InterviewRound).where(
                and_(
                    InterviewRound.conducted_by == body.conducted_by,
                    InterviewRound.scheduled_at.isnot(None),
                )
            )
        )
        for existing in result.scalars():
            existing_start = existing.scheduled_at.replace(tzinfo=None) if existing.scheduled_at.tzinfo else existing.scheduled_at
            existing_end = existing_start + INTERVIEW_DURATION
            if start < existing_end and end > existing_start:
                raise HTTPException(
                    status_code=409,
                    detail=f"Interviewer has a conflicting interview at {existing.scheduled_at}",
                )

    interview = InterviewRound(
        application_id=body.application_id,
        round_number=body.round_number,
        scheduled_at=body.scheduled_at,
        conducted_by=body.conducted_by,
    )
    db.add(interview)

    # FIX-05: Handle IntegrityError for duplicate round number
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Round {body.round_number} already exists for this application"
        )

    await db.refresh(interview)
    return interview


@router.get("/application/{app_id}", response_model=list[InterviewOut])
async def list_interviews(
    app_id: uuid.UUID,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    await _verify_ownership(app_id, recruiter, db)
    result = await db.execute(
        select(InterviewRound)
        .where(InterviewRound.application_id == app_id)
        .order_by(InterviewRound.round_number)
    )
    return result.scalars().all()


@router.patch("/{interview_id}/outcome", response_model=InterviewOut)
async def update_outcome(
    interview_id: uuid.UUID,
    body: OutcomeUpdate,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    interview = await db.get(InterviewRound, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview round not found")
    await _verify_ownership(interview.application_id, recruiter, db)
    interview.outcome = body.outcome
    interview.notes = body.notes
    await db.commit()
    await db.refresh(interview)
    return interview


# --- ENDPOINT-05: Interview Round Detail ---

@router.get("/{interview_id}", response_model=InterviewOut)
async def get_interview_detail(
    interview_id: uuid.UUID,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    interview = await db.get(InterviewRound, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview round not found")
    await _verify_ownership(interview.application_id, recruiter, db)
    return interview


# --- ENDPOINT-05: Cancel Interview Round ---

@router.delete("/{interview_id}")
async def cancel_interview(
    interview_id: uuid.UUID,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    interview = await db.get(InterviewRound, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview round not found")
    await _verify_ownership(interview.application_id, recruiter, db)

    # Can only cancel if outcome is still pending
    if interview.outcome != "pending":
        raise HTTPException(
            status_code=409,
            detail="Cannot cancel a completed interview"
        )

    interview.outcome = "cancelled"
    await db.commit()
    await db.refresh(interview)
    return {"message": "Interview cancelled", "id": str(interview.id)}
