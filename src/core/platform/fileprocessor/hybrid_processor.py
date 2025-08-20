import asyncio
import logging
from typing import Dict, Any, Optional, List
from src.core.platform.config.service import ConfigurationService
from src.core.platform.fileprocessor.pdf_processor import FileImageProcessor
from src.core.platform.fileprocessor.xlsx_processor import ExcelImageProcessor
from src.core.platform.fileprocessor.langchain_processor import (
    LangChainDocumentProcessor,
)

logger = logging.getLogger(__name__)


class HybridDocumentProcessor:
    def __init__(self, config_service: ConfigurationService):
        self.config_service = config_service
        self.pdf_processor = FileImageProcessor(config_service)
        self.excel_processor = ExcelImageProcessor(config_service)
        self.langchain_processor = LangChainDocumentProcessor(config_service)

    async def process_pdf_hybrid(
        self, pdf_url: str, use_langchain: bool = True
    ) -> Dict[str, Any]:
        try:
            if use_langchain:
                logger.info("Processing PDF with LangChain")
                result = await self.langchain_processor.process_pdf_with_langchain(
                    pdf_url
                )

                if "error" not in result:
                    return result
                else:
                    logger.warning(
                        "LangChain processing failed, falling back to legacy processor"
                    )

            logger.info("Processing PDF with legacy processor")
            result = await self.pdf_processor.analyze_pdf_content(pdf_url)

            full_text = "\n".join(
                [r.extracted_text for r in result.text_extraction_results]
            )

            summary = self._generate_summary(full_text, max_chars=5000)

            return {
                "extracted_text": {
                    "full_text": summary,
                    "chunks": [
                        r.extracted_text for r in result.text_extraction_results
                    ],
                    "total_chunks": len(result.text_extraction_results),
                    "avg_confidence": (
                        sum([r.text_confidence for r in result.text_extraction_results])
                        / len(result.text_extraction_results)
                        if result.text_extraction_results
                        else 0
                    ),
                    "original_length": len(full_text),
                    "summary_length": len(summary),
                },
                "processing_method": "hybrid_legacy_fallback",
                "metadata": {
                    "source": pdf_url,
                    "file_type": "pdf",
                    "has_text": result.has_text,
                    "total_pages": result.total_pages,
                    "text_pages": result.text_pages,
                    "image_pages": result.image_pages,
                },
            }

        except Exception as e:
            logger.error(f"Error in hybrid PDF processing: {e}")
            return {"error": f"Error processing PDF: {str(e)}"}

    async def process_xlsx_hybrid(
        self, xlsx_url: str, use_langchain: bool = True
    ) -> Dict[str, Any]:
        try:
            if use_langchain:
                logger.info("Processing XLSX with LangChain")
                result = await self.langchain_processor.process_xlsx_with_langchain(
                    xlsx_url
                )

                if "error" not in result:
                    return result
                else:
                    logger.warning(
                        "LangChain processing failed, falling back to legacy processor"
                    )

            logger.info("Processing XLSX with legacy processor")
            result = await self.excel_processor.analyze_excel_data(xlsx_url)

            if "error" in result:
                return result

            text_content = result.get("sheets_text_content", {})
            all_text = []

            for sheet_name, sheet_data in text_content.items():
                sheet_text = f"\n[HOJA: {sheet_name}]\n"
                for item in sheet_data:
                    sheet_text += f"{item.get('text', '')}\n"
                all_text.append(sheet_text)

            full_text = "\n".join(all_text)
            chunks = [chunk.strip() for chunk in full_text.split("\n") if chunk.strip()]

            summary = self._generate_summary(full_text, max_chars=5000)

            return {
                "extracted_text": {
                    "full_text": summary,
                    "chunks": chunks,
                    "total_chunks": len(chunks),
                    "avg_confidence": 0.9,
                    "original_length": len(full_text),
                    "summary_length": len(summary),
                },
                "processing_method": "hybrid_legacy_fallback",
                "metadata": {
                    "source": xlsx_url,
                    "file_type": "xlsx",
                    "sheets_analyzed": list(text_content.keys()),
                },
            }

        except Exception as e:
            logger.error(f"Error in hybrid XLSX processing: {e}")
            return {"error": f"Error processing XLSX: {str(e)}"}

    async def process_document_with_vectors(
        self, file_url: str, file_type: str, use_langchain: bool = True
    ) -> Dict[str, Any]:
        try:
            if file_type.lower() == "pdf":
                base_result = await self.process_pdf_hybrid(file_url, use_langchain)
            elif file_type.lower() in ["xlsx", "xls"]:
                base_result = await self.process_xlsx_hybrid(file_url, use_langchain)
            else:
                return {"error": f"Unsupported file type: {file_type}"}

            if "error" in base_result:
                return base_result

            if use_langchain and "vector_store" not in base_result:
                try:
                    from langchain.schema import Document

                    chunks = [
                        Document(page_content=chunk, metadata={"source": file_url})
                        for chunk in base_result["extracted_text"]["chunks"]
                    ]

                    vectorstore = await self.langchain_processor.create_vector_store(
                        chunks, f"doc_{file_type}_{hash(file_url)}"
                    )

                    base_result["vector_store"] = {
                        "collection_name": vectorstore.collection.name,
                        "total_vectors": len(chunks),
                    }

                    base_result["processing_method"] = "hybrid_with_vectors"

                except Exception as e:
                    logger.warning(f"Vector store creation failed: {e}")
                    base_result["processing_method"] = "hybrid_without_vectors"

            return base_result

        except Exception as e:
            logger.error(f"Error in vector document processing: {e}")
            return {"error": f"Error processing document: {str(e)}"}

    async def search_across_documents(
        self, query: str, file_urls: List[str], file_types: List[str]
    ) -> Dict[str, Any]:
        try:
            all_chunks = []
            all_sources = []

            for file_url, file_type in zip(file_urls, file_types):
                result = await self.process_document_with_vectors(
                    file_url, file_type, use_langchain=True
                )

                if "error" not in result and "extracted_text" in result:
                    chunks = result["extracted_text"]["chunks"]
                    all_chunks.extend(chunks)
                    all_sources.extend([file_url] * len(chunks))

            if not all_chunks:
                return {"error": "No documents could be processed"}

            from langchain.schema import Document

            documents = [
                Document(page_content=chunk, metadata={"source": source})
                for chunk, source in zip(all_chunks, all_sources)
            ]

            vectorstore = await self.langchain_processor.create_vector_store(
                documents, "search_collection"
            )
            search_results = await self.langchain_processor.search_similar_chunks(
                query, vectorstore, k=10
            )

            return {
                "query": query,
                "search_results": [
                    {
                        "content": doc.page_content,
                        "source": doc.metadata.get("source", "unknown"),
                        "score": 0.95,
                    }
                    for doc in search_results
                ],
                "total_results": len(search_results),
                "vector_store": {
                    "collection_name": vectorstore.collection.name,
                    "total_vectors": len(documents),
                },
            }

        except Exception as e:
            logger.error(f"Error in document search: {e}")
            return {"error": f"Error searching documents: {str(e)}"}

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
