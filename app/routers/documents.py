import uuid
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_candidate
from app.core.constants import ACTIVE_STATUSES
from app.models.candidate import Candidate
from app.models.document import Document
from app.models.application import Application

router = APIRouter(prefix="/documents", tags=["documents"])


# --- GET /documents/me (paginated) ---

@router.get("/me")
async def list_my_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    candidate: Candidate = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    query = select(Document).where(Document.candidate_id == candidate.id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Document.uploaded_at.desc()).offset(offset).limit(page_size)
    )
    documents = result.scalars().all()

    items = [
        {
            "id": doc.id,
            "original_filename": doc.original_filename,
            "uploaded_at": doc.uploaded_at,
        }
        for doc in documents
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": ceil(total / page_size) if total > 0 else 0,
        "has_next": offset + page_size < total,
        "has_previous": page > 1,
    }


# --- DELETE /documents/{document_id} ---

@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    candidate: Candidate = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    document = await db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify ownership
    if document.candidate_id != candidate.id:
        raise HTTPException(status_code=403, detail="Not your document")

    # Check if linked to active application
    active_app = await db.scalar(
        select(Application)
        .where(Application.document_id == document_id)
        .where(Application.current_status.in_(ACTIVE_STATUSES))
    )
    if active_app:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete document linked to an active application"
        )

    # Delete from S3 if configured
    try:
        from app.services.s3 import delete_resume
        delete_resume(document.file_path)
    except (ImportError, RuntimeError):
        pass  # S3 not configured, skip

    await db.delete(document)
    await db.commit()

    return {"message": "Document deleted successfully"}
