import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector

from app.database import get_db
from app.core.dependencies import get_current_recruiter
from app.models.document import Document
from app.models.job import Job
from app.models.recruiter import Recruiter

router = APIRouter(prefix="/jobs", tags=["matching"])


@router.get("/{job_id}/matches")
async def get_job_matches(
    job_id: uuid.UUID,
    limit: int = Query(default=10, ge=1, le=50),
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    """Returns ranked candidate matches for recruiter review. Advisory only — does not affect application status."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.created_by != recruiter.id:
        raise HTTPException(status_code=403, detail="Not your job posting")
    if job.embedding is None:
        raise HTTPException(status_code=404, detail="Job not yet processed for matching")

    query = (
        select(
            Document,
            Document.embedding.cosine_distance(job.embedding).label("distance"),
        )
        .where(Document.embedding.isnot(None))
        .order_by("distance")
        .limit(limit)
    )
    result = await db.execute(query)
    matches = result.all()

    return {
        "job_id": str(job_id),
        "matches": [
            {
                "document_id": str(doc.id),
                "candidate_id": str(doc.candidate_id),
                "similarity_score": round(1 - distance, 4),
                "parsed_data": doc.parsed_data,
            }
            for doc, distance in matches
        ],
    }
