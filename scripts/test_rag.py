import asyncio
from dotenv import load_dotenv

from src.rag.vectorstore import initialize_vector_store, get_document_count, search
from src.rag.embeddings import create_embedding

load_dotenv()


async def main():
    print("Initializing vector store...")
    await initialize_vector_store()

    count = await get_document_count()
    print(f"Total documents: {count}")

    if count == 0:
        print("No documents indexed!")
        return

    # Test 1 — search without filter
    print("\n--- Test 1: Search 'SOP LOR' without channel filter ---")

    embedding1 = await create_embedding("SOP LOR")
    results1 = await search(embedding1, limit=5)

    print(f"Found {len(results1)} results:")

    for i, r in enumerate(results1):
        text_preview = r["text"][:100]
        score = r["score"]
        channel = r["metadata"]["channelName"]

        print(f"{i+1}. [{channel}] {text_preview}... (score: {score:.3f})")

    # Test 2 — channel filtered search
    print("\n--- Test 2: Search 'SOP LOR' in saurav-ltm ---")

    results2 = await search(
        embedding1,
        limit=5,
        channel_name="saurav-ltm"
    )

    print(f"Found {len(results2)} results:")

    for i, r in enumerate(results2):
        text_preview = r["text"][:100]
        score = r["score"]
        channel = r["metadata"]["channelName"]

        print(f"{i+1}. [{channel}] {text_preview}... (score: {score:.3f})")

    # Test 3 — generic search
    print("\n--- Test 3: Generic search for ANY content ---")

    embedding3 = await create_embedding("discussion conversation")
    results3 = await search(embedding3, limit=5)

    print(f"Found {len(results3)} results:")

    for i, r in enumerate(results3):
        text_preview = r["text"][:100]
        score = r["score"]
        channel = r["metadata"]["channelName"]

        print(f"{i+1}. [{channel}] {text_preview}... (score: {score:.3f})")

    # Test 4 — inspect channel distribution
    print("\n--- Test 4: Sample documents from vector store ---")

    embedding4 = await create_embedding("hello")
    all_results = await search(embedding4, limit=20)

    channels = {r["metadata"]["channelName"] for r in all_results}

    print("Channels in vector store:", ", ".join(channels))


if __name__ == "__main__":
    asyncio.run(main())