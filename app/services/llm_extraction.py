import io
import logging
from typing import Optional

from pydantic import BaseModel
from pypdf import PdfReader

from app.core.config import settings

logger = logging.getLogger("ats.llm")


class Education(BaseModel):
    degree: str
    institution: str


class WorkHistory(BaseModel):
    role: str
    company: str
    duration: str


class ResumeExtraction(BaseModel):
    name: str
    email: str
    phone: str
    skills: list[str]
    years_of_experience: Optional[float] = None
    education: list[Education]
    work_history: list[WorkHistory]


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


async def extract_resume_data(resume_text: str) -> ResumeExtraction:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")

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

    import json
    content = response.choices[0].message.content
    data = json.loads(content)
    return ResumeExtraction(**data)
