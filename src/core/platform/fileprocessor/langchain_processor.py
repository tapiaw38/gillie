import asyncio
import tempfile
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import aiohttp
import logging
from io import BytesIO

from langchain_community.document_loaders import UnstructuredFileLoader
from langchain_community.document_loaders import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

from src.core.platform.config.service import ConfigurationService
from src.core.platform.fileprocessor.processor import BaseFileProcessor

logger = logging.getLogger(__name__)


class LangChainDocumentProcessor(BaseFileProcessor):
    def __init__(self, config_service: ConfigurationService):
        super().__init__(config_service)
        self.openai_config = config_service.openai_config
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=self.openai_config.api_key,
            openai_api_base=self.openai_config.base_url,
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

    async def process_pdf_with_langchain(
        self, pdf_url: str, max_pages: int = 50
    ) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url) as response:
                    response.raise_for_status()
                    pdf_data = await response.read()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(pdf_data)

            try:
                loader = UnstructuredFileLoader(temp_path)
                documents = loader.load()

                if not documents:
                    return {"error": "No se pudieron cargar documentos del PDF"}

                chunks = self.text_splitter.split_documents(documents)

                full_text = "\n".join([doc.page_content for doc in chunks])

                result = {
                    "extracted_text": {
                        "full_text": "",
                        "chunks": [doc.page_content for doc in chunks],
                        "total_chunks": len(chunks),
                        "avg_confidence": 0.95,
                        "original_length": len(full_text),
                        "processed_for_vectors": True,
                    },
                    "processing_method": "langchain_unstructured",
                    "metadata": {
                        "source": pdf_url,
                        "file_type": "pdf",
                        "chunk_size": 1000,
                        "chunk_overlap": 200,
                        "vector_ready": True,
                    },
                }

                return result

            finally:
                os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Error processing PDF with LangChain: {e}")
            return {"error": f"Error processing PDF: {str(e)}"}

    async def process_xlsx_with_langchain(self, xlsx_url: str) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(xlsx_url) as response:
                    response.raise_for_status()
                    xlsx_data = await response.read()

            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(xlsx_data)

            try:
                import pandas as pd

                excel_file = pd.ExcelFile(temp_path)
                all_text = ""

                for sheet_name in excel_file.sheet_names:
                    try:
                        df = pd.read_excel(temp_path, sheet_name=sheet_name)

                        if not df.empty:
                            all_text += f"\n[HOJA: {sheet_name}]\n"

                            for column in df.columns:
                                all_text += f"\n[COLUMNA: {column}]\n"
                                for value in df[column].dropna():
                                    if isinstance(value, (str, int, float)):
                                        all_text += f"{str(value)}\n"

                            all_text += "\n"
                    except Exception as e:
                        logger.error(f"Error procesando hoja {sheet_name}: {e}")
                        continue

                if not all_text.strip():
                    return {"error": "No se pudieron cargar documentos del Excel"}

                document = Document(
                    page_content=all_text, metadata={"source": xlsx_url}
                )
                chunks = self.text_splitter.split_documents([document])

                result = {
                    "extracted_text": {
                        "full_text": "",
                        "chunks": [doc.page_content for doc in chunks],
                        "total_chunks": len(chunks),
                        "avg_confidence": 0.95,
                        "original_length": len(all_text),
                        "processed_for_vectors": True,
                    },
                    "processing_method": "langchain_pandas_excel",
                    "metadata": {
                        "source": xlsx_url,
                        "file_type": "xlsx",
                        "chunk_size": 1000,
                        "chunk_overlap": 200,
                        "vector_ready": True,
                    },
                }

                return result

            finally:
                os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Error processing XLSX with LangChain: {e}")
            return {"error": f"Error processing XLSX: {str(e)}"}

    async def create_vector_store(
        self, documents: List[Document], collection_name: str = "documents"
    ) -> Chroma:
        try:
            vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                collection_name=collection_name,
            )
            return vectorstore
        except Exception as e:
            logger.error(f"Error creating vector store: {e}")
            raise

    async def search_similar_chunks(
        self, query: str, vectorstore: Chroma, k: int = 5
    ) -> List[Document]:
        try:
            results = vectorstore.similarity_search(query, k=k)
            return results
        except Exception as e:
            logger.error(f"Error searching similar chunks: {e}")
            return []

    async def process_document_with_vectors(
        self, file_url: str, file_type: str
    ) -> Dict[str, Any]:
        try:
            if file_type.lower() == "pdf":
                result = await self.process_pdf_with_langchain(file_url)
            elif file_type.lower() in ["xlsx", "xls"]:
                result = await self.process_xlsx_with_langchain(file_url)
            else:
                return {"error": f"Unsupported file type: {file_type}"}

            if "error" in result:
                return result

            chunks = [
                Document(page_content=chunk, metadata={"source": file_url})
                for chunk in result["extracted_text"]["chunks"]
            ]

            vectorstore = await self.create_vector_store(
                chunks, f"doc_{file_type}_{hash(file_url)}"
            )

            result["vector_store"] = {
                "collection_name": vectorstore.collection.name,
                "total_vectors": len(chunks),
            }

            return result

        except Exception as e:
            logger.error(f"Error processing document with vectors: {e}")
            return {"error": f"Error processing document: {str(e)}"}

    def _generate_summary(self, text: str, max_chars: int = 5000) -> str:
        """
        Genera un resumen del texto para evitar exceder límites de tokens
        """
        try:
            if len(text) <= max_chars:
                return text

            lines = text.split("\n")
            summary_lines = []
            current_length = 0

            for line in lines:
                if current_length + len(line) + 1 <= max_chars:
                    summary_lines.append(line)
                    current_length += len(line) + 1
                else:
                    break

            summary = "\n".join(summary_lines)

            if len(text) > max_chars:
                summary += f"\n\n[RESUMEN TRUNCADO - Archivo muy grande. Mostrando primeros {max_chars} caracteres de {len(text)} total]"
                summary += (
                    f"\n[Para ver el contenido completo, use el procesador de vectores]"
                )

            logger.info(f"Generated summary: {len(text)} -> {len(summary)} characters")
            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return (
                text[:max_chars] + f"\n\n[TRUNCADO - Error generando resumen: {str(e)}]"
            )
