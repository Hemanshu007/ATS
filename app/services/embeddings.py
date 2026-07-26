import logging

from app.core.config import settings

logger = logging.getLogger("ats.embeddings")


async def _generate_with_openai(text: str) -> list[float]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=text,
    )

    return response.data[0].embedding


async def _generate_with_gemini(text: str) -> list[float]:
    from google import genai

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    result = await client.aio.models.embed_content(
        model=settings.GEMINI_EMBEDDING_MODEL,
        contents=text,
    )

    return result.embeddings[0].values


async def generate_embedding(text: str) -> list[float]:
    if settings.LLM_PROVIDER == "gemini":
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")
        return await _generate_with_gemini(text)

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")
    return await _generate_with_openai(text)
