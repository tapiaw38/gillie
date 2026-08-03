"""
Pydantic Models for Tool Validation

This module defines Pydantic models for validating tool arguments.
Each model corresponds to a tool that can be called by the AI assistant.
"""

import asyncio
import fnmatch
import json
import logging
import os
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
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


def _clip_is_relevant(
    image_base64: str, search_term: str, threshold: float = 0.22
) -> bool:
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
        logger.info(
            f"[tools] CLIP score for '{search_term}': {score:.3f} (threshold={threshold})"
        )
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
    "write_excel": (
        "Create a new Excel file or overwrite/update an existing one with structured data. "
        "Use when the user asks to generate, export, or modify a spreadsheet. "
        "Provide the file path and a dict of sheet names to row data."
    ),
    "read_docx": (
        "Read the full text content of a Word (.docx) document uploaded by the user. "
        "Use when the user asks about the contents of a Word file."
    ),
    "write_docx": (
        "Create a new Word (.docx) document or modify an existing one. "
        "Use when the user asks to generate, write, or edit a Word document. "
        "Content supports headings (#, ##, ###), bold (**text**), italic (*text*), bullets (- item), and numbered lists (1. item)."
    ),
    "modify_excel": (
        "Modify an existing Excel file from profile storage or workspace. "
        "Supports: update cells, add/delete rows, add/rename/delete sheets. "
        "Downloads from storage if not already in workspace. Saves working copy locally. "
        "Use re_upload=True if the user wants to save back to their storage."
    ),
    "modify_docx": (
        "Modify an existing Word (.docx) file from profile storage or workspace. "
        "Supports text replacements and appending new content. "
        "Downloads from storage if not already in workspace. Saves working copy locally. "
        "Use re_upload=True if the user wants to save back to their storage."
    ),
    "insert_image_docx": (
        "Insert an image into an existing Word (.docx) document. "
        "Image source can be a local file path, a URL, or a base64 data URI. "
        "Use position='end' to append at the end, 'start' for the beginning, "
        "or a text string to insert after the paragraph containing that text. "
        "Optionally set width_cm and add a caption. Use re_upload=True to save back to storage. "
        "IMPORTANT: For image URLs, only use sources that allow direct download without authentication. "
        "Recommended free sources: "
        "- Picsum Photos (random real photos): https://picsum.photos/{width}/{height} or https://picsum.photos/seed/{keyword}/{width}/{height} "
        "- Placehold.co (placeholder with text): https://placehold.co/{width}x{height}/png or https://placehold.co/{width}x{height}/{bg}/{text_color}?text={label} "
        "Do NOT use Unsplash URLs (they return 404 without API authentication)."
    ),
    "insert_image_excel": (
        "Insert an image into an existing Excel (.xlsx) file at a specific cell. "
        "Image source can be a local file path, a URL, or a base64 data URI. "
        "Specify the sheet name and anchor cell (e.g. 'B2'). "
        "Optionally set width_cm and height_cm. Use re_upload=True to save back to storage. "
        "IMPORTANT: For image URLs, only use sources that allow direct download without authentication. "
        "Recommended free sources: "
        "- Picsum Photos (random real photos): https://picsum.photos/{width}/{height} or https://picsum.photos/seed/{keyword}/{width}/{height} "
        "- Placehold.co (placeholder with text): https://placehold.co/{width}x{height}/png or https://placehold.co/{width}x{height}/{bg}/{text_color}?text={label} "
        "Do NOT use Unsplash URLs (they return 404 without API authentication)."
    ),
    "insert_image_pptx": (
        "Insert an image into a specific slide of an existing PowerPoint (.pptx) file. "
        "Image source can be a local file path, a URL, or a base64 data URI. "
        "Specify the slide number (1-based), position in cm (left_cm, top_cm), and optional size. "
        "Use re_upload=True to save back to storage. "
        "IMPORTANT: For image URLs, only use sources that allow direct download without authentication. "
        "Recommended free sources: "
        "- Picsum Photos (random real photos): https://picsum.photos/{width}/{height} or https://picsum.photos/seed/{keyword}/{width}/{height} "
        "- Placehold.co (placeholder with text): https://placehold.co/{width}x{height}/png or https://placehold.co/{width}x{height}/{bg}/{text_color}?text={label} "
        "Do NOT use Unsplash URLs (they return 404 without API authentication)."
    ),
    "describe_image": (
        "Describe the visual content of an image from a source. "
        "image_source supports URL, local file path, or file:// URI. "
        "Use after search_images returns image URLs or when user provides a local image path. "
        "For local image analysis, use this tool directly. "
        "WORKFLOW: call describe_image exactly once with the given source, then answer from that result. Never call it a second time for same request. "
        "Do NOT call take_screenshot, send_screenshot, send_file, or run_shell for image description tasks."
    ),
    "generate_image": (
        "Generate an image from text, text+images, or text+videos. "
        "Use when the user asks to create a new image asset."
    ),
    "generate_video": (
        "Generate a normal-quality 6-second video from text, text+images, or text+videos. "
        "Use when the user asks to create a short video clip."
    ),
    "search_documents": (
        "Search for information in the user's uploaded documents. "
        "Use when the user asks a question that may be answered by their uploaded files."
    ),
    "list_storage_files": (
        "List all files the user has uploaded to their storage. "
        "Returns file names, types, sizes, and upload dates. "
        "Use when the user asks 'what files do I have?', 'show my documents', "
        "'list my uploads', or before searching to know available files."
    ),
    "query_database": (
        "Query the LIVE connected PostgreSQL database and return actual rows of data. "
        "Use this tool — NOT code exploration tools — when the user asks about records, "
        "tables, data, or wants to verify/inspect what is stored in the database. "
        "Do NOT use repo_map, find_files, or read_file for database questions."
    ),
    "run_workflow": (
        "Execute a configured multi-step workflow by name. Use this for the "
        "assistant's configured integrations (calendar, bookings, business APIs) "
        "instead of curl or fetch_url: it substitutes parameters, sends the right "
        "authentication headers, chains the steps and passes values between them. "
        "Call it with the workflow name and its input parameters."
    ),
    "fetch_url": (
        "Fetch and extract the text content of a specific web page URL. "
        "Use when the user mentions a specific website by name or URL "
        "(e.g. 'consulta en dolarhoy', 'abre infobae.com', 'revisa la página X'). "
        "Prepend https:// if the user gives a domain without protocol."
    ),
    "download_file": (
        "Download a file from an HTTP or HTTPS URL and save it inside the workspace. "
        "Use when the user asks to download an image, PDF, ZIP, audio, document, or any other file from the web. "
        "Prefer this tool over fetch_url when the goal is to save the original file instead of extracting page text. "
        "If save_as is omitted, infer a safe filename from the URL or response content type."
    ),
    "web_search": (
        "Search the internet for current, real-time information using DuckDuckGo. "
        "Use when the user asks about recent news, current events, live data, prices, "
        "or any information that may have changed after the model's training cutoff. "
        "Also use when the user explicitly asks to 'search the web', 'look it up online', "
        "'busca en internet', 'busca en google', or similar phrases."
    ),
    "organize_memory": (
        "Reorganize and deduplicate general.skill.md, which is reserved for always-on core facts. "
        "Use when the user asks to organize, clean, or rewrite those core facts. "
        "WORKFLOW: 1) Read the current general.skill.md content from context. "
        "2) Merge duplicate or overlapping notes into single coherent entries. "
        "3) Call this tool with the consolidated content as the new_content argument. "
        "The file will be fully replaced with your organized version. "
        "Preserve all unique information — only merge actual duplicates."
    ),
    "save_memory": (
        "Save important information to long-term assistant memory. "
        "When the soul store is available, save it there so it can be retrieved by relevance. "
        "If the brain/soul store is not available, fall back to facts.skill.md. "
        "ALWAYS use this tool when the user says phrases like: "
        "'recuerda', 'recuerda esto', 'guarda esto', 'ten en cuenta', "
        "'guarda en memoria', 'anota', 'no olvides', 'para el futuro', "
        "'remember this', 'save this', 'keep in mind', 'note that'. "
        "Save the exact information the user wants remembered, with its context."
    ),
    "search_memory": (
        "Search previously saved facts about the user. "
        "Use when the user refers to past conversations or when context about the user is needed."
    ),
    "owner_insights": (
        "Get owner-level insights from backend APIs: contacts, conversations, and owner memories. "
        "Use when the owner asks things like how many contacts they have, which contacts have activity, "
        "or memory/conversation counts by contact."
    ),
    "save_solution": (
        "Save a problem-solution pair to long-term memory (solutions.skill.md). "
        "Use when the user explicitly asks to save a solution, or after solving a recurring or "
        "noteworthy problem: 'guarda esta solución', 'anota cómo lo resolví', 'save this fix', "
        "'remember how we fixed this'. "
        "Always capture the exact problem description, the solution steps, and whether it worked."
    ),
    "system_propose": (
        "Propose a shell command to execute on the Linux server. "
        "Use when the user asks to run a command, check server status (CPU, memory, disk, processes, network), "
        "or make changes to the system. The command will require user confirmation before execution. "
        "Read-only commands (ps, df, free, uptime, ls, cat, top -bn1) are recommended for monitoring. "
        "ALWAYS explain what the command will do before proposing it."
    ),
    "system_confirm": (
        "Execute a previously proposed command after the user provides the confirmation code. "
        "Use ONLY when the user responds with a 6-character hex code (like 'A3F9C1') to confirm a command."
    ),
    "cron_create": (
        "Create a cron job that combines a source (system command, HTTP request, or static text) "
        "with a destination (WhatsApp, Telegram, Slack, or none). "
        "Use when the user wants to schedule a recurring task, like 'send me RAM usage via WhatsApp every 5 minutes' "
        "or 'notify me on Telegram daily with the server uptime'. "
        "ALWAYS confirm the cron schedule and integration details with the user before creating."
    ),
    "cron_list": (
        "List all cron jobs for the current user. "
        "Use when the user asks to see their scheduled jobs or wants to know what jobs are configured."
    ),
    "cron_delete": (
        "Delete a cron job by ID. "
        "Use when the user wants to remove a scheduled job. Ask for confirmation before deleting."
    ),
    "cron_run": (
        "Run a cron job immediately without waiting for the next scheduled time. "
        "Use when the user wants to test a job or trigger it on demand."
    ),
    "read_file": (
        "Read the contents of a file. Use when you need to inspect code, "
        "config files, logs, or any text file before making changes. "
        "Supports line ranges via offset and limit."
    ),
    "write_file": (
        "Create a new file or completely overwrite an existing one. "
        "Use for creating new files or when changes are extensive enough "
        "to rewrite the whole file. For small changes prefer edit_file."
    ),
    "edit_file": (
        "Make a surgical edit to a file by replacing an exact string with new content. "
        "Use for targeted code changes: fixing bugs, updating functions, modifying config. "
        "Always read_file first to get the exact current content before editing."
    ),
    "list_directory": (
        "List files and directories at a given path. Use to explore the project structure, "
        "find files, or understand the layout of a repository before editing."
    ),
    "find_files": (
        "Search for files matching a glob pattern (e.g. '**/*.py', 'src/**/*.ts'). "
        "Use when you need to find files by name or extension across a project."
    ),
    "run_shell": (
        "Execute a shell command in the workspace. Use for running tests, installing "
        "packages, checking service status, viewing logs, or any terminal operation. "
        "Always prefer specific commands over broad destructive ones. "
        "Use working_dir to set the execution context."
    ),
    "grep_files": (
        "Search for text or regex patterns inside file contents across the workspace. "
        "Use before editing to find all usages of a function, class, or variable. "
        "Supports glob filtering (e.g. '*.py', '*.ts') and case-insensitive search."
    ),
    "git_status": (
        "Show the current git status and diff statistics of the workspace. "
        "Use before and after file edits to understand what changed."
    ),
    "git_diff": (
        "Show git diff for a specific file or the entire workspace. "
        "Use to review changes before committing or to understand recent edits."
    ),
    "git_log": (
        "Show recent git commit history. Use to understand what changed recently "
        "or to find the commit that introduced a specific change."
    ),
    "git_commit": (
        "Stage and commit changes to git. Provide a clear commit message. "
        "Specify files to stage specific changes, or leave empty to stage all changes. "
        "Only use when the user explicitly asks to commit."
    ),
    "send_file": (
        "Upload a local file to storage and send it to the user through the current chat "
        "(WhatsApp, Telegram, Slack, etc.). "
        "Use whenever the user asks to receive a file, report, PDF, CSV, or any other file. "
        "Do NOT use this for image analysis requests; use describe_image instead. "
        "Works with any file type. "
        "IMPORTANT: You MUST call this tool to get a real URL. NEVER invent or guess a URL. "
        "Only include the URL returned by this tool in your response."
    ),
    "send_screenshot": (
        "Capture the desktop screen and send it directly to the user as an image in the chat "
        "(WhatsApp, Telegram, Slack, etc.). "
        "Use this tool whenever the user asks for a screenshot, screen capture, or photo of the screen. "
        "Do NOT use take_screenshot for this — that tool only describes the screen without sending. "
        "IMPORTANT: You MUST call this tool to get a real URL. NEVER invent or guess a URL. "
        "Only include the URL returned by this tool in your response."
    ),
    "take_screenshot": (
        "Take a screenshot of the current desktop screen and describe what is visible. "
        "Use when the user asks what is on their screen, what windows are open, "
        "what a specific application looks like, or anything about the visual state "
        "of the desktop. Optionally focus on a specific region or window. "
        "Do NOT use this to analyze a local image file path; use describe_image for file/URL images."
    ),
    "browser_act": (
        "Perform one or more browser actions using natural language on the connected browser. "
        "Uses an indexed DOM snapshot so the LLM can precisely target any element — no CSS selectors needed. "
        "PREFER this over browser_click/browser_type for real user browser sessions. "
        "Supports multi-step: 'search for cats then click the first result'. "
        "Requires browser_connect first."
    ),
    "browser_extract": (
        "Extract structured information from the current page using natural language. "
        "Uses the indexed DOM to find and return specific data accurately. "
        "Examples: 'list all video titles', 'get the product price', 'find all nav links'. "
        "Requires browser_connect first."
    ),
    "browser_navigate": (
        "Open a URL in the connected browser and return the page title and visible text. "
        "Use to visit websites, web apps, or local URLs. The browser session persists "
        "across tool calls so you can navigate, interact, then read content."
    ),
    "browser_click": (
        "Click an element by CSS selector or visible text. "
        "Use browser_act instead when you don't know the exact selector. "
        "Examples: 'button#submit', 'text=Login'."
    ),
    "browser_type": (
        "Type text into an input field on the current browser page. "
        "Use after browser_navigate to fill forms, search boxes, etc."
    ),
    "browser_get_content": (
        "Extract text or HTML content from the current browser page or a specific element. "
        "Use to read page content after navigating or after interactions. "
        "Returns visible text by default, or raw HTML when as_html=True."
    ),
    "browser_screenshot": (
        "Take a screenshot of the current browser page and describe its contents. "
        "Use to visually verify the state of a web page after navigation or interaction."
    ),
    "browser_close": (
        "End the browser session. With Chrome this only detaches and the user's browser "
        "stays open; with Firefox, which is driven directly, this closes the browser window."
    ),
    "browser_connect": (
        "Connect to the user's real browser (Firefox or Chrome). "
        "Attaches to an already-open remote-debugging session when there is one; otherwise "
        "launches Firefox with the user's real profile, or relaunches Chrome with CDP. "
        "If a browser is already running and has to be closed first, the user is asked for "
        "permission — tell them what you are about to do before calling this. "
        "Calling it again while connected is a no-op. "
        "After connecting, all browser_* tools operate on the real browser. "
        "Lists all open tabs so you can switch to the right one."
    ),
    "browser_switch_tab": (
        "Switch the active browser tab to a specific index. "
        "Use after browser_connect lists the open tabs to select the right one."
    ),
    "browser_evaluate": (
        "Execute JavaScript code in the current browser page and return the result. "
        "Use to read DOM content, extract data, interact with page elements, or run any "
        "JavaScript logic. Works only after browser_connect has been called. "
        "Example: extract chat names from WhatsApp Web, get form values, check page state."
    ),
    "repo_map": (
        "Generate a compact map of the repository showing file tree and code signatures "
        "(classes, functions, methods). Use at the start of a coding task to understand "
        "the project structure before reading or editing files. Much more efficient than "
        "multiple find_files + read_file calls for orientation."
    ),
    "check_code": (
        "Run a static type checker or linter on a file or directory and return diagnostics. "
        "Use after writing or editing code to catch type errors, undefined variables, and "
        "other issues before running. Supports pyright, mypy (Python), tsc (TypeScript), eslint (JS/TS). "
        "Use tool='auto' to auto-detect the right checker."
    ),
    "read_pptx": (
        "Read the content of a PowerPoint (.pptx) file uploaded by the user. "
        "Returns all slides with their titles, text, and notes. "
        "Use when the user asks about the contents of a presentation."
    ),
    "write_pptx": (
        "Create a new PowerPoint (.pptx) presentation from structured slide data. "
        "Use when the user asks to generate or create a presentation. "
        "Each slide can have a title, body text (bullet points), and speaker notes."
    ),
    "modify_pptx": (
        "Modify an existing PowerPoint (.pptx) file from profile storage or workspace. "
        "Supports: replace text across all slides, add new slides, update slide titles. "
        "Downloads from storage if not already in workspace. "
        "Use re_upload=True if the user wants to save back to their storage."
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
            prompts.update(
                {k: v for k, v in custom.items() if v and isinstance(v, str)}
            )
    except Exception:
        logger.warning("Could not parse profile.tool_prompts — using defaults")
    return prompts


class SearchImagesArgs(BaseModel):
    """Arguments for searching images in files"""

    search_term: str = Field(
        description="The term to search for in images. Can be a product name, feature, or keyword."
    )
    max_results: int = Field(
        default=5, description="Maximum number of images to return", ge=1, le=20
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
        default=None, description="Optional search term to filter extracted content"
    )


class AnalyzeExcelArgs(BaseModel):
    """Arguments for analyzing Excel file"""

    file_name: str = Field(
        description="Name (or partial name) of the Excel file uploaded by the user, e.g. 'datos.xlsx'"
    )


class WriteExcelArgs(BaseModel):
    """Arguments for creating or modifying an Excel file"""

    path: str = Field(
        description="Path to the Excel file to create or modify (e.g. 'report.xlsx')"
    )
    sheets: dict = Field(
        description=(
            "Dict of sheet_name -> list of rows. Each row is a list of cell values. "
            "First row is treated as headers. Example: {'Sheet1': [['Name','Age'],['Ana',30]]}"
        )
    )
    mode: str = Field(
        default="overwrite",
        description="'overwrite' to replace the file, 'update' to modify existing sheets",
    )


class ReadDocxArgs(BaseModel):
    """Arguments for reading a Word document"""

    file_name: str = Field(
        description="Name (or partial name) of the .docx file, e.g. 'report.docx'"
    )


class WriteDocxArgs(BaseModel):
    """Arguments for creating or modifying a Word document"""

    path: str = Field(
        description="Path to the .docx file to create or modify (e.g. 'report.docx')"
    )
    content: str = Field(
        description=(
            "Document content in a simple markdown-like format:\n"
            "# Heading 1\n## Heading 2\n### Heading 3\n"
            "Regular paragraph text.\n**bold** and *italic* inline.\n"
            "- bullet item\n1. numbered item"
        )
    )
    mode: str = Field(
        default="overwrite",
        description="'overwrite' to replace the file, 'append' to add content at the end",
    )


class ModifyExcelArgs(BaseModel):
    """Arguments for modifying an existing Excel file"""

    file_name: str = Field(
        description="Name of the Excel file in profile files or workspace (e.g. 'ventas.xlsx')"
    )
    operations: List[dict] = Field(
        description=(
            "List of operations to apply. Each operation is a dict with 'type' and params:\n"
            "- update_cell: {type, sheet, row (1-based int), col (letter or 1-based int), value}\n"
            "- add_row: {type, sheet, data (list of values)}\n"
            "- delete_row: {type, sheet, row (1-based int)}\n"
            "- add_sheet: {type, name, rows (list of lists)}\n"
            "- rename_sheet: {type, old_name, new_name}\n"
            "- delete_sheet: {type, name}"
        )
    )
    save_as: Optional[str] = Field(
        default=None,
        description="Output filename in workspace. Defaults to same name as input.",
    )
    re_upload: bool = Field(
        default=False,
        description="If True, re-upload the modified file to storage after saving",
    )


class ModifyDocxArgs(BaseModel):
    """Arguments for modifying an existing Word document"""

    file_name: str = Field(
        description="Name of the .docx file in profile files or workspace (e.g. 'report.docx')"
    )
    replacements: Optional[List[dict]] = Field(
        default=None,
        description=(
            "List of text replacements: [{old: 'text to find', new: 'replacement text'}]"
        ),
    )
    append: Optional[str] = Field(
        default=None,
        description="Markdown-like content to append at the end of the document",
    )
    save_as: Optional[str] = Field(
        default=None,
        description="Output filename in workspace. Defaults to same name as input.",
    )
    re_upload: bool = Field(
        default=False,
        description="If True, re-upload the modified file to storage after saving",
    )


class ReadPptxArgs(BaseModel):
    """Arguments for reading a PowerPoint file"""

    file_name: str = Field(
        description="Name (or partial name) of the .pptx file, e.g. 'presentacion.pptx'"
    )


class WritePptxArgs(BaseModel):
    """Arguments for creating a PowerPoint presentation"""

    path: str = Field(description="Output file path (e.g. 'presentacion.pptx')")
    slides: List[dict] = Field(
        description=(
            "List of slide dicts. Each slide can have:\n"
            "  title (str): slide title\n"
            "  body (list[str]): bullet point lines\n"
            "  notes (str): speaker notes (optional)\n"
            'Example: [{"title": "Intro", "body": ["Point 1", "Point 2"], "notes": "Say hello"}]'
        )
    )


class ModifyPptxArgs(BaseModel):
    """Arguments for modifying an existing PowerPoint file"""

    file_name: str = Field(
        description="Name of the .pptx file in profile files or workspace"
    )
    replacements: Optional[List[dict]] = Field(
        default=None,
        description=(
            "List of text replacements across all slides: [{old: 'text to find', new: 'replacement'}]"
        ),
    )
    add_slides: Optional[List[dict]] = Field(
        default=None,
        description=(
            "List of new slides to append. Each slide: {title, body (list[str]), notes (optional str)}"
        ),
    )
    save_as: Optional[str] = Field(
        default=None, description="Output filename. Defaults to same name as input."
    )
    re_upload: bool = Field(
        default=False,
        description="If True, re-upload the modified file to storage after saving",
    )


class InsertImageDocxArgs(BaseModel):
    """Arguments for inserting an image into a Word document"""

    file_name: str = Field(
        description="Name of the .docx file in profile files or workspace (e.g. 'report.docx')"
    )
    image_source: str = Field(
        description="Image source: local file path, URL, or base64 data URI (data:image/...;base64,...)"
    )
    position: str = Field(
        default="end",
        description=(
            "Where to insert the image: 'end' (append at end), 'start' (prepend at beginning), "
            "or a text string to insert the image AFTER the first paragraph containing that text."
        ),
    )
    width_cm: Optional[float] = Field(
        default=None,
        description="Image width in centimetres. Height scales proportionally. Omit to use original size.",
    )
    caption: Optional[str] = Field(
        default=None, description="Optional caption text to add below the image."
    )
    save_as: Optional[str] = Field(
        default=None, description="Output filename. Defaults to same name as input."
    )
    re_upload: bool = Field(
        default=False,
        description="If True, re-upload the modified file to storage after saving",
    )


class InsertImageExcelArgs(BaseModel):
    """Arguments for inserting an image into an Excel file"""

    file_name: str = Field(
        description="Name of the .xlsx file in profile files or workspace (e.g. 'data.xlsx')"
    )
    image_source: str = Field(
        description="Image source: local file path, URL, or base64 data URI"
    )
    sheet: str = Field(description="Sheet name where the image will be inserted")
    cell: str = Field(
        default="A1",
        description="Cell anchor for the top-left corner of the image (e.g. 'B2', 'D5')",
    )
    width_cm: Optional[float] = Field(
        default=None,
        description="Image width in centimetres. Omit to use original size.",
    )
    height_cm: Optional[float] = Field(
        default=None,
        description="Image height in centimetres. Omit to scale proportionally with width.",
    )
    save_as: Optional[str] = Field(
        default=None, description="Output filename. Defaults to same name as input."
    )
    re_upload: bool = Field(
        default=False,
        description="If True, re-upload the modified file to storage after saving",
    )


class InsertImagePptxArgs(BaseModel):
    """Arguments for inserting an image into a PowerPoint slide"""

    file_name: str = Field(
        description="Name of the .pptx file in profile files or workspace (e.g. 'slides.pptx')"
    )
    image_source: str = Field(
        description="Image source: local file path, URL, or base64 data URI"
    )
    slide_number: int = Field(
        description="1-based slide index where the image will be inserted"
    )
    left_cm: float = Field(
        default=2.0,
        description="Distance from the left edge of the slide in centimetres",
    )
    top_cm: float = Field(
        default=4.0,
        description="Distance from the top edge of the slide in centimetres",
    )
    width_cm: Optional[float] = Field(
        default=None,
        description="Image width in centimetres. Omit to use original size.",
    )
    height_cm: Optional[float] = Field(
        default=None,
        description="Image height in centimetres. Omit to scale proportionally.",
    )
    save_as: Optional[str] = Field(
        default=None, description="Output filename. Defaults to same name as input."
    )
    re_upload: bool = Field(
        default=False,
        description="If True, re-upload the modified file to storage after saving",
    )


class DescribeImageArgs(BaseModel):
    """Arguments for describing an image"""

    image_source: str = Field(
        description="Image source to describe: URL, local file path, or file:// URI"
    )


class GenerateImageArgs(BaseModel):
    """Arguments for image generation"""

    prompt: str = Field(description="Main text prompt describing the desired image")
    image_sources: List[str] = Field(
        default_factory=list,
        description="Optional reference images (URLs or data URIs)",
    )
    video_sources: List[str] = Field(
        default_factory=list, description="Optional reference videos (URLs)."
    )
    size: str = Field(
        default="1024x1024", description="Output image size, for example 1024x1024"
    )


class GenerateVideoArgs(BaseModel):
    """Arguments for 6-second video generation"""

    prompt: str = Field(description="Main text prompt describing the desired video")
    image_sources: List[str] = Field(
        default_factory=list,
        description="Optional reference images (URLs or data URIs)",
    )
    video_sources: List[str] = Field(
        default_factory=list, description="Optional reference videos (URLs)."
    )


class SendFileArgs(BaseModel):
    """Arguments for sending a file to the user via chat."""

    file_path: str = Field(
        description="Absolute or home-relative path to the file (e.g. ~/report.pdf, /tmp/data.csv)"
    )
    caption: str = Field(
        default="", description="Optional caption or description to accompany the file"
    )


class SendScreenshotArgs(BaseModel):
    """Arguments for sending a desktop screenshot to the user via chat."""

    caption: str = Field(
        default="", description="Optional caption to include with the screenshot"
    )


class TakeScreenshotArgs(BaseModel):
    """Arguments for taking a screenshot"""

    question: str = Field(
        default="Describe what is visible on the screen.",
        description="What to look for or describe in the screenshot (e.g. 'what tabs are open in Firefox?')",
    )


class BrowserNavigateArgs(BaseModel):
    url: str = Field(description="URL to navigate to (include https://)")
    wait_for: str = Field(
        default="load",
        description="Wait condition: 'load', 'domcontentloaded', or 'networkidle'",
    )


class BrowserActArgs(BaseModel):
    instruction: str = Field(
        description="Natural language instruction: what to do in the browser. Examples: 'click the first video', 'type cats in the search box and press enter', 'click Subscribe button'"
    )


class BrowserExtractArgs(BaseModel):
    instruction: str = Field(
        description="What to extract from the page. Examples: 'get all video titles', 'get the price', 'list all links in the nav'"
    )


class BrowserClickArgs(BaseModel):
    selector: str = Field(
        description="CSS selector or visible text to click (e.g. 'button#submit', 'text=Login')"
    )


class BrowserTypeArgs(BaseModel):
    selector: str = Field(
        description="CSS selector of the input field (e.g. 'input[name=email]')"
    )
    text: str = Field(description="Text to type into the field")
    clear_first: bool = Field(default=True, description="Clear the field before typing")


class BrowserGetContentArgs(BaseModel):
    selector: str = Field(
        default="",
        description="CSS selector to extract content from, or empty for full page text",
    )
    as_html: bool = Field(
        default=False, description="Return raw HTML instead of visible text"
    )


class BrowserScreenshotArgs(BaseModel):
    selector: str = Field(
        default="",
        description="CSS selector to screenshot a specific element, or empty for full page",
    )
    question: str = Field(
        default="Describe what is visible on this page.",
        description="What to look for in the screenshot",
    )


class BrowserCloseArgs(BaseModel):
    pass


class BrowserConnectArgs(BaseModel):
    cdp_url: str = Field(
        default="http://localhost:9222",
        description="CDP endpoint of the running browser (default: http://localhost:9222)",
    )


class BrowserSwitchTabArgs(BaseModel):
    index: int = Field(description="Tab index to switch to (shown by browser_connect)")


class BrowserEvaluateArgs(BaseModel):
    script: str = Field(
        description="JavaScript code to execute in the current page context. Return values are serialized to JSON."
    )


class SystemProposeArgs(BaseModel):
    """Arguments for proposing a server command"""

    command: str = Field(
        description="The shell command to propose for execution on the Linux server."
    )


class SystemConfirmArgs(BaseModel):
    """Arguments for confirming a pending command"""

    code: str = Field(
        description="The 6-character confirmation code returned by system_propose (e.g. 'A3F9C1')."
    )


class CronCreateArgs(BaseModel):
    """Arguments for creating a cron job"""

    name: str = Field(description="Job name, short and descriptive")
    cron_expr: str = Field(
        description="5-field cron expression, e.g. '*/5 * * * *' for every 5 minutes, '0 8 * * *' for daily at 8am"
    )
    source_type: str = Field(
        description="Source type: 'system_command' (run shell command), 'http_get' (HTTP GET request), 'static' (fixed text)"
    )
    source_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Source parameters. For system_command: {'command': 'free -m'}. For http_get: {'url': 'https://...'}. For static: {'text': 'Hello'}.",
    )
    destination_type: str = Field(
        description="Destination type: 'whatsapp', 'telegram', 'slack', 'none'"
    )
    destination_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Destination parameters. For whatsapp/telegram/slack: {'phone': '+5491...'} or {'chat_id': '...'} or {'channel': '#general'}.",
    )
    message_template: str = Field(
        default="{{output}}",
        description="Message template. Use {{output}} as placeholder for the source result.",
    )
    description: str = Field(default="", description="Optional job description")


class CronDeleteArgs(BaseModel):
    """Arguments for deleting a cron job"""

    job_id: str = Field(description="The job ID to delete")


class CronRunArgs(BaseModel):
    """Arguments for running a cron job immediately"""

    job_id: str = Field(description="The job ID to run now")


AVATAR_ANIMATIONS = ("greeting", "happy", "finger-gun", "dance")

_AVATAR_ANIMATION_SYNONYMS = {
    "wave": "greeting",
    "hello": "greeting",
    "hi": "greeting",
    "greet": "greeting",
    "smile": "happy",
    "cheer": "happy",
    "fingergun": "finger-gun",
    "gun": "finger-gun",
    "dancing": "dance",
}


def normalize_avatar_animation(value: str) -> str:
    """Map what a model actually writes onto the installed animation names."""
    cleaned = str(value).strip().lower().replace(" ", "-").replace("_", "-")
    if cleaned in AVATAR_ANIMATIONS:
        return cleaned
    return _AVATAR_ANIMATION_SYNONYMS.get(cleaned.replace("-", ""), cleaned)


class AvatarPlayAnimationArgs(BaseModel):
    animation: Literal["greeting", "happy", "finger-gun", "dance"] = Field(
        description="The gesture to make: greeting, happy, finger-gun, or dance"
    )

    @field_validator("animation", mode="before")
    @classmethod
    def _normalize(cls, value):
        return normalize_avatar_animation(value) if isinstance(value, str) else value


class AvatarControlWindowArgs(BaseModel):
    action: Literal["show", "hide", "toggle"] = Field(
        description="Window action: show, hide, or toggle"
    )

    @field_validator("action", mode="before")
    @classmethod
    def _normalize(cls, value):
        return str(value).strip().lower() if isinstance(value, str) else value


class SearchDocumentsArgs(BaseModel):
    """Arguments for searching content in documents"""

    query: str = Field(
        description="The search query to find relevant information in documents (e.g., product names, prices, specifications)"
    )
    max_results: int = Field(
        default=5,
        description="Maximum number of relevant results to return",
        ge=1,
        le=10,
    )


class ListStorageFilesArgs(BaseModel):
    """Arguments for listing storage files (no parameters required)"""

    pass


class SearchFAQsArgs(BaseModel):
    """Arguments for searching FAQs"""

    query: str = Field(
        description="The user's question to search in frequently asked questions"
    )
    max_results: int = Field(
        default=5, description="Maximum number of FAQs to return", ge=1, le=10
    )


class SaveMemoryArgs(BaseModel):
    """Arguments for saving a memory fact"""

    content: str = Field(description="Hecho o información relevante a recordar")
    category: str = Field(
        default="General",
        description="Categoría del hecho: Preferencias, Contacto, Historial, etc.",
    )


class RunWorkflowArgs(BaseModel):
    workflow_name: str = Field(description="Name of the configured workflow to execute")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input parameters for the workflow, keyed by parameter name",
    )


class FetchUrlArgs(BaseModel):
    """Arguments for fetching a web page"""

    url: str = Field(description="Full URL to fetch (e.g. https://dolarhoy.com)")


class DownloadFileArgs(BaseModel):
    """Arguments for downloading a file into the workspace"""

    url: str = Field(description="Full HTTP or HTTPS URL to download")
    save_as: Optional[str] = Field(
        default=None,
        description="Output path inside the workspace. If omitted, a filename is inferred automatically.",
    )
    create_dirs: bool = Field(
        default=True,
        description="Create intermediate directories for save_as if they do not exist.",
    )


class WebSearchArgs(BaseModel):
    """Arguments for web search"""

    query: str = Field(description="Search query to look up on the internet")
    max_results: int = Field(
        default=5, ge=1, le=10, description="Number of results to return"
    )


class OrganizeMemoryArgs(BaseModel):
    """Arguments for reorganizing core always-on facts in general.skill.md"""

    new_content: str = Field(
        description="The full consolidated content to replace general.skill.md with."
    )


class SearchMemoryArgs(BaseModel):
    """Arguments for searching the assistant memory"""

    query: str = Field(description="Término a buscar en la memoria del asistente")
    max_results: int = Field(default=5, ge=1, le=10)


class OwnerInsightsArgs(BaseModel):
    """Arguments for owner-level analytics across contacts, conversations and memories"""

    contact_id: Optional[str] = Field(
        default=None, description="Optional contact ID to focus counts on one contact"
    )
    memory_limit: int = Field(
        default=200,
        ge=1,
        le=500,
        description="Max owner memory episodes to scan when aggregating",
    )


class SaveSolutionArgs(BaseModel):
    """Arguments for saving a problem-solution pair"""

    problem: str = Field(description="Description of the problem that was solved")
    solution: str = Field(
        description="The solution or steps taken to resolve the problem"
    )
    context: Optional[str] = Field(
        default=None,
        description="Optional additional context (environment, constraints, related tools, etc.)",
    )
    effective: bool = Field(
        default=True, description="Whether the solution was effective. True by default."
    )


class ReadFileArgs(BaseModel):
    """Arguments for reading a file"""

    path: str = Field(
        description="Path to the file to read (relative to workspace or absolute)"
    )
    offset: int = Field(
        default=1, ge=1, description="Line number to start reading from (1-based)"
    )
    limit: int = Field(
        default=200, ge=1, le=2000, description="Maximum number of lines to read"
    )


class WriteFileArgs(BaseModel):
    """Arguments for writing a file"""

    path: str = Field(
        description="Path to the file to create or overwrite (relative to workspace or absolute)"
    )
    content: str = Field(description="Full content to write to the file")
    create_dirs: bool = Field(
        default=True, description="Create intermediate directories if they do not exist"
    )


class EditFileArgs(BaseModel):
    """Arguments for making a surgical edit to a file"""

    path: str = Field(
        description="Path to the file to edit (relative to workspace or absolute)"
    )
    old_string: str = Field(
        description="The exact string to find and replace in the file"
    )
    new_string: str = Field(description="The string to replace old_string with")


class ListDirectoryArgs(BaseModel):
    """Arguments for listing directory contents"""

    path: str = Field(
        default=".",
        description="Directory path to list (relative to workspace or absolute)",
    )
    show_hidden: bool = Field(
        default=False,
        description="Whether to include hidden files and directories (starting with .)",
    )


class FindFilesArgs(BaseModel):
    """Arguments for finding files by glob pattern"""

    pattern: str = Field(
        description="Glob pattern to match files (e.g. '**/*.py', 'src/**/*.ts', '*.json')"
    )
    path: str = Field(
        default=".",
        description="Base directory to search in (relative to workspace or absolute)",
    )
    max_results: int = Field(
        default=50, ge=1, le=200, description="Maximum number of results to return"
    )


class RunShellArgs(BaseModel):
    """Arguments for running a shell command"""

    command: str = Field(description="Shell command to execute")
    working_dir: str = Field(
        default=".", description="Working directory (relative to workspace)"
    )
    timeout: int = Field(default=30, ge=1, le=300, description="Timeout in seconds")


class GrepFilesArgs(BaseModel):
    """Arguments for searching file contents by pattern"""

    pattern: str = Field(description="Text or regex pattern to search for")
    path: str = Field(
        default=".",
        description="Directory to search in (relative to workspace or absolute)",
    )
    file_glob: str = Field(
        default="*", description="File pattern filter (e.g. '*.py', '*.ts')"
    )
    max_results: int = Field(
        default=50, ge=1, le=200, description="Maximum number of matches to return"
    )
    ignore_case: bool = Field(default=False, description="Case-insensitive search")
    context_lines: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Number of context lines to show before and after each match",
    )


class GitStatusArgs(BaseModel):
    """Arguments for git status (no args needed)"""

    pass


class GitDiffArgs(BaseModel):
    """Arguments for git diff"""

    file_path: str = Field(
        default="", description="Specific file to diff, or empty for full diff"
    )
    staged: bool = Field(
        default=False, description="Show staged changes instead of unstaged"
    )


class GitLogArgs(BaseModel):
    """Arguments for git log"""

    max_entries: int = Field(
        default=10, ge=1, le=50, description="Maximum number of commits to show"
    )
    file_path: str = Field(default="", description="Filter log to a specific file")


class GitCommitArgs(BaseModel):
    """Arguments for git commit"""

    message: str = Field(description="Commit message")
    files: List[str] = Field(
        default=[], description="Specific files to stage, or empty to stage all changes"
    )


class RepoMapArgs(BaseModel):
    """Arguments for generating a repository map"""

    path: str = Field(
        default=".", description="Directory to map (relative to workspace)"
    )
    max_depth: int = Field(default=4, ge=1, le=8, description="Max directory depth")
    include_signatures: bool = Field(
        default=True, description="Include class/function signatures"
    )
    file_glob: str = Field(
        default="*.py",
        description="File types to extract signatures from (e.g. '*.py', '*.ts')",
    )


class CheckCodeArgs(BaseModel):
    """Arguments for checking code for errors and warnings"""

    path: str = Field(
        default=".", description="File or directory to check (relative to workspace)"
    )
    tool: str = Field(
        default="auto",
        description="Checker to use: 'auto', 'pyright', 'mypy', 'tsc', 'eslint'",
    )


class QueryDatabaseArgs(BaseModel):
    """Arguments for querying the database"""

    table: str = Field(
        description="Table name to query. Must be one of the allowed tables configured in the integration."
    )
    columns: List[str] = Field(
        default=["*"],
        description="Column names to retrieve. Use ['*'] for all columns.",
    )
    filters: Optional[str] = Field(
        default=None,
        description=(
            "Optional WHERE clause fragment. Examples: "
            "\"nombre ILIKE '%leche%'\", "
            '"precio < 100", '
            "\"categoria = 'lacteos' AND stock > 0\""
        ),
    )
    limit: int = Field(
        default=20,
        description="Maximum number of rows to return",
        ge=1,
        le=50,
    )


class ExecuteSQLArgs(BaseModel):
    """Arguments for executing a raw SQL statement"""

    sql: str = Field(
        description=(
            "The full SQL statement to execute. "
            "Only tables in the allowed list may be referenced. "
            "DML operations (INSERT, UPDATE, DELETE) are allowed only if not blocked by the integration config."
        )
    )


def _get_sql_integrations(profile):
    """Return list of (slug, SQLDatabaseIntegration) for all active DB integrations."""
    import re as _re

    if not profile or not profile.integrations:
        return []

    results = []
    seen_slugs = set()

    for integration in profile.integrations:
        is_db = integration.type == "database" or integration.name == "sqldatabase"
        if not is_db or not integration.activated:
            continue

        config = integration.config or {}
        connection_string = config.get("connection_string")

        allowed_tables = config.get("allowed_tables")
        if not allowed_tables:
            single = config.get("allowed_table")
            if single:
                allowed_tables = [
                    {"name": single, "description": config.get("table_description", "")}
                ]

        if not connection_string or not allowed_tables:
            continue

        from src.adapters.web.integrations.sqldatabase.sqldatabase import (
            SQLDatabaseIntegration,
        )

        inst = SQLDatabaseIntegration(
            connection_string=connection_string,
            allowed_tables=allowed_tables,
            blocked_keywords=config.get("blocked_keywords", None),
        )

        # Build a unique valid slug from integration name
        base_slug = (
            _re.sub(r"[^a-z0-9]", "_", integration.name.lower()).strip("_") or "db"
        )
        slug = base_slug
        counter = 2
        while slug in seen_slugs:
            slug = f"{base_slug}_{counter}"
            counter += 1
        seen_slugs.add(slug)

        results.append((slug, inst))

    return results


def _get_sql_integration(profile):
    """Deprecated: use _get_sql_integrations. Returns first active DB integration or None."""
    results = _get_sql_integrations(profile)
    return results[0][1] if results else None


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


def _resolve_output_path(path: str, workspace: str):
    """Resolve an output path against workspace, avoiding double-directory issues.

    If the relative path starts with the workspace's own basename
    (e.g. workspace='/home/user/Documentos', path='Documentos/IEST/f.docx')
    the duplicate leading component is stripped before joining.
    Absolute paths are returned as-is.
    """
    from pathlib import Path as _Path

    p = _Path(path).expanduser()
    if p.is_absolute():
        return p
    if workspace:
        ws = _Path(workspace)
        parts = p.parts
        if parts and parts[0] == ws.name:
            p = _Path(*parts[1:]) if len(parts) > 1 else _Path(".")
        return ws / p
    return p


def _find_local_file(file_name: str, workspace: str):
    """Resolve a file_name to an existing local Path.

    Resolution order:
    1. Absolute path (or ~/…) — used as-is.
    2. workspace / file_name  — exact relative path from workspace root.
    3. Recursive search inside workspace by filename (case-insensitive).
       Returns the first match found via os.walk.
    Returns None if nothing is found.
    """
    from pathlib import Path as _Path
    import os as _os

    candidate = _Path(file_name).expanduser()
    if candidate.is_absolute():
        return candidate if candidate.exists() else None

    if workspace:
        direct = _Path(workspace) / file_name
        if direct.exists():
            return direct

        target_name = _Path(file_name).name.lower()
        for root, _dirs, files in _os.walk(workspace):
            for fname in files:
                if fname.lower() == target_name:
                    return _Path(root) / fname

    return None


# ── Browser session state (module-level so it persists across requests) ──────
_browser_state: Dict[str, Any] = {
    "playwright": None,
    "browser": None,  # CDP Browser object (Chrome) or None
    "context": None,  # BrowserContext (Firefox launch_persistent_context) or None
    "page": None,
    "connected": False,  # True when attached to a real browser
    "prev_indices": set(),  # for new-element diffing
    "frames": {},  # element index -> Frame that owns it (iframe support)
    "launched_chrome": False,  # True when we opened the CDP port ourselves
}

# connect/teardown only — two browser_act calls racing on the same page will
# still scramble each other's indices. Key the lock (and _browser_state) by
# profile id if this ever has to serve more than one user at a time.
_browser_lock = asyncio.Lock()

# ── DOM serializer JS (browser-use/Skyvern style) ─────────────────────────────
# Injects sequential [index] markers on every interactive element.
# Pure JS — no extra deps. MIT-compatible technique from browser-use.
_JS_DOM_SERIALIZER = r"""
(startIndex) => {
    const INTERACTIVE_TAGS = new Set(['a','button','input','select','textarea','details','summary']);
    const INTERACTIVE_ROLES = new Set([
        'button','link','checkbox','radio','tab','menuitem','option',
        'combobox','listbox','switch','treeitem','searchbox','spinbutton'
    ]);

    // Reset previous markers
    document.querySelectorAll('[data-ai-idx]').forEach(e => e.removeAttribute('data-ai-idx'));

    let counter = startIndex || 0;
    const indices = [];

    function isVisible(el) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) return false;
        const s = window.getComputedStyle(el);
        return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0';
    }

    function isInteractive(el) {
        const tag = el.tagName.toLowerCase();
        // The iframe box itself is not clickable — its contents are serialized
        // as their own frame, so indexing the container just wastes an action.
        if (tag === 'iframe' || tag === 'frame') return false;
        if (INTERACTIVE_TAGS.has(tag)) return true;
        const role = (el.getAttribute('role') || '').toLowerCase();
        if (role && INTERACTIVE_ROLES.has(role)) return true;
        if (window.getComputedStyle(el).cursor === 'pointer') return true;
        if (el.hasAttribute('onclick') || el.hasAttribute('ng-click') || el.hasAttribute('@click')) return true;
        if (el.tabIndex >= 0 && !['div','span','p'].includes(tag)) return true;
        return false;
    }

    function getAttrs(el) {
        const attrs = [];
        for (const a of ['type','placeholder','aria-label','name','value','href','role','for','title']) {
            const v = el.getAttribute(a);
            if (v) attrs.push(`${a}="${v.slice(0,80).replace(/"/g,"'")}"`);
        }
        return attrs.length ? ' ' + attrs.join(' ') : '';
    }

    function serialize(el, depth) {
        if (!isVisible(el)) return '';
        const tag = el.tagName.toLowerCase();
        if (['script','style','head','meta','link','noscript','svg'].includes(tag)) return '';
        const indent = '  '.repeat(Math.min(depth, 6));
        const lines = [];

        if (isInteractive(el)) {
            const idx = ++counter;
            el.setAttribute('data-ai-idx', String(idx));
            indices.push(idx);
            const attrStr = getAttrs(el);
            const text = (el.innerText || el.value || '').trim().slice(0, 80);
            lines.push(`${indent}[${idx}]<${tag}${attrStr} />`);
            if (text) lines.push(`${indent}  ${text}`);
        } else {
            // Non-interactive: emit visible text if leaf node
            const directText = [...el.childNodes]
                .filter(n => n.nodeType === 3)
                .map(n => n.textContent.trim())
                .join(' ')
                .trim()
                .slice(0, 100);
            if (directText) lines.push(`${indent}${directText}`);
        }

        // Shadow roots hold the real content of web components.
        const kids = el.shadowRoot ? [...el.shadowRoot.children, ...el.children] : [...el.children];
        for (const child of kids) {
            const s = serialize(child, depth + 1);
            if (s) lines.push(s);
        }
        return lines.join('\n');
    }

    const snapshot = document.body ? serialize(document.body, 0) : '';
    return { snapshot, indices };
}
"""

_JS_CLICK_BY_IDX = "([idx]) => { const el = document.querySelector(`[data-ai-idx='${idx}']`); if (!el) return false; el.click(); return true; }"
_JS_FOCUS_BY_IDX = "([idx]) => { const el = document.querySelector(`[data-ai-idx='${idx}']`); if (!el) return false; el.focus(); return true; }"
_JS_EXISTS_BY_IDX = "([idx]) => !!document.querySelector(`[data-ai-idx='${idx}']`)"

# Cleanup lives in main.py's shutdown hook (_close_browser_sessions). An atexit
# handler cannot await anything useful once the loop is gone, so there isn't one.


async def _dom_snapshot(page) -> dict:
    """Serialize every frame of the page into one indexed snapshot.

    Indices are unique across frames; _browser_state["frames"] maps each index
    back to the frame that owns it so actions can target the right document.
    """
    parts: list[str] = []
    indices: list[int] = []
    frames: Dict[int, Any] = {}
    offset = 0

    for frame in page.frames:
        try:
            result = await frame.evaluate(_JS_DOM_SERIALIZER, offset)
        except Exception:
            continue  # cross-origin frame or frame detached mid-walk
        frame_indices = result.get("indices") or []
        snippet = (result.get("snapshot") or "").strip()
        if not snippet:
            continue
        for idx in frame_indices:
            frames[idx] = frame
        indices.extend(frame_indices)
        if frame_indices:
            offset = max(frame_indices)
        if frame is not page.main_frame:
            parts.append(f"[iframe {frame.url[:60]}]\n{snippet}")
        else:
            parts.append(snippet)

    snapshot = "\n".join(parts)
    prev: set = _browser_state["prev_indices"]
    new_indices = set(indices) - prev
    _browser_state["prev_indices"] = set(indices)
    _browser_state["frames"] = frames
    for idx in new_indices:
        snapshot = snapshot.replace(f"[{idx}]", f"*[{idx}]")
    return {"snapshot": snapshot, "indices": indices}


def _clip_snapshot(snapshot: str, limit: int = 7000) -> str:
    """Cut at a line boundary and say so, so the model knows to scroll."""
    if len(snapshot) <= limit:
        return snapshot
    cut = snapshot[:limit].rsplit("\n", 1)[0]
    return cut + "\n… (snapshot truncated — scroll to index the rest of the page)"


def _frame_for(page, idx):
    return _browser_state["frames"].get(idx) or page


async def _execute_actions(page, actions: list[dict]) -> list[str]:
    """Execute LLM-produced actions against the snapshot they were planned on.

    Stops as soon as the page stops matching that snapshot: any index the plan
    references must still be attached, otherwise the click would land on
    whatever re-render took its place.
    """
    results: list[str] = []
    acted = False

    for action in actions[:6]:
        atype = action.get("type", "")
        idx = action.get("index")
        text = action.get("text", "")
        url = action.get("url", "")
        key = action.get("key", "Enter")
        frame = _frame_for(page, idx)
        target = f"[data-ai-idx='{idx}']"

        if idx is not None and acted:
            try:
                if not await frame.evaluate(_JS_EXISTS_BY_IDX, [idx]):
                    results.append(
                        f"stopped before {atype}[{idx}]: page changed, re-run browser_act"
                    )
                    break
            except Exception:
                results.append(
                    f"stopped before {atype}[{idx}]: frame is gone, re-run browser_act"
                )
                break

        try:
            if atype == "click" and idx is not None:
                try:
                    await frame.locator(target).click(timeout=6000)
                except Exception:
                    # Fallback for elements Playwright considers unactionable
                    # (covered by an overlay, zero-size hit target).
                    if not await frame.evaluate(_JS_CLICK_BY_IDX, [idx]):
                        raise
                results.append(f"clicked [{idx}]")

            elif atype == "type" and idx is not None:
                await frame.locator(target).fill(text, timeout=6000)
                results.append(f"typed '{text}' into [{idx}]")

            elif atype == "press" and idx is not None:
                await frame.evaluate(_JS_FOCUS_BY_IDX, [idx])
                await page.keyboard.press(key)
                results.append(f"pressed {key} on [{idx}]")

            elif atype == "press_key":
                await page.keyboard.press(key)
                results.append(f"pressed {key}")

            elif atype == "go_to_url" and url:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                results.append(f"navigated to {url}")
                break  # re-snapshot after navigation

            elif atype == "scroll":
                direction = action.get("direction", "down")
                amount = action.get("amount", 300)
                if idx is not None:
                    await frame.locator(target).scroll_into_view_if_needed()
                else:
                    dy = amount if direction == "down" else -amount
                    await page.evaluate(f"window.scrollBy(0, {dy})")
                results.append(f"scrolled {direction}")

            elif atype == "select" and idx is not None:
                await frame.locator(target).select_option(label=text, timeout=6000)
                results.append(f"selected '{text}' in [{idx}]")

            elif atype == "hover" and idx is not None:
                await frame.locator(target).hover(timeout=6000)
                results.append(f"hovered [{idx}]")

            else:
                results.append(f"skipped unknown action: {atype}")
                continue

            acted = True
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=3000)
            except Exception:
                pass

        except Exception as e:
            results.append(f"error on {atype}[{idx}]: {e}")

    return results


def create_langchain_tools(
    openai_integration,
    profile,
    skill_manager=None,
    store_service=None,
    job_usecases=None,
    shell_output_callback=None,
    client_workspace: str = "",
    approval_callback=None,
    plan_mode: bool = False,
    brain=None,
    avatar_mcp=None,
    auth_token: str = "",
) -> List[StructuredTool]:
    """
    Create LangChain StructuredTool instances with Pydantic validation.

    Args:
        openai_integration: OpenAI integration instance with tool methods
        profile: User profile for context
        skill_manager: Optional skill manager for memory tools
        store_service: Optional store service for image uploads
        job_usecases: Optional job use cases for cron tools
        shell_output_callback: Optional async callable(line: str) -> None.
            When provided, run_shell streams stdout line by line through this
            callback instead of buffering the full output before returning.
        approval_callback: Optional async callable(request_id, tool_name, path, diff) -> bool.
            When provided, edit_file and write_file pause and wait for explicit
            user approval before applying any changes to disk.
        plan_mode: When True, state-mutating tools (edit_file, write_file,
            download_file, run_shell, git_commit) describe what they *would* do without
            actually executing anything.

    Returns:
        List of LangChain StructuredTool instances
    """

    async def search_images_tool(
        search_term: str, max_results: int = 5
    ) -> List[Dict[str, Any]]:
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
            url = result.get("metadata", {}).get("file_url") or result.get(
                "metadata", {}
            ).get("source")
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
            return {
                "found": False,
                "message": "No se encontraron imágenes relacionadas con ese término.",
            }

        MIN_CONFIDENCE = 0.2
        candidates = [
            r for r in results if getattr(r, "confidence", 1.0) >= MIN_CONFIDENCE
        ]
        if not candidates:
            candidates = results  # keep all if all are below threshold

        images = []
        for i, result in enumerate(candidates):
            image_base64 = getattr(result, "image_base64", None)
            if not image_base64:
                continue

            if not _clip_is_relevant(image_base64, search_term):
                logger.info(
                    f"[tools] Image {i} filtered by CLIP (not relevant to '{search_term}')"
                )
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
                images.append(
                    {
                        "image_url": image_url,
                        "page_number": getattr(result, "page_number", None),
                    }
                )

        if not images:
            return {
                "found": False,
                "message": "No se encontraron imágenes relevantes para ese término.",
            }

        return {
            "found": True,
            "images": images,
            "instruction": "Include each image_url literally in your response text.",
        }

    async def analyze_pdf_tool(file_name: str) -> Dict[str, Any]:
        """Analyze PDF content structure"""
        file = _find_file_by_name(profile.files, file_name)
        if not file:
            return {
                "error": f"No se encontró ningún archivo con el nombre '{file_name}' en los archivos del usuario."
            }
        return await openai_integration.analyze_pdf_content(file.url)

    async def extract_text_tool(
        file_name: str, search_term: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract text and images from PDF"""
        file = _find_file_by_name(profile.files, file_name)
        if not file:
            return {
                "error": f"No se encontró ningún archivo con el nombre '{file_name}' en los archivos del usuario."
            }
        return await openai_integration.extract_text_and_images_from_pdf(
            pdf_url=file.url,
            search_term=search_term,
        )

    async def analyze_excel_tool(file_name: str) -> Dict[str, Any]:
        """Analyze Excel file data"""
        import asyncio

        local = _find_local_file(file_name, client_workspace)
        if local:

            def _read_local():
                import openpyxl

                wb = openpyxl.load_workbook(local, data_only=True)
                result = {"sheets": [], "total_sheets": len(wb.sheetnames)}
                for name in wb.sheetnames:
                    ws = wb[name]
                    rows = list(ws.iter_rows(values_only=True))
                    result["sheets"].append(
                        {
                            "name": name,
                            "rows": len(rows),
                            "columns": ws.max_column,
                            "sample": [list(r) for r in rows[:5]],
                        }
                    )
                result["note"] = (
                    "Use modify_excel to edit cells. Sample shows first 5 rows per sheet."
                )
                return result

            try:
                return await asyncio.get_event_loop().run_in_executor(None, _read_local)
            except Exception as e:
                return {"error": str(e)}

        file = _find_file_by_name(profile.files, file_name)
        if not file:
            return {
                "error": f"File '{file_name}' not found on disk or in profile storage."
            }
        return await openai_integration.analyze_excel_file(file.url)

    async def write_excel_tool(
        path: str, sheets: dict, mode: str = "overwrite"
    ) -> Dict[str, Any]:
        """Create or modify an Excel file with structured data."""
        import asyncio
        from pathlib import Path as _Path
        import openpyxl

        resolved = _resolve_output_path(path, client_workspace)

        def _write():
            if mode == "update" and resolved.exists():
                wb = openpyxl.load_workbook(resolved)
            else:
                wb = openpyxl.Workbook()
                wb.remove(wb.active)

            for sheet_name, rows in sheets.items():
                if sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    ws.delete_rows(1, ws.max_row)
                else:
                    ws = wb.create_sheet(title=sheet_name)
                for row in rows:
                    ws.append(row)

            resolved.parent.mkdir(parents=True, exist_ok=True)
            wb.save(resolved)
            total_rows = sum(len(r) for r in sheets.values())
            return {
                "path": str(resolved),
                "sheets": list(sheets.keys()),
                "rows_written": total_rows,
            }

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _write)
        except Exception as e:
            return {"error": str(e)}

    async def read_docx_tool(file_name: str) -> Dict[str, Any]:
        """Read the text content of a Word (.docx) document."""
        import asyncio, io
        from pathlib import Path as _Path

        def _read():
            try:
                from docx import Document
            except ImportError:
                return {
                    "error": "python-docx not installed. Run: pip install python-docx"
                }

            local = _find_local_file(file_name, client_workspace)
            if local:
                doc = Document(str(local))
            else:
                profile_file = _find_file_by_name(profile.files, file_name)
                if not profile_file:
                    return {
                        "error": f"File '{file_name}' not found on disk or in profile storage."
                    }
                import requests as _requests

                resp = _requests.get(profile_file.url, timeout=30)
                resp.raise_for_status()
                doc = Document(io.BytesIO(resp.content))

            sections = []
            for para in doc.paragraphs:
                if para.text.strip():
                    sections.append({"style": para.style.name, "text": para.text})

            tables = []
            for table in doc.tables:
                rows = [[cell.text for cell in row.cells] for row in table.rows]
                tables.append(rows)

            total = len(sections)
            if total > 80:
                sections = sections[:80]
                sections.append(
                    {
                        "style": "Note",
                        "text": f"[... {total - 80} more paragraphs truncated. Ask for a specific section if you need more.]",
                    }
                )
            return {
                "paragraphs": sections,
                "tables": tables,
                "total_paragraphs": total,
                "truncated": total > 80,
            }

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _read)
        except Exception as e:
            return {"error": str(e)}

    async def write_docx_tool(
        path: str, content: str, mode: str = "overwrite"
    ) -> Dict[str, Any]:
        """Create or modify a Word (.docx) document."""
        import asyncio
        from pathlib import Path as _Path

        resolved = _resolve_output_path(path, client_workspace)

        def _write():
            try:
                from docx import Document
                from docx.shared import Pt
            except ImportError:
                return {
                    "error": "python-docx not installed. Run: pip install python-docx"
                }

            if mode == "append" and resolved.exists():
                doc = Document(str(resolved))
            else:
                doc = Document()

            for line in content.splitlines():
                stripped = line.rstrip()
                if stripped.startswith("### "):
                    doc.add_heading(stripped[4:], level=3)
                elif stripped.startswith("## "):
                    doc.add_heading(stripped[3:], level=2)
                elif stripped.startswith("# "):
                    doc.add_heading(stripped[2:], level=1)
                elif stripped.startswith("- ") or stripped.startswith("* "):
                    doc.add_paragraph(stripped[2:], style="List Bullet")
                elif stripped and stripped[0].isdigit() and ". " in stripped[:4]:
                    doc.add_paragraph(stripped.split(". ", 1)[1], style="List Number")
                elif stripped == "":
                    doc.add_paragraph("")
                else:
                    para = doc.add_paragraph()
                    # Handle inline **bold** and *italic*
                    import re as _re

                    parts = _re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", stripped)
                    for part in parts:
                        if part.startswith("**") and part.endswith("**"):
                            run = para.add_run(part[2:-2])
                            run.bold = True
                        elif part.startswith("*") and part.endswith("*"):
                            run = para.add_run(part[1:-1])
                            run.italic = True
                        else:
                            para.add_run(part)

            resolved.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(resolved))
            return {
                "path": str(resolved),
                "paragraphs_written": len(content.splitlines()),
            }

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _write)
        except Exception as e:
            return {"error": str(e)}

    async def modify_excel_tool(
        file_name: str,
        operations: List[dict],
        save_as: str = None,
        re_upload: bool = False,
    ) -> Dict[str, Any]:
        """Download and modify an Excel file with targeted operations, save to workspace."""
        import asyncio, io
        import openpyxl
        from pathlib import Path as _Path

        def _execute():
            output_name = save_as or file_name
            ws_path = _resolve_output_path(output_name, client_workspace)

            local_input = _find_local_file(file_name, client_workspace)
            if local_input:
                # Save output next to the source file by default
                if not save_as and not _Path(output_name).is_absolute():
                    ws_path = local_input.parent / _Path(output_name).name
                wb = openpyxl.load_workbook(local_input)
            else:
                profile_file = _find_file_by_name(profile.files, file_name)
                if not profile_file:
                    return {
                        "error": f"File '{file_name}' not found in profile files or workspace."
                    }
                import requests as _req

                resp = _req.get(profile_file.url, timeout=30)
                resp.raise_for_status()
                wb = openpyxl.load_workbook(io.BytesIO(resp.content))

            applied = []
            errors = []
            for op in operations:
                op_type = op.get("type")
                try:
                    if op_type == "update_cell":
                        ws = wb[op["sheet"]]
                        row, col = int(op["row"]), op["col"]
                        if isinstance(col, str) and col.isalpha():
                            ws[f"{col.upper()}{row}"] = op["value"]
                        else:
                            ws.cell(row=row, column=int(col)).value = op["value"]
                        applied.append(
                            f"update_cell: {op['sheet']}!{col}{row}={op['value']}"
                        )
                    elif op_type == "add_row":
                        ws = wb[op["sheet"]]
                        ws.append(op["data"])
                        applied.append(f"add_row: {op['sheet']}")
                    elif op_type == "delete_row":
                        ws = wb[op["sheet"]]
                        ws.delete_rows(int(op["row"]))
                        applied.append(f"delete_row: {op['sheet']} row {op['row']}")
                    elif op_type == "add_sheet":
                        ws = wb.create_sheet(title=op["name"])
                        for row_data in op.get("rows", []):
                            ws.append(row_data)
                        applied.append(f"add_sheet: {op['name']}")
                    elif op_type == "rename_sheet":
                        wb[op["old_name"]].title = op["new_name"]
                        applied.append(
                            f"rename_sheet: {op['old_name']} -> {op['new_name']}"
                        )
                    elif op_type == "delete_sheet":
                        del wb[op["name"]]
                        applied.append(f"delete_sheet: {op['name']}")
                    else:
                        errors.append(f"Unknown operation type: {op_type}")
                except Exception as ex:
                    errors.append(f"{op_type} failed: {ex}")

            ws_path.parent.mkdir(parents=True, exist_ok=True)
            wb.save(ws_path)
            return {
                "saved_to": str(ws_path),
                "operations_applied": applied,
                "errors": errors,
            }

        result = await asyncio.get_event_loop().run_in_executor(None, _execute)

        if re_upload and "error" not in result:
            saved_path = _Path(result["saved_to"])
            if saved_path.exists():
                import aiohttp

                try:
                    with open(saved_path, "rb") as fh:
                        data = aiohttp.FormData()
                        data.add_field(
                            "files",
                            fh,
                            filename=saved_path.name,
                            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                "http://localhost:8000/profile/files/upload", data=data
                            ) as resp:
                                if resp.status == 200:
                                    result["re_uploaded"] = True
                                else:
                                    result["re_upload_error"] = f"HTTP {resp.status}"
                except Exception as e:
                    result["re_upload_error"] = str(e)

        return result

    async def modify_docx_tool(
        file_name: str,
        replacements: List[dict] = None,
        append: str = None,
        save_as: str = None,
        re_upload: bool = False,
    ) -> Dict[str, Any]:
        """Download and modify a Word document: replace text and/or append content."""
        import asyncio, io
        from pathlib import Path as _Path

        def _execute():
            try:
                from docx import Document
            except ImportError:
                return {
                    "error": "python-docx not installed. Run: pip install python-docx"
                }

            output_name = save_as or file_name
            ws_path = _resolve_output_path(output_name, client_workspace)

            local_input = _find_local_file(file_name, client_workspace)
            if local_input:
                # Save output next to the source file by default
                if not save_as and not _Path(output_name).is_absolute():
                    ws_path = local_input.parent / _Path(output_name).name
                doc = Document(str(local_input))
            else:
                profile_file = _find_file_by_name(profile.files, file_name)
                if not profile_file:
                    return {
                        "error": f"File '{file_name}' not found in profile files or workspace."
                    }
                import requests as _req

                resp = _req.get(profile_file.url, timeout=30)
                resp.raise_for_status()
                doc = Document(io.BytesIO(resp.content))

            applied = []

            if replacements:
                for rep in replacements:
                    old, new = rep.get("old", ""), rep.get("new", "")
                    count = 0
                    for para in doc.paragraphs:
                        if old in para.text:
                            for run in para.runs:
                                if old in run.text:
                                    run.text = run.text.replace(old, new)
                                    count += 1
                    for table in doc.tables:
                        for row in table.rows:
                            for cell in row.cells:
                                for para in cell.paragraphs:
                                    if old in para.text:
                                        for run in para.runs:
                                            if old in run.text:
                                                run.text = run.text.replace(old, new)
                                                count += 1
                    applied.append(f"replace '{old}' -> '{new}' ({count} occurrences)")

            if append:
                import re as _re

                for line in append.splitlines():
                    stripped = line.rstrip()
                    if stripped.startswith("### "):
                        doc.add_heading(stripped[4:], level=3)
                    elif stripped.startswith("## "):
                        doc.add_heading(stripped[3:], level=2)
                    elif stripped.startswith("# "):
                        doc.add_heading(stripped[2:], level=1)
                    elif stripped.startswith("- ") or stripped.startswith("* "):
                        doc.add_paragraph(stripped[2:], style="List Bullet")
                    elif stripped and stripped[0].isdigit() and ". " in stripped[:4]:
                        doc.add_paragraph(
                            stripped.split(". ", 1)[1], style="List Number"
                        )
                    elif not stripped:
                        doc.add_paragraph("")
                    else:
                        para = doc.add_paragraph()
                        parts = _re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", stripped)
                        for part in parts:
                            if part.startswith("**") and part.endswith("**"):
                                run = para.add_run(part[2:-2])
                                run.bold = True
                            elif part.startswith("*") and part.endswith("*"):
                                run = para.add_run(part[1:-1])
                                run.italic = True
                            else:
                                para.add_run(part)
                applied.append(f"appended {len(append.splitlines())} lines")

            ws_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(ws_path))
            return {"saved_to": str(ws_path), "operations_applied": applied}

        result = await asyncio.get_event_loop().run_in_executor(None, _execute)

        if re_upload and "error" not in result:
            saved_path = _Path(result["saved_to"])
            if saved_path.exists():
                import aiohttp

                try:
                    with open(saved_path, "rb") as fh:
                        data = aiohttp.FormData()
                        data.add_field(
                            "files",
                            fh,
                            filename=saved_path.name,
                            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                "http://localhost:8000/profile/files/upload", data=data
                            ) as resp:
                                if resp.status == 200:
                                    result["re_uploaded"] = True
                                else:
                                    result["re_upload_error"] = f"HTTP {resp.status}"
                except Exception as e:
                    result["re_upload_error"] = str(e)

        return result

    # ── PowerPoint tools ──────────────────────────────────────────────────────

    async def read_pptx_tool(file_name: str) -> Dict[str, Any]:
        """Read content of a PowerPoint (.pptx) file."""
        import asyncio, io

        def _read():
            try:
                from pptx import Presentation as _Prs
            except ImportError:
                return {
                    "error": "python-pptx not installed. Run: pip install python-pptx"
                }

            local = _find_local_file(file_name, client_workspace)
            if local:
                prs = _Prs(str(local))
            else:
                profile_file = _find_file_by_name(profile.files, file_name)
                if not profile_file:
                    return {
                        "error": f"File '{file_name}' not found in profile files or workspace."
                    }
                import requests as _req

                resp = _req.get(profile_file.url, timeout=30)
                resp.raise_for_status()
                prs = _Prs(io.BytesIO(resp.content))

            slides_data = []
            for i, slide in enumerate(prs.slides, 1):
                title = ""
                body_lines = []
                notes = ""
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        if shape.shape_type == 13:
                            continue
                        text = shape.text_frame.text.strip()
                        if not text:
                            continue
                        if shape.name.lower().startswith("title") or (
                            i == 1 and not title
                        ):
                            title = text
                        else:
                            body_lines.extend(
                                [ln.strip() for ln in text.splitlines() if ln.strip()]
                            )
                if slide.has_notes_slide:
                    notes = slide.notes_slide.notes_text_frame.text.strip()
                slides_data.append(
                    {"slide": i, "title": title, "body": body_lines, "notes": notes}
                )

            return {"slides": slides_data, "total_slides": len(slides_data)}

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _read)
        except Exception as e:
            return {"error": str(e)}

    async def write_pptx_tool(path: str, slides: List[dict]) -> Dict[str, Any]:
        """Create a new PowerPoint presentation from slide data."""
        import asyncio

        resolved = _resolve_output_path(path, client_workspace)

        def _write():
            try:
                from pptx import Presentation as _Prs
                from pptx.util import Inches, Pt
            except ImportError:
                return {
                    "error": "python-pptx not installed. Run: pip install python-pptx"
                }

            prs = _Prs()
            slide_layout_title_content = prs.slide_layouts[1]
            slide_layout_title_only = prs.slide_layouts[5]

            for slide_data in slides:
                title_text = slide_data.get("title", "")
                body_lines = slide_data.get("body", [])
                notes_text = slide_data.get("notes", "")

                layout = (
                    slide_layout_title_content
                    if body_lines
                    else slide_layout_title_only
                )
                slide = prs.slides.add_slide(layout)

                if slide.shapes.title:
                    slide.shapes.title.text = title_text

                if body_lines and len(slide.placeholders) > 1:
                    tf = slide.placeholders[1].text_frame
                    tf.clear()
                    for i, line in enumerate(body_lines):
                        if i == 0:
                            tf.paragraphs[0].text = line
                        else:
                            tf.add_paragraph().text = line

                if notes_text:
                    slide.notes_slide.notes_text_frame.text = notes_text

            resolved.parent.mkdir(parents=True, exist_ok=True)
            prs.save(str(resolved))
            return {"path": str(resolved), "slides_written": len(slides)}

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _write)
        except Exception as e:
            return {"error": str(e)}

    async def modify_pptx_tool(
        file_name: str,
        replacements: List[dict] = None,
        add_slides: List[dict] = None,
        save_as: str = None,
        re_upload: bool = False,
    ) -> Dict[str, Any]:
        """Modify an existing PowerPoint file."""
        import asyncio, io

        def _modify():
            try:
                from pptx import Presentation as _Prs
                from pptx.util import Inches
            except ImportError:
                return {
                    "error": "python-pptx not installed. Run: pip install python-pptx"
                }

            output_name = save_as or file_name
            ws_path = _resolve_output_path(output_name, client_workspace)

            local = _find_local_file(file_name, client_workspace)
            if local:
                if not save_as:
                    ws_path = local.parent / output_name
                prs = _Prs(str(local))
            else:
                profile_file = _find_file_by_name(profile.files, file_name)
                if not profile_file:
                    return {
                        "error": f"File '{file_name}' not found in profile files or workspace."
                    }
                import requests as _req

                resp = _req.get(profile_file.url, timeout=30)
                resp.raise_for_status()
                prs = _Prs(io.BytesIO(resp.content))

            applied = []

            # Text replacements across all slides
            if replacements:
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if not shape.has_text_frame:
                            continue
                        for para in shape.text_frame.paragraphs:
                            for run in para.runs:
                                for rep in replacements:
                                    if rep.get("old") and rep["old"] in run.text:
                                        run.text = run.text.replace(
                                            rep["old"], rep.get("new", "")
                                        )
                                        applied.append(
                                            f"replaced: '{rep['old']}' → '{rep.get('new', '')}'"
                                        )

            # Add new slides
            if add_slides:
                layout_content = prs.slide_layouts[1]
                layout_blank = prs.slide_layouts[5]
                for slide_data in add_slides:
                    body_lines = slide_data.get("body", [])
                    layout = layout_content if body_lines else layout_blank
                    slide = prs.slides.add_slide(layout)
                    if slide.shapes.title:
                        slide.shapes.title.text = slide_data.get("title", "")
                    if body_lines and len(slide.placeholders) > 1:
                        tf = slide.placeholders[1].text_frame
                        tf.clear()
                        for i, line in enumerate(body_lines):
                            if i == 0:
                                tf.paragraphs[0].text = line
                            else:
                                tf.add_paragraph().text = line
                    notes_text = slide_data.get("notes", "")
                    if notes_text:
                        slide.notes_slide.notes_text_frame.text = notes_text
                    applied.append(f"added slide: '{slide_data.get('title', '')}'")

            ws_path.parent.mkdir(parents=True, exist_ok=True)
            prs.save(str(ws_path))
            result = {"path": str(ws_path), "applied": applied}

            if re_upload and store_service:
                try:
                    import aiohttp, asyncio as _aio

                    async def _up():
                        async with aiohttp.ClientSession() as session:
                            data = aiohttp.FormData()
                            data.add_field(
                                "file", open(ws_path, "rb"), filename=ws_path.name
                            )
                            async with session.post(
                                "http://localhost:8000/profile/files/upload", data=data
                            ) as resp:
                                if resp.status == 200:
                                    result["re_uploaded"] = True
                                else:
                                    result["re_upload_error"] = f"HTTP {resp.status}"

                    _aio.get_event_loop().run_until_complete(_up())
                except Exception as e:
                    result["re_upload_error"] = str(e)

            return result

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _modify)
        except Exception as e:
            return {"error": str(e)}

    # ── Image insertion tools ─────────────────────────────────────────────────

    def _fetch_image_to_tempfile(image_source: str) -> "tuple[str, bool]":
        """Resolve image_source (path / URL / base64) to a temp file path.

        Returns (path, is_temp) where is_temp=True means the caller must delete it.
        """
        import tempfile, os, base64 as _b64
        from pathlib import Path as _P

        if image_source.startswith("data:"):
            # base64 data URI  →  data:image/png;base64,<data>
            header, data = image_source.split(",", 1)
            ext = header.split(";")[0].split("/")[-1]
            tmp = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
            tmp.write(_b64.b64decode(data))
            tmp.close()
            return tmp.name, True

        if image_source.startswith("http://") or image_source.startswith("https://"):
            import requests as _req

            resp = _req.get(image_source, timeout=30)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "image/png").split(";")[0]
            ext = content_type.split("/")[-1]
            tmp = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
            tmp.write(resp.content)
            tmp.close()
            return tmp.name, True

        # Local path — resolve against workspace or absolute
        local = _find_local_file(image_source, client_workspace)
        if local:
            return str(local), False
        if _P(image_source).exists():
            return image_source, False
        raise FileNotFoundError(f"Image not found: {image_source}")

    async def insert_image_docx_tool(
        file_name: str,
        image_source: str,
        position: str = "end",
        width_cm: float = None,
        caption: str = None,
        save_as: str = None,
        re_upload: bool = False,
    ) -> Dict[str, Any]:
        """Insert an image into an existing Word (.docx) document."""
        import asyncio, io, os
        from pathlib import Path as _Path

        def _execute():
            try:
                from docx import Document
                from docx.shared import Cm
            except ImportError:
                return {
                    "error": "python-docx not installed. Run: pip install python-docx"
                }

            output_name = save_as or file_name
            ws_path = _resolve_output_path(output_name, client_workspace)

            local_input = _find_local_file(file_name, client_workspace)
            if local_input:
                if not save_as:
                    ws_path = local_input.parent / _Path(output_name).name
                doc = Document(str(local_input))
            else:
                profile_file = _find_file_by_name(profile.files, file_name)
                if not profile_file:
                    return {
                        "error": f"File '{file_name}' not found in profile files or workspace."
                    }
                import requests as _req

                resp = _req.get(profile_file.url, timeout=30)
                resp.raise_for_status()
                doc = Document(io.BytesIO(resp.content))

            img_path, is_temp = _fetch_image_to_tempfile(image_source)
            try:
                width = Cm(width_cm) if width_cm else None

                if position == "end":
                    doc.add_picture(img_path, width=width)
                    if caption:
                        doc.add_paragraph(caption)
                elif position == "start":
                    # Insert before first paragraph
                    from docx.oxml.ns import qn
                    from docx.oxml import OxmlElement
                    import copy

                    # Use a temp doc to get the picture XML
                    tmp_doc = Document()
                    tmp_doc.add_picture(img_path, width=width)
                    pic_para = tmp_doc.paragraphs[-1]._element
                    doc.paragraphs[0]._element.addprevious(copy.deepcopy(pic_para))
                    if caption:
                        cap_para = OxmlElement("w:p")
                        cap_run = OxmlElement("w:r")
                        cap_text = OxmlElement("w:t")
                        cap_text.text = caption
                        cap_run.append(cap_text)
                        cap_para.append(cap_run)
                        pic_para.addnext(cap_para)
                else:
                    # Insert after first paragraph whose text contains `position`
                    inserted = False
                    import copy
                    from docx import Document as _Doc

                    tmp_doc = _Doc()
                    tmp_doc.add_picture(img_path, width=width)
                    pic_element = copy.deepcopy(tmp_doc.paragraphs[-1]._element)
                    for para in doc.paragraphs:
                        if position in para.text:
                            para._element.addnext(pic_element)
                            if caption:
                                from docx.oxml import OxmlElement as _OE

                                cap_para = _OE("w:p")
                                cap_run = _OE("w:r")
                                cap_text = _OE("w:t")
                                cap_text.text = caption
                                cap_run.append(cap_text)
                                cap_para.append(cap_run)
                                pic_element.addnext(cap_para)
                            inserted = True
                            break
                    if not inserted:
                        return {
                            "error": f"No paragraph found containing text: '{position}'"
                        }

                ws_path.parent.mkdir(parents=True, exist_ok=True)
                doc.save(str(ws_path))
                return {
                    "saved_to": str(ws_path),
                    "image_inserted": True,
                    "position": position,
                }
            finally:
                if is_temp:
                    os.unlink(img_path)

        result = await asyncio.get_event_loop().run_in_executor(None, _execute)

        if re_upload and "error" not in result:
            saved_path = _Path(result["saved_to"])
            if saved_path.exists():
                import aiohttp

                try:
                    with open(saved_path, "rb") as fh:
                        data = aiohttp.FormData()
                        data.add_field(
                            "files",
                            fh,
                            filename=saved_path.name,
                            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                "http://localhost:8000/profile/files/upload", data=data
                            ) as resp:
                                result["re_uploaded"] = resp.status == 200
                except Exception as e:
                    result["re_upload_error"] = str(e)
        return result

    async def insert_image_excel_tool(
        file_name: str,
        image_source: str,
        sheet: str,
        cell: str = "A1",
        width_cm: float = None,
        height_cm: float = None,
        save_as: str = None,
        re_upload: bool = False,
    ) -> Dict[str, Any]:
        """Insert an image into an Excel (.xlsx) file at a specific cell."""
        import asyncio, io, os
        from pathlib import Path as _Path

        def _execute():
            try:
                import openpyxl
                from openpyxl.drawing.image import Image as XLImage
            except ImportError:
                return {"error": "openpyxl not installed. Run: pip install openpyxl"}

            output_name = save_as or file_name
            ws_path = _resolve_output_path(output_name, client_workspace)

            local_input = _find_local_file(file_name, client_workspace)
            if local_input:
                if not save_as:
                    ws_path = local_input.parent / _Path(output_name).name
                wb = openpyxl.load_workbook(str(local_input))
            else:
                profile_file = _find_file_by_name(profile.files, file_name)
                if not profile_file:
                    return {
                        "error": f"File '{file_name}' not found in profile files or workspace."
                    }
                import requests as _req

                resp = _req.get(profile_file.url, timeout=30)
                resp.raise_for_status()
                wb = openpyxl.load_workbook(io.BytesIO(resp.content))

            if sheet not in wb.sheetnames:
                return {
                    "error": f"Sheet '{sheet}' not found. Available: {wb.sheetnames}"
                }

            img_path, is_temp = _fetch_image_to_tempfile(image_source)
            try:
                img = XLImage(img_path)
                if width_cm:
                    img.width = int(width_cm * 37.795)  # cm → pixels at 96dpi
                if height_cm:
                    img.height = int(height_cm * 37.795)
                elif width_cm and not height_cm:
                    # scale height proportionally
                    from PIL import Image as PILImage

                    with PILImage.open(img_path) as pil_img:
                        orig_w, orig_h = pil_img.size
                    if orig_w:
                        img.height = int(img.width * orig_h / orig_w)

                wb[sheet].add_image(img, cell)
                ws_path.parent.mkdir(parents=True, exist_ok=True)
                wb.save(str(ws_path))
                return {
                    "saved_to": str(ws_path),
                    "image_inserted": True,
                    "sheet": sheet,
                    "cell": cell,
                }
            finally:
                if is_temp:
                    os.unlink(img_path)

        result = await asyncio.get_event_loop().run_in_executor(None, _execute)

        if re_upload and "error" not in result:
            saved_path = _Path(result["saved_to"])
            if saved_path.exists():
                import aiohttp

                try:
                    with open(saved_path, "rb") as fh:
                        data = aiohttp.FormData()
                        data.add_field(
                            "files",
                            fh,
                            filename=saved_path.name,
                            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                "http://localhost:8000/profile/files/upload", data=data
                            ) as resp:
                                result["re_uploaded"] = resp.status == 200
                except Exception as e:
                    result["re_upload_error"] = str(e)
        return result

    async def insert_image_pptx_tool(
        file_name: str,
        image_source: str,
        slide_number: int,
        left_cm: float = 2.0,
        top_cm: float = 4.0,
        width_cm: float = None,
        height_cm: float = None,
        save_as: str = None,
        re_upload: bool = False,
    ) -> Dict[str, Any]:
        """Insert an image into a specific slide of a PowerPoint (.pptx) file."""
        import asyncio, io, os
        from pathlib import Path as _Path

        def _execute():
            try:
                from pptx import Presentation as _Prs
                from pptx.util import Cm
            except ImportError:
                return {
                    "error": "python-pptx not installed. Run: pip install python-pptx"
                }

            output_name = save_as or file_name
            ws_path = _resolve_output_path(output_name, client_workspace)

            local_input = _find_local_file(file_name, client_workspace)
            if local_input:
                if not save_as:
                    ws_path = local_input.parent / _Path(output_name).name
                prs = _Prs(str(local_input))
            else:
                profile_file = _find_file_by_name(profile.files, file_name)
                if not profile_file:
                    return {
                        "error": f"File '{file_name}' not found in profile files or workspace."
                    }
                import requests as _req

                resp = _req.get(profile_file.url, timeout=30)
                resp.raise_for_status()
                prs = _Prs(io.BytesIO(resp.content))

            total = len(prs.slides)
            if slide_number < 1 or slide_number > total:
                return {
                    "error": f"slide_number {slide_number} out of range. Presentation has {total} slides."
                }

            slide = prs.slides[slide_number - 1]
            img_path, is_temp = _fetch_image_to_tempfile(image_source)
            try:
                left = Cm(left_cm)
                top = Cm(top_cm)
                width = Cm(width_cm) if width_cm else None
                height = Cm(height_cm) if height_cm else None
                slide.shapes.add_picture(
                    img_path, left, top, width=width, height=height
                )
                ws_path.parent.mkdir(parents=True, exist_ok=True)
                prs.save(str(ws_path))
                return {
                    "saved_to": str(ws_path),
                    "image_inserted": True,
                    "slide": slide_number,
                }
            finally:
                if is_temp:
                    os.unlink(img_path)

        result = await asyncio.get_event_loop().run_in_executor(None, _execute)

        if re_upload and "error" not in result:
            saved_path = _Path(result["saved_to"])
            if saved_path.exists():
                import aiohttp

                try:
                    with open(saved_path, "rb") as fh:
                        data = aiohttp.FormData()
                        data.add_field(
                            "files",
                            fh,
                            filename=saved_path.name,
                            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        )
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                "http://localhost:8000/profile/files/upload", data=data
                            ) as resp:
                                result["re_uploaded"] = resp.status == 200
                except Exception as e:
                    result["re_upload_error"] = str(e)
        return result

    # ─────────────────────────────────────────────────────────────────────────

    async def describe_image_tool(image_source: str) -> str:
        """Describe an image from URL, local file path, or file URI."""
        import aiohttp
        import base64 as b64
        import os
        from pathlib import Path
        from urllib.parse import urlparse, unquote

        max_bytes = 8 * 1024 * 1024

        try:
            source = (image_source or "").strip()
            if not source:
                return "Error fetching image source: image_source is required"

            parsed = urlparse(source)
            if parsed.scheme in ("", "file"):
                if parsed.scheme == "file":
                    file_path = Path(unquote(parsed.path)).expanduser()
                else:
                    local = _find_local_file(source, client_workspace)
                    file_path = local or Path(source).expanduser()

                if not file_path.exists() or not file_path.is_file():
                    return f"Error fetching image source: file not found: {file_path}"

                file_size = os.path.getsize(file_path)
                if file_size > max_bytes:
                    return f"Error fetching image source: file too large ({file_size} bytes), max allowed is {max_bytes}"

                with open(file_path, "rb") as f:
                    image_bytes = f.read()
            elif parsed.scheme in ("http", "https"):
                timeout = aiohttp.ClientTimeout(total=20)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(source) as resp:
                        resp.raise_for_status()
                        content_length = int(
                            resp.headers.get("Content-Length", "0") or 0
                        )
                        if content_length and content_length > max_bytes:
                            return f"Error fetching image source: remote file too large ({content_length} bytes), max allowed is {max_bytes}"
                        image_bytes = await resp.read()
                        if len(image_bytes) > max_bytes:
                            return f"Error fetching image source: remote file too large ({len(image_bytes)} bytes), max allowed is {max_bytes}"
            else:
                return (
                    f"Error fetching image source: unsupported scheme '{parsed.scheme}'"
                )

            image_base64 = b64.b64encode(image_bytes).decode()
            return await openai_integration.describe_image_from_base64(image_base64)
        except Exception as e:
            return f"Error fetching image source: {e}"

    def _as_data_url(source: str, default_mime: str) -> str:
        """Normalize source into a data URL when possible."""
        import base64 as _b64
        import mimetypes as _mimetypes
        from pathlib import Path as _Path

        if source.startswith("data:"):
            return source
        if source.startswith("http://") or source.startswith("https://"):
            return source

        local = _find_local_file(source, client_workspace)
        local_path = local or (_Path(source) if _Path(source).exists() else None)
        if local_path is None:
            raise FileNotFoundError(f"Media source not found: {source}")

        mime = _mimetypes.guess_type(str(local_path))[0] or default_mime
        with open(local_path, "rb") as f:
            encoded = _b64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime};base64,{encoded}"

    async def _upload_generated_asset(
        file_bytes: bytes, filename: str
    ) -> Dict[str, Any]:
        """Upload generated media to store_service when available."""
        import io
        from uuid import uuid4

        if not store_service:
            return {"uploaded": False, "reason": "store_service unavailable"}

        key = store_service.put_object(
            file=io.BytesIO(file_bytes),
            user_file=profile.user_id,
            filename=filename,
            size=len(file_bytes),
            object_id=uuid4().hex[:12],
        )
        return {
            "uploaded": True,
            "storage_key": key,
            "url": store_service.generate_url(key),
        }

    def _get_generation_client(kind: str):
        """Return an OpenAI-compatible client and model for image/video generation."""
        from openai import AsyncOpenAI

        config_service = getattr(openai_integration, "_config_service", None)
        specific_cfg = (
            getattr(config_service, f"{kind}_generation_config", None)
            if config_service
            else None
        )
        fallback_cfg = openai_integration._config_service.openai_config

        if (
            specific_cfg
            and specific_cfg.api_key
            and specific_cfg.base_url
            and specific_cfg.model
        ):
            return {
                "client": AsyncOpenAI(
                    api_key=specific_cfg.api_key, base_url=specific_cfg.base_url
                ),
                "model": specific_cfg.model,
                "base_url": specific_cfg.base_url,
                "kind": kind,
                "uses_fallback": False,
            }

        return {
            "client": openai_integration.client,
            "model": openai_integration.model,
            "base_url": fallback_cfg.base_url,
            "kind": kind,
            "uses_fallback": True,
        }

    async def generate_image_tool(
        prompt: str,
        image_sources: List[str] = None,
        video_sources: List[str] = None,
        size: str = "1024x1024",
    ) -> Dict[str, Any]:
        """Generate image from text, text+images, or text+videos."""
        import base64 as _b64

        image_sources = image_sources or []
        video_sources = video_sources or []

        input_payload: List[Dict[str, Any]] = [
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]}
        ]
        user_content = input_payload[0]["content"]

        for src in image_sources:
            normalized = _as_data_url(src, "image/png")
            user_content.append({"type": "input_image", "image_url": normalized})

        for src in video_sources:
            normalized = _as_data_url(src, "video/mp4")
            user_content.append({"type": "input_video", "video_url": normalized})

        client_info = _get_generation_client("image")

        try:
            response = await client_info["client"].responses.create(
                model=client_info["model"],
                input=input_payload,
                modalities=["image"],
                image={"size": size},
            )
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "hint": "Current provider/model may not support image generation via Responses API.",
            }

        response_dump = response.model_dump() if hasattr(response, "model_dump") else {}
        image_b64 = None
        image_url = None
        for item in (
            response_dump.get("output", []) if isinstance(response_dump, dict) else []
        ):
            for content in item.get("content", []) if isinstance(item, dict) else []:
                if content.get("type") == "output_image":
                    image_b64 = content.get("b64_json") or image_b64
                    image_url = content.get("url") or image_url

        result: Dict[str, Any] = {
            "ok": True,
            "provider_model": client_info["model"],
            "provider_base_url": client_info["base_url"],
            "uses_fallback_provider": client_info["uses_fallback"],
            "prompt": prompt,
            "size": size,
            "image_url": image_url,
            "has_b64": bool(image_b64),
        }

        if image_b64:
            file_bytes = _b64.b64decode(image_b64)
            upload = await _upload_generated_asset(file_bytes, "generated_image.png")
            result["stored"] = upload
            if upload.get("uploaded"):
                result["deliver_to_user_url"] = upload.get("url")

        if not image_b64 and not image_url:
            result["warning"] = "No image payload found in response."
            result["raw_response"] = response_dump

        return result

    async def generate_video_tool(
        prompt: str,
        image_sources: List[str] = None,
        video_sources: List[str] = None,
    ) -> Dict[str, Any]:
        """Generate a 6-second normal-quality video from multimodal input."""
        import base64 as _b64

        image_sources = image_sources or []
        video_sources = video_sources or []

        input_payload: List[Dict[str, Any]] = [
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]}
        ]
        user_content = input_payload[0]["content"]

        for src in image_sources:
            normalized = _as_data_url(src, "image/png")
            user_content.append({"type": "input_image", "image_url": normalized})

        for src in video_sources:
            normalized = _as_data_url(src, "video/mp4")
            user_content.append({"type": "input_video", "video_url": normalized})

        client_info = _get_generation_client("video")

        try:
            response = await client_info["client"].responses.create(
                model=client_info["model"],
                input=input_payload,
                modalities=["video"],
                video={"duration": 6, "quality": "standard"},
            )
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "hint": "Current provider/model may not support video generation via Responses API.",
            }

        response_dump = response.model_dump() if hasattr(response, "model_dump") else {}
        video_b64 = None
        video_url = None
        for item in (
            response_dump.get("output", []) if isinstance(response_dump, dict) else []
        ):
            for content in item.get("content", []) if isinstance(item, dict) else []:
                if content.get("type") == "output_video":
                    video_b64 = content.get("b64_json") or video_b64
                    video_url = content.get("url") or video_url

        result: Dict[str, Any] = {
            "ok": True,
            "provider_model": client_info["model"],
            "provider_base_url": client_info["base_url"],
            "uses_fallback_provider": client_info["uses_fallback"],
            "prompt": prompt,
            "duration_seconds": 6,
            "quality": "standard",
            "video_url": video_url,
            "has_b64": bool(video_b64),
        }

        if video_b64:
            file_bytes = _b64.b64decode(video_b64)
            upload = await _upload_generated_asset(file_bytes, "generated_video.mp4")
            result["stored"] = upload
            if upload.get("uploaded"):
                result["deliver_to_user_url"] = upload.get("url")

        if not video_b64 and not video_url:
            result["warning"] = "No video payload found in response."
            result["raw_response"] = response_dump

        return result

    async def _capture_screen() -> str:
        """
        Capture the desktop to a temp PNG file and return its path.
        The caller is responsible for deleting the file after use.
        Returns the file path on success, or an error string starting with 'ERROR:'.
        """
        import asyncio
        import tempfile
        import os

        is_wayland = bool(os.environ.get("WAYLAND_DISPLAY"))
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        path = tmp.name

        _wlroots_compositors = {"sway", "wayfire", "river", "hyprland", "labwc"}
        grim_likely_works = any(d in desktop for d in _wlroots_compositors)

        if is_wayland and grim_likely_works:
            cmds = [
                ["grim", path],
                ["gnome-screenshot", "-f", path],
                ["spectacle", "-b", "-o", path],
                ["scrot", path],
                ["import", "-window", "root", path],
            ]
        elif is_wayland:
            cmds = [
                ["scrot", path],
                ["import", "-window", "root", path],
                ["gnome-screenshot", "-f", path],
                ["spectacle", "-b", "-o", path],
                ["grim", path],
            ]
        else:
            cmds = [
                ["scrot", path],
                ["maim", path],
                ["import", "-window", "root", path],
                ["gnome-screenshot", "-f", path],
                ["spectacle", "-b", "-o", path],
            ]

        uid = os.getuid()
        env = {
            **os.environ,
            "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY", "wayland-0"),
            "DISPLAY": os.environ.get("DISPLAY", ":0"),
            "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{uid}"),
        }

        for cmd in cmds:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
                await asyncio.wait_for(proc.wait(), timeout=10)
                if proc.returncode == 0 and os.path.getsize(path) > 0:
                    return path
            except (FileNotFoundError, asyncio.TimeoutError):
                continue

        os.unlink(path)
        hint = (
            "grim (Wayland), gnome-screenshot, or spectacle"
            if is_wayland
            else "scrot, maim, imagemagick, gnome-screenshot, or spectacle"
        )
        return f"ERROR: Could not take a screenshot. Running on {'Wayland' if is_wayland else 'X11'}. Install: {hint}"

    async def take_screenshot_tool(
        question: str = "Describe what is visible on the screen.",
    ) -> str:
        """Capture the desktop screen and describe its contents using vision AI."""
        import base64 as b64
        import os

        result = await _capture_screen()
        if result.startswith("ERROR:"):
            return result.removeprefix("ERROR: ")

        path = result
        try:
            with open(path, "rb") as f:
                image_base64 = b64.b64encode(f.read()).decode()
        finally:
            os.unlink(path)

        prompt = f"Screenshot of the user's desktop. {question}"
        try:
            return await openai_integration.describe_image_from_base64(
                image_base64, prompt=prompt
            )
        except Exception as e:
            return f"Screenshot captured but vision analysis failed: {e}"

    async def send_screenshot_tool(caption: str = "") -> str:
        """
        Capture the desktop screen and send it directly to the user via chat
        (WhatsApp, Telegram, Slack, etc.).

        Use this tool whenever the user asks to receive a screenshot, capture,
        or photo of the screen. It uploads the image to storage and returns a
        URL that will be delivered as an image message in the chat.

        Args:
            caption: Optional caption to include with the screenshot.
        """
        import io
        import os
        from uuid import uuid4

        if not store_service:
            return "Storage service is not available. Cannot send screenshot."

        result = await _capture_screen()
        if result.startswith("ERROR:"):
            return result.removeprefix("ERROR: ")

        path = result
        try:
            with open(path, "rb") as f:
                file_bytes = f.read()
        finally:
            os.unlink(path)

        try:
            filename = f"screenshot_{uuid4().hex[:8]}.png"
            key = store_service.put_object(
                file=io.BytesIO(file_bytes),
                user_file=profile.user_id,
                filename=filename,
                size=len(file_bytes),
                object_id=uuid4().hex[:12],
            )
            url = store_service.generate_url(key)
            result_msg = f"Screenshot ready. URL: {url}"
            if caption:
                result_msg += f"\nCaption: {caption}"
            result_msg += "\nInclude this URL in your response so it gets delivered as an image to the user."
            return result_msg
        except Exception as e:
            return f"Screenshot captured but upload failed: {e}"

    async def send_file_tool(file_path: str, caption: str = "") -> str:
        """
        Upload a local file to storage and return its public URL so it can be
        sent to the user in the current chat (WhatsApp, Telegram, Slack, etc.).

        Supports any file type: images (png, jpg, gif…), documents (pdf, xlsx,
        csv, txt, docx…), archives (zip, gz…), audio/video (mp3, mp4, ogg…).

        After this tool returns, include the URL literally in your reply text —
        the chat platform will automatically deliver it as a file/image message.

        Args:
            file_path: Absolute or home-relative path to the file to send.
                       Supports ~ expansion (e.g. ~/Documents/report.pdf).
            caption:   Optional caption / description to accompany the file.
        """
        import io
        import mimetypes
        import os
        from uuid import uuid4

        path = os.path.expanduser(file_path)
        if not os.path.isfile(path):
            return f"File not found: {file_path}"

        if not store_service:
            return "Storage service is not available. Cannot upload file."

        filename = os.path.basename(path)
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        try:
            with open(path, "rb") as f:
                file_bytes = f.read()

            key = store_service.put_object(
                file=io.BytesIO(file_bytes),
                user_file=profile.user_id,
                filename=filename,
                size=len(file_bytes),
                object_id=uuid4().hex[:12],
            )
            url = store_service.generate_url(key)
            result = f"File uploaded successfully. URL: {url}"
            if caption:
                result += f"\nCaption: {caption}"
            result += (
                "\nInclude this URL in your response so it gets delivered to the user."
            )
            return result
        except Exception as e:
            return f"Failed to upload file: {e}"

    # ── Browser session (Playwright) ──────────────────────────────────────────

    async def _get_page():
        """Return the active browser page. Auto-connects to the real Chrome via CDP if needed."""
        page = _browser_state.get("page")
        if page and not page.is_closed():
            return page
        result = await browser_connect_tool()
        page = _browser_state.get("page")
        if not page or page.is_closed():
            raise RuntimeError(f"Could not connect to browser: {result}")
        return page

    async def _cdp_is_ready(host: str, port: int) -> bool:
        """Check if CDP endpoint is responding via plain HTTP (avoids IPv6 issues)."""
        import urllib.request

        def _probe() -> bool:
            try:
                with urllib.request.urlopen(
                    f"http://{host}:{port}/json/version", timeout=2
                ) as r:
                    return r.status == 200
            except Exception:
                return False

        # urllib blocks; off the event loop it would freeze audio/avatar for 2s a try.
        return await asyncio.to_thread(_probe)

    def _autodismiss_dialogs(target) -> None:
        """alert()/confirm() block every later action until something answers them."""
        try:
            target.on("dialog", lambda d: asyncio.create_task(d.dismiss()))
        except Exception:
            logger.debug("Could not attach dialog handler", exc_info=True)

    async def _connect_cdp(cdp_url: str):
        """Internal: attempt CDP connection and update _browser_state. Raises on failure."""
        from playwright.async_api import async_playwright

        if _browser_state["browser"] and not _browser_state["connected"]:
            await _browser_state["browser"].close()
        if _browser_state["playwright"] is None:
            _browser_state["playwright"] = await async_playwright().start()
        normalized = cdp_url.replace("localhost", "127.0.0.1")
        browser = await _browser_state["playwright"].chromium.connect_over_cdp(
            normalized
        )
        _browser_state["browser"] = browser
        _browser_state["connected"] = True
        contexts = browser.contexts
        if contexts and contexts[0].pages:
            page = contexts[0].pages[0]
        else:
            page = (
                await contexts[0].new_page()
                if contexts
                else await (await browser.new_context()).new_page()
            )
        for ctx in browser.contexts:
            _autodismiss_dialogs(ctx)
        _browser_state["page"] = page
        return browser

    async def _proc_running(name: str) -> bool:
        """Exact process name only. `pgrep -f chrome` also matches this very agent."""
        proc = await asyncio.create_subprocess_exec(
            "pgrep",
            "-x",
            name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        return await proc.wait() == 0

    async def _confirm_close(label: str) -> bool:
        """Closing the user's browser is their call, never ours."""
        if not approval_callback:
            return False
        import uuid as _uuid

        return await approval_callback(
            str(_uuid.uuid4()),
            "browser_connect",
            label,
            f"Quit the running {label} so the assistant can drive it?\n"
            f"{label} is asked to close gracefully and restores its tabs on relaunch, "
            f"but anything typed into an open form may be lost.",
        )

    async def _terminate(name: str) -> bool:
        """Graceful SIGTERM only — SIGKILL is what loses the user's session."""
        proc = await asyncio.create_subprocess_exec(
            "pkill",
            "-x",
            name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        for _ in range(15):
            await asyncio.sleep(1)
            if not await _proc_running(name):
                return True
        return False

    def _firefox_profile_dir():
        import glob as _glob

        home = os.path.expanduser("~")
        for pattern in [
            f"{home}/.mozilla/firefox/*.default-release",
            f"{home}/.mozilla/firefox/*.default",
            f"{home}/.mozilla/firefox/*",
        ]:
            matches = [m for m in _glob.glob(pattern) if os.path.isdir(m)]
            if matches:
                return matches[0]
        return None

    def _tab_report(header: str, pages) -> str:
        tab_list = "\n".join(f"  [{i}] {p.url[:80]}" for i, p in enumerate(pages))
        return (
            f"{header}\n"
            f"Open tabs ({len(pages)}):\n{tab_list}\n\n"
            f"Active tab: {_browser_state['page'].url}"
        )

    async def _connect_firefox():
        """Attach to Firefox via Playwright's own protocol. None = caller should try Chrome."""
        from playwright.async_api import async_playwright

        profile_dir = _firefox_profile_dir()
        if not profile_dir:
            return None  # never launched; nothing to attach to

        if await _proc_running("firefox"):
            # Playwright cannot attach to an already-running Firefox: the profile
            # has to be handed over, so the running window must close first.
            if not await _confirm_close("Firefox"):
                return None
            if not await _terminate("firefox"):
                return "Firefox is still running after being asked to quit. Close it manually and try again."

        # Only safe once the process is gone — removing these under a live
        # Firefox corrupts the profile.
        for lock_file in ("lock", ".parentlock"):
            lf = os.path.join(profile_dir, lock_file)
            if os.path.exists(lf):
                try:
                    os.remove(lf)
                except OSError:
                    pass

        for key in ("context", "browser"):
            stale = _browser_state.get(key)
            if stale:
                try:
                    await stale.close()
                except Exception:
                    logger.debug("Could not close stale %s", key, exc_info=True)

        if _browser_state["playwright"] is None:
            _browser_state["playwright"] = await async_playwright().start()

        try:
            context = await _browser_state[
                "playwright"
            ].firefox.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=False,
                args=["--no-remote"],
            )
        except Exception as e:
            return f"Failed to launch Firefox with profile {profile_dir}: {e}"

        _autodismiss_dialogs(context)
        _browser_state["context"] = context
        _browser_state["browser"] = None
        _browser_state["connected"] = True

        await asyncio.sleep(1)  # let Firefox settle
        pages = context.pages or [await context.new_page()]
        _browser_state["page"] = pages[0]
        return _tab_report(
            f"Connected to Firefox (profile: {os.path.basename(profile_dir)})", pages
        )

    async def _connect_chrome(cdp_url: str, port: int):
        """Relaunch Chrome with CDP on the user's real profile, then attach."""
        import shutil

        chrome_bin = next(
            (
                b
                for b in (
                    "google-chrome-stable",
                    "google-chrome",
                    "chromium",
                    "chromium-browser",
                )
                if shutil.which(b)
            ),
            None,
        )
        if not chrome_bin:
            return None

        for name in ("chrome", "chromium"):
            if not await _proc_running(name):
                continue
            if not await _confirm_close("Chrome"):
                return (
                    "Chrome is running without remote debugging, so there is nothing to attach to.\n"
                    "Either let me close it, or restart it yourself with:\n"
                    f"  {chrome_bin} --remote-debugging-port={port}"
                )
            if not await _terminate(name):
                return f"Chrome ({name}) is still running after being asked to quit. Close it manually and try again."

        # SECURITY: this port grants full control of the logged-in profile to
        # anything running on this machine. browser_close shuts Chrome down again.
        await asyncio.create_subprocess_exec(
            chrome_bin,
            f"--remote-debugging-port={port}",
            "--remote-debugging-address=127.0.0.1",
            f"--user-data-dir={os.path.expanduser('~/.config/google-chrome')}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-session-crashed-bubble",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        _browser_state["launched_chrome"] = True

        for _ in range(30):
            await asyncio.sleep(1)
            if await _cdp_is_ready("127.0.0.1", port):
                break
        else:
            return (
                f"Chrome was relaunched with --remote-debugging-port={port} but "
                "the CDP endpoint is not responding after 30s. Chrome may have failed to start."
            )

        try:
            await _connect_cdp(cdp_url)
        except Exception as e:
            return f"CDP endpoint is up but Playwright connection failed: {e}"
        all_pages = [p for ctx in _browser_state["browser"].contexts for p in ctx.pages]
        return _tab_report(f"Connected to Chrome at {cdp_url}", all_pages)

    async def browser_connect_tool(cdp_url: str = "http://localhost:9222") -> str:
        """Connect to the user's real browser.

        Never closes a browser the user is using without asking first. Order of
        preference: an already-open CDP endpoint (free), then Firefox via
        Playwright's native protocol, then relaunching Chrome with CDP.
        """
        async with _browser_lock:
            page = _browser_state.get("page")
            if _browser_state.get("connected") and page and not page.is_closed():
                return f"Already connected. Active tab: {page.url}"

            try:
                import playwright.async_api  # noqa: F401
            except ImportError:
                return "playwright not installed. Run: pip install playwright && playwright install chromium"

            port = int(cdp_url.split(":")[-1]) if ":" in cdp_url else 9222

            # Attaching to a live CDP endpoint costs the user nothing, so try it first.
            if await _cdp_is_ready("127.0.0.1", port):
                try:
                    await _connect_cdp(cdp_url)
                except Exception as e:
                    return (
                        f"CDP endpoint responded but Playwright connection failed: {e}"
                    )
                all_pages = [
                    p for ctx in _browser_state["browser"].contexts for p in ctx.pages
                ]
                return _tab_report(f"Connected to Chrome at {cdp_url}", all_pages)

            import shutil

            if shutil.which("firefox"):
                result = await _connect_firefox()
                if result:
                    return result

            result = await _connect_chrome(cdp_url, port)
            if result:
                return result

            return (
                "No browser could be attached.\n"
                "Firefox is either not installed or in use, and Chrome is unavailable.\n"
                f"Start a browser with remote debugging and try again:\n"
                f"  google-chrome --remote-debugging-port={port}"
            )

    async def browser_switch_tab_tool(index: int) -> str:
        """Switch to a specific open tab by index (use browser_connect first to list tabs)."""
        try:
            context = _browser_state.get("context")
            browser = _browser_state.get("browser")
            if context:
                all_pages = list(context.pages)
            elif browser:
                all_pages = [p for ctx in browser.contexts for p in ctx.pages]
            else:
                return "No browser connected. Use browser_connect first."
            if index < 0 or index >= len(all_pages):
                return f"Invalid tab index {index}. Available: 0–{len(all_pages) - 1}"
            _browser_state["page"] = all_pages[index]
            # Indices belong to the old tab; keeping them would mark the new
            # tab's elements as "already seen" and its frames as reachable.
            _browser_state["prev_indices"] = set()
            _browser_state["frames"] = {}
            await all_pages[index].bring_to_front()
            return f"Switched to tab [{index}]: {all_pages[index].url}"
        except Exception as e:
            return f"Switch tab error: {e}"

    async def browser_navigate_tool(url: str, wait_for: str = "load") -> str:
        """Navigate to a URL and return page title + visible text excerpt."""
        try:
            page = await _get_page()
            wait_map = {
                "load": "load",
                "domcontentloaded": "domcontentloaded",
                "networkidle": "networkidle",
            }
            await page.goto(
                url, wait_until=wait_map.get(wait_for, "load"), timeout=30000
            )
            _browser_state["prev_indices"] = set()  # indices belong to the old document
            _browser_state["frames"] = {}
            title = await page.title()
            text = await page.inner_text("body")
            text = text[:3000] + "..." if len(text) > 3000 else text
            return f"Page: {title}\nURL: {page.url}\n\n{text}"
        except Exception as e:
            return f"Navigation error: {e}"

    async def browser_click_tool(selector: str) -> str:
        """Click an element by CSS selector or visible text."""
        try:
            page = await _get_page()
            if selector.startswith("text="):
                await page.get_by_text(selector[5:]).first.click(timeout=10000)
            else:
                await page.click(selector, timeout=10000)
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            return (
                f"Clicked '{selector}'. Current page: {await page.title()} ({page.url})"
            )
        except Exception as e:
            return f"Click error: {e}"

    async def browser_type_tool(
        selector: str, text: str, clear_first: bool = True
    ) -> str:
        """Type text into an input field."""
        try:
            page = await _get_page()
            if clear_first:
                await page.fill(selector, "", timeout=10000)
            await page.type(selector, text, delay=30)
            return f"Typed into '{selector}' on {page.url}"
        except Exception as e:
            return f"Type error: {e}"

    # ── browser_act / browser_extract — DOM-indexed AI browser control ────────

    _ACT_SYSTEM_PROMPT = """You are a browser automation agent. You receive a snapshot of the current page where interactive elements are marked with [index] numbers.

Elements marked with *[index] are NEW since the last action — pay attention to them.

Your job: return a JSON object with an "actions" array (up to 6 actions) to fulfill the user instruction.

Action types:
- {"type": "click", "index": N}
- {"type": "type", "index": N, "text": "..."}
- {"type": "press", "index": N, "key": "Enter"}
- {"type": "press_key", "key": "Enter"}
- {"type": "select", "index": N, "text": "option value"}
- {"type": "scroll", "direction": "down"|"up", "amount": 300}
- {"type": "scroll", "index": N}  (scroll element into view)
- {"type": "go_to_url", "url": "https://..."}
- {"type": "hover", "index": N}

Rules:
- Reference elements ONLY by their [index] number
- For search boxes: use "type" then "press_key" with key "Enter"
- Indices cover iframes too — just use the number, the right frame is picked for you
- Execution stops as soon as an index from this snapshot disappears, so plan only
  actions that make sense against the page as it is right now
- For dropdowns: "click" to open it and stop there; the next call will show the options as *[index]
- Stop the actions array after go_to_url (page will reload)
- If the task is already done, return {"actions": [], "done": true, "result": "..."}
- Return ONLY valid JSON, no markdown"""

    async def browser_act_tool(instruction: str) -> str:
        """Perform browser actions using natural language and indexed DOM."""
        import json as _json

        try:
            page = await _get_page()
        except Exception as e:
            return f"No browser connected: {e}"

        # Snapshot
        snap = await _dom_snapshot(page)
        if not snap["snapshot"].strip():
            return "Page appears empty or could not be indexed. Try browser_navigate first."

        page_info = f"URL: {page.url}\nTitle: {await page.title()}"
        user_msg = f"{page_info}\n\nPage snapshot:\n{_clip_snapshot(snap['snapshot'])}\n\nInstruction: {instruction}"

        try:
            resp = await openai_integration.client.chat.completions.create(
                model=openai_integration.model,
                messages=[
                    {"role": "system", "content": _ACT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
                max_tokens=600,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content.strip()
            data = _json.loads(raw)
        except Exception as e:
            return f"LLM error: {e}"

        if data.get("done"):
            return data.get("result", "Task completed.")

        actions = data.get("actions", [])
        if not actions:
            return "LLM found no applicable actions for that instruction."

        # ponytail: no retry loop here — the agent re-calls browser_act, which
        # re-snapshots for free. A local retry just paid for a second LLM call
        # against the same stale snapshot.
        executed = await _execute_actions(page, actions)

        summary = " → ".join(executed)
        title = await page.title()
        return f"Done: {summary}\nPage: {title} ({page.url})"

    async def browser_extract_tool(instruction: str) -> str:
        """Extract structured data from the current page using natural language."""
        import json as _json

        try:
            page = await _get_page()
        except Exception as e:
            return f"No browser connected: {e}"

        snap = await _dom_snapshot(page)
        snapshot_text = snap["snapshot"] or await page.inner_text("body")
        snapshot_text = _clip_snapshot(snapshot_text, 8000)

        prompt = f"""Extract information from this web page based on the instruction.

URL: {page.url}
Title: {await page.title()}

Page elements (interactive elements have [index] markers, others show their text):
{snapshot_text}

Instruction: {instruction}

Return a clean, structured plain-text answer.
For lists, use a numbered format.
If data is not found, say so clearly."""

        try:
            resp = await openai_integration.client.chat.completions.create(
                model=openai_integration.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1200,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"Extract error: {e}"

    # ─────────────────────────────────────────────────────────────────────────

    async def browser_get_content_tool(
        selector: str = "", as_html: bool = False
    ) -> str:
        """Extract text or HTML from the page or a specific element."""
        try:
            page = await _get_page()
            target = selector or "body"
            if as_html:
                content = await page.inner_html(target)
            else:
                content = await page.inner_text(target)
            content = content[:5000] + "..." if len(content) > 5000 else content
            return f"Content from '{target}' on {page.url}:\n\n{content}"
        except Exception as e:
            return f"Get content error: {e}"

    async def browser_screenshot_tool(
        selector: str = "", question: str = "Describe what is visible on this page."
    ) -> str:
        """Take a screenshot of the browser page and describe it."""
        import base64 as b64

        try:
            page = await _get_page()
            if selector:
                element = await page.query_selector(selector)
                if not element:
                    return f"Element '{selector}' not found on page."
                png = await element.screenshot()
            else:
                png = await page.screenshot(full_page=False)
            image_base64 = b64.b64encode(png).decode()
            prompt = f"Browser page: {await page.title()} ({page.url}). {question}"
            description = await openai_integration.describe_image_from_base64(
                image_base64, prompt=prompt
            )
            return description
        except Exception as e:
            return f"Browser screenshot error: {e}"

    async def browser_evaluate_tool(script: str) -> str:
        """Execute JavaScript in the current page and return the result."""
        try:
            page = _browser_state.get("page")
            if not page or page.is_closed():
                return "No browser page available. Use browser_connect first."

            if plan_mode:
                return {
                    "plan_only": True,
                    "would_do": f"Run JavaScript on {page.url}",
                    "diff": script[:500],
                }

            # This runs with the full authority of whatever the user is logged
            # into — cookies, localStorage, open banking or chat tabs. It is the
            # most privileged tool in the set, so it asks like write_file does.
            if approval_callback:
                import uuid as _uuid

                request_id = str(_uuid.uuid4())
                approved = await approval_callback(
                    request_id,
                    "browser_evaluate",
                    page.url,
                    script[:2000],
                )
                if not approved:
                    from src.core.platform.ai.tools.approval_manager import get_feedback

                    feedback = get_feedback(request_id)
                    msg = f"JavaScript execution on '{page.url}' was rejected by the user."
                    if feedback:
                        msg += f" Reason: {feedback}. Please try a different approach."
                    return msg

            # Playwright's page.evaluate requires an expression or a function.
            # Top-level `return` is a SyntaxError. Auto-wrap in IIFE when needed.
            needs_wrap = "return " in script or script.strip().startswith("//")
            if needs_wrap:
                script = f"(function() {{\n{script}\n}})()"
            result = await page.evaluate(script)
            if result is None:
                return "(script executed, no return value)"
            return (
                json.dumps(result, ensure_ascii=False, indent=2)
                if isinstance(result, (dict, list))
                else str(result)
            )
        except Exception as e:
            return f"JavaScript error: {e}"

    async def browser_close_tool() -> str:
        """Disconnect from the browser session. When connected to a real browser via
        browser_connect, this only disconnects — it does NOT close the user's browser."""
        try:
            context = _browser_state.get("context")
            browser = _browser_state.get("browser")

            if context:
                await context.close()
                msg = "Disconnected from Firefox (your browser session was closed)."
            elif browser:
                await browser.close()
                msg = "Disconnected from browser (your browser remains open)."
            else:
                msg = "No browser session active."

            # We opened the debugging port, so we close it. Left open it lets any
            # local process drive the user's logged-in profile.
            if _browser_state.get("launched_chrome"):
                if await _confirm_close("Chrome"):
                    for name in ("chrome", "chromium"):
                        if await _proc_running(name):
                            await _terminate(name)
                    msg += " Chrome (opened by me with remote debugging) was closed."
                else:
                    msg += (
                        " Note: Chrome is still running with remote debugging enabled — "
                        "close it when you are done."
                    )
                _browser_state["launched_chrome"] = False

            _browser_state["context"] = None
            _browser_state["browser"] = None
            _browser_state["page"] = None
            _browser_state["connected"] = False
            _browser_state["prev_indices"] = set()
            _browser_state["frames"] = {}

            if _browser_state["playwright"]:
                await _browser_state["playwright"].stop()
                _browser_state["playwright"] = None

            return msg
        except Exception as e:
            return f"Error closing browser: {e}"

    async def search_documents_tool(query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search for relevant content in user's uploaded documents"""
        import logging

        logger = logging.getLogger(__name__)

        logger.info(
            f"search_documents_tool called with query: {query}, profile: {profile.user_id}"
        )

        search_result = await openai_integration.rag_processor.search_relevant_content(
            query=query,
            document_ids=[],
            max_results=max_results,
            profile_id=profile.user_id,
        )

        results = search_result.get("results", [])
        unified_context = search_result.get("unified_context", "")

        logger.info(
            f"search_documents_tool found {len(results)} results for query: {query}"
        )

        if results:
            return {
                "found": True,
                "results": results,
                "context": unified_context,
                "total_chunks": len(results),
            }

        logger.warning(f"No results found in Qdrant for profile {profile.user_id}")
        return {
            "found": False,
            "context": "No hay información disponible en el catálogo.",
            "results": [],
        }

    async def list_storage_files_tool() -> Dict[str, Any]:
        """List all files in user's storage"""
        if not profile.files:
            return {
                "total": 0,
                "files": [],
                "message": "No hay archivos subidos. El usuario puede subir archivos PDF, Excel o Word.",
            }

        files_list = []
        for f in profile.files:
            # Detect file type from extension
            name = f.name.lower() if f.name else ""
            if name.endswith(".pdf"):
                file_type = "PDF"
            elif name.endswith((".xlsx", ".xls")):
                file_type = "Excel"
            elif name.endswith((".docx", ".doc")):
                file_type = "Word"
            else:
                file_type = "Otro"

            files_list.append(
                {
                    "id": str(f.id)
                    if hasattr(f, "id")
                    else f._id
                    if hasattr(f, "_id")
                    else None,
                    "name": f.name,
                    "type": file_type,
                    "url": f.url,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
            )

        return {
            "total": len(files_list),
            "files": files_list,
            "message": f"El usuario tiene {len(files_list)} archivo(s) disponible(s).",
        }

    # ── File editing tools ────────────────────────────────────────────────────

    import os as _os
    from pathlib import Path as _Path

    if client_workspace:
        workspace = _Path(client_workspace).resolve()
    else:
        workspace = _Path(_os.environ.get("GILLIE_WORKSPACE", _Path.home())).resolve()

    def _resolve_safe_path(path: str) -> tuple:
        """
        Resolve a path to an absolute path and verify it stays within the workspace.

        Returns (resolved_path, None) if safe, (None, error_message) if not.
        Prevents directory traversal attacks and symlink escaping.
        """
        candidate = _Path(path)
        if candidate.is_absolute():
            target = candidate.resolve()
        else:
            target = (workspace / path).resolve()
        if not str(target).startswith(str(workspace)):
            return (
                None,
                f"Access denied: path '{path}' is outside workspace '{workspace}'",
            )
        return target, None

    def _is_ignored(path: _Path, ws: _Path) -> bool:
        """Check if a path is excluded by .gillierignore in the workspace root."""
        ignore_file = ws / ".gillierignore"
        if not ignore_file.exists():
            return False
        try:
            lines = ignore_file.read_text().splitlines()
        except Exception:
            return False
        patterns = [
            l.strip() for l in lines if l.strip() and not l.strip().startswith("#")
        ]
        try:
            rel = path.relative_to(ws)
        except ValueError:
            return False
        rel_str = str(rel)
        for pattern in patterns:
            if fnmatch.fnmatch(rel_str, pattern) or fnmatch.fnmatch(path.name, pattern):
                return True
            if pattern.endswith("/") and rel_str.startswith(pattern[:-1]):
                return True
        return False

    async def read_file_tool(path: str, offset: int = 1, limit: int = 200) -> str:
        """Read a file and return its contents with line numbers."""
        resolved, err = _resolve_safe_path(path)
        if err:
            return err
        if _is_ignored(resolved, workspace):
            return {"error": f"Access denied: '{path}' is excluded by .gillierignore"}
        if not resolved.exists():
            return f"Error: file not found: '{path}'"
        if not resolved.is_file():
            return f"Error: '{path}' is not a file"
        try:
            raw = resolved.read_bytes()
            # Detect binary files by checking for null bytes in the first 8KB
            if b"\x00" in raw[:8192]:
                return f"Error: '{path}' appears to be a binary file and cannot be read as text"
            text = raw.decode("utf-8", errors="replace")
        except Exception as e:
            return f"Error reading file: {e}"

        lines = text.splitlines()
        total_lines = len(lines)
        start = max(0, offset - 1)
        end = min(start + limit, total_lines)
        selected = lines[start:end]

        header = f"File: {path} (lines {start + 1}-{end} of {total_lines})\n"
        numbered = "\n".join(
            f"{start + i + 1:>6}\t{line}" for i, line in enumerate(selected)
        )
        return header + numbered

    async def write_file_tool(path: str, content: str, create_dirs: bool = True) -> str:
        """Create or overwrite a file with the given content."""
        import difflib as _difflib
        import uuid as _uuid

        resolved, err = _resolve_safe_path(path)
        if err:
            return err
        if _is_ignored(resolved, workspace):
            return {"error": f"Access denied: '{path}' is excluded by .gillierignore"}

        if plan_mode:
            if resolved.exists() and resolved.is_file():
                try:
                    current_lines = resolved.read_text(errors="replace").splitlines(
                        keepends=True
                    )
                except Exception:
                    current_lines = []
            else:
                current_lines = []
            new_lines = content.splitlines(keepends=True)
            diff = "".join(
                _difflib.unified_diff(
                    current_lines,
                    new_lines,
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    lineterm="",
                )
            )
            return {
                "plan_only": True,
                "would_do": f"Write '{path}' ({len(content.splitlines())} lines)",
                "diff": diff[:500],
            }

        if approval_callback:
            if resolved.exists() and resolved.is_file():
                try:
                    current_lines = resolved.read_text(errors="replace").splitlines(
                        keepends=True
                    )
                except Exception:
                    current_lines = []
            else:
                current_lines = []
            new_lines = content.splitlines(keepends=True)
            diff = "".join(
                _difflib.unified_diff(
                    current_lines,
                    new_lines,
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    lineterm="",
                )
            )
            request_id = str(_uuid.uuid4())
            approved = await approval_callback(
                request_id,
                "write_file",
                path,
                diff or f"(new file) {path}",
            )
            if not approved:
                from src.core.platform.ai.tools.approval_manager import get_feedback

                feedback = get_feedback(request_id)
                msg = f"Change to '{path}' was rejected by the user."
                if feedback:
                    msg += f" Reason: {feedback}. Please try a different approach."
                return {"skipped": True, "message": msg}

        try:
            if create_dirs:
                resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            line_count = len(content.splitlines())
            return f"Written {line_count} lines to '{path}'"
        except Exception as e:
            return f"Error writing file: {e}"

    async def edit_file_tool(path: str, old_string: str, new_string: str) -> str:
        """Replace old_string with new_string in a file using cascading match strategies."""
        import difflib
        import uuid as _uuid

        resolved, err = _resolve_safe_path(path)
        if err:
            return err
        if _is_ignored(resolved, workspace):
            return {"error": f"Access denied: '{path}' is excluded by .gillierignore"}
        if not resolved.exists():
            return f"Error: file not found: '{path}'"
        if not resolved.is_file():
            return f"Error: '{path}' is not a file"

        try:
            original = resolved.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"

        if plan_mode:
            old_lines = (old_string or "").splitlines(keepends=True)
            new_lines_p = (new_string or "").splitlines(keepends=True)
            diff_plan = "".join(
                difflib.unified_diff(
                    old_lines,
                    new_lines_p,
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    lineterm="",
                )
            )
            return {
                "plan_only": True,
                "would_do": f"Edit '{path}'",
                "diff": diff_plan[:500],
            }

        if approval_callback:
            old_lines = (old_string or "").splitlines(keepends=True)
            new_lines = (new_string or "").splitlines(keepends=True)
            diff = "".join(
                difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    lineterm="",
                )
            )
            request_id = str(_uuid.uuid4())
            approved = await approval_callback(
                request_id,
                "edit_file",
                path,
                diff or f"Replace content in {path}",
            )
            if not approved:
                from src.core.platform.ai.tools.approval_manager import get_feedback

                feedback = get_feedback(request_id)
                msg = f"Change to '{path}' was rejected by the user."
                if feedback:
                    msg += f" Reason: {feedback}. Please try a different approach."
                return {"skipped": True, "message": msg}

        exact_count = original.count(old_string)
        if exact_count > 1:
            return (
                f"Error: found {exact_count} occurrences of the search string. "
                f"Provide more surrounding context to make the match unique."
            )
        if exact_count == 1:
            updated = original.replace(old_string, new_string, 1)
            resolved.write_text(updated, encoding="utf-8")
            return f"Edited '{path}': replaced 1 occurrence (exact match)"

        def _normalize(text: str) -> str:
            return "\n".join(line.strip() for line in text.splitlines())

        norm_original = _normalize(original)
        norm_old = _normalize(old_string)
        norm_count = norm_original.count(norm_old)
        if norm_count == 1:
            norm_idx = norm_original.index(norm_old)
            orig_lines = original.splitlines(keepends=True)
            old_lines = old_string.splitlines()
            new_lines = new_string.splitlines(keepends=True)
            norm_old_lines = [l.strip() for l in old_lines]
            for i in range(len(orig_lines) - len(old_lines) + 1):
                window = [
                    orig_lines[i + j].rstrip("\n").rstrip("\r").strip()
                    for j in range(len(old_lines))
                ]
                if window == norm_old_lines:
                    updated_lines = (
                        orig_lines[:i] + new_lines + orig_lines[i + len(old_lines) :]
                    )
                    resolved.write_text("".join(updated_lines), encoding="utf-8")
                    return f"Edited '{path}': replaced 1 occurrence (normalized whitespace match)"
        elif norm_count > 1:
            return (
                f"Error: found {norm_count} normalized occurrences of the search string. "
                f"Provide more surrounding context to make the match unique."
            )

        old_lines_raw = old_string.splitlines()
        if old_lines_raw:
            non_empty = [l for l in old_lines_raw if l.strip()]
            if non_empty:
                common_indent = min(len(l) - len(l.lstrip()) for l in non_empty)
                dedented_old = [
                    l[common_indent:] if len(l) >= common_indent else l.lstrip()
                    for l in old_lines_raw
                ]
                orig_lines_full = original.splitlines(keepends=True)
                for i in range(len(orig_lines_full) - len(old_lines_raw) + 1):
                    window = orig_lines_full[i : i + len(old_lines_raw)]
                    window_stripped = [l.rstrip("\n").rstrip("\r") for l in window]
                    non_empty_w = [l for l in window_stripped if l.strip()]
                    if not non_empty_w:
                        continue
                    win_indent = min(len(l) - len(l.lstrip()) for l in non_empty_w)
                    dedented_win = [
                        l[win_indent:] if len(l) >= win_indent else l.lstrip()
                        for l in window_stripped
                    ]
                    if dedented_win == dedented_old:
                        # Re-indent new_string to match the window's base indentation
                        indent_str = " " * win_indent
                        new_reindented = "\n".join(
                            indent_str + nl if nl.strip() else nl
                            for nl in new_string.splitlines()
                        )
                        updated_lines = (
                            orig_lines_full[:i]
                            + [new_reindented + "\n"]
                            + orig_lines_full[i + len(old_lines_raw) :]
                        )
                        resolved.write_text("".join(updated_lines), encoding="utf-8")
                        return f"Edited '{path}': replaced 1 occurrence (indentation-flexible match)"

        orig_lines = original.splitlines()
        old_lines_stripped = old_string.splitlines()
        window_size = len(old_lines_stripped)
        if window_size == 0:
            return "Error: old_string is empty"

        best_ratio = 0.0
        best_start = -1
        for i in range(len(orig_lines) - window_size + 1):
            window = orig_lines[i : i + window_size]
            ratio = difflib.SequenceMatcher(None, "\n".join(window), old_string).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_start = i

        if best_ratio >= 0.8 and best_start >= 0:
            window_lines = orig_lines[best_start : best_start + window_size]
            updated_lines = (
                orig_lines[:best_start]
                + new_string.splitlines()
                + orig_lines[best_start + window_size :]
            )
            resolved.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
            return (
                f"Edited '{path}': replaced 1 occurrence (fuzzy match, similarity={best_ratio:.2f}). "
                f"Replaced lines {best_start + 1}-{best_start + window_size}."
            )

        nearby_lines = "\n".join(
            f"{i + 1:>6}\t{line}" for i, line in enumerate(orig_lines[:30])
        )
        return (
            f"Error: could not find old_string in '{path}' using exact, normalized, or fuzzy matching. "
            f"Use read_file to get the current content and retry with the exact text.\n"
            f"First 30 lines of file:\n{nearby_lines}"
        )

    async def list_directory_tool(path: str = ".", show_hidden: bool = False) -> str:
        """List the contents of a directory in a simple tree format."""
        resolved, err = _resolve_safe_path(path)
        if err:
            return err
        if not resolved.exists():
            return f"Error: path not found: '{path}'"
        if not resolved.is_dir():
            return f"Error: '{path}' is not a directory"

        try:
            entries = sorted(
                resolved.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
            )
        except PermissionError:
            return f"Error: permission denied reading directory '{path}'"

        lines = [f"Directory: {path}"]
        for entry in entries:
            if not show_hidden and entry.name.startswith("."):
                continue
            if entry.is_dir():
                lines.append(f"  [dir]  {entry.name}/")
            elif entry.is_file():
                try:
                    size = entry.stat().st_size
                    if size >= 1_048_576:
                        size_str = f"{size / 1_048_576:.1f}MB"
                    elif size >= 1024:
                        size_str = f"{size / 1024:.1f}KB"
                    else:
                        size_str = f"{size}B"
                except OSError:
                    size_str = "?"
                lines.append(f"  [file] {entry.name}  ({size_str})")
            else:
                lines.append(f"  [other] {entry.name}")

        if len(lines) == 1:
            lines.append("  (empty)")
        return "\n".join(lines)

    async def find_files_tool(
        pattern: str, path: str = ".", max_results: int = 50
    ) -> str:
        """Search for files matching a glob pattern."""
        resolved, err = _resolve_safe_path(path)
        if err:
            return err
        if not resolved.exists():
            return f"Error: base path not found: '{path}'"
        if not resolved.is_dir():
            return f"Error: '{path}' is not a directory"

        try:
            matches = []
            for match in resolved.glob(pattern):
                if _is_ignored(match, workspace):
                    continue
                rel = match.relative_to(resolved)
                matches.append((str(rel), match.is_dir()))
                if len(matches) >= max_results:
                    break
        except Exception as e:
            return f"Error during glob search: {e}"

        if not matches:
            return f"No files found matching '{pattern}' in '{path}'"

        lines = [f"Found {len(matches)} result(s) for '{pattern}' in '{path}':"]
        for rel_path, is_dir in sorted(matches, key=lambda t: t[0]):
            suffix = "/" if is_dir else ""
            lines.append(f"  {rel_path}{suffix}")

        if len(matches) == max_results:
            lines.append(f"  (results capped at {max_results})")
        return "\n".join(lines)

    async def repo_map_tool(
        path: str = ".",
        max_depth: int = 4,
        include_signatures: bool = True,
        file_glob: str = "*.py",
    ) -> Dict[str, Any]:
        """Generate a compact repository map with file tree and code signatures."""
        import ast as _ast

        resolved, err = _resolve_safe_path(path)
        if err:
            return {"error": err}

        lines: List[str] = []

        def _tree(dir_path: _Path, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return
            skip = {
                ".git",
                "node_modules",
                "__pycache__",
                ".venv",
                "venv",
                ".mypy_cache",
                "dist",
                "build",
                ".next",
            }
            try:
                entries = sorted(
                    dir_path.iterdir(), key=lambda e: (e.is_file(), e.name)
                )
            except PermissionError:
                return
            entries = [
                e
                for e in entries
                if e.name not in skip and not _is_ignored(e, workspace)
            ]
            for i, entry in enumerate(entries):
                connector = "└── " if i == len(entries) - 1 else "├── "
                lines.append(f"{prefix}{connector}{entry.name}")
                if entry.is_dir():
                    extension = "    " if i == len(entries) - 1 else "│   "
                    _tree(entry, prefix + extension, depth + 1)
                elif include_signatures and entry.is_file():
                    _extract_signatures(
                        entry, prefix + ("    " if i == len(entries) - 1 else "│   ")
                    )

        def _extract_signatures(file_path: _Path, prefix: str):
            """Extract class/function signatures from supported file types."""
            if not fnmatch.fnmatch(file_path.name, file_glob):
                return
            try:
                source = file_path.read_text(errors="replace")
                if "\x00" in source:
                    return
            except Exception:
                return

            if file_path.suffix == ".py":
                try:
                    tree = _ast.parse(source)
                    for node in _ast.walk(tree):
                        if isinstance(node, _ast.ClassDef):
                            lines.append(f"{prefix}    class {node.name}")
                            for item in node.body:
                                if isinstance(
                                    item, (_ast.FunctionDef, _ast.AsyncFunctionDef)
                                ):
                                    args = [a.arg for a in item.args.args]
                                    lines.append(
                                        f"{prefix}        def {item.name}({', '.join(args)})"
                                    )
                        elif isinstance(
                            node, (_ast.FunctionDef, _ast.AsyncFunctionDef)
                        ):
                            args = [a.arg for a in node.args.args]
                            lines.append(
                                f"{prefix}    def {node.name}({', '.join(args)})"
                            )
                except SyntaxError:
                    pass
            else:
                import re as _re_sig

                patterns = [
                    r"^(export\s+)?(async\s+)?function\s+(\w+)",
                    r"^(export\s+)?(abstract\s+)?class\s+(\w+)",
                    r"^def\s+(\w+)",
                    r"^class\s+(\w+)",
                ]
                for line in source.splitlines()[:200]:
                    stripped = line.strip()
                    for pat in patterns:
                        if _re_sig.match(pat, stripped):
                            lines.append(f"{prefix}    {stripped[:80]}")
                            break

        lines.append(str(resolved))
        _tree(resolved)

        result = "\n".join(lines)
        truncated = False
        if len(result) > 8000:
            result = result[:8000]
            truncated = True

        return {"map": result, "truncated": truncated}

    async def check_code_tool(path: str = ".", tool: str = "auto") -> Dict[str, Any]:
        """Run a static analysis / type checker and return diagnostics."""
        import shutil as _shutil

        resolved, err = _resolve_safe_path(path)
        if err:
            return {"error": err}

        # Auto-detect: pick checker based on file extension or available tool
        def _pick_tool() -> str:
            p = resolved
            if p.is_file():
                if p.suffix in (".ts", ".tsx"):
                    return "tsc"
                if p.suffix in (".js", ".jsx"):
                    return "eslint"
                if p.suffix == ".py":
                    return "pyright" if _shutil.which("pyright") else "mypy"
            # directory: prefer pyright > mypy if python files exist
            if list(p.rglob("*.py")):
                return "pyright" if _shutil.which("pyright") else "mypy"
            if list(p.rglob("*.ts")) or list(p.rglob("*.tsx")):
                return "tsc"
            return "none"

        chosen = tool if tool != "auto" else _pick_tool()

        if chosen == "none":
            return {
                "tool": "none",
                "diagnostics": [],
                "summary": "No supported checker found for this path.",
            }

        if not _shutil.which(chosen):
            return {
                "tool": chosen,
                "error": f"'{chosen}' is not installed or not in PATH. Install it first.",
            }

        if chosen == "pyright":
            cmd = ["pyright", "--outputjson", str(resolved)]
        elif chosen == "mypy":
            cmd = ["mypy", "--show-column-numbers", "--no-error-summary", str(resolved)]
        elif chosen == "tsc":
            cmd = ["tsc", "--noEmit", "--pretty", "false", str(resolved)]
        elif chosen == "eslint":
            cmd = ["eslint", "--format=json", str(resolved)]
        else:
            return {"tool": chosen, "error": f"Unknown checker: '{chosen}'"}

        try:
            proc = await _asyncio.create_subprocess_exec(
                *cmd,
                stdout=_asyncio.subprocess.PIPE,
                stderr=_asyncio.subprocess.PIPE,
                cwd=str(resolved if resolved.is_dir() else resolved.parent),
            )
            raw_out, raw_err = await proc.communicate()
            stdout = raw_out.decode("utf-8", errors="replace")
            stderr = raw_err.decode("utf-8", errors="replace")
        except Exception as e:
            return {"tool": chosen, "error": f"Failed to run {chosen}: {e}"}

        diagnostics = []

        if chosen == "pyright":
            try:
                import json as _json

                data = _json.loads(stdout)
                for diag in data.get("generalDiagnostics", []):
                    diagnostics.append(
                        {
                            "file": diag.get("file", ""),
                            "line": diag.get("range", {})
                            .get("start", {})
                            .get("line", 0)
                            + 1,
                            "severity": diag.get("severity", "error"),
                            "message": diag.get("message", ""),
                            "rule": diag.get("rule", ""),
                        }
                    )
                summary = data.get("summary", {})
            except Exception:
                diagnostics = [{"raw": stdout[:2000]}]
                summary = {}
        elif chosen == "mypy":
            import re as _re_diag

            pat = _re_diag.compile(
                r"^(.+?):(\d+):(?:\d+:)?\s*(error|warning|note):\s*(.+)$"
            )
            for line in stdout.splitlines():
                m = pat.match(line.strip())
                if m:
                    diagnostics.append(
                        {
                            "file": m.group(1),
                            "line": int(m.group(2)),
                            "severity": m.group(3),
                            "message": m.group(4),
                        }
                    )
            summary = {
                "errors": sum(1 for d in diagnostics if d.get("severity") == "error")
            }
        else:
            diagnostics = [{"raw": (stdout + stderr)[:3000]}]
            summary = {}

        error_count = sum(1 for d in diagnostics if d.get("severity") == "error")
        return {
            "tool": chosen,
            "diagnostics": diagnostics[:50],
            "truncated": len(diagnostics) > 50,
            "error_count": error_count,
            "summary": summary,
        }

    # ── Shell and git tools ───────────────────────────────────────────────────

    import asyncio as _asyncio
    import re as _re

    _SHELL_BLACKLIST = [
        "rm -rf /",
        "mkfs",
        "dd if=",
        "shutdown",
        "reboot",
        ":(){ :|:& };:",
        "chmod -R 777 /",
        "chown -R",
    ]

    async def run_shell_tool(
        command: str, working_dir: str = ".", timeout: int = 30
    ) -> Dict[str, Any]:
        """Execute a shell command inside the workspace."""
        for blocked in _SHELL_BLACKLIST:
            if blocked in command:
                return {
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Command rejected: contains blocked pattern '{blocked}'",
                    "truncated": False,
                }

        if plan_mode:
            return {
                "plan_only": True,
                "would_do": f"Run: {command}",
                "working_dir": working_dir,
            }

        resolved_dir, err = _resolve_safe_path(working_dir)
        if err:
            return {"exit_code": -1, "stdout": "", "stderr": err, "truncated": False}
        if _is_ignored(resolved_dir, workspace):
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Access denied: '{working_dir}' is excluded by .gillierignore",
                "truncated": False,
            }

        try:
            proc = await _asyncio.create_subprocess_shell(
                command,
                stdout=_asyncio.subprocess.PIPE,
                stderr=_asyncio.subprocess.PIPE,
                cwd=str(resolved_dir),
            )

            if shell_output_callback is not None:
                # Streaming mode: emit each stdout line via the callback as it arrives.
                # stderr is collected silently to avoid interleaving with streamed output.
                stdout_lines: list = []
                truncated = False

                async def _read_stdout_streaming():
                    nonlocal truncated
                    async for raw_line in proc.stdout:
                        decoded = raw_line.decode("utf-8", errors="replace")
                        stdout_lines.append(decoded)
                        await shell_output_callback(decoded.rstrip("\n"))
                        if sum(len(l) for l in stdout_lines) > 3500:
                            truncated = True
                            proc.kill()
                            break

                try:
                    await _asyncio.wait_for(
                        _asyncio.gather(_read_stdout_streaming(), proc.wait()),
                        timeout=timeout,
                    )
                except _asyncio.TimeoutError:
                    proc.kill()
                    return {
                        "exit_code": -1,
                        "stdout": "".join(stdout_lines),
                        "stderr": f"Command timed out after {timeout}s: {command}",
                        "truncated": True,
                        "streamed": True,
                    }

                raw_stderr = await proc.stderr.read()
                stderr = raw_stderr.decode("utf-8", errors="replace")[:500]
                stdout_full = "".join(stdout_lines)
                if len(stdout_full) > 3500:
                    stdout_full = stdout_full[:3500]
                    truncated = True

                return {
                    "exit_code": proc.returncode,
                    "stdout": stdout_full,
                    "stderr": stderr,
                    "truncated": truncated,
                    "streamed": True,
                }
            else:
                # Non-streaming mode: buffer all output before returning (original behaviour).
                try:
                    raw_stdout, raw_stderr = await _asyncio.wait_for(
                        proc.communicate(), timeout=timeout
                    )
                except _asyncio.TimeoutError:
                    proc.kill()
                    await proc.communicate()
                    return {
                        "exit_code": -1,
                        "stdout": "",
                        "stderr": f"Command timed out after {timeout}s: {command}",
                        "truncated": False,
                    }

                stdout = raw_stdout.decode("utf-8", errors="replace")
                stderr = raw_stderr.decode("utf-8", errors="replace")
                combined = stdout + stderr
                truncated = len(combined) > 4000
                if truncated:
                    stdout = stdout[:3500]
                    stderr = stderr[:500]

                return {
                    "exit_code": proc.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "truncated": truncated,
                }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Error running command: {e}",
                "truncated": False,
            }

    async def grep_files_tool(
        pattern: str,
        path: str = ".",
        file_glob: str = "*",
        max_results: int = 50,
        ignore_case: bool = False,
        context_lines: int = 0,
    ) -> Dict[str, Any]:
        """Search for a text/regex pattern inside files. Uses ripgrep when available."""
        import shutil as _shutil

        resolved, err = _resolve_safe_path(path)
        if err:
            return {"found": 0, "results": [], "truncated": False, "error": err}
        if not resolved.exists() or not resolved.is_dir():
            return {
                "found": 0,
                "results": [],
                "truncated": False,
                "error": f"Path not found or not a directory: '{path}'",
            }

        if _shutil.which("rg"):
            try:
                rg_cmd = [
                    "rg",
                    "--json",
                    f"--glob={file_glob}",
                    f"--max-count={max_results}",
                ]
                if ignore_case:
                    rg_cmd.append("-i")
                if context_lines > 0:
                    rg_cmd += [f"-C{context_lines}"]
                rg_cmd += ["--", pattern, str(resolved)]

                proc = await _asyncio.create_subprocess_exec(
                    *rg_cmd,
                    stdout=_asyncio.subprocess.PIPE,
                    stderr=_asyncio.subprocess.PIPE,
                )
                raw_out, _ = await proc.communicate()
                results = []
                for line in raw_out.decode("utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = __import__("json").loads(line)
                    except Exception:
                        continue
                    if obj.get("type") == "match":
                        data = obj["data"]
                        file_rel = str(
                            _Path(data["path"]["text"]).relative_to(resolved)
                        )
                        line_num = data["line_number"]
                        content = data["lines"]["text"].rstrip("\n")
                        result_entry: Dict[str, Any] = {
                            "file": file_rel,
                            "line": line_num,
                            "content": content,
                        }
                        if context_lines > 0:
                            # submatches context will be included naturally via -C in output
                            pass
                        results.append(result_entry)
                        if len(results) >= max_results:
                            break
                truncated = len(results) >= max_results
                return {
                    "found": len(results),
                    "results": results,
                    "truncated": truncated,
                }
            except Exception:
                pass  # fall through to Python implementation

        _SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
        flags = _re.IGNORECASE if ignore_case else 0
        try:
            compiled = _re.compile(pattern, flags)
        except _re.error as e:
            return {
                "found": 0,
                "results": [],
                "truncated": False,
                "error": f"Invalid regex pattern: {e}",
            }

        results = []
        truncated = False

        for file_path in resolved.rglob(file_glob):
            if any(part in _SKIP_DIRS for part in file_path.parts):
                continue
            if _is_ignored(file_path, workspace):
                continue
            if not file_path.is_file():
                continue

            try:
                raw = file_path.read_bytes()
                if b"\x00" in raw[:8192]:
                    continue
                text = raw.decode("utf-8", errors="replace")
            except Exception:
                continue

            all_lines = text.splitlines()
            for line_num, line in enumerate(all_lines, start=1):
                if compiled.search(line):
                    entry: Dict[str, Any] = {
                        "file": str(file_path.relative_to(resolved)),
                        "line": line_num,
                        "content": line.strip(),
                    }
                    if context_lines > 0:
                        before = all_lines[
                            max(0, line_num - 1 - context_lines) : line_num - 1
                        ]
                        after = all_lines[
                            line_num : min(len(all_lines), line_num + context_lines)
                        ]
                        entry["before"] = before
                        entry["after"] = after
                    results.append(entry)
                    if len(results) >= max_results:
                        truncated = True
                        break
            if truncated:
                break

        return {"found": len(results), "results": results, "truncated": truncated}

    _git_workspace = workspace

    async def _run_git(*args) -> tuple:
        """Run a git command in the workspace and return (stdout, stderr, returncode)."""
        proc = await _asyncio.create_subprocess_exec(
            "git",
            *args,
            stdout=_asyncio.subprocess.PIPE,
            stderr=_asyncio.subprocess.PIPE,
            cwd=str(_git_workspace),
        )
        raw_out, raw_err = await proc.communicate()
        return (
            raw_out.decode("utf-8", errors="replace"),
            raw_err.decode("utf-8", errors="replace"),
            proc.returncode,
        )

    async def git_status_tool() -> Dict[str, Any]:
        """Return git status --short and git diff --stat."""
        status_out, status_err, status_rc = await _run_git("status", "--short")
        if status_rc != 0:
            return {"error": status_err.strip() or "Not a git repository"}
        diff_out, _, _ = await _run_git("diff", "--stat")
        return {"status": status_out.strip(), "diff_stat": diff_out.strip()}

    async def git_diff_tool(
        file_path: str = "", staged: bool = False
    ) -> Dict[str, Any]:
        """Return git diff output for a file or the whole repo."""
        args = ["diff"]
        if staged:
            args.append("--staged")
        if file_path:
            args += ["--", file_path]
        out, err, rc = await _run_git(*args)
        if rc != 0:
            return {"diff": "", "truncated": False, "error": err.strip()}
        truncated = len(out) > 6000
        return {"diff": out[:6000], "truncated": truncated}

    async def git_log_tool(
        max_entries: int = 10, file_path: str = ""
    ) -> Dict[str, Any]:
        """Return the last N commits from git log --oneline."""
        args = ["log", "--oneline", f"-{max_entries}"]
        if file_path:
            args += ["--", file_path]
        out, err, rc = await _run_git(*args)
        if rc != 0:
            return {"log": "", "error": err.strip()}
        return {"log": out.strip()}

    async def git_commit_tool(message: str, files: List[str] = None) -> Dict[str, Any]:
        """Stage and commit changes."""
        if not message or not message.strip():
            return {"success": False, "output": "Commit message cannot be empty"}

        if plan_mode:
            return {
                "plan_only": True,
                "would_do": f"Commit with message: '{message}'",
                "files": files or [],
            }

        files = files or []

        if files:
            for f in files:
                _, err = _resolve_safe_path(f)
                if err:
                    return {"success": False, "output": err}
            add_args = ["add"] + files
        else:
            add_args = ["add", "-A"]

        add_out, add_err, add_rc = await _run_git(*add_args)
        if add_rc != 0:
            return {"success": False, "output": f"git add failed: {add_err.strip()}"}

        commit_out, commit_err, commit_rc = await _run_git("commit", "-m", message)
        if commit_rc != 0:
            return {
                "success": False,
                "output": f"git commit failed: {commit_err.strip()}",
            }

        return {"success": True, "output": commit_out.strip()}

    # ── End of file editing tools ─────────────────────────────────────────────

    prompts = _get_tool_prompts(profile)
    sql_integrations = _get_sql_integrations(profile)
    sql_integration = sql_integrations[0][1] if sql_integrations else None

    if sql_integration is not None and "search_documents" not in (
        json.loads(profile.tool_prompts)
        if getattr(profile, "tool_prompts", None)
        else {}
    ):
        prompts["search_documents"] = (
            "Search for information in the user's uploaded documents (PDFs, Excel). "
            "Do NOT use for database queries — use query_database instead. "
            "Use only when the user asks about uploaded files or documents."
        )

    disabled = set(getattr(profile, "disabled_tools", None) or [])

    def _tool(name, description, func, schema):
        if name in disabled:
            return None
        return StructuredTool(
            name=name,
            description=description,
            func=func,
            args_schema=schema,
            coroutine=func,
        )

    def _available_workflows() -> Dict[str, Dict[str, Any]]:
        """Every workflow this profile can run, keyed by name."""
        from src.core.platform.functions.global_workflows import get_available_workflows

        found: Dict[str, Dict[str, Any]] = {}
        raw = getattr(profile, "functions", None)
        if raw:
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(parsed, dict):
                    parsed = parsed.get("functions", [parsed])
                for item in parsed or []:
                    if isinstance(item, dict) and item.get("type") == "workflow" and item.get("name"):
                        found[item["name"]] = item
            except (json.JSONDecodeError, TypeError):
                logger.warning("Profile functions are not valid JSON; skipping workflows")

        try:
            for workflow in get_available_workflows(profile) or []:
                if workflow.get("name"):
                    found.setdefault(workflow["name"], workflow)
        except Exception:
            logger.warning("Could not load global workflows", exc_info=True)
        return found

    async def run_workflow_tool(workflow_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run a configured workflow through the workflow engine.

        The streaming path used to hand the model a list of endpoints and tell
        it to curl them, which skipped parameter substitution, the auth headers
        and the step chaining entirely.
        """
        from src.core.platform.functions.workflow_executor import WorkflowExecutor

        workflows = _available_workflows()
        workflow = workflows.get(workflow_name)
        if not workflow:
            return {
                "error": f"Workflow '{workflow_name}' is not configured.",
                "available": sorted(workflows.keys()),
            }

        if plan_mode:
            return {
                "plan_only": True,
                "would_do": f"Run workflow '{workflow_name}' ({len(workflow.get('steps', []))} steps)",
                "diff": json.dumps(params or {}, ensure_ascii=False)[:500],
            }

        try:
            return await WorkflowExecutor().execute_workflow(
                workflow=workflow,
                input_params=params or {},
                profile=profile,
                auth_token=auth_token or None,
            )
        except Exception as e:
            logger.error(f"run_workflow '{workflow_name}' failed: {e}", exc_info=True)
            return {"error": str(e), "workflow_name": workflow_name}

    async def fetch_url_tool(url: str) -> Dict[str, Any]:
        """Fetch and extract text from a URL."""
        import httpx
        from html.parser import HTMLParser

        class _TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self._text = []
                self._skip = False

            def handle_starttag(self, tag, attrs):
                if tag in ("script", "style", "nav", "footer", "header"):
                    self._skip = True

            def handle_endtag(self, tag):
                if tag in ("script", "style", "nav", "footer", "header"):
                    self._skip = False

            def handle_data(self, data):
                if not self._skip:
                    stripped = data.strip()
                    if stripped:
                        self._text.append(stripped)

            def get_text(self):
                return " ".join(self._text)

        if not url.startswith("http"):
            url = "https://" + url
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                parser = _TextExtractor()
                parser.feed(resp.text)
                text = parser.get_text()[:4000]  # cap to avoid token overflow
                return {"url": url, "content": text}
        except Exception as e:
            logger.error(f"fetch_url error for {url}: {e}")
            return {"error": str(e), "url": url}

    async def download_file_tool(
        url: str,
        save_as: Optional[str] = None,
        create_dirs: bool = True,
    ) -> Dict[str, Any]:
        """Download a file from a URL and save it inside the workspace."""
        import mimetypes
        from urllib.parse import urlparse, unquote
        import httpx

        def _infer_name(final_url: str, content_type: str) -> str:
            parsed = urlparse(final_url)
            candidate = _Path(unquote(parsed.path)).name.strip()
            if candidate and candidate not in {".", "..", "/"}:
                return candidate

            base = "downloaded_file"
            clean_type = (content_type or "").split(";")[0].strip().lower()
            ext = mimetypes.guess_extension(clean_type) if clean_type else ""
            if clean_type == "image/jpg":
                ext = ".jpg"
            return base + (ext or "")

        if not url.startswith(("http://", "https://")):
            return {"error": "Only HTTP and HTTPS URLs are supported", "url": url}

        if plan_mode:
            inferred = save_as or _infer_name(url, "")
            return {
                "plan_only": True,
                "would_do": f"Download '{url}' to '{inferred}'",
            }

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
                response = await client.get(
                    url, headers={"User-Agent": "Mozilla/5.0 (gillie-ai)"}
                )
                response.raise_for_status()

            final_url = str(response.url)
            content_type = response.headers.get("content-type", "")
            output_name = save_as or _infer_name(final_url, content_type)

            resolved, err = _resolve_safe_path(output_name)
            if err:
                return {"error": err, "url": url, "save_as": output_name}
            if _is_ignored(resolved, workspace):
                return {
                    "error": f"Access denied: '{output_name}' is excluded by .gillierignore",
                    "url": url,
                    "save_as": output_name,
                }

            if create_dirs:
                resolved.parent.mkdir(parents=True, exist_ok=True)

            resolved.write_bytes(response.content)

            return {
                "success": True,
                "url": url,
                "final_url": final_url,
                "path": str(resolved.relative_to(workspace)),
                "saved_to": str(resolved),
                "bytes": len(response.content),
                "content_type": content_type or "application/octet-stream",
                "status_code": response.status_code,
            }
        except Exception as e:
            logger.error(f"download_file error for {url}: {e}")
            return {"error": str(e), "url": url, "save_as": save_as}

    async def web_search_tool(query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the internet using DuckDuckGo."""
        import asyncio

        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return {
                "error": "duckduckgo-search not installed. Run: pip install duckduckgo-search"
            }

        backends = ["lite", "html", "api"]
        last_error = None

        for attempt, backend in enumerate(backends):
            if attempt > 0:
                await asyncio.sleep(1)
            try:
                results = []
                with DDGS() as ddgs:
                    for r in ddgs.text(query, max_results=max_results, backend=backend):
                        results.append(
                            {
                                "title": r.get("title", ""),
                                "url": r.get("href", ""),
                                "snippet": r.get("body", ""),
                            }
                        )
                if results:
                    logger.info(
                        f"web_search: {len(results)} results via backend='{backend}'"
                    )
                    return {"found": True, "query": query, "results": results}
                last_error = f"backend={backend} returned no results"
            except Exception as e:
                last_error = str(e)
                logger.warning(f"web_search backend='{backend}' failed: {e}")

        return {
            "found": False,
            "error": last_error,
            "message": f"All backends failed: {last_error}",
        }

    async def owner_insights_tool(
        contact_id: Optional[str] = None, memory_limit: int = 200
    ) -> Dict[str, Any]:
        """Fetch owner-level counts from backend endpoints."""
        import httpx

        base_url = os.getenv("GILLIE_API_BASE_URL", "http://localhost:8000").rstrip("/")
        active_api_key = next(
            (
                k.value
                for k in (getattr(profile, "api_keys", None) or [])
                if getattr(k, "is_active", False) and getattr(k, "value", None)
            ),
            None,
        )

        headers: Dict[str, str] = {}
        if active_api_key:
            headers["x-api-key"] = active_api_key

        endpoint_errors: Dict[str, str] = {}
        contacts_payload: Any = []
        conversations_payload: Any = []
        memories_payload: Any = {"data": [], "has_more": False, "next_offset": None}

        timeout = httpx.Timeout(15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                contacts_resp = await client.get(
                    f"{base_url}/profile/contacts", headers=headers
                )
                contacts_resp.raise_for_status()
                contacts_payload = contacts_resp.json()
            except Exception as e:
                endpoint_errors["contacts"] = str(e)

            try:
                conv_resp = await client.get(
                    f"{base_url}/conversation/user", headers=headers
                )
                conv_resp.raise_for_status()
                conversations_payload = conv_resp.json()
            except Exception as e:
                endpoint_errors["conversations"] = str(e)

            memory_params: Dict[str, Any] = {"limit": memory_limit, "offset": 0}
            if contact_id:
                memory_params["contact_id"] = contact_id
            try:
                memory_resp = await client.get(
                    f"{base_url}/api/v1/memory/owner/episodes",
                    headers=headers,
                    params=memory_params,
                )
                memory_resp.raise_for_status()
                memories_payload = memory_resp.json()
            except Exception as e:
                endpoint_errors["owner_memories"] = str(e)

        contacts_list = (
            contacts_payload
            if isinstance(contacts_payload, list)
            else contacts_payload.get("data", [])
            if isinstance(contacts_payload, dict)
            else []
        )
        conversations_list = (
            conversations_payload
            if isinstance(conversations_payload, list)
            else conversations_payload.get("data", [])
            if isinstance(conversations_payload, dict)
            else []
        )
        memory_items = (
            memories_payload.get("data", [])
            if isinstance(memories_payload, dict)
            else []
        )

        contact_index: Dict[str, Dict[str, Any]] = {}
        for c in contacts_list:
            if not isinstance(c, dict):
                continue
            cid = c.get("id") or c.get("contact_id")
            if not cid:
                continue
            contact_index[cid] = {
                "contact_id": cid,
                "name": c.get("name") or c.get("contact_name") or "",
                "conversation_count": 0,
                "memory_count": 0,
            }

        owner_conversation_count = 0
        for conv in conversations_list:
            if not isinstance(conv, dict):
                continue
            conv_contact_id = conv.get("contact_id")
            if conv_contact_id:
                if conv_contact_id not in contact_index:
                    contact_index[conv_contact_id] = {
                        "contact_id": conv_contact_id,
                        "name": conv.get("contact_name") or "",
                        "conversation_count": 0,
                        "memory_count": 0,
                    }
                contact_index[conv_contact_id]["conversation_count"] += 1
            else:
                owner_conversation_count += 1

        owner_memory_count = 0
        for mem in memory_items:
            if not isinstance(mem, dict):
                continue
            scope = mem.get("memory_scope_id") or ""
            inferred_contact_id = None
            marker = "__contact__"
            if marker in scope:
                inferred_contact_id = scope.split(marker, 1)[1] or None

            if inferred_contact_id:
                if inferred_contact_id not in contact_index:
                    contact_index[inferred_contact_id] = {
                        "contact_id": inferred_contact_id,
                        "name": "",
                        "conversation_count": 0,
                        "memory_count": 0,
                    }
                contact_index[inferred_contact_id]["memory_count"] += 1
            else:
                owner_memory_count += 1

        contacts_summary = list(contact_index.values())
        if contact_id:
            contacts_summary = [
                row for row in contacts_summary if row.get("contact_id") == contact_id
            ]

        return {
            "ok": len(endpoint_errors) < 3,
            "base_url": base_url,
            "filter": {"contact_id": contact_id, "memory_limit": memory_limit},
            "totals": {
                "contacts": len(contacts_list),
                "conversations": len(conversations_list),
                "owner_only_conversations": owner_conversation_count,
                "owner_memories_scanned": len(memory_items),
                "owner_only_memories": owner_memory_count,
            },
            "contacts": contacts_summary,
            "memory_pagination": {
                "has_more": bool(memories_payload.get("has_more", False))
                if isinstance(memories_payload, dict)
                else False,
                "next_offset": memories_payload.get("next_offset")
                if isinstance(memories_payload, dict)
                else None,
            },
            "errors": endpoint_errors,
            "note": "Counts are aggregated from /profile/contacts, /conversation/user and /api/v1/memory/owner/episodes.",
        }

    tools = list(
        filter(
            None,
            [
                _tool(
                    "run_workflow",
                    prompts.get("run_workflow", _DEFAULT_TOOL_PROMPTS["run_workflow"]),
                    run_workflow_tool,
                    RunWorkflowArgs,
                ),
                _tool(
                    "fetch_url",
                    prompts.get("fetch_url", _DEFAULT_TOOL_PROMPTS["fetch_url"]),
                    fetch_url_tool,
                    FetchUrlArgs,
                ),
                _tool(
                    "download_file",
                    prompts.get(
                        "download_file", _DEFAULT_TOOL_PROMPTS["download_file"]
                    ),
                    download_file_tool,
                    DownloadFileArgs,
                ),
                _tool(
                    "web_search",
                    prompts.get("web_search", _DEFAULT_TOOL_PROMPTS["web_search"]),
                    web_search_tool,
                    WebSearchArgs,
                ),
                _tool(
                    "owner_insights",
                    prompts.get(
                        "owner_insights", _DEFAULT_TOOL_PROMPTS["owner_insights"]
                    ),
                    owner_insights_tool,
                    OwnerInsightsArgs,
                ),
                _tool(
                    "read_file",
                    prompts.get("read_file", _DEFAULT_TOOL_PROMPTS["read_file"]),
                    read_file_tool,
                    ReadFileArgs,
                ),
                _tool(
                    "write_file",
                    prompts.get("write_file", _DEFAULT_TOOL_PROMPTS["write_file"]),
                    write_file_tool,
                    WriteFileArgs,
                ),
                _tool(
                    "edit_file",
                    prompts.get("edit_file", _DEFAULT_TOOL_PROMPTS["edit_file"]),
                    edit_file_tool,
                    EditFileArgs,
                ),
                _tool(
                    "list_directory",
                    prompts.get(
                        "list_directory", _DEFAULT_TOOL_PROMPTS["list_directory"]
                    ),
                    list_directory_tool,
                    ListDirectoryArgs,
                ),
                _tool(
                    "find_files",
                    prompts.get("find_files", _DEFAULT_TOOL_PROMPTS["find_files"]),
                    find_files_tool,
                    FindFilesArgs,
                ),
                _tool(
                    "run_shell",
                    prompts.get("run_shell", _DEFAULT_TOOL_PROMPTS["run_shell"]),
                    run_shell_tool,
                    RunShellArgs,
                ),
                _tool(
                    "grep_files",
                    prompts.get("grep_files", _DEFAULT_TOOL_PROMPTS["grep_files"]),
                    grep_files_tool,
                    GrepFilesArgs,
                ),
                _tool(
                    "repo_map",
                    prompts.get("repo_map", _DEFAULT_TOOL_PROMPTS["repo_map"]),
                    repo_map_tool,
                    RepoMapArgs,
                ),
                _tool(
                    "check_code",
                    prompts.get("check_code", _DEFAULT_TOOL_PROMPTS["check_code"]),
                    check_code_tool,
                    CheckCodeArgs,
                ),
                _tool(
                    "git_status",
                    prompts.get("git_status", _DEFAULT_TOOL_PROMPTS["git_status"]),
                    git_status_tool,
                    GitStatusArgs,
                ),
                _tool(
                    "git_diff",
                    prompts.get("git_diff", _DEFAULT_TOOL_PROMPTS["git_diff"]),
                    git_diff_tool,
                    GitDiffArgs,
                ),
                _tool(
                    "git_log",
                    prompts.get("git_log", _DEFAULT_TOOL_PROMPTS["git_log"]),
                    git_log_tool,
                    GitLogArgs,
                ),
                _tool(
                    "git_commit",
                    prompts.get("git_commit", _DEFAULT_TOOL_PROMPTS["git_commit"]),
                    git_commit_tool,
                    GitCommitArgs,
                ),
                _tool(
                    "search_images",
                    prompts["search_images"],
                    search_images_tool,
                    SearchImagesArgs,
                ),
                _tool(
                    "analyze_pdf",
                    prompts["analyze_pdf"],
                    analyze_pdf_tool,
                    AnalyzePDFArgs,
                ),
                _tool(
                    "extract_text_from_pdf",
                    prompts["extract_text_from_pdf"],
                    extract_text_tool,
                    ExtractTextArgs,
                ),
                _tool(
                    "analyze_excel",
                    prompts["analyze_excel"],
                    analyze_excel_tool,
                    AnalyzeExcelArgs,
                ),
                _tool(
                    "write_excel",
                    prompts["write_excel"],
                    write_excel_tool,
                    WriteExcelArgs,
                ),
                _tool("read_docx", prompts["read_docx"], read_docx_tool, ReadDocxArgs),
                _tool(
                    "write_docx", prompts["write_docx"], write_docx_tool, WriteDocxArgs
                ),
                _tool(
                    "modify_excel",
                    prompts["modify_excel"],
                    modify_excel_tool,
                    ModifyExcelArgs,
                ),
                _tool(
                    "modify_docx",
                    prompts["modify_docx"],
                    modify_docx_tool,
                    ModifyDocxArgs,
                ),
                _tool(
                    "insert_image_docx",
                    prompts.get(
                        "insert_image_docx", _DEFAULT_TOOL_PROMPTS["insert_image_docx"]
                    ),
                    insert_image_docx_tool,
                    InsertImageDocxArgs,
                ),
                _tool(
                    "insert_image_excel",
                    prompts.get(
                        "insert_image_excel",
                        _DEFAULT_TOOL_PROMPTS["insert_image_excel"],
                    ),
                    insert_image_excel_tool,
                    InsertImageExcelArgs,
                ),
                _tool(
                    "describe_image",
                    prompts["describe_image"],
                    describe_image_tool,
                    DescribeImageArgs,
                ),
                _tool(
                    "generate_image",
                    prompts.get(
                        "generate_image", _DEFAULT_TOOL_PROMPTS["generate_image"]
                    ),
                    generate_image_tool,
                    GenerateImageArgs,
                ),
                _tool(
                    "generate_video",
                    prompts.get(
                        "generate_video", _DEFAULT_TOOL_PROMPTS["generate_video"]
                    ),
                    generate_video_tool,
                    GenerateVideoArgs,
                ),
                _tool(
                    "send_file",
                    prompts.get("send_file", _DEFAULT_TOOL_PROMPTS["send_file"]),
                    send_file_tool,
                    SendFileArgs,
                ),
                _tool(
                    "send_screenshot",
                    prompts.get(
                        "send_screenshot", _DEFAULT_TOOL_PROMPTS["send_screenshot"]
                    ),
                    send_screenshot_tool,
                    SendScreenshotArgs,
                ),
                _tool(
                    "take_screenshot",
                    prompts.get(
                        "take_screenshot", _DEFAULT_TOOL_PROMPTS["take_screenshot"]
                    ),
                    take_screenshot_tool,
                    TakeScreenshotArgs,
                ),
                _tool(
                    "browser_connect",
                    prompts.get(
                        "browser_connect", _DEFAULT_TOOL_PROMPTS["browser_connect"]
                    ),
                    browser_connect_tool,
                    BrowserConnectArgs,
                ),
                _tool(
                    "browser_switch_tab",
                    prompts.get(
                        "browser_switch_tab",
                        _DEFAULT_TOOL_PROMPTS["browser_switch_tab"],
                    ),
                    browser_switch_tab_tool,
                    BrowserSwitchTabArgs,
                ),
                _tool(
                    "browser_evaluate",
                    prompts.get(
                        "browser_evaluate", _DEFAULT_TOOL_PROMPTS["browser_evaluate"]
                    ),
                    browser_evaluate_tool,
                    BrowserEvaluateArgs,
                ),
                _tool(
                    "browser_act",
                    prompts.get("browser_act", _DEFAULT_TOOL_PROMPTS["browser_act"]),
                    browser_act_tool,
                    BrowserActArgs,
                ),
                _tool(
                    "browser_extract",
                    prompts.get(
                        "browser_extract", _DEFAULT_TOOL_PROMPTS["browser_extract"]
                    ),
                    browser_extract_tool,
                    BrowserExtractArgs,
                ),
                _tool(
                    "browser_navigate",
                    prompts.get(
                        "browser_navigate", _DEFAULT_TOOL_PROMPTS["browser_navigate"]
                    ),
                    browser_navigate_tool,
                    BrowserNavigateArgs,
                ),
                _tool(
                    "browser_click",
                    prompts.get(
                        "browser_click", _DEFAULT_TOOL_PROMPTS["browser_click"]
                    ),
                    browser_click_tool,
                    BrowserClickArgs,
                ),
                _tool(
                    "browser_type",
                    prompts.get("browser_type", _DEFAULT_TOOL_PROMPTS["browser_type"]),
                    browser_type_tool,
                    BrowserTypeArgs,
                ),
                _tool(
                    "browser_get_content",
                    prompts.get(
                        "browser_get_content",
                        _DEFAULT_TOOL_PROMPTS["browser_get_content"],
                    ),
                    browser_get_content_tool,
                    BrowserGetContentArgs,
                ),
                _tool(
                    "browser_screenshot",
                    prompts.get(
                        "browser_screenshot",
                        _DEFAULT_TOOL_PROMPTS["browser_screenshot"],
                    ),
                    browser_screenshot_tool,
                    BrowserScreenshotArgs,
                ),
                _tool(
                    "browser_close",
                    prompts.get(
                        "browser_close", _DEFAULT_TOOL_PROMPTS["browser_close"]
                    ),
                    browser_close_tool,
                    BrowserCloseArgs,
                ),
                _tool(
                    "search_documents",
                    prompts["search_documents"],
                    search_documents_tool,
                    SearchDocumentsArgs,
                ),
                _tool(
                    "list_storage_files",
                    prompts["list_storage_files"],
                    list_storage_files_tool,
                    ListStorageFilesArgs,
                ),
            ],
        )
    )

    for _db_slug, _db_inst in sql_integrations:
        _query_tool_name = f"query_{_db_slug}"
        _exec_tool_name = f"execute_sql_{_db_slug}"

        def _make_query_fn(inst):
            async def _query(
                table: str,
                columns: List[str] = None,
                filters: Optional[str] = None,
                limit: int = 20,
            ) -> Dict[str, Any]:
                return await inst.query(
                    table=table, columns=columns or ["*"], filters=filters, limit=limit
                )

            return _query

        def _make_exec_fn(inst):
            async def _exec(sql: str) -> Dict[str, Any]:
                return await inst.execute(sql)

            return _exec

        if _query_tool_name not in disabled and "query_database" not in disabled:
            _qfn = _make_query_fn(_db_inst)
            _db_description = prompts.get(
                "query_database", _DEFAULT_TOOL_PROMPTS["query_database"]
            )
            _tables_summary = "; ".join(
                f"{name}: {desc}" if desc else name
                for name, desc in _db_inst.tables_info.items()
            )
            _db_description += (
                f" Base de datos: {_db_slug}. Tablas disponibles: {_tables_summary}."
            )

            tools.append(
                StructuredTool(
                    name=_query_tool_name,
                    description=_db_description,
                    func=_qfn,
                    args_schema=QueryDatabaseArgs,
                    coroutine=_qfn,
                )
            )

        if _exec_tool_name not in disabled and "execute_sql" not in disabled:
            _efn = _make_exec_fn(_db_inst)
            _ops = _db_inst.allowed_operations
            _ops_str = ", ".join(_ops) if _ops else "SELECT"
            _exec_description = (
                f"Execute a raw SQL statement on the '{_db_slug}' database. "
                f"Allowed operations: {_ops_str}. "
                f"Only these tables may be referenced: {', '.join(_db_inst.table_names)}. "
                f"Use for INSERT, UPDATE, DELETE or complex queries."
            )
            tools.append(
                StructuredTool(
                    name=_exec_tool_name,
                    description=_exec_description,
                    func=_efn,
                    args_schema=ExecuteSQLArgs,
                    coroutine=_efn,
                )
            )

    if skill_manager is not None:

        async def save_memory_tool(content: str, category: str = "General") -> str:
            soul_vector = (
                getattr(brain, "soul_vector", None) if brain is not None else None
            )
            if soul_vector is not None:
                stored = soul_vector.store_statement(profile.user_id, content, category)
                if stored:
                    return f"Guardado en memoria de largo plazo (Qdrant soul store) para el usuario {profile.user_id}."
                return "No se guardó en el soul store porque ya existía una entrada semánticamente similar."

            existing_id = skill_manager._find_similar_note(
                content, skill_manager.load_skill("facts")
            )
            if existing_id:
                return (
                    f"Ya existe una nota similar en memoria (ID {existing_id}). "
                    f"No se creó duplicado. Si quieres actualizar la información usa organize_memory."
                )
            note_id = skill_manager.save_memory_fact(content, category)
            return f"Guardado en memoria fallback (facts.skill.md) con ID {note_id}."

        async def search_memory_tool(query: str, max_results: int = 5) -> str:
            return skill_manager.search_memory(query, max_results)

        async def organize_memory_tool(new_content: str) -> str:
            skill_manager.overwrite_general_memory(new_content)
            return "general.skill.md reorganizado y actualizado correctamente como memoria nuclear."

        async def save_solution_tool(
            problem: str,
            solution: str,
            context: Optional[str] = None,
            effective: bool = True,
        ) -> str:
            existing_id = skill_manager._find_similar_note(
                problem, skill_manager.load_skill("solutions")
            )
            if existing_id:
                return (
                    f"Ya existe una solución similar en memoria (ID {existing_id}). "
                    f"No se creó duplicado."
                )
            solution_id = skill_manager.append_solution(
                problem, solution, context, effective
            )
            return f"Solución guardada en memoria (solutions.skill.md) con ID {solution_id}."

        if "save_memory" not in disabled:
            tools.append(
                StructuredTool(
                    name="save_memory",
                    description=prompts["save_memory"],
                    func=save_memory_tool,
                    args_schema=SaveMemoryArgs,
                    coroutine=save_memory_tool,
                )
            )
        if "search_memory" not in disabled:
            tools.append(
                StructuredTool(
                    name="search_memory",
                    description=prompts["search_memory"],
                    func=search_memory_tool,
                    args_schema=SearchMemoryArgs,
                    coroutine=search_memory_tool,
                )
            )
        if "organize_memory" not in disabled:
            tools.append(
                StructuredTool(
                    name="organize_memory",
                    description=prompts.get(
                        "organize_memory", _DEFAULT_TOOL_PROMPTS["organize_memory"]
                    ),
                    func=organize_memory_tool,
                    args_schema=OrganizeMemoryArgs,
                    coroutine=organize_memory_tool,
                )
            )
        if "save_solution" not in disabled:
            tools.append(
                StructuredTool(
                    name="save_solution",
                    description=prompts.get(
                        "save_solution", _DEFAULT_TOOL_PROMPTS["save_solution"]
                    ),
                    func=save_solution_tool,
                    args_schema=SaveSolutionArgs,
                    coroutine=save_solution_tool,
                )
            )

    if "system_propose" not in disabled or "system_confirm" not in disabled:
        from src.core.platform.tools.system_monitor import (
            propose_command,
            confirm_command,
            _requires_confirmation,
        )

        needs_confirmation = _requires_confirmation(profile)

        if "system_propose" not in disabled:

            async def system_propose_tool(command: str) -> Dict[str, Any]:
                return await propose_command(command, profile)

            if needs_confirmation:
                propose_desc = prompts.get(
                    "system_propose", _DEFAULT_TOOL_PROMPTS["system_propose"]
                )
            else:
                propose_desc = (
                    "Execute a shell command directly on the Linux server and return the output. "
                    "Use when the user asks to run a command or check server status (CPU, memory, disk, processes). "
                    "The command runs immediately — NO confirmation code is needed. "
                    "Just call this tool and show the user the result."
                )

            tools.append(
                StructuredTool(
                    name="system_propose",
                    description=propose_desc,
                    func=system_propose_tool,
                    args_schema=SystemProposeArgs,
                    coroutine=system_propose_tool,
                )
            )

        # system_confirm is only useful when confirmation is required
        if "system_confirm" not in disabled and needs_confirmation:

            async def system_confirm_tool(code: str) -> Dict[str, Any]:
                return await confirm_command(code)

            tools.append(
                StructuredTool(
                    name="system_confirm",
                    description=prompts.get(
                        "system_confirm", _DEFAULT_TOOL_PROMPTS["system_confirm"]
                    ),
                    func=system_confirm_tool,
                    args_schema=SystemConfirmArgs,
                    coroutine=system_confirm_tool,
                )
            )

    if job_usecases is not None:

        async def cron_create_tool(
            name: str,
            cron_expr: str,
            source_type: str,
            source_params: Dict[str, Any] = None,
            destination_type: str = "none",
            destination_params: Dict[str, Any] = None,
            message_template: str = "{{output}}",
            description: str = "",
        ) -> Dict[str, Any]:
            from src.schemas.job import JobInput

            job_input = JobInput(
                name=name,
                cron_expr=cron_expr,
                source_type=source_type,
                source_params=source_params or {},
                destination_type=destination_type,
                destination_params=destination_params or {},
                message_template=message_template,
                description=description,
            )
            result = job_usecases.create_usecase.execute(job_input, profile.user_id)
            return {
                "job_id": result.data.id,
                "name": result.data.name,
                "cron_expr": result.data.cron_expr,
                "status": "created",
            }

        async def cron_list_tool() -> Dict[str, Any]:
            result = job_usecases.list_usecase.execute(profile.user_id)
            return {
                "jobs": [
                    {
                        "id": j.id,
                        "name": j.name,
                        "cron_expr": j.cron_expr,
                        "source_type": j.source_type,
                        "destination_type": j.destination_type,
                        "enabled": j.enabled,
                        "status": j.status,
                        "last_run_at": j.last_run_at,
                    }
                    for j in result.data
                ]
            }

        async def cron_delete_tool(job_id: str) -> Dict[str, Any]:
            job_usecases.delete_usecase.execute(job_id)
            return {"deleted": True, "job_id": job_id}

        async def cron_run_tool(job_id: str) -> Dict[str, Any]:
            result = await job_usecases.run_usecase.execute(job_id)
            return {"status": result.status, "result": result.result}

        if "cron_create" not in disabled:
            tools.append(
                StructuredTool(
                    name="cron_create",
                    description=prompts.get(
                        "cron_create", _DEFAULT_TOOL_PROMPTS["cron_create"]
                    ),
                    func=cron_create_tool,
                    args_schema=CronCreateArgs,
                    coroutine=cron_create_tool,
                )
            )
        if "cron_list" not in disabled:
            tools.append(
                StructuredTool(
                    name="cron_list",
                    description=prompts.get(
                        "cron_list", _DEFAULT_TOOL_PROMPTS["cron_list"]
                    ),
                    func=cron_list_tool,
                    args_schema=None,
                    coroutine=cron_list_tool,
                )
            )
        if "cron_delete" not in disabled:
            tools.append(
                StructuredTool(
                    name="cron_delete",
                    description=prompts.get(
                        "cron_delete", _DEFAULT_TOOL_PROMPTS["cron_delete"]
                    ),
                    func=cron_delete_tool,
                    args_schema=CronDeleteArgs,
                    coroutine=cron_delete_tool,
                )
            )
        if "cron_run" not in disabled:
            tools.append(
                StructuredTool(
                    name="cron_run",
                    description=prompts.get(
                        "cron_run", _DEFAULT_TOOL_PROMPTS["cron_run"]
                    ),
                    func=cron_run_tool,
                    args_schema=CronRunArgs,
                    coroutine=cron_run_tool,
                )
            )

    if "read_pptx" not in disabled:
        tools.append(
            StructuredTool(
                name="read_pptx",
                description=prompts.get(
                    "read_pptx", _DEFAULT_TOOL_PROMPTS["read_pptx"]
                ),
                func=read_pptx_tool,
                args_schema=ReadPptxArgs,
                coroutine=read_pptx_tool,
            )
        )
    if "write_pptx" not in disabled:
        tools.append(
            StructuredTool(
                name="write_pptx",
                description=prompts.get(
                    "write_pptx", _DEFAULT_TOOL_PROMPTS["write_pptx"]
                ),
                func=write_pptx_tool,
                args_schema=WritePptxArgs,
                coroutine=write_pptx_tool,
            )
        )
    if "modify_pptx" not in disabled:
        tools.append(
            StructuredTool(
                name="modify_pptx",
                description=prompts.get(
                    "modify_pptx", _DEFAULT_TOOL_PROMPTS["modify_pptx"]
                ),
                func=modify_pptx_tool,
                args_schema=ModifyPptxArgs,
                coroutine=modify_pptx_tool,
            )
        )
    if "insert_image_pptx" not in disabled:
        tools.append(
            StructuredTool(
                name="insert_image_pptx",
                description=prompts.get(
                    "insert_image_pptx", _DEFAULT_TOOL_PROMPTS["insert_image_pptx"]
                ),
                func=insert_image_pptx_tool,
                args_schema=InsertImagePptxArgs,
                coroutine=insert_image_pptx_tool,
            )
        )

    if avatar_mcp is not None and avatar_mcp.avatar_available():

        async def avatar_play_animation_tool(animation: str) -> Dict[str, Any]:
            requested = animation
            animation = normalize_avatar_animation(animation)
            if animation not in AVATAR_ANIMATIONS:
                logger.warning("Avatar animation not installed: %r", requested)
                return {
                    "success": False,
                    "error": f"Unsupported avatar animation: {animation}",
                    "valid": list(AVATAR_ANIMATIONS),
                }
            if not await avatar_mcp.avatar_play_animation(animation):
                return {
                    "success": False,
                    "error": "The avatar app is not reachable, so the gesture was not played.",
                    "animation": animation,
                }
            return {"success": True, "animation": animation}

        async def avatar_control_window_tool(action: str) -> Dict[str, Any]:
            action = str(action).strip().lower()
            if action not in {"show", "hide", "toggle"}:
                return {
                    "success": False,
                    "error": f"Unsupported avatar window action: {action}",
                    "valid": ["show", "hide", "toggle"],
                }
            if not await avatar_mcp.avatar_control_window(action):
                return {
                    "success": False,
                    "error": "The avatar app is not reachable, so the window was not changed.",
                    "action": action,
                }
            return {"success": True, "action": action}

        async def avatar_get_status_tool() -> Dict[str, Any]:
            return await avatar_mcp.avatar_status()

        tools.extend(
            [
                StructuredTool(
                    name="avatar_play_animation",
                    description="Make a deliberate gesture with your own body, which the user can see on screen. Use it when you want to dance, wave, greet, or react. Afterwards refer to it in the first person: you danced, not the avatar. Your talking motion and lip sync happen on their own — never call this to look like you are speaking.",
                    func=avatar_play_animation_tool,
                    args_schema=AvatarPlayAnimationArgs,
                    coroutine=avatar_play_animation_tool,
                ),
                StructuredTool(
                    name="avatar_control_window",
                    description="Show or hide yourself on the user's screen.",
                    func=avatar_control_window_tool,
                    args_schema=AvatarControlWindowArgs,
                    coroutine=avatar_control_window_tool,
                ),
                StructuredTool(
                    name="avatar_get_status",
                    description="Check whether you are currently visible on screen and whether you are speaking.",
                    func=avatar_get_status_tool,
                    args_schema=None,
                    coroutine=avatar_get_status_tool,
                ),
            ]
        )

    # -------------------------------------------------------------------------
    # Google Calendar tools — only registered when integration is active
    # -------------------------------------------------------------------------
    _calendar_active = any(
        getattr(i, "name", None) == "google_calendar" and getattr(i, "activated", False)
        for i in (getattr(profile, "integrations", None) or [])
    )
    if _calendar_active:
        import httpx as _httpx

        _api_key = next(
            (
                k.value
                for k in (getattr(profile, "api_keys", None) or [])
                if k.is_active
            ),
            None,
        )
        _cal_base = "http://localhost:8000/api/v1/calendar"
        _cal_headers = (
            {"Authorization": f"Bearer {_api_key}", "Content-Type": "application/json"}
            if _api_key
            else {}
        )

        class CalendarListEventsArgs(BaseModel):
            start_date: Optional[str] = Field(
                None, description="Start date filter ISO 8601, e.g. 2025-06-01T00:00:00"
            )
            end_date: Optional[str] = Field(
                None, description="End date filter ISO 8601, e.g. 2025-06-30T23:59:59"
            )
            limit: Optional[int] = Field(
                None, description="Max number of events to return"
            )

        class CalendarCreateEventArgs(BaseModel):
            title: str = Field(..., description="Event title")
            start_time: str = Field(
                ..., description="Start datetime ISO 8601, e.g. 2025-06-10T10:00:00"
            )
            end_time: str = Field(
                ..., description="End datetime ISO 8601, e.g. 2025-06-10T11:00:00"
            )
            description: Optional[str] = Field("", description="Event description")
            location: Optional[str] = Field("", description="Event location")

        class CalendarUpdateEventArgs(BaseModel):
            event_id: str = Field(..., description="ID of the event to update")
            title: Optional[str] = Field(None, description="New title")
            start_time: Optional[str] = Field(
                None, description="New start datetime ISO 8601"
            )
            end_time: Optional[str] = Field(
                None, description="New end datetime ISO 8601"
            )
            description: Optional[str] = Field(None, description="New description")
            location: Optional[str] = Field(None, description="New location")

        class CalendarDeleteEventArgs(BaseModel):
            event_id: str = Field(..., description="ID of the event to delete")

        async def calendar_list_events_tool(
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            limit: Optional[int] = None,
        ) -> Dict[str, Any]:
            params = {}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            if limit:
                params["limit"] = limit
            async with _httpx.AsyncClient(timeout=30) as client:
                r = await client.get(
                    f"{_cal_base}/events", headers=_cal_headers, params=params
                )
                return r.json()

        async def calendar_create_event_tool(
            title: str,
            start_time: str,
            end_time: str,
            description: Optional[str] = "",
            location: Optional[str] = "",
        ) -> Dict[str, Any]:
            body = {
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "description": description or "",
                "location": location or "",
            }
            async with _httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    f"{_cal_base}/events", headers=_cal_headers, json=body
                )
                return r.json()

        async def calendar_update_event_tool(
            event_id: str,
            title: Optional[str] = None,
            start_time: Optional[str] = None,
            end_time: Optional[str] = None,
            description: Optional[str] = None,
            location: Optional[str] = None,
        ) -> Dict[str, Any]:
            body = {
                k: v
                for k, v in {
                    "title": title,
                    "start_time": start_time,
                    "end_time": end_time,
                    "description": description,
                    "location": location,
                }.items()
                if v is not None
            }
            async with _httpx.AsyncClient(timeout=30) as client:
                r = await client.put(
                    f"{_cal_base}/events/{event_id}", headers=_cal_headers, json=body
                )
                return r.json()

        async def calendar_delete_event_tool(event_id: str) -> Dict[str, Any]:
            async with _httpx.AsyncClient(timeout=30) as client:
                r = await client.delete(
                    f"{_cal_base}/events/{event_id}", headers=_cal_headers
                )
                if r.status_code == 204:
                    return {"success": True, "message": "Event deleted"}
                return r.json()

        tools.append(
            StructuredTool(
                name="calendar_list_events",
                description="List the user's Google Calendar events. Optionally filter by start_date and end_date (ISO 8601). Use when the user asks what events, meetings or appointments they have.",
                func=calendar_list_events_tool,
                args_schema=CalendarListEventsArgs,
                coroutine=calendar_list_events_tool,
            )
        )
        tools.append(
            StructuredTool(
                name="calendar_create_event",
                description="Create a new Google Calendar event. Requires title, start_time and end_time in ISO 8601 (e.g. 2025-06-10T10:00:00). Use when the user asks to create, add, schedule or book an event.",
                func=calendar_create_event_tool,
                args_schema=CalendarCreateEventArgs,
                coroutine=calendar_create_event_tool,
            )
        )
        tools.append(
            StructuredTool(
                name="calendar_update_event",
                description="Update an existing Google Calendar event by its ID. Can change title, start_time, end_time, description or location.",
                func=calendar_update_event_tool,
                args_schema=CalendarUpdateEventArgs,
                coroutine=calendar_update_event_tool,
            )
        )
        tools.append(
            StructuredTool(
                name="calendar_delete_event",
                description="Delete a Google Calendar event by its ID. Use when the user asks to delete, remove or cancel an event.",
                func=calendar_delete_event_tool,
                args_schema=CalendarDeleteEventArgs,
                coroutine=calendar_delete_event_tool,
            )
        )
        logger.info("Google Calendar tools registered (integration active)")

    return tools
