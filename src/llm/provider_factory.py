import os

from src.llm.openai_provider import OpenAIProvider
from src.llm.gemini_provider import GeminiProvider
from src.llm.grok_provider import GrokProvider
from src.llm.openrouter_provider import OpenRouterProvider


def get_llm_provider():

    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "openai":
        return OpenAIProvider()

    if provider == "gemini":
        return GeminiProvider()

    if provider == "grok":
        return GrokProvider()

    if provider == "openrouter":
        return OpenRouterProvider()

    raise ValueError(f"Unsupported LLM provider: {provider}")