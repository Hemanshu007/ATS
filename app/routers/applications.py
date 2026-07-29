import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.dependencies import get_current_user, get_current_recruiter, get_current_candidate
from app.core.constants import (
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE_MB,
    MAX_FILE_SIZE_BYTES,
    VALID_STATUSES,
)
from app.models.user import User
from app.models.candidate import Candidate
from app.models.recruiter import Recruiter
from app.models.job import Job
from app.models.document import Document
from app.models.application import Application, ApplicationStatusHistory
from app.schemas.application import ApplicationOut, StatusUpdate, StatusHistoryOut
from app.schemas.pagination import paginate
from app.services.email import send_status_change_email
from app.services.application_service import validate_status_transition

log = structlog.get_logger("ats.applications")

router = APIRouter(prefix="/applications", tags=["applications"])


async def validate_resume_file(file: UploadFile) -> bytes:
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="A resume file is required")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Only PDF files are accepted.",
        )

    contents = await file.read()

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_MB}MB.",
        )

    await file.seek(0)
    return contents


@router.post("/", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def apply(
    job_id: str = Form(...),
    resume: UploadFile = File(...),
    candidate: Candidate = Depends(get_current_candidate),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await validate_resume_file(resume)

    job_uuid = uuid.UUID(job_id)

    try:
        job_query = select(Job).where(Job.id == job_uuid)
        dialect = db.bind.dialect.name if db.bind else ""
        if dialect != "sqlite":
            job_query = job_query.with_for_update()

        result = await db.execute(job_query)
        job = result.scalar_one_or_none()

        if not job or job.status != "open":
            raise HTTPException(status_code=400, detail="Job not found or closed")

        if hasattr(job, "is_deleted") and job.is_deleted:
            raise HTTPException(status_code=400, detail="Job not found or closed")

        from app.services.storage import save_resume
        file_path, original_filename = await save_resume(resume)

        doc = Document(
            candidate_id=candidate.id,
            file_path=file_path,
            original_filename=original_filename,
        )
        db.add(doc)
        await db.flush()

        application = Application(
            job_id=job_uuid,
            candidate_id=candidate.id,
            document_id=doc.id,
        )
        db.add(application)
        await db.flush()

        history = ApplicationStatusHistory(
            application_id=application.id,
            status="applied",
            changed_by=user.id,
        )
        db.add(history)

        await db.commit()

    except HTTPException:
        raise
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Already applied to this job")
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Application could not be created")

    await db.refresh(application)

    try:
        from app.tasks.resume_processing_tasks import process_resume
        process_resume.delay(str(doc.id))
    except Exception as e:
        log.warn("resume_processing.dispatch_failed", document_id=str(doc.id), error=str(e))

    return application


@router.get("/job/{job_id}")
async def list_applications_for_job(
    job_id: uuid.UUID,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)
    if not job or job.created_by != recruiter.id:
        raise HTTPException(status_code=403, detail="Not your job posting")

    query = select(Application).where(Application.job_id == job_id)

    if status_filter:
        if status_filter not in VALID_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status '{status_filter}'. Must be one of: {VALID_STATUSES}",
            )
        query = query.where(Application.current_status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Application.applied_at.desc()).offset(offset).limit(page_size)
    )
    items = result.scalars().all()

    return paginate(
        items=[ApplicationOut.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/me")
async def my_applications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    candidate: Candidate = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    query = select(Application).where(Application.candidate_id == candidate.id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Application.applied_at.desc()).offset(offset).limit(page_size)
    )
    items = result.scalars().all()

    return paginate(
        items=[ApplicationOut.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{app_id}/status", response_model=ApplicationOut)
async def update_status(
    app_id: uuid.UUID,
    body: StatusUpdate,
    background_tasks: BackgroundTasks,
    recruiter: Recruiter = Depends(get_current_recruiter),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await db.scalar(
        select(Application).where(Application.id == app_id).options(
            selectinload(Application.job).selectinload(Job.company),
            selectinload(Application.candidate).selectinload(Candidate.user),
        )
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.job.created_by != recruiter.id:
        raise HTTPException(status_code=403, detail="Not your job posting")

    validate_status_transition(application.current_status, body.status)

    application.current_status = body.status
    history = ApplicationStatusHistory(
        application_id=application.id,
        status=body.status,
        changed_by=user.id,
        notes=body.notes,
    )
    db.add(history)
    await db.commit()

    background_tasks.add_task(
        send_status_change_email,
        candidate_email=application.candidate.user.email,
        candidate_name=application.candidate.name,
        job_title=application.job.title,
        company_name=application.job.company.name,
        new_status=body.status,
    )
    await db.refresh(application)
    return application


@router.get("/{app_id}/history", response_model=list[StatusHistoryOut])
async def get_history(
    app_id: uuid.UUID,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    application = await db.scalar(
        select(Application).where(Application.id == app_id).options(selectinload(Application.job))
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.job.created_by != recruiter.id:
        raise HTTPException(status_code=403, detail="Not your job posting")

    result = await db.execute(
        select(ApplicationStatusHistory)
        .where(ApplicationStatusHistory.application_id == app_id)
        .order_by(ApplicationStatusHistory.changed_at)
    )
    return result.scalars().all()


@router.get("/{app_id}", response_model=None)
async def get_application_detail(
    app_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    application = await db.scalar(
        select(Application)
        .where(Application.id == app_id)
        .options(
            selectinload(Application.job).selectinload(Job.company),
            selectinload(Application.candidate),
            selectinload(Application.status_history),
            selectinload(Application.interview_rounds),
        )
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if user.role == "recruiter":
        recruiter = await db.scalar(select(Recruiter).where(Recruiter.user_id == user.id))
        if not recruiter or application.job.created_by != recruiter.id:
            raise HTTPException(status_code=403, detail="Not your job posting")
    elif user.role == "candidate":
        candidate = await db.scalar(select(Candidate).where(Candidate.user_id == user.id))
        if not candidate or application.candidate_id != candidate.id:
            raise HTTPException(status_code=403, detail="Not your application")
    else:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": application.id,
        "job": {
            "id": application.job.id,
            "title": application.job.title,
            "company": application.job.company.name,
            "job_type": application.job.job_type,
        },
        "candidate": {
            "id": application.candidate.id,
            "name": application.candidate.name,
        },
        "current_status": application.current_status,
        "applied_at": application.applied_at,
        "interview_rounds": [
            {
                "round_number": r.round_number,
                "outcome": r.outcome,
                "scheduled_at": r.scheduled_at,
            }
            for r in sorted(application.interview_rounds, key=lambda r: r.round_number)
        ],
        "status_history": [
            {"status": h.status, "changed_at": h.changed_at}
            for h in sorted(application.status_history, key=lambda h: h.changed_at)
        ],
    }


@router.get("/{app_id}/resume")
async def get_resume_download_url(
    app_id: uuid.UUID,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    application = await db.scalar(
        select(Application).where(Application.id == app_id).options(selectinload(Application.job))
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.job.created_by != recruiter.id:
        raise HTTPException(status_code=403, detail="Not your job posting")

    document = await db.get(Document, application.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Resume not found")

    try:
        from app.services.s3 import get_presigned_download_url
        url = get_presigned_download_url(document.file_path, expiry_seconds=3600)
        return {
            "url": url,
            "filename": document.original_filename,
            "expires_in_seconds": 3600,
            "expires_in_human": "1 hour",
        }
    except (ImportError, RuntimeError):
        return {
            "filename": document.original_filename,
            "message": "Resume storage is not available for remote download.",
        }
