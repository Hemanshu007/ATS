from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.dependencies import get_current_candidate, get_current_user
from app.core.constants import VALID_STATUSES
from app.models.candidate import Candidate
from app.models.application import Application
from app.models.job import Job
from app.models.company import Company
from app.models.user import User

router = APIRouter(prefix="/candidates", tags=["candidates"])


# --- Schemas ---

class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    location: str | None = Field(default=None, max_length=100)


# --- GET /candidates/me/profile ---

@router.get("/me/profile")
async def get_profile(
    candidate: Candidate = Depends(get_current_candidate),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {
        "id": candidate.id,
        "name": candidate.name,
        "phone": candidate.phone,
        "location": candidate.location,
        "email": user.email,
        "created_at": candidate.created_at,
    }


# --- PATCH /candidates/me/profile ---

@router.patch("/me/profile")
async def update_profile(
    body: ProfileUpdate,
    candidate: Candidate = Depends(get_current_candidate),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields provided to update")

    for key, value in update_data.items():
        setattr(candidate, key, value)

    await db.commit()
    await db.refresh(candidate)

    return {
        "id": candidate.id,
        "name": candidate.name,
        "phone": candidate.phone,
        "location": candidate.location,
        "email": user.email,
        "created_at": candidate.created_at,
    }


# --- GET /candidates/me/dashboard ---

@router.get("/me/dashboard")
async def candidate_dashboard(
    candidate: Candidate = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    # Status breakdown
    status_breakdown = {}
    for s in VALID_STATUSES:
        count = await db.scalar(
            select(func.count(Application.id))
            .where(Application.candidate_id == candidate.id)
            .where(Application.current_status == s)
        ) or 0
        status_breakdown[s] = count

    total_applications = sum(status_breakdown.values())

    # Recent applications (last 5)
    result = await db.execute(
        select(Application)
        .where(Application.candidate_id == candidate.id)
        .options(
            selectinload(Application.job).selectinload(Job.company),
        )
        .order_by(Application.applied_at.desc())
        .limit(5)
    )
    recent = result.scalars().all()

    recent_applications = [
        {
            "job_title": app.job.title,
            "company_name": app.job.company.name,
            "current_status": app.current_status,
            "applied_at": app.applied_at,
        }
        for app in recent
    ]

    return {
        "total_applications": total_applications,
        "status_breakdown": status_breakdown,
        "recent_applications": recent_applications,
    }
