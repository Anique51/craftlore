from functools import lru_cache

from langchain_groq import ChatGroq

from app.config import settings


@lru_cache(maxsize=1)
def get_llm():
    if settings.llm_provider != "groq":
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0,
        max_tokens=1000,
    )
