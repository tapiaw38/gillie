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
    "describe_image": (
        "Describe the visual content of an image using its URL. "
        "Use after search_images returns image URLs and the user wants to know what an image shows."
    ),
    "search_documents": (
        "Search for information in the user's uploaded documents. "
        "Use when the user asks a question that may be answered by their uploaded files."
    ),
    "query_database": (
        "Query the LIVE connected PostgreSQL database and return actual rows of data. "
        "Use this tool — NOT code exploration tools — when the user asks about records, "
        "tables, data, or wants to verify/inspect what is stored in the database. "
        "Do NOT use repo_map, find_files, or read_file for database questions."
    ),
    "fetch_url": (
        "Fetch and extract the text content of a specific web page URL. "
        "Use when the user mentions a specific website by name or URL "
        "(e.g. 'consulta en dolarhoy', 'abre infobae.com', 'revisa la página X'). "
        "Prepend https:// if the user gives a domain without protocol."
    ),
    "web_search": (
        "Search the internet for current, real-time information using DuckDuckGo. "
        "Use when the user asks about recent news, current events, live data, prices, "
        "or any information that may have changed after the model's training cutoff. "
        "Also use when the user explicitly asks to 'search the web', 'look it up online', "
        "'busca en internet', 'busca en google', or similar phrases."
    ),
    "organize_memory": (
        "Reorganize and deduplicate general.skill.md. "
        "Use when the user asks to organize, clean, or consolidate memory. "
        "WORKFLOW: 1) Read the current general.skill.md content from context. "
        "2) Merge duplicate or overlapping notes into single coherent entries. "
        "3) Call this tool with the consolidated content as the new_content argument. "
        "The file will be fully replaced with your organized version. "
        "Preserve all unique information — only merge actual duplicates."
    ),
    "save_memory": (
        "Save important information to long-term memory (general.skill.md). "
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
    "take_screenshot": (
        "Take a screenshot of the current desktop screen and describe what is visible. "
        "Use when the user asks what is on their screen, what windows are open, "
        "what a specific application looks like, or anything about the visual state "
        "of the desktop. Optionally focus on a specific region or window."
    ),
    "browser_navigate": (
        "Open a URL in a headless browser and return the page title and visible text. "
        "Use to visit websites, web apps, or local URLs. The browser session persists "
        "across tool calls so you can navigate, interact, then read content."
    ),
    "browser_click": (
        "Click an element in the current browser page by CSS selector or visible text. "
        "Examples: 'button#submit', 'text=Login', '.nav-item:first-child'. "
        "Use after browser_navigate to interact with the page."
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
        "Disconnect from the browser session. When connected to a real browser via "
        "browser_connect, this only disconnects without closing the user's browser."
    ),
    "browser_connect": (
        "Connect to an already-running Chrome, Chromium, or Firefox browser via CDP "
        "(Chrome DevTools Protocol). Use this when the user wants the AI to control "
        "their real browser with their existing session, cookies, and open tabs "
        "(e.g. WhatsApp Web, Gmail, any logged-in site). "
        "The user must start their browser with --remote-debugging-port=9222. "
        "After connecting, all browser_* tools operate on the real browser. "
        "Lists all open tabs so you can switch to the right one."
    ),
    "browser_switch_tab": (
        "Switch the active browser tab to a specific index. "
        "Use after browser_connect lists the open tabs to select the right one."
    ),
    "browser_enable_remote_debug": (
        "Enable Chrome DevTools Protocol (CDP) remote debugging in Firefox permanently "
        "by writing user.js to the Firefox profile. After running this tool, the user "
        "only needs to restart Firefox once — Firefox will restore the session automatically. "
        "Use this when the user wants the AI to control their existing Firefox browser "
        "but it was not started with --remote-debugging-port."
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


class WriteExcelArgs(BaseModel):
    """Arguments for creating or modifying an Excel file"""
    path: str = Field(description="Path to the Excel file to create or modify (e.g. 'report.xlsx')")
    sheets: dict = Field(description=(
        "Dict of sheet_name -> list of rows. Each row is a list of cell values. "
        "First row is treated as headers. Example: {'Sheet1': [['Name','Age'],['Ana',30]]}"
    ))
    mode: str = Field(default="overwrite", description="'overwrite' to replace the file, 'update' to modify existing sheets")


class ReadDocxArgs(BaseModel):
    """Arguments for reading a Word document"""
    file_name: str = Field(description="Name (or partial name) of the .docx file, e.g. 'report.docx'")


class WriteDocxArgs(BaseModel):
    """Arguments for creating or modifying a Word document"""
    path: str = Field(description="Path to the .docx file to create or modify (e.g. 'report.docx')")
    content: str = Field(description=(
        "Document content in a simple markdown-like format:\n"
        "# Heading 1\n## Heading 2\n### Heading 3\n"
        "Regular paragraph text.\n**bold** and *italic* inline.\n"
        "- bullet item\n1. numbered item"
    ))
    mode: str = Field(default="overwrite", description="'overwrite' to replace the file, 'append' to add content at the end")


class ModifyExcelArgs(BaseModel):
    """Arguments for modifying an existing Excel file"""
    file_name: str = Field(description="Name of the Excel file in profile files or workspace (e.g. 'ventas.xlsx')")
    operations: List[dict] = Field(description=(
        "List of operations to apply. Each operation is a dict with 'type' and params:\n"
        "- update_cell: {type, sheet, row (1-based int), col (letter or 1-based int), value}\n"
        "- add_row: {type, sheet, data (list of values)}\n"
        "- delete_row: {type, sheet, row (1-based int)}\n"
        "- add_sheet: {type, name, rows (list of lists)}\n"
        "- rename_sheet: {type, old_name, new_name}\n"
        "- delete_sheet: {type, name}"
    ))
    save_as: Optional[str] = Field(default=None, description="Output filename in workspace. Defaults to same name as input.")
    re_upload: bool = Field(default=False, description="If True, re-upload the modified file to storage after saving")


class ModifyDocxArgs(BaseModel):
    """Arguments for modifying an existing Word document"""
    file_name: str = Field(description="Name of the .docx file in profile files or workspace (e.g. 'report.docx')")
    replacements: Optional[List[dict]] = Field(default=None, description=(
        "List of text replacements: [{old: 'text to find', new: 'replacement text'}]"
    ))
    append: Optional[str] = Field(default=None, description="Markdown-like content to append at the end of the document")
    save_as: Optional[str] = Field(default=None, description="Output filename in workspace. Defaults to same name as input.")
    re_upload: bool = Field(default=False, description="If True, re-upload the modified file to storage after saving")


class DescribeImageArgs(BaseModel):
    """Arguments for describing an image"""
    image_url: str = Field(
        description="URL of the image to describe (e.g. obtained from search_images results)"
    )


class TakeScreenshotArgs(BaseModel):
    """Arguments for taking a screenshot"""
    question: str = Field(
        default="Describe what is visible on the screen.",
        description="What to look for or describe in the screenshot (e.g. 'what tabs are open in Firefox?')"
    )


class BrowserNavigateArgs(BaseModel):
    url: str = Field(description="URL to navigate to (include https://)")
    wait_for: str = Field(default="load", description="Wait condition: 'load', 'domcontentloaded', or 'networkidle'")


class BrowserClickArgs(BaseModel):
    selector: str = Field(description="CSS selector or visible text to click (e.g. 'button#submit', 'text=Login')")


class BrowserTypeArgs(BaseModel):
    selector: str = Field(description="CSS selector of the input field (e.g. 'input[name=email]')")
    text: str = Field(description="Text to type into the field")
    clear_first: bool = Field(default=True, description="Clear the field before typing")


class BrowserGetContentArgs(BaseModel):
    selector: str = Field(default="", description="CSS selector to extract content from, or empty for full page text")
    as_html: bool = Field(default=False, description="Return raw HTML instead of visible text")


class BrowserScreenshotArgs(BaseModel):
    selector: str = Field(default="", description="CSS selector to screenshot a specific element, or empty for full page")
    question: str = Field(default="Describe what is visible on this page.", description="What to look for in the screenshot")


class BrowserCloseArgs(BaseModel):
    pass


class BrowserConnectArgs(BaseModel):
    cdp_url: str = Field(
        default="http://localhost:9222",
        description="CDP endpoint of the running browser (default: http://localhost:9222)"
    )


class BrowserSwitchTabArgs(BaseModel):
    index: int = Field(description="Tab index to switch to (shown by browser_connect)")


class BrowserEnableRemoteDebugArgs(BaseModel):
    port: int = Field(default=9222, description="Port for CDP remote debugging (default: 9222)")


class BrowserEvaluateArgs(BaseModel):
    script: str = Field(description="JavaScript code to execute in the current page context. Return values are serialized to JSON.")


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
    cron_expr: str = Field(description="5-field cron expression, e.g. '*/5 * * * *' for every 5 minutes, '0 8 * * *' for daily at 8am")
    source_type: str = Field(description="Source type: 'system_command' (run shell command), 'http_get' (HTTP GET request), 'static' (fixed text)")
    source_params: Dict[str, Any] = Field(default_factory=dict, description="Source parameters. For system_command: {'command': 'free -m'}. For http_get: {'url': 'https://...'}. For static: {'text': 'Hello'}.")
    destination_type: str = Field(description="Destination type: 'whatsapp', 'telegram', 'slack', 'none'")
    destination_params: Dict[str, Any] = Field(default_factory=dict, description="Destination parameters. For whatsapp/telegram/slack: {'phone': '+5491...'} or {'chat_id': '...'} or {'channel': '#general'}.")
    message_template: str = Field(default="{{output}}", description="Message template. Use {{output}} as placeholder for the source result.")
    description: str = Field(default="", description="Optional job description")


class CronDeleteArgs(BaseModel):
    """Arguments for deleting a cron job"""
    job_id: str = Field(description="The job ID to delete")


class CronRunArgs(BaseModel):
    """Arguments for running a cron job immediately"""
    job_id: str = Field(description="The job ID to run now")


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


class FetchUrlArgs(BaseModel):
    """Arguments for fetching a web page"""
    url: str = Field(description="Full URL to fetch (e.g. https://dolarhoy.com)")


class WebSearchArgs(BaseModel):
    """Arguments for web search"""
    query: str = Field(description="Search query to look up on the internet")
    max_results: int = Field(default=5, ge=1, le=10, description="Number of results to return")


class OrganizeMemoryArgs(BaseModel):
    """Arguments for reorganizing general.skill.md"""
    new_content: str = Field(
        description="The full consolidated content to replace general.skill.md with."
    )


class SearchMemoryArgs(BaseModel):
    """Arguments for searching the assistant memory"""
    query: str = Field(description="Término a buscar en la memoria del asistente")
    max_results: int = Field(default=5, ge=1, le=10)


class SaveSolutionArgs(BaseModel):
    """Arguments for saving a problem-solution pair"""
    problem: str = Field(description="Description of the problem that was solved")
    solution: str = Field(description="The solution or steps taken to resolve the problem")
    context: Optional[str] = Field(
        default=None,
        description="Optional additional context (environment, constraints, related tools, etc.)"
    )
    effective: bool = Field(
        default=True,
        description="Whether the solution was effective. True by default."
    )


class ReadFileArgs(BaseModel):
    """Arguments for reading a file"""
    path: str = Field(description="Path to the file to read (relative to workspace or absolute)")
    offset: int = Field(default=1, ge=1, description="Line number to start reading from (1-based)")
    limit: int = Field(default=200, ge=1, le=2000, description="Maximum number of lines to read")


class WriteFileArgs(BaseModel):
    """Arguments for writing a file"""
    path: str = Field(description="Path to the file to create or overwrite (relative to workspace or absolute)")
    content: str = Field(description="Full content to write to the file")
    create_dirs: bool = Field(default=True, description="Create intermediate directories if they do not exist")


class EditFileArgs(BaseModel):
    """Arguments for making a surgical edit to a file"""
    path: str = Field(description="Path to the file to edit (relative to workspace or absolute)")
    old_string: str = Field(description="The exact string to find and replace in the file")
    new_string: str = Field(description="The string to replace old_string with")


class ListDirectoryArgs(BaseModel):
    """Arguments for listing directory contents"""
    path: str = Field(default=".", description="Directory path to list (relative to workspace or absolute)")
    show_hidden: bool = Field(default=False, description="Whether to include hidden files and directories (starting with .)")


class FindFilesArgs(BaseModel):
    """Arguments for finding files by glob pattern"""
    pattern: str = Field(description="Glob pattern to match files (e.g. '**/*.py', 'src/**/*.ts', '*.json')")
    path: str = Field(default=".", description="Base directory to search in (relative to workspace or absolute)")
    max_results: int = Field(default=50, ge=1, le=200, description="Maximum number of results to return")


class RunShellArgs(BaseModel):
    """Arguments for running a shell command"""
    command: str = Field(description="Shell command to execute")
    working_dir: str = Field(default=".", description="Working directory (relative to workspace)")
    timeout: int = Field(default=30, ge=1, le=300, description="Timeout in seconds")


class GrepFilesArgs(BaseModel):
    """Arguments for searching file contents by pattern"""
    pattern: str = Field(description="Text or regex pattern to search for")
    path: str = Field(default=".", description="Directory to search in (relative to workspace or absolute)")
    file_glob: str = Field(default="*", description="File pattern filter (e.g. '*.py', '*.ts')")
    max_results: int = Field(default=50, ge=1, le=200, description="Maximum number of matches to return")
    ignore_case: bool = Field(default=False, description="Case-insensitive search")
    context_lines: int = Field(default=0, ge=0, le=10, description="Number of context lines to show before and after each match")


class GitStatusArgs(BaseModel):
    """Arguments for git status (no args needed)"""
    pass


class GitDiffArgs(BaseModel):
    """Arguments for git diff"""
    file_path: str = Field(default="", description="Specific file to diff, or empty for full diff")
    staged: bool = Field(default=False, description="Show staged changes instead of unstaged")


class GitLogArgs(BaseModel):
    """Arguments for git log"""
    max_entries: int = Field(default=10, ge=1, le=50, description="Maximum number of commits to show")
    file_path: str = Field(default="", description="Filter log to a specific file")


class GitCommitArgs(BaseModel):
    """Arguments for git commit"""
    message: str = Field(description="Commit message")
    files: List[str] = Field(default=[], description="Specific files to stage, or empty to stage all changes")


class RepoMapArgs(BaseModel):
    """Arguments for generating a repository map"""
    path: str = Field(default=".", description="Directory to map (relative to workspace)")
    max_depth: int = Field(default=4, ge=1, le=8, description="Max directory depth")
    include_signatures: bool = Field(default=True, description="Include class/function signatures")
    file_glob: str = Field(default="*.py", description="File types to extract signatures from (e.g. '*.py', '*.ts')")


class CheckCodeArgs(BaseModel):
    """Arguments for checking code for errors and warnings"""
    path: str = Field(default=".", description="File or directory to check (relative to workspace)")
    tool: str = Field(default="auto", description="Checker to use: 'auto', 'pyright', 'mypy', 'tsc', 'eslint'")


class QueryDatabaseArgs(BaseModel):
    """Arguments for querying the database"""
    table: str = Field(
        description="Table name to query. Must be one of the allowed tables configured in the integration."
    )
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
        is_db = (integration.type == "database" or integration.name == "sqldatabase")
        if not is_db or not integration.activated:
            continue

        config = integration.config or {}
        connection_string = config.get("connection_string")

        allowed_tables = config.get("allowed_tables")
        if not allowed_tables:
            single = config.get("allowed_table")
            if single:
                allowed_tables = [{"name": single, "description": config.get("table_description", "")}]

        if not connection_string or not allowed_tables:
            continue

        from src.adapters.web.integrations.sqldatabase.sqldatabase import SQLDatabaseIntegration
        inst = SQLDatabaseIntegration(
            connection_string=connection_string,
            allowed_tables=allowed_tables,
            blocked_keywords=config.get("blocked_keywords", None),
        )

        # Build a unique valid slug from integration name
        base_slug = _re.sub(r"[^a-z0-9]", "_", integration.name.lower()).strip("_") or "db"
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


def _resolve_output_path(path: str, workspace: str) -> "Path":
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


def _find_local_file(file_name: str, workspace: str) -> "Path | None":
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

        # Recursive search by filename (handles subdirectories like IEST/)
        target_name = _Path(file_name).name.lower()
        for root, _dirs, files in _os.walk(workspace):
            for fname in files:
                if fname.lower() == target_name:
                    return _Path(root) / fname

    return None


# ── Browser session state (module-level so it persists across requests) ──────
_browser_state: Dict[str, Any] = {
    "playwright": None,
    "browser": None,
    "page": None,
    "connected": False,   # True when attached to a real browser via CDP
}


def create_langchain_tools(openai_integration, profile, skill_manager=None, store_service=None, job_usecases=None, shell_output_callback=None, client_workspace: str = "", approval_callback=None, plan_mode: bool = False) -> List[StructuredTool]:
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
            run_shell, git_commit) describe what they *would* do without
            actually executing anything.

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
                    result["sheets"].append({
                        "name": name,
                        "rows": len(rows),
                        "columns": ws.max_column,
                        "sample": [list(r) for r in rows[:5]],
                    })
                result["note"] = "Use modify_excel to edit cells. Sample shows first 5 rows per sheet."
                return result
            try:
                return await asyncio.get_event_loop().run_in_executor(None, _read_local)
            except Exception as e:
                return {"error": str(e)}

        file = _find_file_by_name(profile.files, file_name)
        if not file:
            return {"error": f"File '{file_name}' not found on disk or in profile storage."}
        return await openai_integration.analyze_excel_file(file.url)

    async def write_excel_tool(path: str, sheets: dict, mode: str = "overwrite") -> Dict[str, Any]:
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
            return {"path": str(resolved), "sheets": list(sheets.keys()), "rows_written": total_rows}

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
                return {"error": "python-docx not installed. Run: pip install python-docx"}

            local = _find_local_file(file_name, client_workspace)
            if local:
                doc = Document(str(local))
            else:
                profile_file = _find_file_by_name(profile.files, file_name)
                if not profile_file:
                    return {"error": f"File '{file_name}' not found on disk or in profile storage."}
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
                sections.append({"style": "Note", "text": f"[... {total - 80} more paragraphs truncated. Ask for a specific section if you need more.]"})
            return {"paragraphs": sections, "tables": tables, "total_paragraphs": total, "truncated": total > 80}

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _read)
        except Exception as e:
            return {"error": str(e)}

    async def write_docx_tool(path: str, content: str, mode: str = "overwrite") -> Dict[str, Any]:
        """Create or modify a Word (.docx) document."""
        import asyncio
        from pathlib import Path as _Path

        resolved = _resolve_output_path(path, client_workspace)

        def _write():
            try:
                from docx import Document
                from docx.shared import Pt
            except ImportError:
                return {"error": "python-docx not installed. Run: pip install python-docx"}

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
                    parts = _re.split(r'(\*\*[^*]+\*\*|\*[^*]+\*)', stripped)
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
            return {"path": str(resolved), "paragraphs_written": len(content.splitlines())}

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _write)
        except Exception as e:
            return {"error": str(e)}


    async def modify_excel_tool(file_name: str, operations: List[dict], save_as: str = None, re_upload: bool = False) -> Dict[str, Any]:
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
                    return {"error": f"File '{file_name}' not found in profile files or workspace."}
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
                        applied.append(f"update_cell: {op['sheet']}!{col}{row}={op['value']}")
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
                        applied.append(f"rename_sheet: {op['old_name']} -> {op['new_name']}")
                    elif op_type == "delete_sheet":
                        del wb[op["name"]]
                        applied.append(f"delete_sheet: {op['name']}")
                    else:
                        errors.append(f"Unknown operation type: {op_type}")
                except Exception as ex:
                    errors.append(f"{op_type} failed: {ex}")

            ws_path.parent.mkdir(parents=True, exist_ok=True)
            wb.save(ws_path)
            return {"saved_to": str(ws_path), "operations_applied": applied, "errors": errors}

        result = await asyncio.get_event_loop().run_in_executor(None, _execute)

        if re_upload and "error" not in result:
            saved_path = _Path(result["saved_to"])
            if saved_path.exists():
                import aiohttp
                try:
                    with open(saved_path, "rb") as fh:
                        data = aiohttp.FormData()
                        data.add_field("files", fh, filename=saved_path.name, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                        async with aiohttp.ClientSession() as session:
                            async with session.post("http://localhost:8000/profile/files/upload", data=data) as resp:
                                if resp.status == 200:
                                    result["re_uploaded"] = True
                                else:
                                    result["re_upload_error"] = f"HTTP {resp.status}"
                except Exception as e:
                    result["re_upload_error"] = str(e)

        return result

    async def modify_docx_tool(file_name: str, replacements: List[dict] = None, append: str = None, save_as: str = None, re_upload: bool = False) -> Dict[str, Any]:
        """Download and modify a Word document: replace text and/or append content."""
        import asyncio, io
        from pathlib import Path as _Path

        def _execute():
            try:
                from docx import Document
            except ImportError:
                return {"error": "python-docx not installed. Run: pip install python-docx"}

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
                    return {"error": f"File '{file_name}' not found in profile files or workspace."}
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
                        doc.add_paragraph(stripped.split(". ", 1)[1], style="List Number")
                    elif not stripped:
                        doc.add_paragraph("")
                    else:
                        para = doc.add_paragraph()
                        parts = _re.split(r'(\*\*[^*]+\*\*|\*[^*]+\*)', stripped)
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
                        data.add_field("files", fh, filename=saved_path.name, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                        async with aiohttp.ClientSession() as session:
                            async with session.post("http://localhost:8000/profile/files/upload", data=data) as resp:
                                if resp.status == 200:
                                    result["re_uploaded"] = True
                                else:
                                    result["re_upload_error"] = f"HTTP {resp.status}"
                except Exception as e:
                    result["re_upload_error"] = str(e)

        return result

    async def describe_image_tool(image_url: str) -> str:
        """Describe an image from its URL or local file path"""
        import aiohttp, base64 as b64, os
        from urllib.parse import urlparse, unquote
        try:
            parsed = urlparse(image_url)
            if parsed.scheme in ("", "file") or os.path.exists(image_url):
                # Local file
                file_path = unquote(parsed.path) if parsed.scheme == "file" else image_url
                with open(file_path, "rb") as f:
                    image_bytes = f.read()
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        resp.raise_for_status()
                        image_bytes = await resp.read()
            image_base64 = b64.b64encode(image_bytes).decode()
            return await openai_integration.describe_image_from_base64(image_base64)
        except Exception as e:
            return f"Error fetching image from URL: {e}"

    async def take_screenshot_tool(question: str = "Describe what is visible on the screen.") -> str:
        """Capture the desktop screen and describe its contents using vision AI."""
        import asyncio
        import base64 as b64
        import tempfile
        import os

        # Detect display server to pick the right tool
        is_wayland = bool(os.environ.get("WAYLAND_DISPLAY"))
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        path = tmp.name

        # Some Wayland compositors (MangoWM, etc.) don't implement wlr-screencopy
        # properly and grim produces a black image. For those, use X11/XWayland first.
        _wlroots_compositors = {"sway", "wayfire", "river", "hyprland", "labwc"}
        grim_likely_works = any(d in desktop for d in _wlroots_compositors)

        if is_wayland and grim_likely_works:
            _CAPTURE_CMDS = [
                ["grim", path],
                ["gnome-screenshot", "-f", path],
                ["spectacle", "-b", "-o", path],
                ["scrot", path],
                ["import", "-window", "root", path],
            ]
        elif is_wayland:
            # Wayland compositor without reliable wlr-screencopy — try X11 tools first
            _CAPTURE_CMDS = [
                ["scrot", path],
                ["import", "-window", "root", path],
                ["gnome-screenshot", "-f", path],
                ["spectacle", "-b", "-o", path],
                ["grim", path],
            ]
        else:
            _CAPTURE_CMDS = [
                ["scrot", path],
                ["maim", path],
                ["import", "-window", "root", path],
                ["gnome-screenshot", "-f", path],
                ["spectacle", "-b", "-o", path],
            ]

        # Pass display env vars explicitly so subprocesses can reach the Wayland/X11 session
        import pwd
        uid = os.getuid()
        capture_env = {
            **os.environ,
            "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY", "wayland-0"),
            "DISPLAY": os.environ.get("DISPLAY", ":0"),
            "XDG_RUNTIME_DIR": os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{uid}"),
        }

        captured = False
        for cmd in _CAPTURE_CMDS:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                    env=capture_env,
                )
                await asyncio.wait_for(proc.wait(), timeout=10)
                if proc.returncode == 0 and os.path.getsize(path) > 0:
                    captured = True
                    break
            except (FileNotFoundError, asyncio.TimeoutError):
                continue

        if not captured:
            os.unlink(path)
            install_hint = (
                "grim (Wayland), gnome-screenshot, or spectacle"
                if is_wayland else
                "scrot, maim, imagemagick, gnome-screenshot, or spectacle"
            )
            return f"Could not take a screenshot. Running on {'Wayland' if is_wayland else 'X11'}. Install: {install_hint}"

        try:
            with open(path, "rb") as f:
                image_base64 = b64.b64encode(f.read()).decode()
        finally:
            os.unlink(path)

        prompt = f"Screenshot of the user's desktop. {question}"
        try:
            description = await openai_integration.describe_image_from_base64(
                image_base64, prompt=prompt
            )
            return description
        except Exception as e:
            return f"Screenshot captured but vision analysis failed: {e}"

    # ── Browser session (Playwright) ──────────────────────────────────────────
    # _browser_state is module-level (defined above create_langchain_tools) so
    # it persists across requests within the same process.

    async def _get_page():
        """Return the active browser page. Auto-connects to the real Chrome via CDP if needed."""
        page = _browser_state.get("page")
        if page and not page.is_closed():
            return page
        # No active page — auto-connect to the real Chrome browser
        result = await browser_connect_tool()
        page = _browser_state.get("page")
        if not page or page.is_closed():
            raise RuntimeError(f"Could not connect to browser: {result}")
        return page

    async def _cdp_is_ready(host: str, port: int) -> bool:
        """Check if CDP endpoint is responding via plain HTTP (avoids IPv6 issues)."""
        import urllib.request
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/json/version", timeout=2) as r:
                return r.status == 200
        except Exception:
            return False

    async def _connect_cdp(cdp_url: str):
        """Internal: attempt CDP connection and update _browser_state. Raises on failure."""
        from playwright.async_api import async_playwright
        if _browser_state["browser"] and not _browser_state["connected"]:
            await _browser_state["browser"].close()
        if _browser_state["playwright"] is None:
            _browser_state["playwright"] = await async_playwright().start()
        # Always use 127.0.0.1 to avoid IPv6 resolution issues
        normalized = cdp_url.replace("localhost", "127.0.0.1")
        browser = await _browser_state["playwright"].chromium.connect_over_cdp(normalized)
        _browser_state["browser"] = browser
        _browser_state["connected"] = True
        contexts = browser.contexts
        if contexts and contexts[0].pages:
            page = contexts[0].pages[0]
        else:
            page = await contexts[0].new_page() if contexts else await (await browser.new_context()).new_page()
        _browser_state["page"] = page
        return browser

    async def browser_connect_tool(cdp_url: str = "http://localhost:9222") -> str:
        """Connect to the user's real Chrome browser via CDP.

        If Chrome is not already listening on the CDP port, automatically:
        1. Kills any running Chrome instance
        2. Relaunches Chrome with --remote-debugging-port using the real user profile
           so all existing sessions (WhatsApp Web, Gmail, etc.) are preserved
        3. Connects via CDP
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return "playwright not installed. Run: pip install playwright && playwright install chromium"

        import shutil
        port = int(cdp_url.split(":")[-1]) if ":" in cdp_url else 9222

        # Check if CDP is already available (Chrome running with --remote-debugging-port)
        if await _cdp_is_ready("127.0.0.1", port):
            try:
                await _connect_cdp(cdp_url)
            except Exception as e:
                return f"CDP endpoint responded but Playwright connection failed: {e}"
        else:
            # CDP not available — relaunch Chrome with real user profile + remote debugging
            logger.info("browser_connect: CDP not available, relaunching Chrome with remote debugging...")

            # Find Chrome binary
            chrome_bins = ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser"]
            chrome_bin = next((b for b in chrome_bins if shutil.which(b)), None)
            if not chrome_bin:
                return "Chrome is not installed. Install google-chrome-stable and try again."

            # Kill ALL chrome processes (main + renderers + helpers)
            for sig in ("TERM", "KILL"):
                await asyncio.create_subprocess_exec(
                    "pkill", f"-{sig}", "-f", "chrome",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.sleep(1)

            # Wait until every chrome process is fully gone (profile lock released)
            for _ in range(10):
                chk = await asyncio.create_subprocess_exec(
                    "pgrep", "-f", "chrome",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await chk.wait()
                if chk.returncode != 0:
                    break  # no chrome processes left
                await asyncio.sleep(1)

            # Relaunch Chrome with real user profile so sessions are preserved
            real_profile = os.path.expanduser("~/.config/google-chrome")
            await asyncio.create_subprocess_exec(
                chrome_bin,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={real_profile}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-session-crashed-bubble",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

            # Wait up to 30s for CDP HTTP endpoint to respond, then connect
            ready = False
            for _ in range(30):
                await asyncio.sleep(1)
                if await _cdp_is_ready("127.0.0.1", port):
                    ready = True
                    break

            if not ready:
                return (
                    f"Chrome was relaunched with --remote-debugging-port={port} but "
                    "the CDP endpoint is not responding after 30s. "
                    "Chrome may have failed to start. Check that google-chrome-stable is installed."
                )

            try:
                await _connect_cdp(cdp_url)
            except Exception as e:
                return f"CDP endpoint is up but Playwright connection failed: {e}"

        # Build tab list
        all_pages = [p for ctx in _browser_state["browser"].contexts for p in ctx.pages]
        tab_list = "\n".join(f"  [{i}] {p.url[:80]}" for i, p in enumerate(all_pages))
        return (
            f"Connected to Chrome at {cdp_url}\n"
            f"Open tabs ({len(all_pages)}):\n{tab_list}\n\n"
            f"Active tab: {_browser_state['page'].url}"
        )

    async def browser_switch_tab_tool(index: int) -> str:
        """Switch to a specific open tab by index (use browser_connect first to list tabs)."""
        try:
            browser = _browser_state["browser"]
            if not browser:
                return "No browser connected. Use browser_connect first."
            all_pages = [p for ctx in browser.contexts for p in ctx.pages]
            if index < 0 or index >= len(all_pages):
                return f"Invalid tab index {index}. Available: 0–{len(all_pages)-1}"
            _browser_state["page"] = all_pages[index]
            await all_pages[index].bring_to_front()
            return f"Switched to tab [{index}]: {all_pages[index].url}"
        except Exception as e:
            return f"Switch tab error: {e}"

    async def browser_enable_remote_debug_tool(port: int = 9222) -> str:
        """Write user.js to the Firefox profile to permanently enable CDP remote debugging.

        Firefox restores its previous session on restart, so the user won't lose
        open tabs or their WhatsApp Web session.
        """
        import glob as _glob

        # Find Firefox profile directory (default-release or default)
        home = os.path.expanduser("~")
        patterns = [
            f"{home}/.mozilla/firefox/*.default-release/",
            f"{home}/.mozilla/firefox/*.default/",
            f"{home}/.mozilla/firefox/*/",
        ]
        profile_dir = None
        for pattern in patterns:
            matches = _glob.glob(pattern)
            if matches:
                profile_dir = matches[0].rstrip("/")
                break

        if not profile_dir:
            return (
                "Could not find Firefox profile directory. "
                "Start Firefox manually with:\n"
                f"  firefox --remote-debugging-port={port} --no-remote\n"
                "Or in a new instance:\n"
                f"  firefox --remote-debugging-port={port} -P default-release"
            )

        user_js_path = os.path.join(profile_dir, "user.js")

        prefs = f"""
// Remote debugging — added by Gillie AI
user_pref("devtools.debugger.remote-enabled", true);
user_pref("devtools.debugger.remote-port", {port});
user_pref("devtools.chrome.enabled", true);
user_pref("devtools.debugger.prompt-connection", false);
user_pref("devtools.debugger.remote-host", "127.0.0.1");
user_pref("devtools.debugger.force-local", true);
"""
        # Append to existing user.js or create it
        try:
            existing = ""
            if os.path.exists(user_js_path):
                with open(user_js_path, "r") as f:
                    existing = f.read()

            if "devtools.debugger.remote-enabled" in existing:
                return (
                    f"Remote debugging is already configured in {user_js_path}.\n"
                    f"Restart Firefox and then use browser_connect to attach."
                )

            with open(user_js_path, "a") as f:
                f.write(prefs)

            return (
                f"✓ Remote debugging enabled in {user_js_path} on port {port}.\n\n"
                f"Next steps:\n"
                f"  1. Restart Firefox (it will restore your session automatically)\n"
                f"  2. Tell me: 'connect to my browser' and I'll attach via CDP\n\n"
                f"Firefox session restore is ON by default — WhatsApp Web and all "
                f"other tabs will reopen automatically."
            )
        except Exception as e:
            return f"Error writing {user_js_path}: {e}"

    async def browser_navigate_tool(url: str, wait_for: str = "load") -> str:
        """Navigate to a URL and return page title + visible text excerpt."""
        try:
            page = await _get_page()
            wait_map = {"load": "load", "domcontentloaded": "domcontentloaded", "networkidle": "networkidle"}
            await page.goto(url, wait_until=wait_map.get(wait_for, "load"), timeout=30000)
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
            return f"Clicked '{selector}'. Current page: {await page.title()} ({page.url})"
        except Exception as e:
            return f"Click error: {e}"

    async def browser_type_tool(selector: str, text: str, clear_first: bool = True) -> str:
        """Type text into an input field."""
        try:
            page = await _get_page()
            if clear_first:
                await page.fill(selector, "", timeout=10000)
            await page.type(selector, text, delay=30)
            return f"Typed into '{selector}' on {page.url}"
        except Exception as e:
            return f"Type error: {e}"

    async def browser_get_content_tool(selector: str = "", as_html: bool = False) -> str:
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

    async def browser_screenshot_tool(selector: str = "", question: str = "Describe what is visible on this page.") -> str:
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
            description = await openai_integration.describe_image_from_base64(image_base64, prompt=prompt)
            return description
        except Exception as e:
            return f"Browser screenshot error: {e}"

    async def browser_evaluate_tool(script: str) -> str:
        """Execute JavaScript in the current page and return the result."""
        try:
            page = _browser_state.get("page")
            if not page or page.is_closed():
                return "No browser page available. Use browser_connect first."
            # Playwright's page.evaluate requires an expression or a function.
            # Top-level `return` is a SyntaxError. Auto-wrap in IIFE when needed.
            needs_wrap = "return " in script or script.strip().startswith("//")
            if needs_wrap:
                script = f"(function() {{\n{script}\n}})()"
            result = await page.evaluate(script)
            if result is None:
                return "(script executed, no return value)"
            return json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, (dict, list)) else str(result)
        except Exception as e:
            return f"JavaScript error: {e}"

    async def browser_close_tool() -> str:
        """Disconnect from the browser session. When connected to a real browser via
        browser_connect, this only disconnects — it does NOT close the user's browser."""
        try:
            if _browser_state["connected"]:
                # Just disconnect — do not close the user's real browser
                if _browser_state["browser"]:
                    await _browser_state["browser"].close()
                msg = "Disconnected from browser (your browser remains open)."
            else:
                if _browser_state["browser"]:
                    await _browser_state["browser"].close()
                msg = "Browser session closed."

            _browser_state["browser"] = None
            _browser_state["page"] = None
            _browser_state["connected"] = False

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
            return None, f"Access denied: path '{path}' is outside workspace '{workspace}'"
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
        patterns = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
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
        numbered = "\n".join(f"{start + i + 1:>6}\t{line}" for i, line in enumerate(selected))
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

        # Plan mode: describe the change without executing it.
        if plan_mode:
            if resolved.exists() and resolved.is_file():
                try:
                    current_lines = resolved.read_text(errors="replace").splitlines(keepends=True)
                except Exception:
                    current_lines = []
            else:
                current_lines = []
            new_lines = content.splitlines(keepends=True)
            diff = "".join(_difflib.unified_diff(
                current_lines, new_lines,
                fromfile=f"a/{path}", tofile=f"b/{path}", lineterm="",
            ))
            return {
                "plan_only": True,
                "would_do": f"Write '{path}' ({len(content.splitlines())} lines)",
                "diff": diff[:500],
            }

        if approval_callback:
            # Build a unified diff so the user can review what will change.
            if resolved.exists() and resolved.is_file():
                try:
                    current_lines = resolved.read_text(errors="replace").splitlines(keepends=True)
                except Exception:
                    current_lines = []
            else:
                current_lines = []
            new_lines = content.splitlines(keepends=True)
            diff = "".join(_difflib.unified_diff(
                current_lines, new_lines,
                fromfile=f"a/{path}", tofile=f"b/{path}", lineterm="",
            ))
            request_id = str(_uuid.uuid4())
            approved = await approval_callback(
                request_id, "write_file", path,
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

        # Plan mode: describe the change without executing it.
        if plan_mode:
            old_lines = (old_string or "").splitlines(keepends=True)
            new_lines_p = (new_string or "").splitlines(keepends=True)
            diff_plan = "".join(difflib.unified_diff(
                old_lines, new_lines_p,
                fromfile=f"a/{path}", tofile=f"b/{path}", lineterm="",
            ))
            return {
                "plan_only": True,
                "would_do": f"Edit '{path}'",
                "diff": diff_plan[:500],
            }

        if approval_callback:
            old_lines = (old_string or "").splitlines(keepends=True)
            new_lines = (new_string or "").splitlines(keepends=True)
            diff = "".join(difflib.unified_diff(
                old_lines, new_lines,
                fromfile=f"a/{path}", tofile=f"b/{path}", lineterm="",
            ))
            request_id = str(_uuid.uuid4())
            approved = await approval_callback(
                request_id, "edit_file", path,
                diff or f"Replace content in {path}",
            )
            if not approved:
                from src.core.platform.ai.tools.approval_manager import get_feedback
                feedback = get_feedback(request_id)
                msg = f"Change to '{path}' was rejected by the user."
                if feedback:
                    msg += f" Reason: {feedback}. Please try a different approach."
                return {"skipped": True, "message": msg}

        # Strategy 1: Exact match
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

        # Strategy 2: Normalized whitespace match
        def _normalize(text: str) -> str:
            return "\n".join(line.strip() for line in text.splitlines())

        norm_original = _normalize(original)
        norm_old = _normalize(old_string)
        norm_count = norm_original.count(norm_old)
        if norm_count == 1:
            # Find the actual span in the original text using the normalized index
            norm_idx = norm_original.index(norm_old)
            # Reconstruct original-text slice by mapping normalized position back
            # We do a line-by-line replacement instead
            orig_lines = original.splitlines(keepends=True)
            old_lines = old_string.splitlines()
            new_lines = new_string.splitlines(keepends=True)
            norm_old_lines = [l.strip() for l in old_lines]
            for i in range(len(orig_lines) - len(old_lines) + 1):
                window = [orig_lines[i + j].rstrip("\n").rstrip("\r").strip() for j in range(len(old_lines))]
                if window == norm_old_lines:
                    updated_lines = orig_lines[:i] + new_lines + orig_lines[i + len(old_lines):]
                    resolved.write_text("".join(updated_lines), encoding="utf-8")
                    return f"Edited '{path}': replaced 1 occurrence (normalized whitespace match)"
            # Fallback: simple normalized replace on the normalized text is not safe to write back,
            # so fall through to fuzzy
        elif norm_count > 1:
            return (
                f"Error: found {norm_count} normalized occurrences of the search string. "
                f"Provide more surrounding context to make the match unique."
            )

        # Strategy 2.5: Indentation-flexible match
        # Strip common leading whitespace from old_string, then find windows with same stripped content
        old_lines_raw = old_string.splitlines()
        if old_lines_raw:
            non_empty = [l for l in old_lines_raw if l.strip()]
            if non_empty:
                common_indent = min(len(l) - len(l.lstrip()) for l in non_empty)
                dedented_old = [l[common_indent:] if len(l) >= common_indent else l.lstrip() for l in old_lines_raw]
                orig_lines_full = original.splitlines(keepends=True)
                for i in range(len(orig_lines_full) - len(old_lines_raw) + 1):
                    window = orig_lines_full[i:i + len(old_lines_raw)]
                    window_stripped = [l.rstrip("\n").rstrip("\r") for l in window]
                    non_empty_w = [l for l in window_stripped if l.strip()]
                    if not non_empty_w:
                        continue
                    win_indent = min(len(l) - len(l.lstrip()) for l in non_empty_w)
                    dedented_win = [l[win_indent:] if len(l) >= win_indent else l.lstrip() for l in window_stripped]
                    if dedented_win == dedented_old:
                        # Re-indent new_string to match the window's base indentation
                        indent_str = " " * win_indent
                        new_reindented = "\n".join(
                            indent_str + nl if nl.strip() else nl
                            for nl in new_string.splitlines()
                        )
                        updated_lines = orig_lines_full[:i] + [new_reindented + "\n"] + orig_lines_full[i + len(old_lines_raw):]
                        resolved.write_text("".join(updated_lines), encoding="utf-8")
                        return f"Edited '{path}': replaced 1 occurrence (indentation-flexible match)"

        # Strategy 3: Fuzzy match using difflib (threshold 0.8)
        orig_lines = original.splitlines()
        old_lines_stripped = old_string.splitlines()
        window_size = len(old_lines_stripped)
        if window_size == 0:
            return "Error: old_string is empty"

        best_ratio = 0.0
        best_start = -1
        for i in range(len(orig_lines) - window_size + 1):
            window = orig_lines[i:i + window_size]
            ratio = difflib.SequenceMatcher(None, "\n".join(window), old_string).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_start = i

        if best_ratio >= 0.8 and best_start >= 0:
            window_lines = orig_lines[best_start:best_start + window_size]
            updated_lines = (
                orig_lines[:best_start]
                + new_string.splitlines()
                + orig_lines[best_start + window_size:]
            )
            resolved.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
            return (
                f"Edited '{path}': replaced 1 occurrence (fuzzy match, similarity={best_ratio:.2f}). "
                f"Replaced lines {best_start + 1}-{best_start + window_size}."
            )

        # No match found — return nearby lines to help the caller correct their search string
        nearby_lines = "\n".join(
            f"{i + 1:>6}\t{line}"
            for i, line in enumerate(orig_lines[:30])
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
            entries = sorted(resolved.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
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

    async def find_files_tool(pattern: str, path: str = ".", max_results: int = 50) -> str:
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
            skip = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", "dist", "build", ".next"}
            try:
                entries = sorted(dir_path.iterdir(), key=lambda e: (e.is_file(), e.name))
            except PermissionError:
                return
            entries = [e for e in entries if e.name not in skip and not _is_ignored(e, workspace)]
            for i, entry in enumerate(entries):
                connector = "└── " if i == len(entries) - 1 else "├── "
                lines.append(f"{prefix}{connector}{entry.name}")
                if entry.is_dir():
                    extension = "    " if i == len(entries) - 1 else "│   "
                    _tree(entry, prefix + extension, depth + 1)
                elif include_signatures and entry.is_file():
                    _extract_signatures(entry, prefix + ("    " if i == len(entries) - 1 else "│   "))

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
                                if isinstance(item, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                                    args = [a.arg for a in item.args.args]
                                    lines.append(f"{prefix}        def {item.name}({', '.join(args)})")
                        elif isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                            args = [a.arg for a in node.args.args]
                            lines.append(f"{prefix}    def {node.name}({', '.join(args)})")
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
            return {"tool": "none", "diagnostics": [], "summary": "No supported checker found for this path."}

        if not _shutil.which(chosen):
            return {"tool": chosen, "error": f"'{chosen}' is not installed or not in PATH. Install it first."}

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
                    diagnostics.append({
                        "file": diag.get("file", ""),
                        "line": diag.get("range", {}).get("start", {}).get("line", 0) + 1,
                        "severity": diag.get("severity", "error"),
                        "message": diag.get("message", ""),
                        "rule": diag.get("rule", ""),
                    })
                summary = data.get("summary", {})
            except Exception:
                diagnostics = [{"raw": stdout[:2000]}]
                summary = {}
        elif chosen == "mypy":
            import re as _re_diag
            pat = _re_diag.compile(r"^(.+?):(\d+):(?:\d+:)?\s*(error|warning|note):\s*(.+)$")
            for line in stdout.splitlines():
                m = pat.match(line.strip())
                if m:
                    diagnostics.append({
                        "file": m.group(1),
                        "line": int(m.group(2)),
                        "severity": m.group(3),
                        "message": m.group(4),
                    })
            summary = {"errors": sum(1 for d in diagnostics if d.get("severity") == "error")}
        else:
            # tsc / eslint: return raw output
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
        "rm -rf /", "mkfs", "dd if=", "shutdown", "reboot",
        ":(){ :|:& };:", "chmod -R 777 /", "chown -R",
    ]

    async def run_shell_tool(command: str, working_dir: str = ".", timeout: int = 30) -> Dict[str, Any]:
        """Execute a shell command inside the workspace."""
        for blocked in _SHELL_BLACKLIST:
            if blocked in command:
                return {
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Command rejected: contains blocked pattern '{blocked}'",
                    "truncated": False,
                }

        # Plan mode: describe the command without running it.
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
            return {"exit_code": -1, "stdout": "", "stderr": f"Access denied: '{working_dir}' is excluded by .gillierignore", "truncated": False}

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
                    raw_stdout, raw_stderr = await _asyncio.wait_for(proc.communicate(), timeout=timeout)
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
            return {"exit_code": -1, "stdout": "", "stderr": f"Error running command: {e}", "truncated": False}

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
            return {"found": 0, "results": [], "truncated": False, "error": f"Path not found or not a directory: '{path}'"}

        # Try ripgrep first (much faster for large repos)
        if _shutil.which("rg"):
            try:
                rg_cmd = [
                    "rg", "--json",
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
                        file_rel = str(_Path(data["path"]["text"]).relative_to(resolved))
                        line_num = data["line_number"]
                        content = data["lines"]["text"].rstrip("\n")
                        result_entry: Dict[str, Any] = {"file": file_rel, "line": line_num, "content": content}
                        if context_lines > 0:
                            # submatches context will be included naturally via -C in output
                            pass
                        results.append(result_entry)
                        if len(results) >= max_results:
                            break
                truncated = len(results) >= max_results
                return {"found": len(results), "results": results, "truncated": truncated}
            except Exception:
                pass  # fall through to Python implementation

        # Python fallback
        _SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
        flags = _re.IGNORECASE if ignore_case else 0
        try:
            compiled = _re.compile(pattern, flags)
        except _re.error as e:
            return {"found": 0, "results": [], "truncated": False, "error": f"Invalid regex pattern: {e}"}

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
                        before = all_lines[max(0, line_num - 1 - context_lines):line_num - 1]
                        after = all_lines[line_num:min(len(all_lines), line_num + context_lines)]
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
            "git", *args,
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

    async def git_diff_tool(file_path: str = "", staged: bool = False) -> Dict[str, Any]:
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

    async def git_log_tool(max_entries: int = 10, file_path: str = "") -> Dict[str, Any]:
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

        # Plan mode: describe what would be committed without doing it.
        if plan_mode:
            return {
                "plan_only": True,
                "would_do": f"Commit with message: '{message}'",
                "files": files or [],
            }

        files = files or []

        if files:
            # Validate each path stays within workspace
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
            return {"success": False, "output": f"git commit failed: {commit_err.strip()}"}

        return {"success": True, "output": commit_out.strip()}

    # ── End of file editing tools ─────────────────────────────────────────────

    prompts = _get_tool_prompts(profile)
    sql_integrations = _get_sql_integrations(profile)
    sql_integration = sql_integrations[0][1] if sql_integrations else None

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

    async def web_search_tool(query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the internet using DuckDuckGo."""
        import asyncio

        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return {"error": "duckduckgo-search not installed. Run: pip install duckduckgo-search"}

        # Try backends in order — "lite" is least rate-limited
        backends = ["lite", "html", "api"]
        last_error = None

        for attempt, backend in enumerate(backends):
            if attempt > 0:
                await asyncio.sleep(1)
            try:
                results = []
                with DDGS() as ddgs:
                    for r in ddgs.text(query, max_results=max_results, backend=backend):
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", ""),
                        })
                if results:
                    logger.info(f"web_search: {len(results)} results via backend='{backend}'")
                    return {"found": True, "query": query, "results": results}
                last_error = f"backend={backend} returned no results"
            except Exception as e:
                last_error = str(e)
                logger.warning(f"web_search backend='{backend}' failed: {e}")

        return {"found": False, "error": last_error, "message": f"All backends failed: {last_error}"}

    tools = list(filter(None, [
        _tool("fetch_url",              prompts.get("fetch_url",  _DEFAULT_TOOL_PROMPTS["fetch_url"]),  fetch_url_tool,  FetchUrlArgs),
        _tool("web_search",             prompts.get("web_search", _DEFAULT_TOOL_PROMPTS["web_search"]), web_search_tool, WebSearchArgs),
        _tool("read_file",              prompts.get("read_file",  _DEFAULT_TOOL_PROMPTS["read_file"]),  read_file_tool,  ReadFileArgs),
        _tool("write_file",             prompts.get("write_file", _DEFAULT_TOOL_PROMPTS["write_file"]), write_file_tool, WriteFileArgs),
        _tool("edit_file",              prompts.get("edit_file",  _DEFAULT_TOOL_PROMPTS["edit_file"]),  edit_file_tool,  EditFileArgs),
        _tool("list_directory",         prompts.get("list_directory", _DEFAULT_TOOL_PROMPTS["list_directory"]), list_directory_tool, ListDirectoryArgs),
        _tool("find_files",             prompts.get("find_files",  _DEFAULT_TOOL_PROMPTS["find_files"]), find_files_tool, FindFilesArgs),
        _tool("run_shell",              prompts.get("run_shell",   _DEFAULT_TOOL_PROMPTS["run_shell"]),  run_shell_tool,  RunShellArgs),
        _tool("grep_files",             prompts.get("grep_files",  _DEFAULT_TOOL_PROMPTS["grep_files"]), grep_files_tool, GrepFilesArgs),
        _tool("repo_map",               prompts.get("repo_map",    _DEFAULT_TOOL_PROMPTS["repo_map"]),   repo_map_tool,   RepoMapArgs),
        _tool("check_code",             prompts.get("check_code",  _DEFAULT_TOOL_PROMPTS["check_code"]), check_code_tool, CheckCodeArgs),
        _tool("git_status",             prompts.get("git_status",  _DEFAULT_TOOL_PROMPTS["git_status"]), git_status_tool, GitStatusArgs),
        _tool("git_diff",               prompts.get("git_diff",    _DEFAULT_TOOL_PROMPTS["git_diff"]),   git_diff_tool,   GitDiffArgs),
        _tool("git_log",                prompts.get("git_log",     _DEFAULT_TOOL_PROMPTS["git_log"]),    git_log_tool,    GitLogArgs),
        _tool("git_commit",             prompts.get("git_commit",  _DEFAULT_TOOL_PROMPTS["git_commit"]), git_commit_tool, GitCommitArgs),
        _tool("search_images",          prompts["search_images"],          search_images_tool,   SearchImagesArgs),
        _tool("analyze_pdf",            prompts["analyze_pdf"],            analyze_pdf_tool,     AnalyzePDFArgs),
        _tool("extract_text_from_pdf",  prompts["extract_text_from_pdf"],  extract_text_tool,    ExtractTextArgs),
        _tool("analyze_excel",          prompts["analyze_excel"],          analyze_excel_tool,   AnalyzeExcelArgs),
        _tool("write_excel",            prompts["write_excel"],            write_excel_tool,     WriteExcelArgs),
        _tool("read_docx",              prompts["read_docx"],              read_docx_tool,       ReadDocxArgs),
        _tool("write_docx",             prompts["write_docx"],             write_docx_tool,      WriteDocxArgs),
        _tool("modify_excel",           prompts["modify_excel"],           modify_excel_tool,    ModifyExcelArgs),
        _tool("modify_docx",            prompts["modify_docx"],            modify_docx_tool,     ModifyDocxArgs),
        _tool("describe_image",         prompts["describe_image"],         describe_image_tool,  DescribeImageArgs),
        _tool("take_screenshot",        prompts.get("take_screenshot",    _DEFAULT_TOOL_PROMPTS["take_screenshot"]),    take_screenshot_tool,    TakeScreenshotArgs),
        _tool("browser_connect",              prompts.get("browser_connect",             _DEFAULT_TOOL_PROMPTS["browser_connect"]),             browser_connect_tool,             BrowserConnectArgs),
        _tool("browser_switch_tab",           prompts.get("browser_switch_tab",          _DEFAULT_TOOL_PROMPTS["browser_switch_tab"]),          browser_switch_tab_tool,          BrowserSwitchTabArgs),
        _tool("browser_enable_remote_debug",  prompts.get("browser_enable_remote_debug", _DEFAULT_TOOL_PROMPTS["browser_enable_remote_debug"]), browser_enable_remote_debug_tool, BrowserEnableRemoteDebugArgs),
        _tool("browser_evaluate",             prompts.get("browser_evaluate",            _DEFAULT_TOOL_PROMPTS["browser_evaluate"]),            browser_evaluate_tool,            BrowserEvaluateArgs),
        _tool("browser_navigate",       prompts.get("browser_navigate",   _DEFAULT_TOOL_PROMPTS["browser_navigate"]),   browser_navigate_tool,   BrowserNavigateArgs),
        _tool("browser_click",          prompts.get("browser_click",      _DEFAULT_TOOL_PROMPTS["browser_click"]),      browser_click_tool,      BrowserClickArgs),
        _tool("browser_type",           prompts.get("browser_type",       _DEFAULT_TOOL_PROMPTS["browser_type"]),       browser_type_tool,       BrowserTypeArgs),
        _tool("browser_get_content",    prompts.get("browser_get_content",_DEFAULT_TOOL_PROMPTS["browser_get_content"]),browser_get_content_tool,BrowserGetContentArgs),
        _tool("browser_screenshot",     prompts.get("browser_screenshot", _DEFAULT_TOOL_PROMPTS["browser_screenshot"]), browser_screenshot_tool, BrowserScreenshotArgs),
        _tool("browser_close",          prompts.get("browser_close",      _DEFAULT_TOOL_PROMPTS["browser_close"]),      browser_close_tool,      BrowserCloseArgs),
        _tool("search_documents",       prompts["search_documents"],       search_documents_tool, SearchDocumentsArgs),
    ]))

    for _db_slug, _db_inst in sql_integrations:
        _query_tool_name = f"query_{_db_slug}"
        _exec_tool_name = f"execute_sql_{_db_slug}"

        def _make_query_fn(inst):
            async def _query(table: str, columns: List[str] = None, filters: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
                return await inst.query(table=table, columns=columns or ["*"], filters=filters, limit=limit)
            return _query

        def _make_exec_fn(inst):
            async def _exec(sql: str) -> Dict[str, Any]:
                return await inst.execute(sql)
            return _exec

        if _query_tool_name not in disabled and "query_database" not in disabled:
            _qfn = _make_query_fn(_db_inst)
            _db_description = prompts.get("query_database", _DEFAULT_TOOL_PROMPTS["query_database"])
            _tables_summary = "; ".join(
                f"{name}: {desc}" if desc else name
                for name, desc in _db_inst.tables_info.items()
            )
            _db_description += f" Base de datos: {_db_slug}. Tablas disponibles: {_tables_summary}."

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
            existing_id = skill_manager._find_similar_note(content, skill_manager.load_skill("general"))
            if existing_id:
                return (
                    f"Ya existe una nota similar en memoria (ID {existing_id}). "
                    f"No se creó duplicado. Si quieres actualizar la información usa organize_memory."
                )
            note_id = skill_manager.append_general_knowledge(content, category)
            return f"Guardado en memoria (general.skill.md) con ID {note_id}."

        async def search_memory_tool(query: str, max_results: int = 5) -> str:
            return skill_manager.search_memory(query, max_results)

        async def organize_memory_tool(new_content: str) -> str:
            skill_manager.overwrite_general_memory(new_content)
            return "general.skill.md reorganizado y actualizado correctamente."

        async def save_solution_tool(
            problem: str,
            solution: str,
            context: Optional[str] = None,
            effective: bool = True,
        ) -> str:
            existing_id = skill_manager._find_similar_note(problem, skill_manager.load_skill("solutions"))
            if existing_id:
                return (
                    f"Ya existe una solución similar en memoria (ID {existing_id}). "
                    f"No se creó duplicado."
                )
            solution_id = skill_manager.append_solution(problem, solution, context, effective)
            return f"Solución guardada en memoria (solutions.skill.md) con ID {solution_id}."

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
        if "organize_memory" not in disabled:
            tools.append(StructuredTool(
                name="organize_memory",
                description=prompts.get("organize_memory", _DEFAULT_TOOL_PROMPTS["organize_memory"]),
                func=organize_memory_tool,
                args_schema=OrganizeMemoryArgs,
                coroutine=organize_memory_tool,
            ))
        if "save_solution" not in disabled:
            tools.append(StructuredTool(
                name="save_solution",
                description=prompts.get("save_solution", _DEFAULT_TOOL_PROMPTS["save_solution"]),
                func=save_solution_tool,
                args_schema=SaveSolutionArgs,
                coroutine=save_solution_tool,
            ))

    if "system_propose" not in disabled or "system_confirm" not in disabled:
        from src.core.platform.tools.system_monitor import (
            propose_command, confirm_command, _requires_confirmation
        )

        needs_confirmation = _requires_confirmation(profile)

        if "system_propose" not in disabled:
            async def system_propose_tool(command: str) -> Dict[str, Any]:
                return await propose_command(command, profile)

            if needs_confirmation:
                propose_desc = prompts.get("system_propose", _DEFAULT_TOOL_PROMPTS["system_propose"])
            else:
                propose_desc = (
                    "Execute a shell command directly on the Linux server and return the output. "
                    "Use when the user asks to run a command or check server status (CPU, memory, disk, processes). "
                    "The command runs immediately — NO confirmation code is needed. "
                    "Just call this tool and show the user the result."
                )

            tools.append(StructuredTool(
                name="system_propose",
                description=propose_desc,
                func=system_propose_tool,
                args_schema=SystemProposeArgs,
                coroutine=system_propose_tool,
            ))

        # system_confirm is only useful when confirmation is required
        if "system_confirm" not in disabled and needs_confirmation:
            async def system_confirm_tool(code: str) -> Dict[str, Any]:
                return await confirm_command(code)

            tools.append(StructuredTool(
                name="system_confirm",
                description=prompts.get("system_confirm", _DEFAULT_TOOL_PROMPTS["system_confirm"]),
                func=system_confirm_tool,
                args_schema=SystemConfirmArgs,
                coroutine=system_confirm_tool,
            ))

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
            return {"job_id": result.data.id, "name": result.data.name, "cron_expr": result.data.cron_expr, "status": "created"}

        async def cron_list_tool() -> Dict[str, Any]:
            result = job_usecases.list_usecase.execute(profile.user_id)
            return {"jobs": [{"id": j.id, "name": j.name, "cron_expr": j.cron_expr, "source_type": j.source_type, "destination_type": j.destination_type, "enabled": j.enabled, "status": j.status, "last_run_at": j.last_run_at} for j in result.data]}

        async def cron_delete_tool(job_id: str) -> Dict[str, Any]:
            job_usecases.delete_usecase.execute(job_id)
            return {"deleted": True, "job_id": job_id}

        async def cron_run_tool(job_id: str) -> Dict[str, Any]:
            result = await job_usecases.run_usecase.execute(job_id)
            return {"status": result.status, "result": result.result}

        if "cron_create" not in disabled:
            tools.append(StructuredTool(
                name="cron_create",
                description=prompts.get("cron_create", _DEFAULT_TOOL_PROMPTS["cron_create"]),
                func=cron_create_tool,
                args_schema=CronCreateArgs,
                coroutine=cron_create_tool,
            ))
        if "cron_list" not in disabled:
            tools.append(StructuredTool(
                name="cron_list",
                description=prompts.get("cron_list", _DEFAULT_TOOL_PROMPTS["cron_list"]),
                func=cron_list_tool,
                args_schema=None,
                coroutine=cron_list_tool,
            ))
        if "cron_delete" not in disabled:
            tools.append(StructuredTool(
                name="cron_delete",
                description=prompts.get("cron_delete", _DEFAULT_TOOL_PROMPTS["cron_delete"]),
                func=cron_delete_tool,
                args_schema=CronDeleteArgs,
                coroutine=cron_delete_tool,
            ))
        if "cron_run" not in disabled:
            tools.append(StructuredTool(
                name="cron_run",
                description=prompts.get("cron_run", _DEFAULT_TOOL_PROMPTS["cron_run"]),
                func=cron_run_tool,
                args_schema=CronRunArgs,
                coroutine=cron_run_tool,
            ))

    return tools
