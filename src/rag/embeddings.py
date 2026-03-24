"""
Embeddings Module

Converts text into embedding vectors for semantic search.

Supports multiple embedding providers:
- OpenAI (text-embedding-3-small, text-embedding-ada-002)
- Cohere (embed-english-v3.0, embed-multilingual-v3.0)
- OpenRouter (via OpenAI-compatible API)

Used by the RAG system to:
- index Slack messages
- search Slack knowledge
"""

import asyncio
import re
import math
from abc import ABC, abstractmethod
from typing import List, Optional

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("embeddings")

# ---------------------------------------------------
# Embedding Configuration
# ---------------------------------------------------

EMBEDDING_PROVIDER = settings.rag.embedding_provider.lower()
EMBEDDING_MODEL = settings.rag.embedding_model
EMBEDDING_DIMENSIONS = settings.rag.embedding_dimensions

MAX_BATCH_SIZE = 96  # Cohere limit is 96, OpenAI is 2048
RATE_LIMIT_DELAY = 0.1


# ---------------------------------------------------
# Base Embedding Provider (Abstract)
# ---------------------------------------------------


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass

    @abstractmethod
    def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name for logging."""
        pass


# ---------------------------------------------------
# OpenAI Embedding Provider
# ---------------------------------------------------


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embeddings provider."""

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        from openai import OpenAI

        self.model = model
        self.base_url = base_url or "https://api.openai.com/v1"
        self.client = OpenAI(api_key=api_key, base_url=self.base_url)

        logger.info(f"Embedding provider initialized: openai (model={model})")

    @property
    def provider_name(self) -> str:
        return "openai"

    def embed_single(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    def embed(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]


# ---------------------------------------------------
# Cohere Embedding Provider
# ---------------------------------------------------


class CohereEmbeddingProvider(BaseEmbeddingProvider):
    """Cohere embeddings provider."""

    def __init__(self, api_key: str, model: str):
        import cohere

        self.model = model
        self.client = cohere.ClientV2(api_key=api_key)

        logger.info(f"Embedding provider initialized: cohere (model={model})")

    @property
    def provider_name(self) -> str:
        return "cohere"

    def embed_single(self, text: str) -> List[float]:
        response = self.client.embed(
            texts=[text],
            model=self.model,
            input_type="search_query",
            embedding_types=["float"],
        )
        return response.embeddings.float_[0]

    def embed(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embed(
            texts=texts,
            model=self.model,
            input_type="search_document",
            embedding_types=["float"],
        )
        return response.embeddings.float_


# ---------------------------------------------------
# Provider Factory
# ---------------------------------------------------


def _build_embedding_provider() -> BaseEmbeddingProvider:
    """Create an embeddings provider based on configuration."""

    provider = EMBEDDING_PROVIDER
    model = EMBEDDING_MODEL

    if provider == "cohere":
        api_key = settings.ai.cohere_api_key

        if not api_key:
            raise RuntimeError(
                "RAG embedding provider is cohere but COHERE_API_KEY is missing"
            )

        # Default to embed-english-v3.0 for Cohere if using OpenAI default model
        if model == "text-embedding-3-small":
            model = "embed-english-v3.0"

        return CohereEmbeddingProvider(api_key=api_key, model=model)

    if provider == "openrouter":
        api_key = settings.ai.openrouter_api_key

        if not api_key:
            raise RuntimeError(
                "RAG embedding provider is openrouter but OPENROUTER_API_KEY is missing"
            )

        return OpenAIEmbeddingProvider(
            api_key=api_key,
            model=model,
            base_url="https://openrouter.ai/api/v1",
        )

    # Default to OpenAI
    api_key = settings.ai.openai_api_key

    if not api_key:
        raise RuntimeError(
            "RAG embedding provider is openai but OPENAI_API_KEY is missing"
        )

    return OpenAIEmbeddingProvider(api_key=api_key, model=model)


# ---------------------------------------------------
# Embeddings Client Instance
# ---------------------------------------------------

_embedding_provider: Optional[BaseEmbeddingProvider] = None
EMBEDDING_BASE_URL: str = ""


def _get_provider() -> BaseEmbeddingProvider:
    """Get or create the embedding provider singleton."""
    global _embedding_provider

    if _embedding_provider is None:
        _embedding_provider = _build_embedding_provider()

    return _embedding_provider


def initialize_embedding_provider() -> bool:
    """Initialize the embedding provider. Returns True if successful."""
    global _embedding_provider, EMBEDDING_BASE_URL

    try:
        _embedding_provider = _build_embedding_provider()

        if isinstance(_embedding_provider, OpenAIEmbeddingProvider):
            EMBEDDING_BASE_URL = _embedding_provider.base_url
        else:
            EMBEDDING_BASE_URL = f"https://api.cohere.ai"

        logger.info("RAG enabled")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize embedding provider: {e}")
        _embedding_provider = None
        return False


def is_embedding_provider_ready() -> bool:
    """Check if the embedding provider is initialized and ready."""
    return _embedding_provider is not None


# ---------------------------------------------------
# Single Embedding
# ---------------------------------------------------


async def create_embedding(text: str) -> List[float]:
    """
    Create embedding for a single text.
    """

    if not text or len(text.strip()) == 0:
        logger.warning("Attempted to embed empty text")
        return [0.0] * EMBEDDING_DIMENSIONS

    try:
        provider = _get_provider()
        embedding = provider.embed_single(text)
        return embedding

    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise


# ---------------------------------------------------
# Batch Embeddings
# ---------------------------------------------------


async def create_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Batch embedding generation.
    """

    if len(texts) == 0:
        return []

    valid_texts = []
    index_map = []

    for i, t in enumerate(texts):
        if t and t.strip():
            valid_texts.append(t)
            index_map.append(i)

    results = [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]

    provider = _get_provider()

    for i in range(0, len(valid_texts), MAX_BATCH_SIZE):

        batch = valid_texts[i : i + MAX_BATCH_SIZE]

        try:

            logger.info(f"Embedding batch {i // MAX_BATCH_SIZE + 1}")

            embeddings = provider.embed(batch)

            for j, emb in enumerate(embeddings):
                original_index = index_map[i + j]
                results[original_index] = emb

            if i + MAX_BATCH_SIZE < len(valid_texts):
                await asyncio.sleep(RATE_LIMIT_DELAY)

        except Exception as e:

            logger.error(f"Batch embedding failed: {e}")
            raise

    return results


# ---------------------------------------------------
# Cosine Similarity
# ---------------------------------------------------


def cosine_similarity(a: List[float], b: List[float]) -> float:

    if len(a) != len(b):
        raise ValueError("Vectors must have same length")

    dot = sum(x * y for x, y in zip(a, b))

    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


# ---------------------------------------------------
# Text Preprocessing
# ---------------------------------------------------


def preprocess_text(text: str) -> str:
    """
    Clean Slack text before embedding.
    """

    processed = text

    # remove user mentions
    processed = re.sub(r"<@[A-Z0-9]+>", "@user", processed)

    # remove channel mentions
    processed = re.sub(r"<#[A-Z0-9]+\|([^>]+)>", r"#\1", processed)
    processed = re.sub(r"<#[A-Z0-9]+>", "#channel", processed)

    # remove URLs
    processed = re.sub(r"<https?://[^>]+>", "[link]", processed)
    processed = re.sub(r"https?://\S+", "[link]", processed)

    # remove emoji codes
    processed = re.sub(r":[a-z0-9_+-]+:", "", processed)

    # normalize whitespace
    processed = re.sub(r"\s+", " ", processed).strip()

    # remove extremely short messages
    if len(processed) < 10:
        return ""

    return processed


# ---------------------------------------------------
# Embedding Config
# ---------------------------------------------------


def get_embedding_config():

    provider = _embedding_provider

    return {
        "provider": EMBEDDING_PROVIDER,
        "base_url": EMBEDDING_BASE_URL,
        "model": EMBEDDING_MODEL,
        "dimensions": EMBEDDING_DIMENSIONS,
        "max_batch_size": MAX_BATCH_SIZE,
        "initialized": provider is not None,
    }
