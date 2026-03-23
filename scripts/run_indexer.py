import sys
import asyncio
from dotenv import load_dotenv

from src.rag.vectorstore import initialize_vector_store
from src.rag.indexer import run_index
from src.rag.vectorstore import get_document_count
from src.utils.logger import get_logger

load_dotenv()

logger = get_logger("manual-indexer")


async def main():
    logger.info("Starting manual indexing...")

    try:
        # Initialize vector store
        await initialize_vector_store()

        before_count = await get_document_count()
        logger.info(f"Documents before indexing: {before_count}")

        # Run indexer
        result = await run_index()

        # Get final count
        after_count = await get_document_count()

        logger.info("=" * 50)
        logger.info("Indexing Complete!")
        logger.info(f"  • Documents indexed: {result['indexed']}")
        logger.info(f"  • Errors: {result['errors']}")
        logger.info(f"  • Total documents: {after_count}")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Indexing failed: {str(e)}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())