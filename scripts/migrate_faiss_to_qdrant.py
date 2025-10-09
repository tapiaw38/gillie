"""
Migration Script: FAISS to Qdrant

This script migrates existing vector stores from FAISS to Qdrant.
Run this script once after deploying Qdrant to migrate existing data.

Usage:
    python scripts/migrate_faiss_to_qdrant.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from src.core.platform.config.service import read_config
from src.adapters.vectorstore.qdrant_adapter import QdrantVectorStoreAdapter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_faiss_to_qdrant():
    """Migrate all FAISS vector stores to Qdrant"""

    try:
        logger.info("Starting FAISS to Qdrant migration...")

        # Initialize configuration
        config_service = read_config()

        # Initialize embeddings (must match what was used in FAISS)
        logger.info("Initializing embeddings model...")
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        # Initialize Qdrant adapter
        logger.info("Initializing Qdrant adapter...")
        qdrant_adapter = QdrantVectorStoreAdapter(
            config_service=config_service,
            embeddings=embeddings
        )

        # Check Qdrant health
        if not qdrant_adapter.health_check():
            logger.error("Qdrant is not healthy. Please ensure Qdrant is running.")
            return False

        logger.info("Qdrant connection successful!")

        # Find all FAISS files
        vector_store_path = Path("./vector_stores")
        if not vector_store_path.exists():
            logger.warning(f"Vector store path {vector_store_path} does not exist")
            return True

        faiss_files = list(vector_store_path.glob("*.faiss"))

        if not faiss_files:
            logger.info("No FAISS files found to migrate")
            return True

        logger.info(f"Found {len(faiss_files)} FAISS vector stores to migrate")

        migrated_count = 0
        failed_count = 0

        for faiss_file in faiss_files:
            try:
                collection_name = faiss_file.stem
                logger.info(f"\nMigrating: {collection_name}")

                # Load FAISS vectorstore
                logger.info(f"  Loading FAISS from {faiss_file}...")
                try:
                    faiss_vectorstore = FAISS.load_local(
                        str(faiss_file.parent),
                        embeddings,
                        index_name=faiss_file.stem
                    )
                except Exception as e:
                    logger.error(f"  Failed to load FAISS file: {e}")
                    failed_count += 1
                    continue

                # Get documents from FAISS
                logger.info("  Extracting documents from FAISS...")
                try:
                    # Get all document IDs
                    doc_ids = list(faiss_vectorstore.docstore._dict.keys())
                    documents = [faiss_vectorstore.docstore._dict[doc_id] for doc_id in doc_ids]

                    logger.info(f"  Found {len(documents)} documents")

                    if not documents:
                        logger.warning(f"  No documents found in {collection_name}")
                        continue

                except Exception as e:
                    logger.error(f"  Failed to extract documents: {e}")
                    failed_count += 1
                    continue

                # Create collection in Qdrant
                logger.info(f"  Creating Qdrant collection: {collection_name}")
                success = qdrant_adapter.create_collection(
                    collection_name=collection_name,
                    vector_size=384  # for all-MiniLM-L6-v2
                )

                if not success:
                    logger.error(f"  Failed to create collection {collection_name}")
                    failed_count += 1
                    continue

                # Add documents to Qdrant
                logger.info(f"  Adding {len(documents)} documents to Qdrant...")
                success = qdrant_adapter.add_documents(
                    collection_name=collection_name,
                    documents=documents
                )

                if success:
                    logger.info(f"  ✓ Successfully migrated {collection_name}")
                    migrated_count += 1

                    # Verify migration
                    info = qdrant_adapter.get_collection_info(collection_name)
                    if info:
                        logger.info(f"  Collection info: {info['points_count']} points")
                else:
                    logger.error(f"  Failed to add documents to Qdrant")
                    failed_count += 1

            except Exception as e:
                logger.error(f"  Error migrating {faiss_file}: {e}")
                failed_count += 1
                continue

        logger.info("\n" + "="*60)
        logger.info("Migration Summary:")
        logger.info(f"  Total FAISS files: {len(faiss_files)}")
        logger.info(f"  Successfully migrated: {migrated_count}")
        logger.info(f"  Failed: {failed_count}")
        logger.info("="*60)

        if failed_count == 0:
            logger.info("\n✓ All vector stores migrated successfully!")
            logger.info("\nNext steps:")
            logger.info("1. Verify the migration by checking Qdrant dashboard")
            logger.info("2. Test search functionality with the new Qdrant backend")
            logger.info("3. Once verified, you can optionally remove FAISS files")
            return True
        else:
            logger.warning(f"\n⚠ Migration completed with {failed_count} failures")
            logger.info("Please review the errors above and retry if needed")
            return False

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    result = asyncio.run(migrate_faiss_to_qdrant())
    sys.exit(0 if result else 1)
