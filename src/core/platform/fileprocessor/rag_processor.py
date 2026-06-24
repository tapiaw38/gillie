import asyncio
import logging
from typing import Dict, Any, List, Optional
import hashlib
import os
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from src.core.platform.config.service import ConfigurationService

logger = logging.getLogger(__name__)


class RAGDocumentProcessor:
    def __init__(self, config_service: ConfigurationService, use_qdrant: bool = True):
        self.config_service = config_service
        self.openai_config = config_service.openai_config
        self.use_qdrant = use_qdrant

        self.embeddings = None
        self._embeddings_initialized = False
        self.qdrant_adapter = None

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

        self.vector_store_path = Path("./vector_stores")
        self.vector_store_path.mkdir(exist_ok=True)

        self.vectorstore_cache = {}
        self.embeddings_cache = {}

    def _ensure_embeddings(self):
        """Lazy-load embeddings and Qdrant adapter on first use."""
        if self._embeddings_initialized:
            return
        self._embeddings_initialized = True
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            logger.info("Using HuggingFace embeddings (local)")
        except Exception as e:
            logger.warning(f"Failed to load HuggingFace embeddings: {e}")
            self.embeddings = None
            logger.info("Falling back to simple TF-IDF embeddings")

        if self.use_qdrant and self.embeddings:
            try:
                from src.adapters.vectorstore.qdrant_adapter import QdrantVectorStoreAdapter
                self.qdrant_adapter = QdrantVectorStoreAdapter(
                    config_service=self.config_service,
                    embeddings=self.embeddings
                )
                if self.qdrant_adapter.health_check():
                    logger.info("Qdrant adapter initialized successfully")
                else:
                    logger.warning("Qdrant health check failed, falling back to FAISS")
                    self.use_qdrant = False
            except Exception as e:
                logger.error(f"Failed to initialize Qdrant adapter: {e}")
                logger.info("Falling back to FAISS storage")
                self.use_qdrant = False
        else:
            self.use_qdrant = False

    def _get_document_id(self, file_url: str) -> str:
        return hashlib.md5(file_url.encode()).hexdigest()

    async def process_and_store_document(
        self, file_url: str, file_type: str, profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        self._ensure_embeddings()
        try:
            document_id = self._get_document_id(file_url)

            if profile_id:
                collection_name = f"profile_{profile_id}"
            else:
                collection_name = f"doc_{document_id}"

            logger.info(f"Processing document for RAG: {file_url}")

            if self.use_qdrant:
                if self.qdrant_adapter.document_exists(collection_name, document_id):
                    logger.info(f"Document already processed in Qdrant: {document_id}")
                    return {
                        "document_id": document_id,
                        "status": "already_processed",
                        "collection_name": collection_name,
                        "storage": "qdrant"
                    }
            else:
                if document_id in self.vectorstore_cache:
                    logger.info(f"Document already processed in cache: {document_id}")
                    vectorstore = self.vectorstore_cache[document_id]
                    vector_count = 0

                    if isinstance(vectorstore, dict) and "chunks" in vectorstore:
                        vector_count = len(vectorstore["chunks"])
                    elif hasattr(vectorstore, "docstore"):
                        vector_count = len(vectorstore.docstore._dict)

                    return {
                        "document_id": document_id,
                        "status": "already_processed",
                        "collection_name": collection_name,
                        "vector_count": vector_count,
                        "storage": "faiss"
                    }

            if file_type.lower() == "pdf":
                documents = await self._process_pdf(file_url)
            elif file_type.lower() in ["xlsx", "xls"]:
                documents = await self._process_xlsx(file_url)
            elif file_type.lower() in ["docx", "doc"]:
                documents = await self._process_docx(file_url)
            else:
                return {"error": f"Unsupported file type: {file_type}"}

            if not documents:
                return {"error": "No se pudo procesar el documento"}

            chunks = self.text_splitter.split_documents(documents)

            for chunk in chunks:
                chunk.metadata.update({
                    "document_id": document_id,
                    "file_url": file_url,
                    "file_type": file_type,
                })
                if profile_id:
                    chunk.metadata["profile_id"] = profile_id

            if self.use_qdrant:
                success = self.qdrant_adapter.add_documents(
                    collection_name=collection_name,
                    documents=chunks
                )

                if not success:
                    logger.error("Failed to store in Qdrant, falling back to FAISS")
                    self.use_qdrant = False
                else:
                    result = {
                        "document_id": document_id,
                        "status": "processed",
                        "collection_name": collection_name,
                        "vector_count": len(chunks),
                        "file_url": file_url,
                        "file_type": file_type,
                        "total_characters": sum(len(doc.page_content) for doc in chunks),
                        "processing_method": "rag_qdrant",
                        "storage": "qdrant"
                    }

                    logger.info(
                        f"Document processed successfully in Qdrant: {len(chunks)} vectors created"
                    )
                    return result

            if self.embeddings:
                from langchain_community.vectorstores import FAISS
                vectorstore = FAISS.from_documents(
                    documents=chunks, embedding=self.embeddings
                )

                vectorstore_path = self.vector_store_path / f"{collection_name}.faiss"
                vectorstore.save_local(str(vectorstore_path))
            else:
                vectorstore = self._create_simple_vectorstore(chunks)

                vectorstore_path = self.vector_store_path / f"{collection_name}.simple"
                self._save_simple_vectorstore(vectorstore, vectorstore_path)

            self.vectorstore_cache[document_id] = vectorstore

            result = {
                "document_id": document_id,
                "status": "processed",
                "collection_name": collection_name,
                "vector_count": len(chunks),
                "file_url": file_url,
                "file_type": file_type,
                "total_characters": sum(len(doc.page_content) for doc in chunks),
                "processing_method": "rag_faiss",
                "storage": "faiss"
            }

            logger.info(
                f"Document processed successfully in FAISS: {len(chunks)} vectors created"
            )
            return result

        except Exception as e:
            logger.error(f"Error processing document for RAG: {e}")
            return {"error": f"Error processing document: {str(e)}"}

    def _create_simple_vectorstore(self, chunks: List[Document]) -> Dict[str, Any]:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            texts = [chunk.page_content for chunk in chunks]

            vectorizer = TfidfVectorizer(
                max_features=1000, stop_words="english", ngram_range=(1, 2)
            )

            tfidf_matrix = vectorizer.fit_transform(texts)

            return {
                "type": "simple_tfidf",
                "vectorizer": vectorizer,
                "matrix": tfidf_matrix,
                "chunks": chunks,
                "texts": texts,
            }

        except Exception as e:
            logger.error(f"Error creating simple vectorstore: {e}")
            return {
                "type": "simple_chunks",
                "chunks": chunks,
                "texts": [chunk.page_content for chunk in chunks],
            }

    def _save_simple_vectorstore(self, vectorstore: Dict[str, Any], path: Path):
        try:
            import pickle

            with open(path, "wb") as f:
                pickle.dump(vectorstore, f)

            logger.info(f"Simple vectorstore saved to {path}")

        except Exception as e:
            logger.error(f"Error saving simple vectorstore: {e}")

    def _load_simple_vectorstore(self, path: Path) -> Dict[str, Any]:
        try:
            import pickle

            with open(path, "rb") as f:
                vectorstore = pickle.load(f)

            logger.info(f"Simple vectorstore loaded from {path}")
            return vectorstore

        except Exception as e:
            logger.error(f"Error loading simple vectorstore: {e}")
            return None

    def _search_simple_tfidf(
        self, vectorstore: Dict[str, Any], query: str, max_results: int
    ) -> List[tuple]:
        try:
            from sklearn.metrics.pairwise import cosine_similarity

            query_vector = vectorstore["vectorizer"].transform([query])

            similarities = cosine_similarity(
                query_vector, vectorstore["matrix"]
            ).flatten()

            indices = similarities.argsort()[-max_results:][::-1]

            results = []
            for idx in indices:
                if similarities[idx] > 0.1:
                    doc = vectorstore["chunks"][idx]
                    score = 1.0 - similarities[idx]
                    results.append((doc, score))

            return results

        except Exception as e:
            logger.error(f"Error in TF-IDF search: {e}")
            return []

    def _search_simple_chunks(
        self, vectorstore: Dict[str, Any], query: str, max_results: int
    ) -> List[tuple]:
        try:
            query_words = set(query.lower().split())
            results = []

            for i, text in enumerate(vectorstore["texts"]):
                text_words = set(text.lower().split())

                overlap = len(query_words.intersection(text_words))
                if overlap > 0:
                    score = 1.0 / (1.0 + overlap)
                    doc = vectorstore["chunks"][i]
                    results.append((doc, score))

            results.sort(key=lambda x: x[1])
            return results[:max_results]

        except Exception as e:
            logger.error(f"Error in simple chunks search: {e}")
            return []

    def _check_pdf_has_text(self, pdf_data: bytes) -> bool:
        """Check if PDF has extractable text (not just images)."""
        try:
            import fitz
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            total_text = ""
            for page in doc:
                total_text += page.get_text()
            doc.close()
            min_chars = 50 * doc.page_count
            return len(total_text.strip()) >= min_chars
        except Exception as e:
            logger.warning(f"Error checking PDF text: {e}")
            return True

    async def _extract_text_with_vision(self, pdf_data: bytes, pdf_url: str) -> List[Document]:
        """Extract text from image-based PDF using vision API."""
        try:
            from pdf2image import convert_from_bytes
            from src.core.platform.fileprocessor.pdf_processor import FileImageProcessor

            processor = FileImageProcessor(self.config_service)
            images = convert_from_bytes(pdf_data, dpi=150)
            documents = []

            for page_num, image in enumerate(images, 1):
                try:
                    import io
                    import base64
                    buffer = io.BytesIO()
                    image.save(buffer, format="PNG")
                    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

                    text = await processor.describe_image(
                        image_base64,
                        prompt="Extract ALL text from this document page. Return only the text content, preserving structure. If handwritten, transcribe carefully."
                    )

                    if text and len(text.strip()) > 20:
                        documents.append(Document(
                            page_content=text,
                            metadata={
                                "source": pdf_url,
                                "type": "pdf",
                                "page": page_num,
                                "extraction_method": "vision"
                            }
                        ))
                        logger.info(f"Vision extracted {len(text)} chars from page {page_num}")
                except Exception as e:
                    logger.warning(f"Vision extraction failed for page {page_num}: {e}")
                    continue

            return documents
        except Exception as e:
            logger.error(f"Vision PDF extraction failed: {e}")
            return []

    async def _process_pdf(self, pdf_url: str) -> List[Document]:
        import aiohttp
        import tempfile

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url) as response:
                    response.raise_for_status()
                    pdf_data = await response.read()

            has_text = self._check_pdf_has_text(pdf_data)

            if has_text:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                    temp_path = temp_file.name
                    temp_file.write(pdf_data)

                try:
                    from langchain_community.document_loaders import UnstructuredFileLoader
                    loader = UnstructuredFileLoader(temp_path)
                    documents = loader.load()

                    for doc in documents:
                        doc.metadata.update({
                            "source": pdf_url,
                            "type": "pdf",
                            "extraction_method": "text"
                        })

                    logger.info(f"Text PDF: extracted {len(documents)} documents")
                    return documents
                finally:
                    os.unlink(temp_path)
            else:
                logger.info("Image-based PDF detected, using vision extraction")
                documents = await self._extract_text_with_vision(pdf_data, pdf_url)

                if not documents:
                    logger.info("Vision failed, falling back to OCR")
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                        temp_path = temp_file.name
                        temp_file.write(pdf_data)
                    try:
                        from langchain_community.document_loaders import UnstructuredFileLoader
                        loader = UnstructuredFileLoader(temp_path)
                        documents = loader.load()
                        for doc in documents:
                            doc.metadata.update({
                                "source": pdf_url,
                                "type": "pdf",
                                "extraction_method": "ocr_fallback"
                            })
                    finally:
                        os.unlink(temp_path)

                return documents

        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return []

    async def _process_xlsx(self, xlsx_url: str) -> List[Document]:
        import aiohttp
        import tempfile
        import pandas as pd

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(xlsx_url) as response:
                    response.raise_for_status()
                    xlsx_data = await response.read()

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(xlsx_data)

            try:
                excel_file = pd.ExcelFile(temp_path)
                documents = []

                for sheet_name in excel_file.sheet_names:
                    try:
                        df = pd.read_excel(temp_path, sheet_name=sheet_name)

                        if not df.empty:
                            for row_idx, row in df.iterrows():
                                row_content = (
                                    f"HOJA: {sheet_name} - FILA: {row_idx + 1}\n"
                                )

                                for col_idx, value in enumerate(row):
                                    if pd.notna(value):
                                        column_name = df.columns[col_idx]
                                        row_content += f"{column_name}: {str(value)}\n"

                                if row_content.strip() and len(row_content) > 10:
                                    doc = Document(
                                        page_content=row_content.strip(),
                                        metadata={
                                            "source": xlsx_url,
                                            "type": "xlsx",
                                            "sheet": sheet_name,
                                            "row": row_idx + 1,
                                            "columns": list(df.columns),
                                        },
                                    )
                                    documents.append(doc)

                    except Exception as e:
                        logger.error(f"Error procesando hoja {sheet_name}: {e}")
                        continue

                return documents
            finally:
                os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Error processing XLSX: {e}")
            return []

    async def _process_docx(self, docx_url: str) -> List[Document]:
        import aiohttp
        import tempfile
        import os

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(docx_url) as response:
                    response.raise_for_status()
                    docx_data = await response.read()

            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(docx_data)

            try:
                from docx import Document as DocxDocument
                doc = DocxDocument(temp_path)
                documents = []

                full_text = []
                for para in doc.paragraphs:
                    if para.text.strip():
                        full_text.append(para.text.strip())

                if full_text:
                    documents.append(Document(
                        page_content="\n".join(full_text),
                        metadata={"source": docx_url, "type": "docx"}
                    ))

                for table_idx, table in enumerate(doc.tables):
                    table_content = []
                    for row in table.rows:
                        row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if row_text:
                            table_content.append(" | ".join(row_text))
                    if table_content:
                        documents.append(Document(
                            page_content="\n".join(table_content),
                            metadata={"source": docx_url, "type": "docx", "table": table_idx + 1}
                        ))

                return documents
            finally:
                os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Error processing DOCX: {e}")
            return []

    async def search_relevant_content(
        self, query: str, document_ids: List[str], max_results: int = 5, profile_id: Optional[str] = None
    ) -> Dict[str, Any]:
        self._ensure_embeddings()
        try:
            all_results = []

            if self.use_qdrant and profile_id:
                collection_name = f"profile_{profile_id}"
                try:
                    results = self.qdrant_adapter.search_similar(
                        collection_name=collection_name,
                        query=query,
                        k=max_results
                    )

                    for doc, score in results:
                        all_results.append({
                            "content": doc.page_content,
                            "metadata": doc.metadata,
                            "score": score,
                            "document_id": doc.metadata.get("document_id", "unknown"),
                        })

                    logger.info(f"Qdrant search in {collection_name}: found {len(results)} results")

                except Exception as e:
                    logger.error(f"Error searching in Qdrant collection {collection_name}: {e}")

            # Search in individual document collections (FAISS or Qdrant)
            for document_id in document_ids:
                vectorstore = None

                if document_id in self.vectorstore_cache:
                    vectorstore = self.vectorstore_cache[document_id]
                    logger.debug(f"Using cached vectorstore for {document_id}")
                else:
                    try:

                        faiss_path = self.vector_store_path / f"doc_{document_id}.faiss"
                        simple_path = (
                            self.vector_store_path / f"doc_{document_id}.simple"
                        )

                        if faiss_path.exists():
                            from langchain_community.vectorstores import FAISS
                            vectorstore = FAISS.load_local(
                                str(faiss_path), self.embeddings
                            )

                            self.vectorstore_cache[document_id] = vectorstore
                            logger.debug(
                                f"Loaded FAISS vectorstore from disk for {document_id}"
                            )
                        elif simple_path.exists():
                            vectorstore = self._load_simple_vectorstore(simple_path)
                            if vectorstore:

                                self.vectorstore_cache[document_id] = vectorstore
                                logger.debug(
                                    f"Loaded simple vectorstore from disk for {document_id}"
                                )
                            else:
                                logger.warning(
                                    f"Failed to load simple vectorstore for {document_id}"
                                )
                                continue
                        else:
                            logger.warning(
                                f"No vectorstore file found for {document_id}"
                            )
                            continue
                    except Exception as e:
                        logger.error(
                            f"Error loading vectorstore for {document_id}: {e}"
                        )
                        continue

                if vectorstore:
                    try:

                        if (
                            isinstance(vectorstore, dict)
                            and vectorstore.get("type") == "simple_tfidf"
                        ):

                            results = self._search_simple_tfidf(
                                vectorstore, query, max_results
                            )
                            for doc, score in results:
                                all_results.append(
                                    {
                                        "content": doc.page_content,
                                        "metadata": doc.metadata,
                                        "score": score,
                                        "document_id": document_id,
                                    }
                                )
                        elif (
                            isinstance(vectorstore, dict)
                            and vectorstore.get("type") == "simple_chunks"
                        ):

                            results = self._search_simple_chunks(
                                vectorstore, query, max_results
                            )
                            for doc, score in results:
                                all_results.append(
                                    {
                                        "content": doc.page_content,
                                        "metadata": doc.metadata,
                                        "score": score,
                                        "document_id": document_id,
                                    }
                                )
                        else:

                            docs = vectorstore.similarity_search_with_score(
                                query, k=max_results
                            )
                            for doc, score in docs:
                                all_results.append(
                                    {
                                        "content": doc.page_content,
                                        "metadata": doc.metadata,
                                        "score": score,
                                        "document_id": document_id,
                                    }
                                )
                    except Exception as e:
                        logger.error(
                            f"Error searching in vectorstore {document_id}: {e}"
                        )
                        continue

            all_results.sort(key=lambda x: x["score"])

            top_results = all_results[:max_results]

            context_parts = []
            for result in top_results:
                context_parts.append(
                    f"[Fuente: {result['metadata'].get('source', 'desconocida')}]"
                )
                context_parts.append(result["content"])
                context_parts.append("---")

            unified_context = "\n".join(context_parts)

            logger.info(f"Query: '{query}'")
            logger.info(f"Total results found: {len(all_results)}")
            logger.info(f"Top results returned: {len(top_results)}")

            for i, result in enumerate(top_results[:3]):
                logger.info(
                    f"Result {i+1} (score: {result['score']:.3f}): {result['content'][:100]}..."
                )

            return {
                "query": query,
                "results": top_results,
                "unified_context": unified_context,
                "total_found": len(all_results),
                "returned": len(top_results),
            }

        except Exception as e:
            logger.error(f"Error searching relevant content: {e}")
            return {
                "query": query,
                "results": [],
                "unified_context": "",
                "error": str(e),
            }

    def get_document_status(self, file_url: str) -> Dict[str, Any]:
        document_id = self._get_document_id(file_url)

        if document_id in self.vectorstore_cache:
            vectorstore = self.vectorstore_cache[document_id]
            vector_count = 0

            if isinstance(vectorstore, dict) and "chunks" in vectorstore:
                vector_count = len(vectorstore["chunks"])
            elif hasattr(vectorstore, "docstore"):
                vector_count = len(vectorstore.docstore._dict)

            return {
                "document_id": document_id,
                "status": "processed",
                "file_url": file_url,
                "vector_count": vector_count,
            }
        else:
            return {
                "document_id": document_id,
                "status": "not_processed",
                "file_url": file_url,
            }
