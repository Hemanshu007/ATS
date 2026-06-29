import uuid
from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.dependencies import get_current_recruiter
from app.core.constants import ACTIVE_STATUSES
from app.models.job import Job
from app.models.recruiter import Recruiter
from app.models.application import Application
from app.schemas.job import JobCreate, JobOut, JobStatusUpdate

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobOut, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: JobCreate,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    job = Job(
        title=body.title,
        description=body.description,
        location=body.location,
        job_type=body.job_type,
        company_id=recruiter.company_id,
        created_by=recruiter.id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job, attribute_names=["company"])
    return job


# --- GET /jobs/ with pagination + filters (PAGE-01, FILTER-02) ---

@router.get("/")
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    job_type: str | None = Query(default=None),
    location: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job).where(Job.status == "open")

    # SOFT-01: Exclude soft-deleted jobs
    if hasattr(Job, "is_deleted"):
        query = query.where(Job.is_deleted == False)

    # FILTER-02: Filter by job_type
    if job_type:
        valid_types = ["onsite", "remote", "hybrid"]
        if job_type not in valid_types:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid job_type '{job_type}'. Must be one of: {valid_types}"
            )
        query = query.where(Job.job_type == job_type)

    # FILTER-02: Filter by location (case-insensitive partial match)
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Paginate
    offset = (page - 1) * page_size
    result = await db.execute(
        query.options(selectinload(Job.company))
        .order_by(Job.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    jobs = result.scalars().all()

    return {
        "items": [JobOut.model_validate(j) for j in jobs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": ceil(total / page_size) if total > 0 else 0,
        "has_next": offset + page_size < total,
        "has_previous": page > 1,
    }


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    query = select(Job).where(Job.id == job_id).options(selectinload(Job.company))

    # SOFT-01: Exclude soft-deleted
    if hasattr(Job, "is_deleted"):
        query = query.where(Job.is_deleted == False)

    result = await db.execute(query)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}/status", response_model=JobOut)
async def update_job_status(
    job_id: uuid.UUID,
    body: JobStatusUpdate,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job).where(Job.id == job_id).options(selectinload(Job.company))
    if hasattr(Job, "is_deleted"):
        query = query.where(Job.is_deleted == False)

    result = await db.execute(query)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.created_by != recruiter.id:
        raise HTTPException(status_code=403, detail="Not your job posting")
    job.status = body.status
    await db.commit()
    await db.refresh(job)
    return job


# --- DELETE /jobs/{job_id} (SOFT-01: Soft Delete) ---

@router.delete("/{job_id}")
async def delete_job(
    job_id: uuid.UUID,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job).where(Job.id == job_id)
    if hasattr(Job, "is_deleted"):
        query = query.where(Job.is_deleted == False)

    result = await db.execute(query)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Validate ownership
    if job.created_by != recruiter.id:
        raise HTTPException(status_code=403, detail="You do not own this job posting")

    # Prevent deletion if active applications exist
    active_count = await db.scalar(
        select(func.count(Application.id))
        .where(Application.job_id == job_id)
        .where(Application.current_status.in_(ACTIVE_STATUSES))
    )

    if active_count and active_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete job with {active_count} active application(s). "
                   "Close the job and resolve all active applications first."
        )

    job.is_deleted = True
    job.deleted_at = datetime.utcnow()
    await db.commit()

    return {"message": "Job deleted successfully"}
