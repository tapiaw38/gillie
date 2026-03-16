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

_clip_model = None


def _get_clip_model():
    global _clip_model
    if _clip_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _clip_model = SentenceTransformer("clip-ViT-B-32")
            logger.info("[tools] CLIP model loaded: clip-ViT-B-32")
        except Exception as e:
            logger.warning(f"[tools] Could not load CLIP model: {e}")
    return _clip_model


def _clip_is_relevant(image_base64: str, search_term: str, threshold: float = 0.22) -> bool:
    """Use CLIP to check if an image is semantically related to the search term.

    Returns True if similarity >= threshold, or if CLIP is unavailable (fail-open).
    """
    try:
        import base64 as _b64
        import io as _io
        from PIL import Image as _PilImage
        from sentence_transformers import util as _st_util

        clip = _get_clip_model()
        if clip is None:
            return True  # CLIP not available — keep image

        img = _PilImage.open(_io.BytesIO(_b64.b64decode(image_base64))).convert("RGB")
        img_emb = clip.encode(img, convert_to_tensor=True)
        text_emb = clip.encode(search_term, convert_to_tensor=True)
        score = _st_util.cos_sim(img_emb, text_emb).item()
        logger.info(f"[tools] CLIP score for '{search_term}': {score:.3f} (threshold={threshold})")
        return score >= threshold
    except Exception as e:
        logger.warning(f"[tools] CLIP check failed: {e}")
        return True  # fail-open


# Default descriptions used when the profile has no custom tool_prompts
_DEFAULT_TOOL_PROMPTS: Dict[str, str] = {
    "search_images": (
        "Search for images inside the user's uploaded documents (PDFs, Excel). "
        "First finds the relevant documents via semantic search, then extracts images from those documents. "
        "Use when the user asks to see images, photos or visual content related to a topic. "
        "IMPORTANT: when images are found, include each image_url literally and completely in your response text so it can be sent to the user."
    ),
    "analyze_pdf": (
        "Analyze the structure of a PDF file uploaded by the user. "
        "Use when the user asks about a specific PDF by name (e.g. 'manual.pdf'). "
        "Provide the file name, not a URL."
    ),
    "extract_text_from_pdf": (
        "Extract detailed text and images from a specific PDF uploaded by the user. "
        "Use when the user needs the full content of a named PDF. "
        "Provide the file name, not a URL."
    ),
    "analyze_excel": (
        "Analyze data from a specific Excel file uploaded by the user. "
        "Use when the user asks about data in a named spreadsheet. "
        "Provide the file name, not a URL."
    ),
    "describe_image": (
        "Describe the visual content of an image using its URL. "
        "Use after search_images returns image URLs and the user wants to know what an image shows."
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
    file_name: str = Field(
        description="Name (or partial name) of the PDF file uploaded by the user, e.g. 'manual.pdf'"
    )


class ExtractTextArgs(BaseModel):
    """Arguments for extracting text and images from PDF"""
    file_name: str = Field(
        description="Name (or partial name) of the PDF file uploaded by the user, e.g. 'manual.pdf'"
    )
    search_term: Optional[str] = Field(
        default=None,
        description="Optional search term to filter extracted content"
    )


class AnalyzeExcelArgs(BaseModel):
    """Arguments for analyzing Excel file"""
    file_name: str = Field(
        description="Name (or partial name) of the Excel file uploaded by the user, e.g. 'datos.xlsx'"
    )


class DescribeImageArgs(BaseModel):
    """Arguments for describing an image"""
    image_url: str = Field(
        description="URL of the image to describe (e.g. obtained from search_images results)"
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


def _find_file_by_name(files, file_name: str):
    """Find a file in profile.files by name (case-insensitive partial match)."""
    if not files:
        return None
    name_lower = file_name.lower()
    for f in files:
        if f.name.lower() == name_lower:
            return f
    for f in files:
        if name_lower in f.name.lower() or f.name.lower() in name_lower:
            return f
    return None


def create_langchain_tools(openai_integration, profile, skill_manager=None, store_service=None) -> List[StructuredTool]:
    """
    Create LangChain StructuredTool instances with Pydantic validation.

    Args:
        openai_integration: OpenAI integration instance with tool methods
        profile: User profile for context

    Returns:
        List of LangChain StructuredTool instances
    """

    async def search_images_tool(search_term: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for images inside documents relevant to the search term."""
        if not profile.files:
            return []

        doc_search = await openai_integration.rag_processor.search_relevant_content(
            query=search_term,
            document_ids=[],
            max_results=20,
            profile_id=profile.user_id,
        )

        relevant_urls: set = set()
        for result in doc_search.get("results", []):
            url = (
                result.get("metadata", {}).get("file_url")
                or result.get("metadata", {}).get("source")
            )
            if url:
                relevant_urls.add(url)

        if relevant_urls:
            filtered_files = [f for f in profile.files if f.url in relevant_urls]
        else:
            filtered_files = list(profile.files)

        if not filtered_files:
            return []

        class _ProfileProxy:
            def __init__(self, files):
                self.files = files

        results = await openai_integration.search_images_with_text_analysis(
            search_term=search_term,
            profile=_ProfileProxy(filtered_files),
            max_results=max_results,
        )

        if not results:
            return {"found": False, "message": "No se encontraron imágenes relacionadas con ese término."}

        MIN_CONFIDENCE = 0.2
        candidates = [r for r in results if getattr(r, "confidence", 1.0) >= MIN_CONFIDENCE]
        if not candidates:
            candidates = results  # keep all if all are below threshold

        images = []
        for i, result in enumerate(candidates):
            image_base64 = getattr(result, "image_base64", None)
            if not image_base64:
                continue

            if not _clip_is_relevant(image_base64, search_term):
                logger.info(f"[tools] Image {i} filtered by CLIP (not relevant to '{search_term}')")
                continue

            image_url = None
            if store_service:
                try:
                    import base64 as _b64
                    import io as _io
                    from uuid import uuid4
                    image_bytes = _b64.b64decode(image_base64)
                    file_name = f"search_result_{uuid4().hex[:8]}.png"
                    key = store_service.put_object(
                        file=_io.BytesIO(image_bytes),
                        user_file=profile.user_id,
                        filename=file_name,
                        size=len(image_bytes),
                        object_id=f"img{i}",
                    )
                    image_url = store_service.generate_url(key)
                except Exception as e:
                    logger.warning(f"Could not upload image to storage: {e}")

            if image_url:
                images.append({
                    "image_url": image_url,
                    "page_number": getattr(result, "page_number", None),
                })

        if not images:
            return {"found": False, "message": "No se encontraron imágenes relevantes para ese término."}

        return {
            "found": True,
            "images": images,
            "instruction": "Include each image_url literally in your response text.",
        }

    async def analyze_pdf_tool(file_name: str) -> Dict[str, Any]:
        """Analyze PDF content structure"""
        file = _find_file_by_name(profile.files, file_name)
        if not file:
            return {"error": f"No se encontró ningún archivo con el nombre '{file_name}' en los archivos del usuario."}
        return await openai_integration.analyze_pdf_content(file.url)

    async def extract_text_tool(file_name: str, search_term: Optional[str] = None) -> Dict[str, Any]:
        """Extract text and images from PDF"""
        file = _find_file_by_name(profile.files, file_name)
        if not file:
            return {"error": f"No se encontró ningún archivo con el nombre '{file_name}' en los archivos del usuario."}
        return await openai_integration.extract_text_and_images_from_pdf(
            pdf_url=file.url,
            search_term=search_term,
        )

    async def analyze_excel_tool(file_name: str) -> Dict[str, Any]:
        """Analyze Excel file data"""
        file = _find_file_by_name(profile.files, file_name)
        if not file:
            return {"error": f"No se encontró ningún archivo con el nombre '{file_name}' en los archivos del usuario."}
        return await openai_integration.analyze_excel_file(file.url)

    async def describe_image_tool(image_url: str) -> str:
        """Describe an image from its URL"""
        import aiohttp, base64 as b64
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    resp.raise_for_status()
                    image_bytes = await resp.read()
            image_base64 = b64.b64encode(image_bytes).decode()
            return await openai_integration.describe_image_from_base64(image_base64)
        except Exception as e:
            return f"Error al obtener la imagen desde la URL: {e}"

    async def search_documents_tool(query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search for relevant content in user's uploaded documents"""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"search_documents_tool called with query: {query}, profile: {profile.user_id}")

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

    if sql_integration is not None and "search_documents" not in (json.loads(profile.tool_prompts) if getattr(profile, "tool_prompts", None) else {}):
        prompts["search_documents"] = (
            "Search for information in the user's uploaded documents (PDFs, Excel). "
            "Do NOT use for database queries — use query_database instead. "
            "Use only when the user asks about uploaded files or documents."
        )

    disabled = set(getattr(profile, "disabled_tools", None) or [])

    def _tool(name, description, func, schema):
        if name in disabled:
            return None
        return StructuredTool(name=name, description=description, func=func, args_schema=schema, coroutine=func)

    tools = list(filter(None, [
        _tool("search_images",          prompts["search_images"],          search_images_tool,   SearchImagesArgs),
        _tool("analyze_pdf",            prompts["analyze_pdf"],            analyze_pdf_tool,     AnalyzePDFArgs),
        _tool("extract_text_from_pdf",  prompts["extract_text_from_pdf"],  extract_text_tool,    ExtractTextArgs),
        _tool("analyze_excel",          prompts["analyze_excel"],          analyze_excel_tool,   AnalyzeExcelArgs),
        _tool("describe_image",         prompts["describe_image"],         describe_image_tool,  DescribeImageArgs),
        _tool("search_documents",       prompts["search_documents"],       search_documents_tool, SearchDocumentsArgs),
    ]))

    if sql_integration is not None and "query_database" not in disabled:
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

        if "save_memory" not in disabled:
            tools.append(StructuredTool(
                name="save_memory",
                description=prompts["save_memory"],
                func=save_memory_tool,
                args_schema=SaveMemoryArgs,
                coroutine=save_memory_tool,
            ))
        if "search_memory" not in disabled:
            tools.append(StructuredTool(
                name="search_memory",
                description=prompts["search_memory"],
                func=search_memory_tool,
                args_schema=SearchMemoryArgs,
                coroutine=search_memory_tool,
            ))

    return tools
