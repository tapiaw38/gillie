"""
Pydantic Models for Tool Validation

This module defines Pydantic models for validating tool arguments.
Each model corresponds to a tool that can be called by the AI assistant.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool


class SearchImagesArgs(BaseModel):
    """Arguments for searching images in files"""
    search_term: str = Field(
        description="The term to search for in images. Can be a product name, feature, or keyword."
    )
    max_results: int = Field(
        default=5,
        description="Maximum number of images to return",
        ge=1,
        le=20
    )


class AnalyzePDFArgs(BaseModel):
    """Arguments for analyzing PDF content"""
    pdf_url: str = Field(
        description="URL of the PDF file to analyze"
    )


class ExtractTextArgs(BaseModel):
    """Arguments for extracting text and images from PDF"""
    pdf_url: str = Field(
        description="URL of the PDF file to process"
    )
    search_term: Optional[str] = Field(
        default=None,
        description="Optional search term to filter extracted content"
    )


class AnalyzeExcelArgs(BaseModel):
    """Arguments for analyzing Excel file"""
    excel_url: str = Field(
        description="URL of the Excel file to analyze"
    )


class DescribeImageArgs(BaseModel):
    """Arguments for describing an image"""
    image_base64: str = Field(
        description="Base64 encoded image data"
    )


class SearchDocumentsArgs(BaseModel):
    """Arguments for searching content in documents"""
    query: str = Field(
        description="The search query to find relevant information in documents (e.g., product names, prices, specifications)"
    )
    max_results: int = Field(
        default=5,
        description="Maximum number of relevant results to return",
        ge=1,
        le=10
    )


class SearchFAQsArgs(BaseModel):
    """Arguments for searching FAQs"""
    query: str = Field(
        description="The user's question to search in frequently asked questions"
    )
    max_results: int = Field(
        default=5,
        description="Maximum number of FAQs to return",
        ge=1,
        le=10
    )


def create_langchain_tools(openai_integration, profile, faq_repository=None) -> List[StructuredTool]:
    """
    Create LangChain StructuredTool instances with Pydantic validation.

    Args:
        openai_integration: OpenAI integration instance with tool methods
        profile: User profile for context
        faq_repository: FAQ repository for searching FAQs (optional)

    Returns:
        List of LangChain StructuredTool instances
    """

    async def search_images_tool(search_term: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for images in user's files"""
        results = await openai_integration.search_images_with_text_analysis(
            search_term=search_term,
            profile=profile,
            max_results=max_results
        )
        # Convert to serializable format
        return [
            {
                "image_url": result.image_url,
                "confidence": result.confidence,
                "page_number": result.page_number,
                "source_file": result.source_file,
            }
            for result in results
        ]

    async def analyze_pdf_tool(pdf_url: str) -> Dict[str, Any]:
        """Analyze PDF content structure"""
        return await openai_integration.analyze_pdf_content(pdf_url)

    async def extract_text_tool(pdf_url: str, search_term: Optional[str] = None) -> Dict[str, Any]:
        """Extract text and images from PDF"""
        return await openai_integration.extract_text_and_images_from_pdf(
            pdf_url=pdf_url,
            search_term=search_term
        )

    async def analyze_excel_tool(excel_url: str) -> Dict[str, Any]:
        """Analyze Excel file data"""
        return await openai_integration.analyze_excel_file(excel_url)

    async def describe_image_tool(image_base64: str) -> str:
        """Describe an image from base64 data"""
        return await openai_integration.describe_image_from_base64(image_base64)

    async def search_faqs_tool(query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search in frequently asked questions"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"search_faqs_tool called with query: {query}")

        try:
            # Check if FAQ repository is available
            if not faq_repository:
                logger.warning("FAQ repository not available")
                return {"found": False, "message": "FAQ system not configured", "faqs": []}

            # Create FAQ context manager
            from src.core.platform.managers.faq_context_manager import FAQContextManager
            faq_manager = FAQContextManager(faq_repository=faq_repository)

            # Search relevant FAQs
            faq_context = faq_manager.search_relevant_faqs(query, max_results=max_results)

            if faq_context:
                logger.info(f"Found relevant FAQs for query: {query}")
                return {
                    "found": True,
                    "faqs_context": faq_context,
                    "message": "Found relevant FAQs. Use these answers as priority."
                }
            else:
                logger.info("No relevant FAQs found")
                return {
                    "found": False,
                    "message": "No relevant FAQs found. You can search in documents if needed.",
                    "faqs": []
                }
        except Exception as e:
            logger.error(f"Error searching FAQs: {e}", exc_info=True)
            return {"found": False, "error": str(e), "faqs": []}

    async def search_documents_tool(query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search for relevant content in user's uploaded documents"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"search_documents_tool called with query: {query}")
        logger.info(f"Profile has {len(profile.files) if profile.files else 0} files")

        # Process and store documents if not already done
        document_ids = []
        for file in profile.files:
            try:
                file_type = (
                    "pdf" if file.url.lower().endswith(".pdf")
                    else "xlsx" if file.url.lower().endswith((".xlsx", ".xls"))
                    else None
                )

                if file_type:
                    logger.info(f"Processing {file_type} document: {file.url}")
                    result = await openai_integration.rag_processor.process_and_store_document(
                        file.url, file_type, profile_id=profile.user_id
                    )
                    logger.info(f"Process result: {result}")
                    if "document_id" in result:
                        document_ids.append(result["document_id"])
                        logger.info(f"Added document_id: {result['document_id']}")
            except Exception as e:
                logger.error(f"Error processing file {file.url}: {e}", exc_info=True)
                continue

        logger.info(f"Total document_ids: {len(document_ids)}")

        # Search for relevant content
        if document_ids:
            logger.info(f"Searching in documents: {document_ids}")
            search_result = await openai_integration.rag_processor.search_relevant_content(
                query=query,
                document_ids=document_ids,
                max_results=max_results,
                profile_id=profile.user_id
            )
            logger.info(f"Search result: {search_result}")
            return {
                "found": True,
                "results": search_result.get("results", []),
                "context": search_result.get("unified_context", ""),
                "total_chunks": len(search_result.get("results", []))
            }

        logger.warning("No documents processed, returning empty result")
        return {"found": False, "context": "No documents available", "results": []}

    # NOTE: search_faqs tool is NOT included because FAQs are already injected
    # into the context in add_message_use_case.py with highest priority.
    # Including the tool would be redundant and confuses the LLM.

    tools = [
        StructuredTool(
            name="search_images",
            description=(
                "Search for images in the user's uploaded files (PDFs and Excel). "
                "Useful when the user asks to find images related to specific products, "
                "features, or keywords. Returns image URLs with confidence scores."
            ),
            func=search_images_tool,
            args_schema=SearchImagesArgs,
            coroutine=search_images_tool,
        ),
        StructuredTool(
            name="analyze_pdf",
            description=(
                "Analyze the structure and content of a PDF file. "
                "Returns information about text extraction method, number of pages, "
                "and whether the PDF contains text or images."
            ),
            func=analyze_pdf_tool,
            args_schema=AnalyzePDFArgs,
            coroutine=analyze_pdf_tool,
        ),
        StructuredTool(
            name="extract_text_from_pdf",
            description=(
                "Extract text and related images from a PDF file. "
                "Can optionally filter results by a search term. "
                "Useful for getting detailed content from PDFs."
            ),
            func=extract_text_tool,
            args_schema=ExtractTextArgs,
            coroutine=extract_text_tool,
        ),
        StructuredTool(
            name="analyze_excel",
            description=(
                "Analyze data from an Excel file. "
                "Returns structured data analysis including sheets, columns, and statistics."
            ),
            func=analyze_excel_tool,
            args_schema=AnalyzeExcelArgs,
            coroutine=analyze_excel_tool,
        ),
        StructuredTool(
            name="describe_image",
            description=(
                "Generate a detailed description of an image from base64 data. "
                "Useful for understanding image content and context."
            ),
            func=describe_image_tool,
            args_schema=DescribeImageArgs,
            coroutine=describe_image_tool,
        ),
        StructuredTool(
            name="search_documents",
            description=(
                "Search for specific information in the user's uploaded documents (PDFs and Excel files). "
                "Use this tool ONLY if search_faqs didn't find the answer. "
                "This searches through uploaded PDF catalogs, price lists, and Excel files. "
                "Returns relevant text chunks with product details, prices, specifications, etc."
            ),
            func=search_documents_tool,
            args_schema=SearchDocumentsArgs,
            coroutine=search_documents_tool,
        ),
    ]

    return tools
