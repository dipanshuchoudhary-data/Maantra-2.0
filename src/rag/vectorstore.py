"""
Vector Store Module

Lightweight vector database for storing Slack message embeddings.

Features
- in-memory store
- JSON persistence
- cosine similarity search
- metadata filtering
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

from src.config.settings import config
from src.utils.logger import get_logger
from src.rag.embeddings import cosine_similarity

logger = get_logger("vectorstore")


# =========================================================
# Data Models
# =========================================================

@dataclass
class DocumentMetadata:
    channelId: str
    channelName: str
    userId: str
    userName: str
    timestamp: str
    messageTs: str
    threadTs: Optional[str] = None
    isThread: Optional[bool] = False
    indexedAt: Optional[str] = None


@dataclass
class Document:
    id: str
    text: str
    embedding: List[float]
    metadata: DocumentMetadata


@dataclass
class SearchResult:
    id: str
    text: str
    score: float
    metadata: DocumentMetadata


# =========================================================
# Simple Vector Store
# =========================================================

class SimpleVectorStore:

    def __init__(self, persist_path: Path):

        self.persist_path = persist_path
        self.documents: Dict[str, Document] = {}
        self.initialized = False

    # -----------------------------------------------------

    async def initialize(self):

        if self.initialized:
            return

        self.persist_path.parent.mkdir(parents=True, exist_ok=True)

        if self.persist_path.exists():

            try:

                data = json.loads(self.persist_path.read_text())

                for doc_id, doc in data.items():
                    self.documents[doc_id] = Document(
                        id=doc["id"],
                        text=doc["text"],
                        embedding=doc["embedding"],
                        metadata=DocumentMetadata(**doc["metadata"]),
                    )

                logger.info(f"Loaded {len(self.documents)} documents")

            except Exception as e:
                logger.warning(f"Failed loading vector store: {e}")

        self.initialized = True

    # -----------------------------------------------------

    def _persist(self):

        try:

            data = {
                doc_id: {
                    "id": doc.id,
                    "text": doc.text,
                    "embedding": doc.embedding,
                    "metadata": asdict(doc.metadata),
                }
                for doc_id, doc in self.documents.items()
            }

            self.persist_path.write_text(json.dumps(data))

        except Exception as e:
            logger.error(f"Vector store persist failed: {e}")

    # -----------------------------------------------------

    async def add(self, documents: List[Document]):

        for doc in documents:
            self.documents[doc.id] = doc

        self._persist()

    # -----------------------------------------------------

    async def update(self, documents: List[Document]):

        for doc in documents:
            if doc.id in self.documents:
                self.documents[doc.id] = doc

        self._persist()

    # -----------------------------------------------------

    async def delete(self, ids: List[str]):

        for doc_id in ids:
            self.documents.pop(doc_id, None)

        self._persist()

    # -----------------------------------------------------

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        channel_id: Optional[str] = None,
        channel_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[SearchResult]:

        results: List[SearchResult] = []

        for doc in self.documents.values():

            if channel_id and doc.metadata.channelId != channel_id:
                continue

            if channel_name and doc.metadata.channelName.lower() != channel_name.lower():
                continue

            if user_id and doc.metadata.userId != user_id:
                continue

            score = cosine_similarity(query_embedding, doc.embedding)

            results.append(
                SearchResult(
                    id=doc.id,
                    text=doc.text,
                    score=score,
                    metadata=doc.metadata,
                )
            )

        results.sort(key=lambda x: x.score, reverse=True)

        return results[:limit]

    # -----------------------------------------------------

    async def get(self, ids: List[str]) -> List[Document]:

        return [self.documents[i] for i in ids if i in self.documents]

    # -----------------------------------------------------

    async def exists(self, doc_id: str) -> bool:

        return doc_id in self.documents

    # -----------------------------------------------------

    async def count(self) -> int:

        return len(self.documents)

    # -----------------------------------------------------

    async def clear(self):

        self.documents.clear()

        self._persist()


# =========================================================
# Global Store Instance
# =========================================================

store: Optional[SimpleVectorStore] = None


# =========================================================
# Public API
# =========================================================

async def initialize_vector_store():

    global store

    if store:
        return

    logger.info("Initializing vector store")

    persist_path = Path(config.rag.vector_db_path) / "vectors.json"

    store = SimpleVectorStore(persist_path)

    await store.initialize()

    count = await store.count()

    logger.info(f"Vector store ready with {count} documents")


# ---------------------------------------------------------

async def add_documents(documents: List[Document]):

    if not store:
        await initialize_vector_store()

    if not documents:
        return

    await store.add(documents)

    logger.info(f"Added {len(documents)} documents")


# ---------------------------------------------------------

async def update_documents(documents: List[Document]):

    if not store:
        await initialize_vector_store()

    if documents:
        await store.update(documents)


# ---------------------------------------------------------

async def delete_documents(ids: List[str]):

    if not store:
        await initialize_vector_store()

    if ids:
        await store.delete(ids)


# ---------------------------------------------------------

async def search(
    query_embedding: List[float],
    limit: int = 10,
    channel_id: Optional[str] = None,
    channel_name: Optional[str] = None,
    user_id: Optional[str] = None,
):

    if not store:
        await initialize_vector_store()

    results = await store.search(
        query_embedding,
        limit,
        channel_id,
        channel_name,
        user_id,
    )

    logger.debug(f"Search returned {len(results)} results")

    return results


# ---------------------------------------------------------

async def get_document_count():

    if not store:
        await initialize_vector_store()

    return await store.count()


# ---------------------------------------------------------

async def document_exists(doc_id: str):

    if not store:
        await initialize_vector_store()

    return await store.exists(doc_id)


# ---------------------------------------------------------

async def get_documents(ids: List[str]):

    if not store:
        await initialize_vector_store()

    docs = await store.get(ids)

    return [
        SearchResult(
            id=d.id,
            text=d.text,
            score=1.0,
            metadata=d.metadata,
        )
        for d in docs
    ]


# ---------------------------------------------------------

async def clear_all():

    if not store:
        await initialize_vector_store()

    await store.clear()

    logger.warning("Vector store cleared")