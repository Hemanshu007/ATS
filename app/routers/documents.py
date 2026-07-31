import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_candidate
from app.models.candidate import Candidate
from app.models.document import Document
from app.models.application import Application
from app.schemas.pagination import paginate

router = APIRouter(prefix="/documents", tags=["documents"])


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

    return paginate(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    candidate: Candidate = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
):
    document = await db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.candidate_id != candidate.id:
        raise HTTPException(status_code=403, detail="Not your document")

    # Application.document_id is a required FK with no cascade, so a document can
    # never be hard-deleted while any application (including terminal ones like
    # "hired"/"rejected") still references it — that history record needs it.
    linked_app = await db.scalar(
        select(Application).where(Application.document_id == document_id)
    )
    if linked_app:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete document linked to an application",
        )

    from app.services.storage import is_s3_configured, delete_local_resume

    if is_s3_configured():
        from app.services.s3 import delete_resume
        delete_resume(document.file_path)
    else:
        delete_local_resume(document.file_path)

    await db.delete(document)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete document linked to an application",
        )

    return {"message": "Document deleted successfully"}
