"""
Embeddings Module

Converts text into embedding vectors for semantic search.

Used by the RAG system to:
- index Slack messages
- search Slack knowledge
"""

import asyncio
import re
import math
from typing import List

from openai import OpenAI

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger("embeddings")

# ---------------------------------------------------
# OpenAI Client
# ---------------------------------------------------

client = OpenAI(api_key=settings.ai.openai_api_key)

# ---------------------------------------------------
# Embedding Configuration
# ---------------------------------------------------

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

MAX_BATCH_SIZE = 100
RATE_LIMIT_DELAY = 0.1


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

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text,
        )

        embedding = response.data[0].embedding

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

    for i in range(0, len(valid_texts), MAX_BATCH_SIZE):

        batch = valid_texts[i:i + MAX_BATCH_SIZE]

        try:

            logger.info(
                f"Embedding batch {i // MAX_BATCH_SIZE + 1}"
            )

            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
            )

            for j, item in enumerate(response.data):

                original_index = index_map[i + j]

                results[original_index] = item.embedding

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

    return {
        "model": EMBEDDING_MODEL,
        "dimensions": EMBEDDING_DIMENSIONS,
        "max_batch_size": MAX_BATCH_SIZE,
    }