"""
Pydantic Models for Tool Validation

This module defines Pydantic models for validating tool arguments.
Each model corresponds to a tool that can be called by the AI assistant.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)

# Default descriptions used when the profile has no custom tool_prompts
_DEFAULT_TOOL_PROMPTS: Dict[str, str] = {
    "search_images": (
        "Search for images in the user's uploaded files. "
        "Use when the user asks to find or see images from their documents."
    ),
    "analyze_pdf": (
        "Analyze the structure and content of a PDF file. "
        "Use when the user asks about a specific PDF document."
    ),
    "extract_text_from_pdf": (
        "Extract text and images from a PDF file. "
        "Use when the user needs detailed content from a PDF."
    ),
    "analyze_excel": (
        "Analyze data from an Excel file. "
        "Use when the user asks about data in a spreadsheet."
    ),
    "describe_image": (
        "Describe the content of an image. "
        "Use when the user shares or asks about an image."
    ),
    "search_documents": (
        "Search for information in the user's uploaded documents. "
        "Use when the user asks a question that may be answered by their uploaded files."
    ),
    "query_database": (
        "Query the database to retrieve information. "
        "Use when the user asks for data that lives in the connected database."
    ),
    "save_memory": (
        "Save a relevant fact from the conversation to remember it later. "
        "Use when the user shares personal information, preferences, or important data."
    ),
    "search_memory": (
        "Search previously saved facts about the user. "
        "Use when the user refers to past conversations or when context about the user is needed."
    ),
}


def _get_tool_prompts(profile) -> Dict[str, str]:
    """Merge default prompts with any custom ones stored in profile.tool_prompts."""
    prompts = dict(_DEFAULT_TOOL_PROMPTS)
    if not profile or not getattr(profile, "tool_prompts", None):
        return prompts
    try:
        custom = json.loads(profile.tool_prompts)
        if isinstance(custom, dict):
            prompts.update({k: v for k, v in custom.items() if v and isinstance(v, str)})
    except Exception:
        logger.warning("Could not parse profile.tool_prompts — using defaults")
    return prompts


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


class QueryDatabaseArgs(BaseModel):
    """Arguments for querying the database"""
    columns: List[str] = Field(
        default=["*"],
        description="Column names to retrieve. Use ['*'] for all columns."
    )
    filters: Optional[str] = Field(
        default=None,
        description=(
            "Optional WHERE clause fragment. Examples: "
            "\"nombre ILIKE '%leche%'\", "
            "\"precio < 100\", "
            "\"categoria = 'lacteos' AND stock > 0\""
        )
    )
    limit: int = Field(
        default=20,
        description="Maximum number of rows to return",
        ge=1,
        le=50,
    )


def _get_sql_integration(profile):
    """Return a SQLDatabaseIntegration if the profile has sqldatabase activated, else None."""
    if not profile or not profile.integrations:
        return None
    for integration in profile.integrations:
        if integration.name == "sqldatabase" and integration.activated:
            config = integration.config or {}
            connection_string = config.get("connection_string")
            allowed_table = config.get("allowed_table")
            if not connection_string or not allowed_table:
                return None
            from src.adapters.web.integrations.sqldatabase.sqldatabase import SQLDatabaseIntegration
            return SQLDatabaseIntegration(
                connection_string=connection_string,
                allowed_table=allowed_table,
                table_description=config.get("table_description", ""),
            )
    return None


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

    prompts = _get_tool_prompts(profile)
    sql_integration = _get_sql_integration(profile)

    # When DB integration is active, override search_documents prompt to avoid conflict
    if sql_integration is not None and "search_documents" not in (json.loads(profile.tool_prompts) if getattr(profile, "tool_prompts", None) else {}):
        prompts["search_documents"] = (
            "Search for information in the user's uploaded documents (PDFs, Excel). "
            "Do NOT use for database queries — use query_database instead. "
            "Use only when the user asks about uploaded files or documents."
        )

    tools = [
        StructuredTool(
            name="search_images",
            description=prompts["search_images"],
            func=search_images_tool,
            args_schema=SearchImagesArgs,
            coroutine=search_images_tool,
        ),
        StructuredTool(
            name="analyze_pdf",
            description=prompts["analyze_pdf"],
            func=analyze_pdf_tool,
            args_schema=AnalyzePDFArgs,
            coroutine=analyze_pdf_tool,
        ),
        StructuredTool(
            name="extract_text_from_pdf",
            description=prompts["extract_text_from_pdf"],
            func=extract_text_tool,
            args_schema=ExtractTextArgs,
            coroutine=extract_text_tool,
        ),
        StructuredTool(
            name="analyze_excel",
            description=prompts["analyze_excel"],
            func=analyze_excel_tool,
            args_schema=AnalyzeExcelArgs,
            coroutine=analyze_excel_tool,
        ),
        StructuredTool(
            name="describe_image",
            description=prompts["describe_image"],
            func=describe_image_tool,
            args_schema=DescribeImageArgs,
            coroutine=describe_image_tool,
        ),
        StructuredTool(
            name="search_documents",
            description=prompts["search_documents"],
            func=search_documents_tool,
            args_schema=SearchDocumentsArgs,
            coroutine=search_documents_tool,
        ),
    ]

    # SQL database tool — only added when the profile has sqldatabase integration active
    if sql_integration is not None:
        async def query_database_tool(
            columns: List[str] = None,
            filters: Optional[str] = None,
            limit: int = 20,
        ) -> Dict[str, Any]:
            """Query the allowed database table and return matching rows."""
            return await sql_integration.query(
                columns=columns or ["*"],
                filters=filters,
                limit=limit,
            )

        db_description = prompts.get("query_database", _DEFAULT_TOOL_PROMPTS["query_database"])
        db_description += f" Tabla: {sql_integration.allowed_table}. {sql_integration.table_description}"

        tools.append(
            StructuredTool(
                name="query_database",
                description=db_description,
                func=query_database_tool,
                args_schema=QueryDatabaseArgs,
                coroutine=query_database_tool,
            )
        )

    if skill_manager is not None:
        async def save_memory_tool(content: str, category: str = "General") -> str:
            fact_id = skill_manager.save_memory_fact(content, category)
            return f"Hecho guardado con ID {fact_id}."

        async def search_memory_tool(query: str, max_results: int = 5) -> str:
            return skill_manager.search_memory(query, max_results)

        tools.append(
            StructuredTool(
                name="save_memory",
                description=prompts["save_memory"],
                func=save_memory_tool,
                args_schema=SaveMemoryArgs,
                coroutine=save_memory_tool,
            )
        )
        tools.append(
            StructuredTool(
                name="search_memory",
                description=prompts["search_memory"],
                func=search_memory_tool,
                args_schema=SearchMemoryArgs,
                coroutine=search_memory_tool,
            )
        )

    return tools
