import io
import json
import logging
from typing import Optional

from pydantic import BaseModel, model_validator
from pypdf import PdfReader

from app.core.config import settings

logger = logging.getLogger("ats.llm")


class Education(BaseModel):
    degree: Optional[str] = ""
    institution: Optional[str] = ""


class WorkHistory(BaseModel):
    role: Optional[str] = ""
    company: Optional[str] = ""
    duration: Optional[str] = ""


class ResumeExtraction(BaseModel):
    name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    skills: list[str] = []
    years_of_experience: Optional[float] = None
    education: list[Education] = []
    work_history: list[WorkHistory] = []


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
    return "\n".join(text_parts)


EXTRACTION_PROMPT = """Extract structured data from this resume text.
Return a JSON object with these fields:
- name: string (full name)
- email: string
- phone: string
- skills: list of strings (technical and soft skills)
- years_of_experience: float or null (estimated total years)
- education: list of objects with "degree" and "institution" strings
- work_history: list of objects with "role", "company", and "duration" strings

Resume text:
{resume_text}"""


async def _extract_with_openai(resume_text: str) -> ResumeExtraction:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a resume parsing assistant. Extract structured data and return valid JSON."},
            {"role": "user", "content": EXTRACTION_PROMPT.format(resume_text=resume_text)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    return ResumeExtraction(**data)


async def _extract_with_gemini(resume_text: str) -> ResumeExtraction:
    from google import genai

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    response = await client.aio.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=(
            "You are a resume parsing assistant. Extract structured data and return valid JSON.\n\n"
            + EXTRACTION_PROMPT.format(resume_text=resume_text)
        ),
        config=genai.types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
        ),
    )

    data = json.loads(response.text)
    return ResumeExtraction(**data)


async def extract_resume_data(resume_text: str) -> ResumeExtraction:
    if settings.LLM_PROVIDER == "gemini":
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")
        return await _extract_with_gemini(resume_text)

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")
    return await _extract_with_openai(resume_text)
