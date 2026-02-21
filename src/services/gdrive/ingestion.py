import os
import tempfile
import logging
from typing import Dict, Any, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from src.core.platform.config.service import ConfigurationService
from src.adapters.vectorstore.qdrant_adapter import QdrantVectorStoreAdapter

logger = logging.getLogger(__name__)

# Maps processed MIME/ext to the correct LangChain loader
_PDF_MIMES   = {"application/pdf", "application/vnd.google-apps.document",
                "application/vnd.google-apps.presentation",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
_EXCEL_MIMES = {"application/vnd.google-apps.spreadsheet",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel"}
_WORD_MIMES  = {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
_TEXT_MIMES  = {"text/plain", "text/csv"}


class DriveIngestionService:
    """
    Orchestrates the full pipeline for a Drive file:
      bytes → tempfile → LangChain loader → text chunks → Qdrant
    """

    COLLECTION_PREFIX = "drive"

    def __init__(
        self,
        config_service: ConfigurationService,
        qdrant_adapter: Optional[QdrantVectorStoreAdapter] = None,
    ):
        self.config_service = config_service
        self.qdrant_adapter = qdrant_adapter

        lc = config_service.langchain_config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=lc.chunk_size,
            chunk_overlap=lc.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

    @staticmethod
    def collection_name(user_id: str) -> str:
        return f"{DriveIngestionService.COLLECTION_PREFIX}_{user_id}"

    # ── Public API ─────────────────────────────────────────────────────────────

    def ingest(
        self,
        file_bytes: bytes,
        original_mime: str,
        file_extension: str,
        metadata: Dict[str, Any],
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Process file bytes and store chunks in Qdrant.

        Args:
            file_bytes:      Raw file content (exported if Google Workspace)
            original_mime:   Original Drive MIME type (used for loader selection)
            file_extension:  Extension for the tempfile (.pdf, .xlsx, etc.)
            metadata:        Metadata to attach to every chunk
            user_id:         Owner — determines the Qdrant collection

        Returns:
            {"status": "indexed", "chunks": N, "collection": "drive_xxx"}
        """
        if not self.qdrant_adapter:
            raise RuntimeError("Qdrant adapter not available — cannot ingest Drive files")

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=file_extension, delete=False
            ) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            docs = self._load_documents(tmp_path, original_mime)
            if not docs:
                logger.warning(f"No text extracted from {metadata.get('file_name')}")
                return {"status": "empty", "chunks": 0}

            chunks = self.text_splitter.split_documents(docs)

            # Attach Drive metadata to every chunk
            base_meta = {
                "user_id": user_id,
                "source": "google_drive",
                **metadata,
            }
            for chunk in chunks:
                chunk.metadata.update(base_meta)

            collection = self.collection_name(user_id)
            self.qdrant_adapter.add_documents(collection, chunks)

            logger.info(
                f"Indexed {len(chunks)} chunks from '{metadata.get('file_name')}' "
                f"into collection '{collection}'"
            )
            return {"status": "indexed", "chunks": len(chunks), "collection": collection}

        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def delete_file_vectors(self, file_id: str, user_id: str) -> bool:
        """Remove all vectors for a given Drive file_id from Qdrant."""
        if not self.qdrant_adapter:
            return False
        collection = self.collection_name(user_id)
        return self.qdrant_adapter.delete_by_metadata(
            collection, {"file_id": file_id}
        )

    def get_file_index_meta(self, user_id: str, file_id: str) -> Optional[dict]:
        """Check Qdrant for existing indexed chunks of this file.

        Returns the payload of the first matching chunk (contains md5_checksum,
        chunks_count, index_status, etc.) or None if not indexed.
        """
        if not self.qdrant_adapter:
            return None
        collection = self.collection_name(user_id)
        try:
            qdrant_filter = self.qdrant_adapter._build_filter({"file_id": file_id})
            results, _ = self.qdrant_adapter.client.scroll(
                collection_name=collection,
                scroll_filter=qdrant_filter,
                limit=1,
                with_payload=True,
            )
            if results:
                return results[0].payload
            return None
        except Exception:
            return None

    def get_index_status(self, user_id: str) -> dict:
        """Get a summary of what is indexed in Qdrant for this user."""
        collection = self.collection_name(user_id)
        if not self.qdrant_adapter:
            return {
                "user_id": user_id,
                "collection": collection,
                "total_chunks": 0,
            }
        info = self.qdrant_adapter.get_collection_info(collection)
        return {
            "user_id": user_id,
            "collection": collection,
            "total_chunks": info.get("points_count", 0) if info else 0,
        }

    def search(
        self,
        query: str,
        user_id: str,
        k: int = 5,
        file_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over indexed Drive documents.

        Args:
            query:   Natural language query
            user_id: Limits search to this user's collection
            k:       Max results to return
            file_id: Optional filter to search within a single file

        Returns:
            List of {"content": str, "score": float, "metadata": {...}}
        """
        if not self.qdrant_adapter:
            return []

        collection = self.collection_name(user_id)
        filter_dict = {"user_id": user_id}
        if file_id:
            filter_dict["file_id"] = file_id

        results = self.qdrant_adapter.search_similar(
            collection_name=collection,
            query=query,
            k=k,
            filter_dict=filter_dict,
        )

        return [
            {
                "content": doc.page_content,
                "score": round(float(score), 4),
                "metadata": doc.metadata,
            }
            for doc, score in results
        ]

    # ── Document loaders ───────────────────────────────────────────────────────

    def _load_documents(self, file_path: str, original_mime: str) -> List[Document]:
        try:
            if original_mime in _PDF_MIMES or file_path.endswith(".pdf"):
                return self._load_pdf(file_path)
            if original_mime in _EXCEL_MIMES or file_path.endswith((".xlsx", ".xls")):
                return self._load_excel(file_path)
            if original_mime in _WORD_MIMES or file_path.endswith(".docx"):
                return self._load_unstructured(file_path)
            if original_mime in _TEXT_MIMES or file_path.endswith((".txt", ".csv")):
                return self._load_text(file_path)
            # Fallback: unstructured handles most formats
            return self._load_unstructured(file_path)
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {e}", exc_info=True)
            return []

    @staticmethod
    def _load_pdf(file_path: str) -> List[Document]:
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(file_path)
        return loader.load()

    @staticmethod
    def _load_excel(file_path: str) -> List[Document]:
        try:
            from langchain_community.document_loaders import UnstructuredExcelLoader
            loader = UnstructuredExcelLoader(file_path, mode="elements")
            return loader.load()
        except Exception:
            # Fallback: read with pandas, convert to text
            import pandas as pd
            docs = []
            xl = pd.ExcelFile(file_path)
            for sheet in xl.sheet_names:
                df = xl.parse(sheet)
                text = f"Sheet: {sheet}\n{df.to_string(index=False)}"
                docs.append(Document(page_content=text, metadata={"sheet": sheet}))
            return docs

    @staticmethod
    def _load_unstructured(file_path: str) -> List[Document]:
        from langchain_community.document_loaders import UnstructuredFileLoader
        loader = UnstructuredFileLoader(file_path)
        return loader.load()

    @staticmethod
    def _load_text(file_path: str) -> List[Document]:
        with open(file_path, "r", errors="ignore") as f:
            content = f.read()
        return [Document(page_content=content)]
