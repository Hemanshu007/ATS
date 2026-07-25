from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_recruiter
from app.core.constants import VALID_STATUSES
from app.models.recruiter import Recruiter
from app.models.job import Job
from app.models.application import Application
from app.schemas.pagination import paginate

router = APIRouter(prefix="/recruiters", tags=["recruiters"])


@router.get("/me/dashboard")
async def recruiter_dashboard(
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    job_query = select(Job.id).where(Job.created_by == recruiter.id)
    if hasattr(Job, "is_deleted"):
        job_query = job_query.where(Job.is_deleted == False)

    job_result = await db.execute(job_query)
    job_ids = [row[0] for row in job_result.all()]

    total_jobs = len(job_ids)
    open_jobs = await db.scalar(
        select(func.count(Job.id))
        .where(Job.created_by == recruiter.id, Job.status == "open")
        .where(Job.is_deleted == False)
    ) or 0
    closed_jobs = total_jobs - open_jobs

    pipeline_summary = {}
    for s in VALID_STATUSES:
        if job_ids:
            count = await db.scalar(
                select(func.count(Application.id))
                .where(Application.job_id.in_(job_ids))
                .where(Application.current_status == s)
            ) or 0
        else:
            count = 0
        pipeline_summary[s] = count

    total_applications = sum(pipeline_summary.values())

    return {
        "total_jobs": total_jobs,
        "open_jobs": open_jobs,
        "closed_jobs": closed_jobs,
        "total_applications": total_applications,
        "pipeline_summary": pipeline_summary,
    }


@router.get("/me/jobs")
async def recruiter_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job).where(Job.created_by == recruiter.id)
    if hasattr(Job, "is_deleted"):
        query = query.where(Job.is_deleted == False)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Job.created_at.desc()).offset(offset).limit(page_size)
    )
    jobs = result.scalars().all()

    items = []
    for job in jobs:
        app_count = await db.scalar(
            select(func.count(Application.id)).where(Application.job_id == job.id)
        ) or 0
        items.append({
            "id": job.id,
            "title": job.title,
            "status": job.status,
            "job_type": job.job_type,
            "application_count": app_count,
            "created_at": job.created_at,
        })

    return paginate(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
