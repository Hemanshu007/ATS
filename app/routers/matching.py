import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector

from app.database import get_db
from app.core.dependencies import get_current_recruiter
from app.models.document import Document
from app.models.job import Job
from app.models.recruiter import Recruiter
from app.services.embeddings import generate_embedding
from app.services.llm_search import generate_search_explanation

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

    matches = await _retrieve_candidates(job.embedding, limit, db)

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


async def _retrieve_candidates(
    embedding: list[float],
    limit: int,
    db: AsyncSession,
) -> list[tuple[Document, float]]:
    query = (
        select(
            Document,
            Document.embedding.cosine_distance(embedding).label("distance"),
        )
        .where(Document.embedding.isnot(None))
        .order_by("distance")
        .limit(limit)
    )
    result = await db.execute(query)
    return result.all()


class SearchQuery(BaseModel):
    query: str


@router.post("/{job_id}/search")
async def search_candidates(
    job_id: uuid.UUID,
    body: SearchQuery,
    limit: int = Query(default=5, ge=1, le=15),
    recruiter: Recruiter = Depends(get_current_recruiter),
    db: AsyncSession = Depends(get_db),
):
    """Advisory read-only search: natural-language query → grounded candidate explanations.

    Never writes to Application.current_status or any other mutating field.
    Limit capped at 15 to control LLM context size — more candidates increase
    cost, latency, and hallucination risk as the model tracks more context.
    """
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.created_by != recruiter.id:
        raise HTTPException(status_code=403, detail="Not your job posting")

    try:
        query_embedding = await generate_embedding(body.query)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Embedding service unavailable. Please retry.",
        )

    retrieved = await _retrieve_candidates(query_embedding, limit, db)

    candidates_for_llm = [
        {
            "document_id": str(doc.id),
            "candidate_id": str(doc.candidate_id),
            "parsed_data": doc.parsed_data,
            "similarity_score": round(1 - distance, 4),
        }
        for doc, distance in retrieved
    ]

    try:
        search_result = await generate_search_explanation(body.query, candidates_for_llm)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="LLM service unavailable. Please retry.",
        )

    return search_result.model_dump()
