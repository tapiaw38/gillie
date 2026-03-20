"""
Pydantic Models for Tool Validation

This module defines Pydantic models for validating tool arguments.
Each model corresponds to a tool that can be called by the AI assistant.
"""

import fnmatch
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
            return f"Error fetching image from URL: {e}"

    async def take_screenshot_tool(question: str = "Describe what is visible on the screen.") -> str:
        """Capture the desktop screen and describe its contents using vision AI."""
        import asyncio
        import base64 as b64
        import tempfile
        import os

        # Detect display server to pick the right tool
        is_wayland = bool(os.environ.get("WAYLAND_DISPLAY"))

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        path = tmp.name

        # Wayland-native tools first, then X11 fallbacks
        if is_wayland:
            _CAPTURE_CMDS = [
                ["grim", path],                                    # Wayland (sway/wlroots)
                ["gnome-screenshot", "-f", path],                  # GNOME on Wayland
                ["spectacle", "-b", "-o", path],                   # KDE on Wayland
                ["scrot", "-z", path],                             # X11 via XWayland
                ["import", "-window", "root", path],               # ImageMagick via XWayland
                ["maim", path],                                    # X11 via XWayland
            ]
        else:
            _CAPTURE_CMDS = [
                ["scrot", "-z", path],
                ["maim", path],
                ["import", "-window", "root", path],               # ImageMagick
                ["gnome-screenshot", "-f", path],
                ["spectacle", "-b", "-o", path],
            ]

        captured = False
        for cmd in _CAPTURE_CMDS:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
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
    # _browser_state holds either:
    #   - a headless Chromium launched by _get_page()
    #   - a real user browser connected via CDP (browser_connect tool)
    # The "connected" flag distinguishes the two so browser_close doesn't
    # try to shut down the user's real browser.
    _browser_state: Dict[str, Any] = {
        "playwright": None,
        "browser": None,
        "page": None,
        "connected": False,   # True when attached to a real browser via CDP
    }

    async def _get_page():
        """Return (or lazily create) the shared Playwright page."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "playwright is not installed. Run: pip install playwright && playwright install chromium"
            )
        if _browser_state["page"] is None or _browser_state["page"].is_closed():
            if _browser_state["playwright"] is None:
                _browser_state["playwright"] = await async_playwright().start()
            _browser_state["browser"] = await _browser_state["playwright"].chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = await _browser_state["browser"].new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            )
            _browser_state["page"] = await context.new_page()
        return _browser_state["page"]

    async def _connect_cdp(cdp_url: str):
        """Internal: attempt CDP connection and update _browser_state. Raises on failure."""
        from playwright.async_api import async_playwright
        if _browser_state["browser"] and not _browser_state["connected"]:
            await _browser_state["browser"].close()
        if _browser_state["playwright"] is None:
            _browser_state["playwright"] = await async_playwright().start()
        browser = await _browser_state["playwright"].chromium.connect_over_cdp(cdp_url)
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

        port = int(cdp_url.split(":")[-1]) if ":" in cdp_url else 9222

        # First attempt — CDP might already be available (Chrome already running with --remote-debugging-port)
        try:
            await _connect_cdp(cdp_url)
        except Exception:
            # CDP not available — relaunch Chrome with real user profile + remote debugging
            logger.info("browser_connect: CDP not available, relaunching Chrome with remote debugging...")

            # Find Chrome binary
            chrome_bins = ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser"]
            import shutil
            chrome_bin = next((b for b in chrome_bins if shutil.which(b)), None)
            if not chrome_bin:
                return (
                    "Chrome is not installed. Install google-chrome-stable and try again."
                )

            # Kill existing Chrome so it releases the profile lock
            await asyncio.create_subprocess_exec(
                "pkill", "-f", chrome_bin,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.sleep(2)

            # Relaunch Chrome with real user profile so sessions are preserved
            real_profile = os.path.expanduser("~/.config/google-chrome")
            await asyncio.create_subprocess_exec(
                chrome_bin,
                f"--remote-debugging-port={port}",
                f"--user-data-dir={real_profile}",
                "--no-first-run",
                "--no-default-browser-check",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )

            # Wait up to 30s for CDP to become available
            connected = False
            for _ in range(30):
                await asyncio.sleep(1)
                try:
                    await _connect_cdp(cdp_url)
                    connected = True
                    break
                except Exception:
                    continue

            if not connected:
                return (
                    f"Chrome was relaunched with remote debugging on port {port} but CDP "
                    "is not yet available. Wait a few seconds and call browser_connect again."
                )

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
                            # Only top-level functions (not methods already handled above)
                            pass
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
    ) -> Dict[str, Any]:
        """Search for a text/regex pattern inside files."""
        resolved, err = _resolve_safe_path(path)
        if err:
            return {"found": 0, "results": [], "truncated": False, "error": err}
        if not resolved.exists() or not resolved.is_dir():
            return {"found": 0, "results": [], "truncated": False, "error": f"Path not found or not a directory: '{path}'"}

        _SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
        flags = _re.IGNORECASE if ignore_case else 0
        try:
            compiled = _re.compile(pattern, flags)
        except _re.error as e:
            return {"found": 0, "results": [], "truncated": False, "error": f"Invalid regex pattern: {e}"}

        results = []
        truncated = False

        for file_path in resolved.rglob(file_glob):
            # Skip excluded directories and ignored paths
            if any(part in _SKIP_DIRS for part in file_path.parts):
                continue
            if _is_ignored(file_path, workspace):
                continue
            if not file_path.is_file():
                continue

            try:
                raw = file_path.read_bytes()
                if b"\x00" in raw[:8192]:
                    continue  # binary file
                text = raw.decode("utf-8", errors="replace")
            except Exception:
                continue

            for line_num, line in enumerate(text.splitlines(), start=1):
                if compiled.search(line):
                    results.append({
                        "file": str(file_path.relative_to(resolved)),
                        "line": line_num,
                        "content": line.strip(),
                    })
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
        _tool("git_status",             prompts.get("git_status",  _DEFAULT_TOOL_PROMPTS["git_status"]), git_status_tool, GitStatusArgs),
        _tool("git_diff",               prompts.get("git_diff",    _DEFAULT_TOOL_PROMPTS["git_diff"]),   git_diff_tool,   GitDiffArgs),
        _tool("git_log",                prompts.get("git_log",     _DEFAULT_TOOL_PROMPTS["git_log"]),    git_log_tool,    GitLogArgs),
        _tool("git_commit",             prompts.get("git_commit",  _DEFAULT_TOOL_PROMPTS["git_commit"]), git_commit_tool, GitCommitArgs),
        _tool("search_images",          prompts["search_images"],          search_images_tool,   SearchImagesArgs),
        _tool("analyze_pdf",            prompts["analyze_pdf"],            analyze_pdf_tool,     AnalyzePDFArgs),
        _tool("extract_text_from_pdf",  prompts["extract_text_from_pdf"],  extract_text_tool,    ExtractTextArgs),
        _tool("analyze_excel",          prompts["analyze_excel"],          analyze_excel_tool,   AnalyzeExcelArgs),
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
