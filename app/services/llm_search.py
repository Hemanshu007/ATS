import json
import logging
from typing import Optional

from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger("ats.llm_search")


class CandidateMatchExplanation(BaseModel):
    document_id: str
    candidate_id: str
    relevance_summary: str
    supporting_evidence: list[str]


class SearchResult(BaseModel):
    query: str
    matches: list[CandidateMatchExplanation]


SYSTEM_PROMPT = """You are an ATS candidate search assistant. Your job is to explain why retrieved candidates match a recruiter's search query.

RULES (non-negotiable):
- ONLY reference facts that are explicitly present in the provided parsed_data for each candidate.
- NEVER infer, assume, or fabricate information not present in the data.
- If a candidate's parsed_data does not contain enough information to assess relevance, say "Insufficient information in parsed data to assess match" as the relevance_summary and provide an empty supporting_evidence list.
- supporting_evidence must be near-verbatim references to specific parsed_data fields (e.g., "Skills include Python, FastAPI, Docker", "Work history: Backend Engineer at Acme Corp").
- Keep relevance_summary to 1-3 sentences. Be specific, not generic.
- A low similarity_score means the candidate is a weak match — do not oversell weak matches. Frame them as partial or tangential fits."""

GROUNDING_PROMPT = """Search query: "{query}"

For each candidate below, explain why they match (or don't match) the query, citing specific parsed_data fields.

Candidates:
{candidates_json}

Return a JSON object with:
- query: the original search query string
- matches: a list of objects, one per candidate, each with:
  - document_id: string
  - candidate_id: string
  - relevance_summary: 1-3 sentence explanation grounded ONLY in parsed_data
  - supporting_evidence: list of near-verbatim field references from parsed_data"""


def _build_candidates_json(candidates: list[dict]) -> str:
    parts = []
    for i, c in enumerate(candidates, 1):
        parts.append(
            f"Candidate {i}:\n"
            f"  document_id: {c['document_id']}\n"
            f"  candidate_id: {c['candidate_id']}\n"
            f"  similarity_score: {c['similarity_score']:.4f}\n"
            f"  parsed_data: {json.dumps(c['parsed_data'], default=str)}"
        )
    return "\n\n".join(parts)


async def _generate_with_gemini(query: str, candidates: list[dict]) -> SearchResult:
    from google import genai

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    candidates_text = _build_candidates_json(candidates)
    user_prompt = GROUNDING_PROMPT.format(query=query, candidates_json=candidates_text)

    response = await client.aio.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=SYSTEM_PROMPT + "\n\n" + user_prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )

    data = json.loads(response.text)
    return SearchResult(**data)


async def _generate_with_openai(query: str, candidates: list[dict]) -> SearchResult:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    candidates_text = _build_candidates_json(candidates)
    user_prompt = GROUNDING_PROMPT.format(query=query, candidates_json=candidates_text)

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    return SearchResult(**data)


async def generate_search_explanation(
    query: str,
    retrieved_candidates: list[dict],
) -> SearchResult:
    if settings.LLM_PROVIDER == "gemini":
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")
        return await _generate_with_gemini(query, retrieved_candidates)

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")
    return await _generate_with_openai(query, retrieved_candidates)
