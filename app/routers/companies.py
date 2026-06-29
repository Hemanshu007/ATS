import uuid
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.dependencies import get_current_recruiter
from app.models.company import Company
from app.models.job import Job
from app.models.recruiter import Recruiter
from app.schemas.job import JobOut

router = APIRouter(prefix="/companies", tags=["companies"])


# --- Schemas ---

class CompanyOut(BaseModel):
    id: uuid.UUID
    name: str
    industry: str | None
    location: str | None
    created_at: object

    class Config:
        from_attributes = True


class CompanyDetailOut(CompanyOut):
    open_jobs_count: int


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    industry: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=100)


# --- GET /companies/ (public, paginated) ---

@router.get("/")
async def list_companies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Company)
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Company.name).offset(offset).limit(page_size)
    )
    companies = result.scalars().all()

    return {
        "items": [CompanyOut.model_validate(c) for c in companies],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": ceil(total / page_size) if total > 0 else 0,
        "has_next": offset + page_size < total,
        "has_previous": page > 1,
    }


# --- GET /companies/me (recruiter only) --- must be before /{company_id}

@router.get("/me")
async def get_my_company(
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    company = await db.get(Company, recruiter.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    open_jobs_count = await db.scalar(
        select(func.count(Job.id))
        .where(Job.company_id == company.id, Job.status == "open")
        .where(Job.is_deleted == False)
    )

    return {
        **CompanyOut.model_validate(company).model_dump(),
        "open_jobs_count": open_jobs_count or 0,
    }


# --- PATCH /companies/me (recruiter only) ---

@router.patch("/me")
async def update_my_company(
    body: CompanyUpdate,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    company = await db.get(Company, recruiter.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields provided to update")

    for key, value in update_data.items():
        setattr(company, key, value)

    await db.commit()
    await db.refresh(company)
    return CompanyOut.model_validate(company)


# --- GET /companies/{company_id} (public) ---

@router.get("/{company_id}")
async def get_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    open_jobs_count = await db.scalar(
        select(func.count(Job.id))
        .where(Job.company_id == company.id, Job.status == "open")
        .where(Job.is_deleted == False)
    )

    return {
        **CompanyOut.model_validate(company).model_dump(),
        "open_jobs_count": open_jobs_count or 0,
    }


# --- GET /companies/{company_id}/jobs (public, paginated) ---

@router.get("/{company_id}/jobs")
async def get_company_jobs(
    company_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    query = (
        select(Job)
        .where(Job.company_id == company_id, Job.status == "open")
        .where(Job.is_deleted == False)
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

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
