import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.core.dependencies import get_current_recruiter
from app.models.recruiter import Recruiter
from app.models.application import Application, ApplicationNote
from app.models.job import Job
from app.schemas.application import NoteCreate, NoteOut

router = APIRouter(tags=["notes"])


async def _verify_note_access(app_id: uuid.UUID, recruiter: Recruiter, db: AsyncSession):
    application = await db.scalar(
        select(Application).where(Application.id == app_id).options(selectinload(Application.job))
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.job.created_by != recruiter.id:
        raise HTTPException(status_code=403, detail="Not your job posting")


@router.post(
    "/applications/{app_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED
)
async def create_note(
    app_id: uuid.UUID,
    body: NoteCreate,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    await _verify_note_access(app_id, recruiter, db)
    note = ApplicationNote(application_id=app_id, content=body.content, created_by=recruiter.id)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.get("/applications/{app_id}/notes", response_model=list[NoteOut])
async def list_notes(
    app_id: uuid.UUID,
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    await _verify_note_access(app_id, recruiter, db)
    result = await db.execute(
        select(ApplicationNote)
        .where(ApplicationNote.application_id == app_id)
        .order_by(ApplicationNote.created_at)
    )
    return result.scalars().all()
