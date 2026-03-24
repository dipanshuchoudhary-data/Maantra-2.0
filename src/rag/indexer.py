"""
RAG Indexer

Background job that fetches Slack messages,
creates embeddings, and stores them in the vector database.

Runs periodically to keep the knowledge base updated.
"""

import asyncio
from typing import Dict, Any

from slack_sdk import WebClient

from src.config.settings import settings
from src.utils.logger import get_logger

from src.rag.embeddings import (
    create_embedding,
    create_embeddings,
    preprocess_text,
)

from src.rag.vectorstore import (
    add_documents,
    document_exists,
    initialize_vector_store,
    get_document_count,
    Document,
    DocumentMetadata,
)

from src.tools.slack_actions import list_channels, get_user_info


logger = get_logger("indexer")

# -----------------------------------------------------
# Slack Client
# -----------------------------------------------------

slack_client = WebClient(token=settings.slack.bot_token)

# -----------------------------------------------------
# Configuration
# -----------------------------------------------------

BATCH_SIZE = 50
MESSAGES_PER_CHANNEL = 200
INDEX_INTERVAL = 3600  # seconds

# channel_id → last indexed ts
last_indexed_timestamps: Dict[str, str] = {}

# runtime state
is_running = False
index_task = None


# -----------------------------------------------------
# Start / Stop Indexer
# -----------------------------------------------------

async def start_indexer():

    global is_running, index_task

    if is_running:
        logger.warning("Indexer already running")
        return

    is_running = True

    logger.info("Starting RAG indexer")

    async def loop():

        while is_running:

            try:
                await run_index()
            except Exception as e:
                logger.error(f"Indexing failed: {e}")

            await asyncio.sleep(INDEX_INTERVAL)

    index_task = asyncio.create_task(loop())


async def stop_indexer():

    global is_running

    is_running = False

    if index_task:
        index_task.cancel()

    logger.info("Indexer stopped")


# -----------------------------------------------------
# Main Index Run
# -----------------------------------------------------

async def run_index():

    logger.info("Starting indexing run")

    await initialize_vector_store()

    total_indexed = 0
    total_errors = 0

    channels = await list_channels()

    member_channels = [c for c in channels if c.is_member]

    logger.info(f"Indexing {len(member_channels)} channels")

    for channel in member_channels:

        try:

            result = await index_channel(
                channel.id,
                channel.name,
            )

            total_indexed += result["indexed"]
            total_errors += result["errors"]

        except Exception as e:

            logger.error(f"Channel indexing failed: {e}")

            total_errors += 1

    doc_count = await get_document_count()

    logger.info(
        f"Index run complete | indexed={total_indexed} errors={total_errors} total_docs={doc_count}"
    )

    return {
        "indexed": total_indexed,
        "errors": total_errors,
    }


# -----------------------------------------------------
# Index Single Channel
# -----------------------------------------------------

async def index_channel(channel_id: str, channel_name: str):

    logger.debug(f"Indexing {channel_name}")

    indexed = 0
    errors = 0

    oldest = last_indexed_timestamps.get(channel_id)

    try:

        result = slack_client.conversations_history(
            channel=channel_id,
            limit=MESSAGES_PER_CHANNEL,
            oldest=oldest,
        )

        messages = result.get("messages", [])

        if not messages:

            logger.debug("No new messages")

            return {"indexed": 0, "errors": 0}

        documents_to_index = []

        for msg in messages:

            if msg.get("subtype"):
                continue

            if msg.get("bot_id"):
                continue

            text = msg.get("text")

            if not text:
                continue

            processed = preprocess_text(text)

            if len(processed) < 10:
                continue

            doc_id = f"{channel_id}:{msg['ts']}"

            if await document_exists(doc_id):
                continue

            documents_to_index.append((msg, processed))

        if not documents_to_index:

            if messages:
                last_indexed_timestamps[channel_id] = messages[0]["ts"]

            return {"indexed": 0, "errors": 0}

        # -------------------------------------------------
        # Batch embedding
        # -------------------------------------------------

        for i in range(0, len(documents_to_index), BATCH_SIZE):

            batch = documents_to_index[i:i + BATCH_SIZE]

            try:

                texts = [d[1] for d in batch]

                embeddings = await create_embeddings(texts)

                docs = []

                for j, (msg, processed) in enumerate(batch):

                    embedding = embeddings[j]

                    user_name = "unknown"

                    if msg.get("user"):

                        user = await get_user_info(msg["user"])

                        if user:
                            user_name = user.real_name or user.name

                    doc_id = f"{channel_id}:{msg['ts']}"

                    metadata = DocumentMetadata(
                        channelId=channel_id,
                        channelName=channel_name,
                        userId=msg.get("user", "unknown"),
                        userName=user_name,
                        timestamp=msg["ts"],
                        messageTs=msg["ts"],
                        threadTs=msg.get("thread_ts"),
                        isThread=bool(msg.get("thread_ts")),
                    )

                    docs.append(Document(
                        id=doc_id,
                        text=processed,
                        embedding=embedding,
                        metadata=metadata,
                    ))

                await add_documents(docs)

                indexed += len(docs)

            except Exception as e:

                logger.error(f"Batch indexing failed: {e}")

                errors += 1

        if messages:
            last_indexed_timestamps[channel_id] = messages[0]["ts"]

        logger.info(f"Indexed {indexed} messages from {channel_name}")

        return {"indexed": indexed, "errors": errors}

    except Exception as e:

        logger.error(f"Channel indexing error: {e}")

        return {"indexed": 0, "errors": 1}


# -----------------------------------------------------
# Manual Index Channel
# -----------------------------------------------------

async def index_channel_manually(channel_id: str, channel_name: str):

    await initialize_vector_store()

    return await index_channel(channel_id, channel_name)


# -----------------------------------------------------
# Index Single Message
# -----------------------------------------------------

async def index_single_message(message: Dict[str, Any], channel_id: str, channel_name: str):

    try:

        processed = preprocess_text(message["text"])

        if len(processed) < 10:
            return False

        doc_id = f"{channel_id}:{message['ts']}"

        if await document_exists(doc_id):
            return False

        embedding = await create_embedding(processed)

        user_name = "unknown"

        if message.get("user"):
            user = await get_user_info(message["user"])
            if user:
                user_name = user.real_name or user.name

        metadata = DocumentMetadata(
            channelId=channel_id,
            channelName=channel_name,
            userId=message.get("user", "unknown"),
            userName=user_name,
            timestamp=message["ts"],
            messageTs=message["ts"],
            threadTs=message.get("thread_ts"),
            isThread=bool(message.get("thread_ts")),
        )

        await add_documents([
            Document(
                id=doc_id,
                text=processed,
                embedding=embedding,
                metadata=metadata,
            )
        ])

        logger.debug(f"Indexed message {doc_id}")

        return True

    except Exception as e:

        logger.error(f"Failed to index message: {e}")

        return False


# -----------------------------------------------------
# Indexer Status
# -----------------------------------------------------

def get_indexer_status():

    return {
        "running": is_running,
        "channelsIndexed": len(last_indexed_timestamps),
        "timestamps": last_indexed_timestamps,
    }
