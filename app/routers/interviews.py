import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_recruiter
from app.models.recruiter import Recruiter
from app.models.application import Application
from app.models.interview import InterviewRound
from app.schemas.interview import InterviewCreate, InterviewOut, OutcomeUpdate
from app.services.interview_service import check_interview_overlap

router = APIRouter(prefix="/interviews", tags=["interviews"])


async def _verify_ownership(app_id: uuid.UUID, recruiter: Recruiter, db) -> Application:
    from sqlalchemy.orm import selectinload
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

    if body.round_number < 1 or body.round_number > 100:
        raise HTTPException(
            status_code=422,
            detail="Round number must be between 1 and 100 inclusive",
        )

    if body.conducted_by:
        interviewer = await db.get(Recruiter, body.conducted_by)
        if not interviewer:
            raise HTTPException(status_code=400, detail="Interviewer not found")

    if body.scheduled_at and body.conducted_by:
        await check_interview_overlap(body.conducted_by, body.scheduled_at, db)

    interview = InterviewRound(
        application_id=body.application_id,
        round_number=body.round_number,
        scheduled_at=body.scheduled_at,
        conducted_by=body.conducted_by,
    )
    db.add(interview)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Round {body.round_number} already exists for this application",
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

    if interview.outcome != "pending":
        raise HTTPException(
            status_code=409,
            detail="Cannot cancel a completed interview",
        )

    interview.outcome = "cancelled"
    await db.commit()
    await db.refresh(interview)
    return {"message": "Interview cancelled", "id": str(interview.id)}
