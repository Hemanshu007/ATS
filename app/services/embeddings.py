import logging

from app.core.config import settings

logger = logging.getLogger("ats.embeddings")


async def generate_embedding(text: str) -> list[float]:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=text,
    )

    return response.data[0].embedding
