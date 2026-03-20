"""
Agent CLI — Interactive chat with the Gillie assistant from the terminal.

Usage:
  gillie agent                  # start or resume the CLI conversation
  gillie agent --new            # force a new conversation
  gillie agent --id <conv_id>   # attach to a specific conversation

In-chat commands:
  /new     — start a new conversation
  /clear   — delete all messages in current conversation
  /id      — show current conversation ID
  /exit    — quit (also Ctrl+C or Ctrl+D)
"""

import os
import re
import sys
import glob as _glob
import typer
import requests
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule
from rich import box
from rich.text import Text

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style as PTStyle
    _PT_AVAILABLE = True
except ImportError:
    _PT_AVAILABLE = False

from cli.config.manager import config_exists, load_config

console = Console()
app = typer.Typer()

_CLI_CONV_TITLE = "CLI Agent"


# ─── Approval modes ────────────────────────────────────────────────────────────

class _Mode:
    PLAN          = "plan"       # read-only: describes changes but never applies them
    DEFAULT       = "default"    # ask for every state-mutating tool
    CONFIRM_RISKY = "risky"      # auto-accept reads/edits, ask only for shell/commit
    AUTO_EDIT     = "auto-edit"  # auto-accept file edits, ask for shell/commit
    YOLO          = "yolo"       # accept everything silently


_MODES_CYCLE = [
    _Mode.PLAN,
    _Mode.DEFAULT,
    _Mode.CONFIRM_RISKY,
    _Mode.AUTO_EDIT,
    _Mode.YOLO,
]

# Pure read tools — always auto-accept in every mode.
_SAFE_TOOLS = {
    "read_file", "list_directory", "find_files", "grep_files", "repo_map",
    "git_status", "git_diff", "git_log",
    "web_search", "fetch_url", "search_images", "search_documents",
    "query_database", "save_memory", "search_memory", "organize_memory",
    "save_solution", "cron_list", "describe_image",
}

# High-risk: always ask, even in AUTO_EDIT.
_ALWAYS_ASK_TOOLS = {"run_shell", "git_commit"}

# File / state mutations: ask in DEFAULT and CONFIRM_RISKY, auto-accept in AUTO_EDIT+YOLO.
_EDIT_TOOLS = {
    "edit_file", "write_file", "cron_create", "cron_delete", "cron_run",
    "system_propose", "system_confirm",
}


def _should_ask(tool_name: str, mode: str, always_approved: set) -> bool:
    """Return True when the user must be prompted before the tool runs."""
    if tool_name in always_approved:
        return False
    if tool_name in _SAFE_TOOLS:
        return False
    if mode == _Mode.YOLO:
        return False
    if mode == _Mode.PLAN:
        # Plan mode never executes — the tool itself returns a plan_only dict.
        return False
    if mode == _Mode.AUTO_EDIT and tool_name in _EDIT_TOOLS:
        return False
    # CONFIRM_RISKY: ask for _EDIT_TOOLS and _ALWAYS_ASK_TOOLS.
    # DEFAULT: ask for everything that isn't in _SAFE_TOOLS.
    return True


def _build_prompt(mode: str) -> str:
    """Return the prompt string for the REPL input line."""
    indicators = {
        _Mode.PLAN:          "[plan] You › ",
        _Mode.CONFIRM_RISKY: "[risky] You › ",
        _Mode.AUTO_EDIT:     "[auto] You › ",
        _Mode.YOLO:          "[yolo] You › ",
        _Mode.DEFAULT:       "You › ",
    }
    return indicators.get(mode, "You › ")


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _base_url() -> str:
    config = load_config()
    host = config.server.host or "127.0.0.1"
    if host == "0.0.0.0":
        host = "127.0.0.1"
    port = config.server.port or 8000
    return f"http://{host}:{port}"


def _workspace_headers(mode: str = "") -> dict:
    """Return HTTP headers carrying the client workspace path and optional mode."""
    headers = {"X-Gillie-Workspace": str(_workspace())}
    if mode == _Mode.PLAN:
        headers["X-Gillie-Mode"] = "plan"
    return headers


def _get(path: str) -> dict:
    try:
        resp = requests.get(_base_url() + path, headers=_workspace_headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("\n[red]✗[/red] Cannot connect to API. Is [bold cyan]gillie start[/bold cyan] running?")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}")
        raise typer.Exit(1)


def _post_json(path: str, data: dict) -> dict:
    try:
        resp = requests.post(_base_url() + path, json=data, headers=_workspace_headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("\n[red]✗[/red] Cannot connect to API. Is [bold cyan]gillie start[/bold cyan] running?")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}")
        raise typer.Exit(1)


def _post_form(path: str, content: str) -> dict:
    try:
        resp = requests.post(
            _base_url() + path,
            data={"content": content},
            headers=_workspace_headers(),
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("\n[red]✗[/red] Cannot connect to API. Is [bold cyan]gillie start[/bold cyan] running?")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}")
        return {}


def _delete(path: str) -> dict:
    try:
        resp = requests.delete(_base_url() + path, headers=_workspace_headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print("\n[red]✗[/red] Cannot connect to API. Is [bold cyan]gillie start[/bold cyan] running?")
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}")
        return {}


# ─── Conversation helpers ──────────────────────────────────────────────────────

def _find_cli_conversation() -> dict | None:
    """Return the existing CLI Agent conversation, or None."""
    result = _get("/conversation/user")
    conversations = result.get("data", [])
    for conv in conversations:
        if conv.get("title") == _CLI_CONV_TITLE:
            return conv
    return None


def _create_conversation() -> dict:
    """Create a new CLI Agent conversation."""
    result = _post_json("/conversation/", {"title": _CLI_CONV_TITLE})
    return result.get("data", result)


def _send_message(conv_id: str, content: str) -> str:
    """Send a message and return the assistant's reply text."""
    result = _post_form(f"/conversation/{conv_id}/message", content)
    messages = result.get("data", [])
    if not messages:
        return "(no reply)"
    # Last message is the assistant's reply
    last = messages[-1]
    return last.get("content", "(no reply)")


def _clear_messages(conv_id: str) -> None:
    _delete(f"/conversation/{conv_id}/message")


# ─── Display helpers ───────────────────────────────────────────────────────────

def _print_header(assistant_name: str, conv_id: str, mode: str = _Mode.CONFIRM_RISKY) -> None:
    ws = _workspace()
    console.print()
    console.print(Panel(
        f"✨🐟 [bold cyan]{assistant_name}[/bold cyan]\n"
        f"[dim]Conversation: {conv_id}[/dim]\n"
        f"[dim]Workspace:    {ws}[/dim]\n"
        f"[dim]Mode: {mode} | /mode para cambiar[/dim]\n"
        f"[dim]/new · /list · /clear · /id · /mode · /compactar · /exit[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
    ))
    console.print()


def _print_user(text: str) -> None:
    console.print(f"[bold white]You[/bold white]  [dim]{text}[/dim]")



def _print_assistant(name: str, text: str) -> None:
    """Print assistant reply (plain, no typewriter — used for history)."""
    console.print()
    console.print(f"[bold cyan]{name}[/bold cyan]")
    console.print(text)
    console.print(Rule(style="dim"))
    console.print()


def _play_audio(url: str) -> None:
    """Play an audio URL using the first available system player."""
    import subprocess
    if not url.startswith("http"):
        return
    players = [
        ["mpv", "--no-video", "--really-quiet", "--speed=1.3", url],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-af", "atempo=1.3", url],
        ["vlc", "--intf", "dummy", "--play-and-exit", "--quiet", "--rate=1.3", url],
    ]
    for cmd in players:
        try:
            subprocess.run(cmd, timeout=120, check=True)
            return
        except FileNotFoundError:
            continue
        except subprocess.CalledProcessError:
            return
    console.print("[yellow]⚠[/yellow] No audio player found. Install [bold]mpv[/bold] or [bold]ffplay[/bold].")


def _stream_assistant(
    conv_id: str,
    name: str,
    content: str,
    auto_approve: bool = False,
    mode: str = _Mode.CONFIRM_RISKY,
    always_approved: set = None,
    always_rejected: set = None,
) -> str:
    """Stream the assistant reply token by token from the SSE endpoint.

    When the backend emits an approval_request event the function pauses,
    shows the diff with ANSI colours, and applies the approval decision
    determined by the current mode and the per-session always_approved /
    always_rejected sets.

    Args:
        conv_id: Conversation ID to stream from.
        name: Assistant display name.
        content: The user message to send.
        auto_approve: Legacy flag — equivalent to mode=YOLO (kept for
                      backward compatibility with ``--yolo``).
        mode: Approval mode string (one of _Mode constants).
        always_approved: Set of tool names that were approved with 'a'
                         during this session; never prompted again.
        always_rejected: Set of tool names rejected with 's' for the whole
                         session; always auto-rejected without prompting.
    """
    import sys
    import threading
    import time

    if always_approved is None:
        always_approved = set()
    if always_rejected is None:
        always_rejected = set()

    # --yolo flag maps to YOLO mode for backward compatibility.
    effective_mode = _Mode.YOLO if auto_approve else mode

    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    _first_token = threading.Event()
    _stop_spinner = threading.Event()

    def _spinner():
        i = 0
        while not _first_token.is_set() and not _stop_spinner.is_set():
            sys.stdout.write(f"\r{_FRAMES[i % len(_FRAMES)]} Thinking...  ")
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1
        sys.stdout.write(f"\r{' ' * 25}\r")
        sys.stdout.flush()

    spinner_thread = threading.Thread(target=_spinner, daemon=True)
    spinner_thread.start()

    console.print()
    console.print(f"[bold cyan]{name}[/bold cyan]")

    full_text = ""
    try:
        resp = requests.post(
            _base_url() + f"/conversation/{conv_id}/message/stream",
            data={"content": content},
            headers=_workspace_headers(effective_mode),
            stream=True,
            timeout=120,
        )
        resp.raise_for_status()
        import json as _json
        audio_url = None
        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            try:
                token = _json.loads(payload)
            except _json.JSONDecodeError:
                token = payload  # fallback for non-JSON frames
            if token == "[DONE]":
                break
            if isinstance(token, dict):
                if token.get("type") == "audio":
                    audio_url = token.get("url")
                elif token.get("type") == "tool_call":
                    tool_name = token.get("name", "tool")
                    sys.stdout.write(f"\r\033[2m🔧 {tool_name}...\033[0m      \n")
                    sys.stdout.flush()
                elif token.get("type") == "compaction":
                    _stop_spinner.set()
                    console.print(
                        f"[dim]Conversation compacted to optimise context[/dim]"
                    )
                elif token.get("type") == "shell_output":
                    line_text = token.get("line", "")
                    if line_text:
                        if not _first_token.is_set():
                            _first_token.set()
                            spinner_thread.join()
                        sys.stdout.write(f"\r\033[2m{line_text}\033[0m\n")
                        sys.stdout.flush()
                elif token.get("type") == "approval_request":
                    # Stop the spinner so we can display an interactive prompt.
                    _stop_spinner.set()
                    spinner_thread.join()

                    request_id = token.get("request_id", "")
                    tool_name  = token.get("tool", "tool")
                    file_path  = token.get("file", "")
                    diff       = token.get("diff", "")

                    console.print(
                        f"\n[bold]🔧 {tool_name}[/bold] → [cyan]{file_path}[/cyan]"
                    )
                    if diff:
                        for diff_line in diff.splitlines():
                            if diff_line.startswith("+") and not diff_line.startswith("+++"):
                                console.print(f"[green]{diff_line}[/green]")
                            elif diff_line.startswith("-") and not diff_line.startswith("---"):
                                console.print(f"[red]{diff_line}[/red]")
                            elif diff_line.startswith("@@"):
                                console.print(f"[cyan]{diff_line}[/cyan]")
                            else:
                                console.print(f"[dim]{diff_line}[/dim]")

                    # Determine whether to prompt or auto-decide.
                    ask = _should_ask(tool_name, effective_mode, always_approved)

                    if tool_name in always_rejected:
                        approved = False
                        feedback = ""
                        console.print("[dim]  Auto-rejected (session skip)[/dim]")
                    elif not ask:
                        approved = True
                        feedback = ""
                        console.print("[dim]  Auto-accepted[/dim]")
                    else:
                        approved = False
                        feedback = ""
                        while True:
                            try:
                                choice = console.input(
                                    "\nApply? "
                                    "[[bold]y[/bold]]es / "
                                    "[[bold]n[/bold]]o / "
                                    "[[bold]a[/bold]]lways (this tool) / "
                                    "[[bold]s[/bold]]kip session: "
                                ).strip().lower()
                            except (KeyboardInterrupt, EOFError):
                                choice = "n"
                            if choice in ("y", "yes", ""):
                                approved = True
                                break
                            elif choice in ("n", "no"):
                                approved = False
                                try:
                                    feedback = console.input(
                                        "[dim]Reason (Enter to skip): [/dim]"
                                    ).strip()
                                except (KeyboardInterrupt, EOFError):
                                    feedback = ""
                                break
                            elif choice in ("a", "always"):
                                approved = True
                                always_approved.add(tool_name)
                                console.print(
                                    f"[dim]'{tool_name}' auto-accepted for the rest of this session[/dim]"
                                )
                                break
                            elif choice in ("s", "skip"):
                                approved = False
                                always_rejected.add(tool_name)
                                console.print(
                                    f"[dim]'{tool_name}' skipped for the rest of this session[/dim]"
                                )
                                break
                            # Any other input: re-prompt

                    try:
                        requests.post(
                            _base_url() + "/conversation/tool/approve",
                            json={
                                "request_id": request_id,
                                "approved": approved,
                                "feedback": feedback,
                            },
                            headers=_workspace_headers(),
                            timeout=10,
                        )
                    except Exception:
                        pass  # best-effort; the backend will timeout after 120s

                    # Restart the spinner while the backend continues processing.
                    _stop_spinner.clear()
                    spinner_thread = threading.Thread(target=_spinner, daemon=True)
                    spinner_thread.start()
                continue
            if isinstance(token, str) and token.startswith("[ERROR]"):
                _first_token.set()
                console.print(f"\n[red]✗[/red] {token[7:].strip()}")
                break
            if not _first_token.is_set():
                _first_token.set()
                spinner_thread.join()
            sys.stdout.write(token)
            sys.stdout.flush()
            full_text += token
    except requests.exceptions.ConnectionError:
        _stop_spinner.set()
        console.print("\n[red]✗[/red] Cannot connect to API.")
    except requests.exceptions.HTTPError as e:
        _stop_spinner.set()
        console.print(f"\n[red]✗[/red] API error {e.response.status_code}")
    finally:
        _stop_spinner.set()

    sys.stdout.write("\n")
    sys.stdout.flush()
    console.print(Rule(style="dim"))
    console.print()

    if audio_url:
        console.print(f"[dim]🔊 Playing audio...[/dim]")
        _play_audio(audio_url)

    return full_text


def _print_history(messages: list, assistant_name: str) -> None:
    """Print the last few messages so the user has context on resume."""
    if not messages:
        return
    recent = messages[-6:]  # last 3 exchanges
    console.print(Rule("[dim]recent history[/dim]", style="dim"))
    for msg in recent:
        sender = msg.get("sender", "")
        content = msg.get("content", "")
        if sender == "user":
            _print_user(content)
        else:
            _print_assistant(assistant_name, content)
    console.print(Rule(style="dim"))
    console.print()


# ─── @ reference resolution ───────────────────────────────────────────────────

_AT_URL_RE  = re.compile(r'@(https?://[^\s]+)')
_AT_GLOB_RE = re.compile(r'@@([^\s]+)')
_AT_DIR_RE  = re.compile(r'@([^\s@]+/)')
_AT_FILE_RE = re.compile(r'@([^\s@/]+(?:\.[^\s@/]*)?)')  # matches with or without extension

_URL_CAP        = 3_000
_FILE_CAP       = 4_000
_DIR_FILE_CAP   = 500
_DIR_TOTAL_CAP  = 5_000
_WARN_TOTAL     = 8_000

_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache", ".pytest_cache"}


def _workspace() -> Path:
    """Return the base directory for @ references and file tools.

    Priority:
    1. GILLIE_WORKSPACE env var  (set by --workspace flag or user env)
    2. Current working directory (where the user ran gillie agent)
    """
    env = os.environ.get("GILLIE_WORKSPACE")
    return Path(env).resolve() if env else Path.cwd().resolve()


def _is_binary(path: Path) -> bool:
    """Return True if the first 512 bytes contain a null byte (binary file)."""
    try:
        with open(path, "rb") as fh:
            return b"\x00" in fh.read(512)
    except OSError:
        return True


def _strip_html(html: str) -> str:
    """Remove HTML tags and collapse whitespace for a plain-text approximation."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _expand_url(url: str) -> tuple[str, str | None]:
    """Fetch a URL and return (plain_text_content, warning_or_None)."""
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "gillie-cli/1.0"})
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        raw = resp.text
        if "html" in content_type:
            raw = _strip_html(raw)
        if len(raw) > _URL_CAP:
            raw = raw[:_URL_CAP] + f"\n[... truncated at {_URL_CAP} chars]"
        return raw, None
    except requests.exceptions.RequestException as exc:
        return "", f"Could not fetch URL {url}: {exc}"


def _expand_glob(pattern: str) -> tuple[str, str | None]:
    """Match a glob pattern relative to the workspace and return a file list."""
    base = _workspace()
    matched = sorted(_glob.glob(str(base / pattern), recursive=True))
    if not matched:
        return "", f"@@{pattern} matched no files"
    # Make paths relative to the workspace for readability
    rel_paths = []
    for p in matched:
        try:
            rel_paths.append(str(Path(p).relative_to(base)))
        except ValueError:
            rel_paths.append(p)
    listing = "\n".join(rel_paths)
    block = f"--- @@{pattern} ({len(rel_paths)} files) ---\n{listing}\n--- end ---"
    return block, None


def _expand_dir(directory: str) -> tuple[str, str | None]:
    """Read all text files in a directory recursively."""
    base = _workspace()
    dir_path = base / directory.rstrip("/")
    if not dir_path.is_dir():
        return "", f"Directory not found: {directory}"

    collected: list[str] = []
    total_chars = 0
    file_count = 0

    for root, dirs, files in os.walk(dir_path):
        # Prune directories we should skip
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in sorted(files):
            fpath = Path(root) / fname
            if _is_binary(fpath):
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if len(text) > _DIR_FILE_CAP:
                text = text[:_DIR_FILE_CAP] + f"\n[... truncated at {_DIR_FILE_CAP} chars]"
            try:
                rel = str(fpath.relative_to(base))
            except ValueError:
                rel = str(fpath)
            entry = f"=== {rel} ===\n{text}"
            if total_chars + len(entry) > _DIR_TOTAL_CAP:
                break
            collected.append(entry)
            total_chars += len(entry)
            file_count += 1
        else:
            continue
        break  # inner break propagates

    if not collected:
        return "", f"No readable text files found in {directory}"

    body = "\n\n".join(collected)
    block = f"--- @{directory} ({file_count} files) ---\n{body}\n--- end ---"
    return block, None


def _expand_file(filepath: str) -> tuple[str, str | None]:
    """Read a single file relative to the workspace."""
    base = _workspace()
    fpath = base / filepath
    if not fpath.exists():
        return "", f"File not found: {filepath}"
    if _is_binary(fpath):
        return "", f"Skipped binary file: {filepath}"
    try:
        text = fpath.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return "", f"Could not read {filepath}: {exc}"
    if len(text) > _FILE_CAP:
        text = text[:_FILE_CAP] + f"\n[... truncated at {_FILE_CAP} chars]"
    block = f"--- @{filepath} ---\n{text}\n--- end ---"
    return block, None


def _resolve_at_references(text: str) -> tuple[str, list[str]]:
    """
    Parse @ references in user input and replace them with their content.

    Supported syntax:
      @https://...          fetch URL content
      @@pattern             glob file listing (names only)
      @path/to/dir/         read all text files in directory
      @path/to/file.ext     read a single file

    Returns (expanded_text, warnings).
    """
    warnings: list[str] = []

    def _replace(match_obj: re.Match, expander, raw_ref: str) -> str:
        content, warn = expander(match_obj.group(1))
        if warn:
            warnings.append(warn)
            return match_obj.group(0)  # leave original token unchanged
        return content

    # Process in specificity order: URL → glob (@@) → directory → file.
    # Each pass operates on the already-substituted text so overlapping
    # patterns don't re-process expanded blocks.

    # 1. URLs — @http:// or @https://
    text = _AT_URL_RE.sub(
        lambda m: _replace(m, lambda u: _expand_url(u), m.group(0)),
        text,
    )

    # 2. Glob — @@pattern (must run before single-@ patterns)
    text = _AT_GLOB_RE.sub(
        lambda m: _replace(m, lambda p: _expand_glob(p), m.group(0)),
        text,
    )

    # 3. Directory — @path/ending/with/slash/
    text = _AT_DIR_RE.sub(
        lambda m: _replace(m, lambda d: _expand_dir(d), m.group(0)),
        text,
    )

    # 4. File — @path/with/extension.ext
    text = _AT_FILE_RE.sub(
        lambda m: _replace(m, lambda f: _expand_file(f), m.group(0)),
        text,
    )

    return text, warnings


# ─── Main command ──────────────────────────────────────────────────────────────

@app.command("listen")
def listen(
    silence: float = typer.Option(2.5, "--silence", "-s", help="Seconds of silence to detect end of phrase"),
    threshold: float = typer.Option(0.01, "--threshold", "-t", help="RMS silence threshold (0.0–1.0)"),
    new: bool = typer.Option(False, "--new", "-n", help="Force a new conversation"),
    conv_id: str = typer.Option(None, "--id", help="Attach to a specific conversation ID"),
):
    """Voice listen mode: record your voice, assistant replies in text."""
    if not config_exists():
        console.print("[red]✗[/red] Not initialized. Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    try:
        import sounddevice as sd
        import numpy as np
    except ImportError:
        console.print("[red]✗[/red] sounddevice not found. Run: [bold cyan]gillie install[/bold cyan]")
        raise typer.Exit(1)

    import wave
    import io
    import tempfile

    config = load_config()
    assistant_name = config.profile.assistant_name

    # ── resolve conversation ──────────────────────────────────────────────────
    if conv_id:
        result = _get(f"/conversation/{conv_id}")
        conversation = result.get("data", result)
    elif new:
        conversation = _create_conversation()
    else:
        conversation = _find_cli_conversation() or _create_conversation()

    current_id = conversation.get("id") or conversation.get("_id")
    if not current_id:
        console.print("[red]✗[/red] Could not retrieve conversation ID.")
        raise typer.Exit(1)

    SAMPLE_RATE = 16000
    CHUNK = int(SAMPLE_RATE * 0.1)  # 100ms chunks
    silence_chunks_needed = int(silence / 0.1)

    # WebRTC VAD for human voice detection (optional)
    _vad = None
    try:
        import webrtcvad as _webrtcvad
        _vad = _webrtcvad.Vad(2)  # aggressiveness 0-3 (2 = balanced; RMS pre-filters energy)
        vad_status = "voice detection: on"
    except ImportError:
        vad_status = "voice detection: off (pip install webrtcvad)"

    console.print()
    console.print(Panel(
        f"✨🐟 [bold cyan]{assistant_name}[/bold cyan] — listen mode\n"
        f"[dim]Speak when you see the mic. {silence}s of silence to send. Ctrl+C to quit.[/dim]\n"
        f"[dim]{vad_status}[/dim]",
        border_style="cyan",
    ))
    console.print()

    BAR_WIDTH = 20
    _VAD_FRAME = int(SAMPLE_RATE * 0.03)  # 30ms frames required by webrtcvad

    def _is_voice(chunk_float: "np.ndarray") -> bool:
        """True if chunk contains human voice (falls back to RMS if VAD unavailable)."""
        rms = float(np.sqrt(np.mean(chunk_float ** 2)))
        # Pre-filter: must have minimum energy regardless of VAD
        if rms <= threshold:
            return False
        if _vad is None:
            return True
        chunk_int16 = (np.clip(chunk_float.flatten(), -1.0, 1.0) * 32767).astype(np.int16)
        n_frames = len(chunk_int16) // _VAD_FRAME
        if n_frames == 0:
            return True
        voice_frames = sum(
            1 for i in range(n_frames)
            if _vad.is_speech(chunk_int16[i * _VAD_FRAME:(i + 1) * _VAD_FRAME].tobytes(), SAMPLE_RATE)
        )
        return voice_frames / n_frames >= 0.5

    def _level_bar(rms: float, recording: bool) -> str:
        """Draw audio level bar."""
        filled = min(BAR_WIDTH, int(rms / (threshold * 5) * BAR_WIDTH))
        bar = "█" * filled + "░" * (BAR_WIDTH - filled)
        if recording:
            return f"[bold red]🔴 [{bar}][/bold red]"
        else:
            return f"[dim]🎙  [{bar}][/dim]"

    _VOICE_STREAK_NEEDED = 3  # 300ms of continuous voice required to start recording

    def _record_utterance() -> bytes | None:
        """Record until N seconds of silence detected. Returns WAV bytes."""
        audio_chunks = []
        pre_buffer = []   # holds chunks before speech confirmed
        silence_count = 0
        voice_streak = 0
        started = False

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
            while True:
                chunk, _ = stream.read(CHUNK)
                rms = float(np.sqrt(np.mean(chunk ** 2)))
                is_voice = _is_voice(chunk)

                if is_voice:
                    voice_streak += 1
                    silence_count = 0
                    if not started:
                        pre_buffer.append(chunk.copy())
                        if voice_streak >= _VOICE_STREAK_NEEDED:
                            # Confirmed speech: flush pre-buffer into recording
                            started = True
                            audio_chunks.extend(pre_buffer)
                            pre_buffer.clear()
                    else:
                        audio_chunks.append(chunk.copy())
                else:
                    voice_streak = 0
                    if not started:
                        # Discard pre-buffer older than the streak window
                        pre_buffer = pre_buffer[-(  _VOICE_STREAK_NEEDED - 1):]
                    elif started:
                        silence_count += 1
                        audio_chunks.append(chunk.copy())

                # Real-time level bar
                bar = _level_bar(rms, started)
                print(f"\r{' ' * 50}\r", end="", flush=True)
                console.print(bar + "  ", end="\r")

                if started and silence_count >= silence_chunks_needed:
                    print(f"\r{' ' * 50}\r", end="", flush=True)
                    break

        if not audio_chunks:
            return None

        _MIN_CHUNKS = int(1.0 / 0.1)  # 10 chunks × 100ms
        if len(audio_chunks) < _MIN_CHUNKS:
            return None

        audio_np = np.concatenate(audio_chunks, axis=0)
        audio_int16 = (np.clip(audio_np, -1.0, 1.0) * 32767).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())
        return buf.getvalue()

    def _send_voice(conv_id: str, wav_bytes: bytes) -> tuple[str, str | None]:
        """Send audio to the message endpoint and return (reply_text, audio_url)."""
        try:
            resp = requests.post(
                _base_url() + f"/conversation/{conv_id}/message",
                data={"content": " "},  # required by multipart form
                files={"voice_content": ("audio.wav", wav_bytes, "audio/wav")},
                headers=_workspace_headers(),
                timeout=60,
            )
            resp.raise_for_status()
            messages = resp.json().get("data", [])
            if messages:
                last = messages[-1]
                return last.get("content", "(no reply)"), last.get("audio_url")
        except requests.exceptions.ConnectionError:
            console.print("\n[red]✗[/red] Cannot connect to the API.")
        except requests.exceptions.HTTPError as e:
            console.print(f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}")
        return "(no reply)", None

    # ── loop principal ────────────────────────────────────────────────────────
    while True:
        try:
            console.print("[dim]🎙  Ready — speak whenever you want...[/dim]")
            wav_bytes = _record_utterance()
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye 👋[/dim]")
            break

        if not wav_bytes:
            continue

        console.print("[dim]⏳ Processing...[/dim]     ", end="\r")
        reply, audio_url = _send_voice(current_id, wav_bytes)
        console.print(" " * 40, end="\r")  # clear line
        _print_assistant(assistant_name, reply)
        console.print(Rule(style="dim"))
        if audio_url:
            console.print("[dim]🔊 Playing audio...[/dim]")
            _play_audio(audio_url)


@app.command("list")
def list_conversations():
    """List all conversations with their ID and title."""
    if not config_exists():
        console.print("[red]✗[/red] Not initialized. Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    from rich.table import Table
    from rich import box as rbox

    result = _get("/conversation/user")
    conversations = result.get("data", [])

    if not conversations:
        console.print("[dim]No conversations found. Start one with [bold cyan]gillie agent[/bold cyan].[/dim]")
        return

    table = Table(box=rbox.ROUNDED, border_style="cyan", show_lines=False)
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Messages", justify="right")
    table.add_column("Last activity", style="dim")

    for conv in conversations:
        cid = conv.get("id") or conv.get("_id", "")
        title = conv.get("title") or "[dim]no title[/dim]"
        msgs = len(conv.get("messages", []))
        updated = (conv.get("updated_at") or conv.get("created_at") or "")[:19].replace("T", " ")
        table.add_row(cid, title, str(msgs), updated)

    console.print()
    console.print(table)
    console.print()
    console.print(f"[dim]Attach to a conversation: [bold cyan]gillie agent --id <ID>[/bold cyan][/dim]")
    console.print()


@app.command("workspace")
def set_workspace(
    path: str = typer.Argument(None, help="Directory to set as workspace. Omit to show current."),
):
    """Show or set the persistent workspace directory for file tools."""
    from cli.config.manager import config_exists, load_config, save_config
    if not config_exists():
        console.print("[red]✗[/red] Not initialized. Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)
    if path is None:
        ws = _workspace()
        console.print(f"\n[bold]Workspace:[/bold] {ws}")
        console.print(f"[dim]Override with: gillie agent workspace /your/path[/dim]\n")
        return
    ws_path = Path(path).resolve()
    if not ws_path.is_dir():
        console.print(f"[red]✗[/red] Directory not found: {ws_path}")
        raise typer.Exit(1)
    config = load_config()
    config.workspace = str(ws_path)
    save_config(config)
    console.print(f"[green]✓[/green] Workspace set to: {ws_path}")


@app.callback(invoke_without_command=True)
def agent(
    ctx: typer.Context,
    new: bool = typer.Option(False, "--new", "-n", help="Force a new conversation"),
    conv_id: str = typer.Option(None, "--id", help="Attach to a specific conversation ID"),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Set workspace directory for this session"),
    show_workspace: bool = typer.Option(False, "--show-workspace", help="Print current workspace and exit"),
    yolo: bool = typer.Option(False, "--yolo", help="Auto-approve all tool calls (alias for --mode yolo)"),
    mode_flag: str = typer.Option(
        _Mode.CONFIRM_RISKY,
        "--mode", "-m",
        help="Approval mode: plan | default | risky | auto-edit | yolo",
    ),
):
    """Interactive chat with the assistant from the terminal."""
    if ctx.invoked_subcommand is not None:
        return

    if show_workspace:
        console.print(f"\n[bold]Workspace:[/bold] {_workspace()}\n")
        raise typer.Exit(0)

    if not config_exists():
        console.print("[red]✗[/red] Not initialized. Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

    # --yolo is a backward-compatible alias for --mode yolo.
    initial_mode = _Mode.YOLO if yolo else mode_flag
    if initial_mode not in _MODES_CYCLE:
        console.print(
            f"[red]✗[/red] Unknown mode '{initial_mode}'. "
            f"Valid modes: {' | '.join(_MODES_CYCLE)}"
        )
        raise typer.Exit(1)

    # Apply --workspace flag for this session
    if workspace:
        ws_path = Path(workspace).resolve()
        if not ws_path.is_dir():
            console.print(f"[red]✗[/red] Workspace directory not found: {ws_path}")
            raise typer.Exit(1)
        os.environ["GILLIE_WORKSPACE"] = str(ws_path)

    config = load_config()
    assistant_name = config.profile.assistant_name

    # ── resolve conversation ──────────────────────────────────────────────────
    if conv_id:
        result = _get(f"/conversation/{conv_id}")
        conversation = result.get("data", result)
    elif new:
        conversation = _create_conversation()
        console.print(f"[green]✓[/green] New conversation created.")
    else:
        conversation = _find_cli_conversation()
        if conversation is None:
            conversation = _create_conversation()
            console.print(f"[green]✓[/green] New CLI conversation created.")

    current_id = conversation.get("id") or conversation.get("_id")
    if not current_id:
        console.print("[red]✗[/red] Could not retrieve conversation ID.")
        raise typer.Exit(1)

    # Mutable mode container — allows /mode command to update it in-place.
    mode = [initial_mode]

    # Per-session tool approval overrides.
    always_approved: set = set()
    always_rejected: set = set()

    _print_header(assistant_name, current_id, mode[0])

    # Show recent history if resuming
    messages = conversation.get("messages", [])
    if messages:
        _print_history(messages, assistant_name)

    # ── REPL ─────────────────────────────────────────────────────────────────
    console.print(f"[dim]Type your message and press Enter. /exit to quit.[/dim]")
    console.print()

    # Build prompt_toolkit session with @ file completer
    _pt_session = None
    if _PT_AVAILABLE:
        class _AtCompleter(Completer):
            """Tab-complete @path references from the workspace."""
            _SLASH_CMDS = [
                "/new", "/list", "/clear", "/id", "/mode",
                "/compactar", "/exit",
            ]

            def get_completions(self, document, complete_event):
                text = document.text_before_cursor
                # Slash command completion
                if text.startswith("/"):
                    for cmd in self._SLASH_CMDS:
                        if cmd.startswith(text):
                            yield Completion(cmd[len(text):], display=cmd)
                    return
                # @ reference completion
                at_match = re.search(r'@@?([^\s@]*)$', text)
                if not at_match:
                    return
                prefix = at_match.group(0)   # e.g. "@src/co"
                typed  = at_match.group(1)   # e.g. "src/co"
                is_glob = prefix.startswith("@@")
                base = _workspace()
                search_path = base / typed
                # If typed ends with partial filename, search in parent dir
                if not search_path.is_dir():
                    parent = search_path.parent
                    stub   = search_path.name
                else:
                    parent = search_path
                    stub   = ""
                try:
                    entries = sorted(parent.iterdir())
                except (PermissionError, FileNotFoundError):
                    return
                for entry in entries:
                    if stub and not entry.name.startswith(stub):
                        continue
                    rel = entry.relative_to(base)
                    suffix = "/" if entry.is_dir() else ""
                    display = f"{rel}{suffix}"
                    completion_text = display[len(typed):]
                    yield Completion(
                        completion_text,
                        display=display,
                        display_meta="dir" if entry.is_dir() else entry.suffix,
                    )

        _pt_session = PromptSession(
            history=InMemoryHistory(),
            completer=_AtCompleter(),
            complete_while_typing=False,   # only on Tab
            style=PTStyle.from_dict({"prompt": "bold ansicyan"}),
        )

    def _read_input() -> str:
        prompt_text = _build_prompt(mode[0])
        if _pt_session:
            return _pt_session.prompt(prompt_text).strip()
        return console.input(f"[bold cyan]{prompt_text}[/bold cyan]").strip()

    while True:
        try:
            user_input = _read_input()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye 👋[/dim]")
            break

        if not user_input:
            continue

        # ── in-chat commands ────────────────────────────────────────────────
        if user_input.lower() in ("/exit", "/quit", "/q"):
            console.print("[dim]Goodbye 👋[/dim]")
            break

        if user_input.lower() == "/id":
            console.print(f"[dim]Conversation ID: [bold]{current_id}[/bold][/dim]\n")
            continue

        if user_input.lower() == "/list":
            from rich.table import Table
            from rich import box as rbox
            result = _get("/conversation/user")
            convs = result.get("data", [])
            table = Table(box=rbox.SIMPLE, border_style="dim", show_lines=False)
            table.add_column("ID", style="dim", no_wrap=True)
            table.add_column("Title", style="bold")
            table.add_column("Msgs", justify="right")
            for c in convs:
                cid = c.get("id") or c.get("_id", "")
                marker = " [cyan]◀ current[/cyan]" if cid == current_id else ""
                table.add_row(cid, (c.get("title") or "no title") + marker, str(len(c.get("messages", []))))
            console.print()
            console.print(table)
            console.print()
            continue

        if user_input.lower() == "/new":
            conversation = _create_conversation()
            current_id = conversation.get("id") or conversation.get("_id")
            console.print(f"[green]✓[/green] New conversation: [bold]{current_id}[/bold]\n")
            _print_header(assistant_name, current_id, mode[0])
            continue

        if user_input.lower() == "/clear":
            _clear_messages(current_id)
            console.print("[green]✓[/green] Messages cleared.\n")
            continue

        if user_input.lower() == "/compactar":
            console.print(
                "[dim]Compaction is automatic: it triggers when the conversation "
                "exceeds the configured threshold (default: 40 messages). "
                "No manual action needed.[/dim]\n"
            )
            continue

        if user_input.lower().startswith("/mode"):
            parts = user_input.split()
            if len(parts) > 1:
                new_mode = parts[1].lower()
                if new_mode in _MODES_CYCLE:
                    mode[0] = new_mode
                    console.print(f"[green]✓[/green] Mode: [bold]{new_mode}[/bold]")
                else:
                    console.print(
                        f"[dim]Unknown mode '{new_mode}'. "
                        f"Modes: {' | '.join(_MODES_CYCLE)}[/dim]"
                    )
            else:
                # Cycle to the next mode.
                current_idx = _MODES_CYCLE.index(mode[0]) if mode[0] in _MODES_CYCLE else 1
                mode[0] = _MODES_CYCLE[(current_idx + 1) % len(_MODES_CYCLE)]
                console.print(f"[green]✓[/green] Mode: [bold]{mode[0]}[/bold]")
            console.print()
            continue

        # ── expand @ references ──────────────────────────────────────────
        expanded, ref_warnings = _resolve_at_references(user_input)
        for w in ref_warnings:
            console.print(f"[yellow]Warning:[/yellow] {w}")
        if expanded != user_input:
            ref_count = len(re.findall(r'(?<!\s)@', user_input))
            console.print(f"[dim]{ref_count} reference(s) expanded[/dim]")
            if len(expanded) > _WARN_TOTAL:
                console.print(
                    f"[yellow]Warning:[/yellow] Message expanded to {len(expanded)} chars"
                    " — consider using more specific references"
                )
        user_input = expanded

        # ── send message (streaming) ─────────────────────────────────────
        _print_user(user_input)
        _stream_assistant(
            current_id,
            assistant_name,
            user_input,
            auto_approve=yolo,
            mode=mode[0],
            always_approved=always_approved,
            always_rejected=always_rejected,
        )
