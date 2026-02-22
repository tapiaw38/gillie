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


class SaveMemoryArgs(BaseModel):
    """Arguments for saving a memory fact"""
    content: str = Field(description="Hecho o información relevante a recordar")
    category: str = Field(
        default="General",
        description="Categoría del hecho: Preferencias, Contacto, Historial, etc."
    )


class SearchMemoryArgs(BaseModel):
    """Arguments for searching the assistant memory"""
    query: str = Field(description="Término a buscar en la memoria del asistente")
    max_results: int = Field(default=5, ge=1, le=10)


def create_langchain_tools(openai_integration, profile, skill_manager=None) -> List[StructuredTool]:
    """
    Create LangChain StructuredTool instances with Pydantic validation.

    Args:
        openai_integration: OpenAI integration instance with tool methods
        profile: User profile for context

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

    async def search_documents_tool(query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search for relevant content in user's uploaded documents"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"search_documents_tool called with query: {query}, profile: {profile.user_id}")

        # Search directly in Qdrant by profile_id — no need to process files first
        search_result = await openai_integration.rag_processor.search_relevant_content(
            query=query,
            document_ids=[],
            max_results=max_results,
            profile_id=profile.user_id
        )

        results = search_result.get("results", [])
        unified_context = search_result.get("unified_context", "")

        logger.info(f"search_documents_tool found {len(results)} results for query: {query}")

        if results:
            return {
                "found": True,
                "results": results,
                "context": unified_context,
                "total_chunks": len(results)
            }

        logger.warning(f"No results found in Qdrant for profile {profile.user_id}")
        return {"found": False, "context": "No hay información disponible en el catálogo.", "results": []}

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
                "OBLIGATORIO: Usa esta herramienta cuando el usuario pregunte sobre productos, precios, "
                "disponibilidad, stock o cualquier información del catálogo. "
                "Ejemplos de cuándo usarla: 'qué productos tienen', 'precio de leche', 'tienen aceite', "
                "'cuánto cuesta', 'qué hay disponible'. "
                "Retorna los productos y precios encontrados en el catálogo."
            ),
            func=search_documents_tool,
            args_schema=SearchDocumentsArgs,
            coroutine=search_documents_tool,
        ),
    ]

    if skill_manager is not None:
        async def save_memory_tool(content: str, category: str = "General") -> str:
            fact_id = skill_manager.save_memory_fact(content, category)
            return f"Hecho guardado con ID {fact_id}."

        async def search_memory_tool(query: str, max_results: int = 5) -> str:
            return skill_manager.search_memory(query, max_results)

        tools.append(
            StructuredTool(
                name="save_memory",
                description=(
                    "Guarda un hecho o dato relevante de la conversación para recordarlo en el futuro. "
                    "Úsala cuando el usuario comparta: nombre, ciudad, preferencias, productos de interés, "
                    "datos de contacto, historial, problemas reportados. "
                    "NO la uses para información genérica del negocio (eso ya está en el contexto del sistema)."
                ),
                func=save_memory_tool,
                args_schema=SaveMemoryArgs,
                coroutine=save_memory_tool,
            )
        )
        tools.append(
            StructuredTool(
                name="search_memory",
                description=(
                    "Busca en la memoria del asistente (hechos guardados, FAQs, conocimiento general) "
                    "información sobre el usuario o datos previos. "
                    "Úsala cuando el usuario haga referencia a conversaciones anteriores, "
                    "o cuando necesites recordar su nombre, preferencias o historial."
                ),
                func=search_memory_tool,
                args_schema=SearchMemoryArgs,
                coroutine=search_memory_tool,
            )
        )

    return tools
