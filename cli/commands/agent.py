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

import atexit
import contextlib
import os
import re
import signal
import subprocess
import sys
import threading
import time
import glob as _glob
import mimetypes
import typer
import requests
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.rule import Rule
from rich import box
from rich.spinner import Spinner as RSpinner

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style as PTStyle
    from prompt_toolkit.layout.processors import Processor, Transformation

    _PT_AVAILABLE = True
except ImportError:
    _PT_AVAILABLE = False

from InquirerPy import inquirer as _inquirer

from cli.config.manager import config_exists, load_config

console = Console()
app = typer.Typer()

_CLI_CONV_TITLE = "CLI Agent"

_config_cache = None


def _get_config():
    global _config_cache
    if _config_cache is None:
        _config_cache = load_config()
    return _config_cache


_session_tokens_in = 0  # estimated input tokens sent this session
_session_tokens_out = 0  # estimated output tokens received this session


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: 4 chars ≈ 1 token."""
    return max(1, len(text) // 4)


def _track_tokens(user_msg: str, assistant_reply: str) -> None:
    global _session_tokens_in, _session_tokens_out
    _session_tokens_in += _estimate_tokens(user_msg)
    _session_tokens_out += _estimate_tokens(assistant_reply)


def _print_session_cost() -> None:
    """Print a token / estimated cost summary for the current session."""
    total = _session_tokens_in + _session_tokens_out
    if total == 0:
        return
    cost_usd = (_session_tokens_in * 0.27 + _session_tokens_out * 1.10) / 1_000_000
    console.print(
        f"\n[dim]Session: ~{_session_tokens_in:,} in · ~{_session_tokens_out:,} out "
        f"· ~{total:,} total tokens · est. ${cost_usd:.4f}[/dim]"
    )


_AGENT_MD_NAMES = ("agent.md", "AGENT.md", ".agent.md")


def _load_agent_md(workspace: "Path") -> str | None:
    """Return the contents of agent.md from the workspace, or None if absent."""
    for name in _AGENT_MD_NAMES:
        candidate = workspace / name
        if candidate.exists() and candidate.is_file():
            try:
                text = candidate.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    return text
            except OSError:
                pass
    return None


class _Mode:
    PLAN = "plan"  # read-only: describes changes but never applies them
    DEFAULT = "default"  # ask for every state-mutating tool
    CONFIRM_RISKY = "risky"  # auto-accept reads/edits, ask only for shell/commit
    AUTO_EDIT = "auto-edit"  # auto-accept file edits, ask for shell/commit
    YOLO = "yolo"  # accept everything silently


_MODES_CYCLE = [
    _Mode.PLAN,
    _Mode.DEFAULT,
    _Mode.CONFIRM_RISKY,
    _Mode.AUTO_EDIT,
    _Mode.YOLO,
]

_SAFE_TOOLS = {
    "read_file",
    "list_directory",
    "find_files",
    "grep_files",
    "repo_map",
    "git_status",
    "git_diff",
    "git_log",
    "web_search",
    "fetch_url",
    "search_images",
    "search_documents",
    "query_database",
    "save_memory",
    "search_memory",
    "organize_memory",
    "save_solution",
    "cron_list",
    "describe_image",
    "take_screenshot",
    "browser_navigate",
    "browser_get_content",
    "browser_screenshot",
    "browser_close",
    "browser_switch_tab",
    "browser_act",
    "browser_extract",
}

_ALWAYS_ASK_TOOLS = {"run_shell", "git_commit"}

_EDIT_TOOLS = {
    "edit_file",
    "write_file",
    "cron_create",
    "cron_delete",
    "cron_run",
    "system_propose",
    "system_confirm",
    "browser_click",
    "browser_type",
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
        return False
    if mode == _Mode.AUTO_EDIT and tool_name in _EDIT_TOOLS:
        return False
    return True


def _build_prompt(mode: str) -> str:
    """Return the prompt string for the REPL input line."""
    indicators = {
        _Mode.PLAN: "[plan] You › ",
        _Mode.CONFIRM_RISKY: "[risky] You › ",
        _Mode.AUTO_EDIT: "[auto] You › ",
        _Mode.YOLO: "[yolo] You › ",
        _Mode.DEFAULT: "You › ",
    }
    return indicators.get(mode, "You › ")


def _base_url() -> str:
    config = _get_config()
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
        resp = requests.get(
            _base_url() + path, headers=_workspace_headers(), timeout=10
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print(
            "\n[red]✗[/red] Cannot connect to API. Is [bold cyan]gillie start[/bold cyan] running?"
        )
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(
            f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}"
        )
        raise typer.Exit(1)


def _post_json(path: str, data: dict) -> dict:
    try:
        resp = requests.post(
            _base_url() + path, json=data, headers=_workspace_headers(), timeout=10
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print(
            "\n[red]✗[/red] Cannot connect to API. Is [bold cyan]gillie start[/bold cyan] running?"
        )
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(
            f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}"
        )
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
        console.print(
            "\n[red]✗[/red] Cannot connect to API. Is [bold cyan]gillie start[/bold cyan] running?"
        )
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(
            f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}"
        )
        return {}


def _delete(path: str) -> dict:
    try:
        resp = requests.delete(
            _base_url() + path, headers=_workspace_headers(), timeout=10
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        console.print(
            "\n[red]✗[/red] Cannot connect to API. Is [bold cyan]gillie start[/bold cyan] running?"
        )
        raise typer.Exit(1)
    except requests.exceptions.HTTPError as e:
        console.print(
            f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}"
        )
        return {}


_ATTACH_EXTS = {
    ".pdf",
    ".xlsx",
    ".xls",
    ".docx",
    ".doc",
    ".csv",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
}


def _upload_file(path: Path) -> dict | None:
    """Upload a file to the profile via multipart form data.

    Returns the first file item from the response data on success,
    or None if the request fails.
    """
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    try:
        with open(path, "rb") as fh:
            resp = requests.post(
                _base_url() + "/profile/files/upload",
                files=[("files", (path.name, fh, mime_type))],
                headers=_workspace_headers(),
                timeout=60,
            )
        resp.raise_for_status()
        return (resp.json().get("data") or [None])[0]
    except requests.exceptions.ConnectionError:
        console.print(
            "\n[red]✗[/red] Cannot connect to API. Is [bold cyan]gillie start[/bold cyan] running?"
        )
        return None
    except requests.exceptions.HTTPError as e:
        console.print(
            f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}"
        )
        return None


def _is_file_path(text: str) -> Path | None:
    """Return a resolved Path if *text* looks like a file path that exists.

    Recognised patterns:
      - Starts with ``/``, ``~/``, or ``./``
      - Plain filename with a known attachment extension

    Returns None if the path does not exist or is a directory.
    """
    stripped = text.strip()
    looks_like_path = (
        stripped.startswith("/")
        or stripped.startswith("~/")
        or stripped.startswith("./")
        or ("/" not in stripped and Path(stripped).suffix.lower() in _ATTACH_EXTS)
    )
    if not looks_like_path:
        return None
    candidate = Path(stripped).expanduser().resolve()
    if candidate.exists() and candidate.is_file():
        return candidate
    return None


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
    last = messages[-1]
    return last.get("content", "(no reply)")


def _clear_messages(conv_id: str) -> None:
    _delete(f"/conversation/{conv_id}/message")


_AUTO_COMPACT_THRESHOLD = 30  # auto-compact when message count exceeds this


def _maybe_auto_compact(conv_id: str, messages: list) -> None:
    """Silently compact the conversation when it grows too large."""
    if len(messages) < _AUTO_COMPACT_THRESHOLD:
        return
    try:
        result = _post_json(f"/conversation/{conv_id}/compact", {})
        if result.get("compacted"):
            n = result.get("summarized", "?")
            console.print(f"[dim]Auto-compacted: {n} messages → 1 summary[/dim]\n")
    except Exception:
        pass


def _print_header(
    assistant_name: str,
    conv_id: str,
    mode: str = _Mode.CONFIRM_RISKY,
    agent_md: bool = False,
) -> None:
    ws = _workspace()
    agent_md_line = (
        "[dim]📋 agent.md loaded — workspace context active[/dim]\n" if agent_md else ""
    )
    console.print()
    console.print(
        Panel(
            f"✨🐙 [bold cyan]{assistant_name}[/bold cyan]\n"
            f"[dim]Conversation: {conv_id}[/dim]\n"
            f"[dim]Workspace:    {ws}[/dim]\n"
            f"[dim]Mode: {mode} | /mode to change[/dim]\n"
            f"{agent_md_line}"
            f"[dim]/new · /list · /clear · /compact · /plan · /mode · /model · /attach · /files · /id · /exit[/dim]\n"
            f"[dim]Esc — cancel running agent[/dim]\n"
            f"[dim]@path — work with local file · /attach path — upload to storage[/dim]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )
    console.print()


def _print_workspace_summary(ws: "Path") -> None:
    """Print a compact summary of workspace contents."""
    try:
        entries = sorted(ws.iterdir())
        files = [e for e in entries if e.is_file() and not e.name.startswith(".")]
        dirs = [e for e in entries if e.is_dir() and not e.name.startswith(".")]
        if not files and not dirs:
            return
        parts = []
        for d in dirs[:8]:
            parts.append(f"[dim cyan]{d.name}/[/dim cyan]")
        for f in files[:10]:
            parts.append(f"[dim]{f.name}[/dim]")
        extra = (len(files) + len(dirs)) - len(parts)
        summary = "  ".join(parts)
        if extra > 0:
            summary += f"  [dim]+{extra} more[/dim]"
        console.print(f"[dim]Workspace:[/dim] {summary}")
        console.print()
    except Exception:
        pass


def _print_user(text: str) -> None:
    console.print(f"[bold white]You[/bold white]  [dim]{text}[/dim]")


def _print_assistant(name: str, text: str) -> None:
    """Print assistant reply with Markdown rendering — used for history."""
    console.print()
    console.print(f"[bold cyan]{name}[/bold cyan]")
    console.print(Markdown(text))
    console.print(Rule(style="dim"))
    console.print()


class SleepToggle:
    """Toggle a rest mode from the keyboard while the microphone loop runs.

    Ctrl+C already leaves listen mode, so resting needs its own key. Ctrl+S and
    Ctrl+Q are flow control and would freeze the terminal, and Ctrl+Z suspends
    the process, so Ctrl+P is the default.
    """

    def __init__(self, key: str = "\x10") -> None:
        import threading

        self._key = key
        self._resting = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        self._settings = None

    @property
    def resting(self) -> bool:
        return self._resting.is_set()

    def start(self) -> "SleepToggle":
        import termios
        import threading
        import tty

        if not sys.stdin.isatty():
            return self
        try:
            self._settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except Exception:
            self._settings = None
            return self
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def _run(self) -> None:
        import select

        while not self._stop.is_set():
            try:
                ready, _, _ = select.select([sys.stdin], [], [], 0.2)
                if not ready:
                    continue
                char = sys.stdin.read(1)
            except Exception:
                return
            if char != self._key:
                continue
            if self._resting.is_set():
                self._resting.clear()
                console.print("\n[green]▶[/green] listening again")
            else:
                self._resting.set()
                console.print("\n[yellow]⏸[/yellow]  resting — Ctrl+P to wake me up")

    def close(self) -> None:
        import termios

        self._stop.set()
        if self._settings is not None:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._settings)
            except Exception:
                pass
            self._settings = None


class AudioQueue:
    """Play audio URLs in arrival order on a worker thread.

    Segments arrive while the model is still writing, so enqueueing must never
    block the stream reader; playback stays strictly sequential so sentences are
    not spoken on top of each other.
    """

    def __init__(self) -> None:
        import queue
        import threading

        self._queue: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._started = False
        self._player = None
        self._stopped = False
        self.playing = threading.Event()

    def add(self, url: str) -> None:
        if self._stopped:
            return
        if not self._started:
            self._started = True
            self._thread.start()
        self.playing.set()
        self._queue.put(url)

    def _track(self, process) -> None:
        with self._lock:
            self._player = process
            if process is not None and self._stopped:
                process.terminate()

    def _run(self) -> None:
        while True:
            url = self._queue.get()
            if url is None:
                self._queue.task_done()
                return
            try:
                if not self._stopped:
                    _play_audio(url, on_process=self._track)
            except Exception:
                pass
            finally:
                self._queue.task_done()

    def stop(self) -> None:
        """Cut playback immediately and discard anything still queued."""
        self._stopped = True
        self.playing.clear()
        with self._lock:
            player = self._player
        if player is not None:
            try:
                player.terminate()
            except Exception:
                pass
        while True:
            try:
                self._queue.get_nowait()
            except Exception:
                break
            self._queue.task_done()

    def wait(self) -> None:
        if not self._started:
            return
        self._queue.join()
        self.playing.clear()
        self._queue.put(None)
        self._thread.join(timeout=5)


_live_players: set = set()
_live_players_lock = threading.Lock()
_player_reaper_installed = False


def _kill_live_players(*_args) -> None:
    """Stop every player this process started.

    Closing the terminal sends SIGHUP, whose default action kills Python without
    running atexit handlers, so the spawned player outlived its parent and kept
    talking with nothing left to stop it.
    """
    with _live_players_lock:
        players = list(_live_players)
        _live_players.clear()
    for player in players:
        with contextlib.suppress(Exception):
            if player.poll() is None:
                player.kill()


def _install_player_reaper() -> None:
    global _player_reaper_installed
    if _player_reaper_installed:
        return
    _player_reaper_installed = True
    atexit.register(_kill_live_players)
    for sig in (signal.SIGHUP, signal.SIGTERM):
        with contextlib.suppress(ValueError, OSError):
            previous = signal.getsignal(sig)

            def handler(signum, frame, _previous=previous):
                _kill_live_players()
                if callable(_previous):
                    _previous(signum, frame)
                else:
                    signal.signal(signum, signal.SIG_DFL)
                    os.kill(os.getpid(), signum)

            signal.signal(sig, handler)


def _track_player(process) -> None:
    with _live_players_lock:
        _live_players.add(process)


def _untrack_player(process) -> None:
    with _live_players_lock:
        _live_players.discard(process)


def _play_audio(url: str, on_process=None) -> None:
    """Play an audio URL using the first available system player.

    `on_process` receives the running player so a caller can stop it early.
    """
    if not url.startswith("http"):
        return
    _install_player_reaper()
    players = [
        ["mpv", "--no-video", "--really-quiet", url],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", url],
        ["vlc", "--intf", "dummy", "--play-and-exit", "--quiet", url],
    ]
    found = False
    for cmd in players:
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            continue
        found = True
        _track_player(process)
        if on_process is not None:
            on_process(process)
        code = 0
        try:
            code = process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            process.kill()
        finally:
            _untrack_player(process)
            if on_process is not None:
                on_process(None)
        if code <= 0:
            return
    if not found:
        console.print(
            "[yellow]⚠[/yellow] No audio player found. Install [bold]mpv[/bold] or [bold]ffplay[/bold]."
        )
    else:
        console.print(f"[dim]⚠ could not play a speech segment ({url})[/dim]")


def _stream_assistant(
    conv_id: str,
    name: str,
    content: str,
    auto_approve: bool = False,
    mode: str = _Mode.CONFIRM_RISKY,
    always_approved: set = None,
    always_rejected: set = None,
    session_local_files: list = None,
) -> AudioQueue:
    """Stream the assistant reply token by token from the SSE endpoint.

    When the backend emits an approval_request event the function pauses,
    shows the diff with ANSI colours, and applies the approval decision
    determined by the current mode and the per-session always_approved /
    always_rejected sets.

    Press Escape at any time to cancel the running agent.

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

    if always_approved is None:
        always_approved = set()
    if always_rejected is None:
        always_rejected = set()

    effective_mode = _Mode.YOLO if auto_approve else mode

    _cancel_requested = threading.Event()
    _stream_done = threading.Event()
    _prompt_active = threading.Event()  # pauses watcher during approval prompts
    _resp_holder = [None]  # filled after the request is established

    def _escape_watcher() -> None:
        """Background thread: set _cancel_requested and close the response when ESC."""
        try:
            import termios, tty, select as _select

            if not sys.stdin.isatty():
                return
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while not _stream_done.is_set():
                    if _prompt_active.is_set():
                        termios.tcsetattr(fd, termios.TCSANOW, old_settings)
                        while _prompt_active.is_set() and not _stream_done.is_set():
                            import time as _t

                            _t.sleep(0.02)
                        if _stream_done.is_set():
                            return
                        tty.setcbreak(fd)
                        continue
                    r, _, _ = _select.select([fd], [], [], 0.05)
                    if not r:
                        continue
                    ch = os.read(fd, 1)
                    if ch in (b"\x1b", b"\x03"):  # ESC or Ctrl+C → cancel running agent
                        _cancel_requested.set()
                        if _resp_holder[0] is not None:
                            try:
                                _resp_holder[0].close()
                            except Exception:
                                pass
                        break
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception:
            pass

    _escape_thread: threading.Thread | None = None
    if sys.stdin.isatty():
        _escape_thread = threading.Thread(target=_escape_watcher, daemon=True)
        _escape_thread.start()

    import time as _time

    full_text = ""
    _had_error = False
    _last_spinner_update = 0.0
    _live_ctx: "Live | None" = None  # Rich Live — only used for spinner
    _streaming_text = False  # True once first content token arrives

    def _terminal_lines(text: str) -> int:
        """Count how many terminal lines text occupies given console width."""
        w = console.width or 80
        total = 0
        for line in text.split("\n"):
            total += max(1, -(-len(line) // w)) if line else 1
        return total

    def _replace_streamed_with_markdown(text: str) -> None:
        """Erase the raw streamed text and re-render as Markdown — called once at end."""
        if not text:
            return
        n = _terminal_lines(text) + 1  # +1 for the \n we're about to write
        sys.stdout.write(f"\n\x1b[{n}A\r\x1b[J")
        sys.stdout.flush()
        console.print(Markdown(text))

    _SPIN_COLORS = [
        "bold cyan",
        "bold blue",
        "bold magenta",
        "bold green",
        "bold yellow",
    ]
    _spin_state = {
        "idx": 0,
        "label": "Thinking...",
        "active": False,
        "stop": threading.Event(),
    }

    def _spinner_cycler():
        while not _spin_state["stop"].is_set():
            _time.sleep(0.35)
            if _spin_state["stop"].is_set() or not _spin_state["active"]:
                break
            _spin_state["idx"] = (_spin_state["idx"] + 1) % len(_SPIN_COLORS)
            if _live_ctx is not None:
                try:
                    _live_ctx.update(
                        RSpinner(
                            "dots",
                            text=f" {_spin_state['label']}",
                            style=_SPIN_COLORS[_spin_state["idx"]],
                        )
                    )
                except Exception:
                    break

    def _stop_spinner_cycling():
        _spin_state["active"] = False
        _spin_state["stop"].set()

    def _stop_live() -> None:
        nonlocal _live_ctx
        if _live_ctx is not None:
            _stop_spinner_cycling()
            _live_ctx.stop()
            _live_ctx = None

    def _start_live_spinner(label: str = "Thinking...") -> None:
        nonlocal _live_ctx
        _stop_spinner_cycling()
        _spin_state["label"] = label
        _spin_state["active"] = True
        _spin_state["stop"] = threading.Event()
        renderable = RSpinner(
            "dots", text=f" {label}", style=_SPIN_COLORS[_spin_state["idx"]]
        )
        if _live_ctx is None:
            _live_ctx = Live(
                renderable,
                console=console,
                transient=True,
                auto_refresh=True,
                refresh_per_second=12,
            )
            _live_ctx.start()
        else:
            _live_ctx.update(renderable)
        threading.Thread(target=_spinner_cycler, daemon=True).start()

    console.print()
    console.print(f"[bold cyan]{name}[/bold cyan]")
    _start_live_spinner("Thinking...")

    audio = AudioQueue()

    try:
        resp = requests.post(
            _base_url() + f"/conversation/{conv_id}/message/stream",
            data={"content": content},
            headers=_workspace_headers(effective_mode),
            stream=True,
            timeout=900,
        )
        resp.raise_for_status()
        _resp_holder[0] = resp
        import json as _json

        for raw_line in resp.iter_lines():
            if _cancel_requested.is_set():
                break
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
                    if token.get("url"):
                        audio.add(token["url"])
                elif token.get("type") == "tool_call":
                    _stop_live()
                    if full_text:
                        if _streaming_text:
                            _replace_streamed_with_markdown(full_text)
                        else:
                            console.print(Markdown(full_text))
                    full_text = ""
                    _streaming_text = False
                    tool_name = token.get("name", "tool")
                    arg = token.get("arg", "")
                    _TOOL_ICONS = {
                        "web_search": "\U0001f50d",
                        "search_web": "\U0001f50d",
                        "read_file": "\U0001f4c4",
                        "read_files": "\U0001f4c4",
                        "write_file": "\u270f\ufe0f",
                        "create_file": "\U0001f4dd",
                        "list_files": "\U0001f4c1",
                        "list_directory": "\U0001f4c1",
                        "search_files": "\U0001f50e",
                        "delete_file": "\U0001f5d1\ufe0f",
                        "run_shell": "\U0001f5a5\ufe0f",
                        "execute_command": "\U0001f5a5\ufe0f",
                        "calendar_list_events": "\U0001f4c5",
                        "calendar_create_event": "\U0001f4c5",
                        "calendar_update_event": "\U0001f4c5",
                        "calendar_delete_event": "\U0001f4c5",
                        "search_memory": "\U0001f9e0",
                        "save_memory": "\U0001f4be",
                        "send_message": "\U0001f4e8",
                        "send_file": "\U0001f4e4",
                        "send_image": "\U0001f5bc\ufe0f",
                        "send_screenshot": "\U0001f4f8",
                        "http_request": "\U0001f310",
                        "fetch_url": "\U0001f310",
                    }
                    icon = _TOOL_ICONS.get(tool_name, "\u2699\ufe0f")
                    suffix = f" · [cyan]{arg}[/cyan]" if arg else ""
                    console.print(f"[dim]{icon} {tool_name}{suffix}[/dim]")
                    _start_live_spinner("Running tool...")
                elif token.get("type") == "tool_result":
                    summary = token.get("summary", "")
                    if summary:
                        _stop_live()
                        if token.get("ok", True):
                            console.print(f"  [green]✓[/green] [dim]{summary}[/dim]")
                        else:
                            console.print(f"  [red]✗[/red] [dim]{summary}[/dim]")
                    _start_live_spinner("Thinking...")
                elif token.get("type") == "citations":
                    urls = token.get("items") or []
                    if urls:
                        _stop_live()
                        for url in urls:
                            console.print(f"  [dim]🔗 {url}[/dim]")
                        _start_live_spinner("Thinking...")
                elif token.get("type") == "local_file_used":
                    path = token.get("path", "")
                    if path and session_local_files is not None:
                        if path not in [f.get("path") for f in session_local_files]:
                            session_local_files.append(
                                {
                                    "path": path,
                                    "tool": token.get("tool", ""),
                                }
                            )
                elif token.get("type") == "compaction":
                    _stop_live()
                    console.print(
                        "[dim]Conversation compacted to optimise context[/dim]"
                    )
                elif token.get("type") == "shell_output":
                    line_text = token.get("line", "")
                    if line_text:
                        _stop_live()
                        console.print(f"[dim]{line_text}[/dim]")
                elif token.get("type") == "approval_request":
                    _stop_live()

                    request_id = token.get("request_id", "")
                    tool_name = token.get("tool", "tool")
                    file_path = token.get("file", "")
                    diff = token.get("diff", "")

                    console.print(
                        f"\n[bold]🔧 {tool_name}[/bold] → [cyan]{file_path}[/cyan]"
                    )
                    if diff:
                        for diff_line in diff.splitlines():
                            if diff_line.startswith("+") and not diff_line.startswith(
                                "+++"
                            ):
                                console.print(f"[green]{diff_line}[/green]")
                            elif diff_line.startswith("-") and not diff_line.startswith(
                                "---"
                            ):
                                console.print(f"[red]{diff_line}[/red]")
                            elif diff_line.startswith("@@"):
                                console.print(f"[cyan]{diff_line}[/cyan]")
                            else:
                                console.print(f"[dim]{diff_line}[/dim]")

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
                        _prompt_active.set()
                        import time as _pt

                        _pt.sleep(0.06)  # let watcher restore settings

                        approved = False
                        feedback = ""
                        try:
                            choice = _inquirer.select(
                                message="Apply?",
                                choices=[
                                    {"name": "  Yes — apply this change", "value": "y"},
                                    {
                                        "name": "  No  — reject this change",
                                        "value": "n",
                                    },
                                    {
                                        "name": "  Always — auto-accept this tool for session",
                                        "value": "a",
                                    },
                                    {
                                        "name": "  Skip  — auto-reject this tool for session",
                                        "value": "s",
                                    },
                                ],
                                pointer="❯",
                                qmark="",
                            ).execute()
                        except (KeyboardInterrupt, EOFError):
                            choice = "n"
                        finally:
                            _prompt_active.clear()

                        if choice == "y":
                            approved = True
                        elif choice == "n":
                            approved = False
                            try:
                                feedback = console.input(
                                    "[dim]Reason (Enter to skip): [/dim]"
                                ).strip()
                            except (KeyboardInterrupt, EOFError):
                                feedback = ""
                        elif choice == "a":
                            approved = True
                            always_approved.add(tool_name)
                            console.print(
                                f"[dim]'{tool_name}' auto-accepted for the rest of this session[/dim]"
                            )
                        elif choice == "s":
                            approved = False
                            always_rejected.add(tool_name)
                            console.print(
                                f"[dim]'{tool_name}' skipped for the rest of this session[/dim]"
                            )

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
                        pass

                    _start_live_spinner("Thinking...")
                continue
            if isinstance(token, str) and token.startswith("[ERROR]"):
                _stop_live()
                console.print(f"\n[red]✗[/red] {token[7:].strip()}")
                break
            if not _streaming_text:
                _stop_live()  # stop spinner, transient=True erases it cleanly
                _streaming_text = True
            full_text += token
            sys.stdout.write(token)
            sys.stdout.flush()
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.ChunkedEncodingError,
        requests.exceptions.ContentDecodingError,
        AttributeError,
    ) as e:
        if not _cancel_requested.is_set():
            _stop_live()
            _had_error = True
            console.print(f"[red]✗[/red] API stream disconnected: {e}")
    except requests.exceptions.HTTPError as e:
        _stop_live()
        _had_error = True
        try:
            body = e.response.json()
            msg = (
                body.get("error", {}).get("message", "")
                or body.get("detail", "")
                or str(body)
            )
        except Exception:
            msg = e.response.text
        console.print(f"[red]✗[/red] API error {e.response.status_code}: {msg}")
    finally:
        _stop_live()
        _stream_done.set()
        if _escape_thread and _escape_thread.is_alive():
            _escape_thread.join(timeout=0.5)

    if _had_error:
        audio.stop()
        console.print(Rule(style="dim red"))
        console.print()
        return audio

    if _cancel_requested.is_set():
        audio.stop()
        if full_text:
            if _streaming_text:
                _replace_streamed_with_markdown(full_text)
            else:
                console.print(Markdown(full_text))
        console.print("[yellow]⏹  Cancelled[/yellow]")
        console.print(Rule(style="dim"))
        console.print()
        return audio

    if full_text:
        if _streaming_text:
            _replace_streamed_with_markdown(full_text)
        else:
            console.print(Markdown(full_text))
    console.print(Rule(style="dim"))
    console.print()

    _track_tokens(content, full_text)
    return audio


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


_AT_URL_RE = re.compile(r"@(https?://[^\s]+)")
_AT_GLOB_RE = re.compile(r"@@([A-Za-z0-9_./~*?\[\]\-]+)")
_AT_DIR_RE = re.compile(r"@([A-Za-z0-9_./~\-]+/)")
_AT_FILE_RE = re.compile(
    r"@([A-Za-z0-9_./~\-]+\.[A-Za-z0-9_]+)"
)
_FILE_PATH_RE = re.compile(r"(?:file://)?(/[^\s]+)")

_LOCAL_DOC_EXTS = {".xlsx", ".xls", ".docx", ".doc", ".csv", ".pdf"}

_URL_CAP = 3_000
_FILE_CAP = 4_000
_DIR_FILE_CAP = 500
_DIR_TOTAL_CAP = 5_000
_WARN_TOTAL = 8_000

_SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
}


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
                text = (
                    text[:_DIR_FILE_CAP] + f"\n[... truncated at {_DIR_FILE_CAP} chars]"
                )
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
    """Read a single file (workspace-relative or absolute path).

    For binary document files (.xlsx, .docx, .pdf, etc.) injects a structured
    context block so the AI can use file tools to work with the local file directly.
    """
    candidate = Path(filepath).expanduser()
    fpath = candidate if candidate.is_absolute() else _workspace() / filepath
    if not fpath.exists():
        return "", f"File not found: {filepath}"

    ext = fpath.suffix.lower()
    if ext in _LOCAL_DOC_EXTS:
        block = (
            f"[Local file on disk: {fpath} (name: {fpath.name})]\n"
            f"This is a local binary document. Do NOT try to read its raw content.\n"
            f'To work with it use the appropriate file tool and pass file_name="{fpath}". '
            f'Save changes back to the same path (save_as="{fpath}") unless the user specifies otherwise. '
            f"Do NOT re_upload unless the user explicitly asks to save it to cloud storage."
        )
        return block, None

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


def _replace_file_paths(text: str, attached_files: list[str]) -> str:
    """Replace absolute file paths with stable [file(N)] tags for this prompt."""

    def repl(match: re.Match) -> str:
        path = match.group(1)
        candidate = Path(path)
        try:
            if not candidate.exists() or not candidate.is_file():
                return match.group(0)
        except OSError:
            return match.group(0)

        normalized = str(candidate.resolve())
        for idx, existing in enumerate(attached_files):
            if existing == normalized:
                return f"[file({idx + 1})]"
        attached_files.append(normalized)
        return f"[file({len(attached_files)})]"

    return _FILE_PATH_RE.sub(repl, text)


def _attach_paste(text: str, pasted_blocks: list[str]) -> str:
    """Store pasted multiline text and return its compact placeholder tag."""
    pasted_blocks.append(text)
    lines = text.count("\n") + 1
    return f"[paste({len(pasted_blocks)}): {lines} lines]"


def _expand_tagged_refs(
    content: str, attached_files: list[str], pasted_blocks: list[str]
) -> str:
    """Expand [file(N)] and [paste(N)] placeholders into sendable context."""
    for idx, path in enumerate(attached_files, 1):
        tag = f"[file({idx})]"
        if tag not in content:
            continue
        try:
            data = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        block = f'<file name="{Path(path).name}">\n{data}\n</file>'
        content = content.replace(tag, block)

    for idx, text in enumerate(pasted_blocks, 1):
        lines = text.count("\n") + 1
        tag = f"[paste({idx}): {lines} lines]"
        content = content.replace(tag, text, 1)

    return content


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

    text = _AT_URL_RE.sub(
        lambda m: _replace(m, lambda u: _expand_url(u), m.group(0)),
        text,
    )

    text = _AT_GLOB_RE.sub(
        lambda m: _replace(m, lambda p: _expand_glob(p), m.group(0)),
        text,
    )

    text = _AT_DIR_RE.sub(
        lambda m: _replace(m, lambda d: _expand_dir(d), m.group(0)),
        text,
    )

    text = _AT_FILE_RE.sub(
        lambda m: _replace(m, lambda f: _expand_file(f), m.group(0)),
        text,
    )

    return text, warnings


@app.command("listen")
def listen(
    silence: float = typer.Option(
        1.0, "--silence", "-s", help="Seconds of silence to detect end of phrase"
    ),
    threshold: float = typer.Option(
        0.01, "--threshold", "-t", help="RMS silence threshold (0.0–1.0)"
    ),
    new: bool = typer.Option(False, "--new", "-n", help="Force a new conversation"),
    conv_id: str = typer.Option(
        None, "--id", help="Attach to a specific conversation ID"
    ),
    avatar: bool = typer.Option(
        False,
        "--avatar",
        "-a",
        help="Open the Gillie Avatar and hide this terminal until it closes",
    ),
    barge_in: bool = typer.Option(
        True,
        "--barge-in/--no-barge-in",
        help="Let speaking over the assistant cut it off",
    ),
    barge_in_sensitivity: float = typer.Option(
        1.5,
        "--barge-in-sensitivity",
        help="How many times the measured room noise an interruption must reach. "
        "Lower it with headphones, raise it if the speakers trigger false cut-offs.",
    ),
):
    """Voice listen mode: record your voice, assistant replies in text."""
    if not config_exists():
        console.print(
            "[red]✗[/red] Not initialized. Run [bold cyan]gillie init[/bold cyan] first."
        )
        raise typer.Exit(1)

    try:
        import sounddevice as sd
        import numpy as np
    except ImportError:
        console.print(
            "[red]✗[/red] sounddevice not found. Run: [bold cyan]gillie install[/bold cyan]"
        )
        raise typer.Exit(1)

    import wave
    import io
    import tempfile

    config = load_config()
    assistant_name = config.profile.assistant_name

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
    _MIN_UTTERANCE_CHUNKS = int(1.0 / 0.1)
    silence_chunks_needed = int(silence / 0.1)

    _vad = None
    try:
        import webrtcvad as _webrtcvad

        _vad = _webrtcvad.Vad(
            2
        )  # aggressiveness 0-3 (2 = balanced; RMS pre-filters energy)
        vad_status = "voice detection: on"
    except ImportError:
        vad_status = "voice detection: off (pip install webrtcvad)"

    BAR_WIDTH = 20
    _VAD_FRAME = int(SAMPLE_RATE * 0.03)  # 30ms frames required by webrtcvad

    def _is_voice(chunk_float: "np.ndarray") -> bool:
        """True if chunk contains human voice (falls back to RMS if VAD unavailable)."""
        rms = float(np.sqrt(np.mean(chunk_float**2)))
        if rms <= threshold:
            return False
        if _vad is None:
            return True
        chunk_int16 = (np.clip(chunk_float.flatten(), -1.0, 1.0) * 32767).astype(
            np.int16
        )
        n_frames = len(chunk_int16) // _VAD_FRAME
        if n_frames == 0:
            return True
        voice_frames = sum(
            1
            for i in range(n_frames)
            if _vad.is_speech(
                chunk_int16[i * _VAD_FRAME : (i + 1) * _VAD_FRAME].tobytes(),
                SAMPLE_RATE,
            )
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
    _BARGE_IN_STREAK_NEEDED = 6  # 600ms, so a stray speaker echo does not interrupt
    _BARGE_IN_PREBUFFER_CHUNKS = 12  # 1.2s kept so the interruption is not clipped
    _BARGE_IN_ECHO_MARGIN = 1.8  # how far above the measured echo a voice must sit
    _BARGE_IN_ECHO_WINDOW = 30  # 3s of levels; a 600ms burst cannot move its median

    def _measure_noise_floor(seconds: float = 0.8) -> float:
        """Sample the room so the interrupt bar sits above this mic, not a constant.

        Ambient level varies enormously between machines, and webrtcvad reports
        speech on roughly two thirds of silent chunks, so a fixed RMS threshold
        either never triggers or triggers constantly.
        """
        levels = []
        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype="float32"
            ) as stream:
                for _ in range(max(1, int(seconds / 0.1))):
                    chunk, _ = stream.read(CHUNK)
                    levels.append(float(np.sqrt(np.mean(chunk**2))))
        except Exception:
            return threshold
        if not levels:
            return threshold
        levels.sort()
        return levels[len(levels) // 2]

    barge_in_level = 0.0
    if barge_in:
        console.print("[dim]calibrando micrófono...[/dim]", end="\r")
        # The floor is ordinary speech level, not a multiple of it: multiplying
        # `threshold` too put the bar so high that normal talking never cut in.
        barge_in_level = max(_measure_noise_floor() * barge_in_sensitivity, threshold)
        console.print(" " * 40, end="\r")
        barge_status = f"barge-in: on (nivel {barge_in_level:.3f})"
    else:
        barge_status = "barge-in: off"

    console.print()
    console.print(
        Panel(
            f"✨🐙 [bold cyan]{assistant_name}[/bold cyan] — listen mode\n"
            f"[dim]Speak when you see the mic. {silence}s of silence to send.[/dim]\n"
            f"[dim]Ctrl+P to rest, Ctrl+C to quit.[/dim]\n"
            f"[dim]{vad_status} · {barge_status}[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    class BargeInWatcher:
        """Listen while the assistant speaks and cut it off when the user does.

        The microphone also picks up the assistant coming out of the speakers,
        so the bar to interrupt is deliberately higher than the one used to
        start a normal recording: a louder signal, held for longer. The audio
        that triggered the interruption is kept so the first words of the
        interruption are not lost.
        """

        def __init__(
            self, audio: "AudioQueue", trigger_level: float, rest=None
        ) -> None:
            import threading

            self._audio = audio
            self._trigger_level = trigger_level
            self._rest = rest
            self._triggered = threading.Event()
            self._stop = threading.Event()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self.pre_buffer: list = []

        def start(self) -> "BargeInWatcher":
            self._thread.start()
            return self

        def _run(self) -> None:
            import collections

            keep = _BARGE_IN_PREBUFFER_CHUNKS
            streak = 0
            levels = collections.deque(maxlen=_BARGE_IN_ECHO_WINDOW)
            rolling: list = []
            try:
                with sd.InputStream(
                    samplerate=SAMPLE_RATE, channels=1, dtype="float32"
                ) as stream:
                    while not self._stop.is_set():
                        chunk, _ = stream.read(CHUNK)
                        rolling.append(chunk.copy())
                        del rolling[:-keep]
                        if self._rest is not None and self._rest.resting:
                            self._audio.stop()
                            return
                        if not self._audio.playing.is_set():
                            streak = 0
                            levels.clear()
                            continue
                        rms = float(np.sqrt(np.mean(chunk**2)))
                        levels.append(rms)
                        echo = float(np.median(levels))
                        bar = max(self._trigger_level, echo * _BARGE_IN_ECHO_MARGIN)
                        if rms > bar and _is_voice(chunk):
                            streak += 1
                            if streak >= _BARGE_IN_STREAK_NEEDED:
                                self.pre_buffer = list(rolling)
                                self._triggered.set()
                                self._audio.stop()
                                return
                        else:
                            streak = 0
            except Exception:
                return

        @property
        def triggered(self) -> bool:
            return self._triggered.is_set()

        def close(self) -> None:
            self._stop.set()
            self._thread.join(timeout=2)

    def _trim_trailing_silence(
        chunks: list, silence_chunks: int, keep: int = 3
    ) -> list:
        trimmed = len(chunks) - max(0, silence_chunks - keep)
        return chunks[:trimmed] if trimmed >= _MIN_UTTERANCE_CHUNKS else chunks

    def _record_utterance(
        carry_over: list | None = None, rest: "SleepToggle | None" = None
    ) -> bytes | None:
        """Record until N seconds of silence detected. Returns WAV bytes.

        `carry_over` holds audio captured before this call — the words that
        interrupted the assistant — so the recording starts mid-sentence.
        """
        audio_chunks = list(carry_over or [])
        pre_buffer = []  # holds chunks before speech confirmed
        silence_count = 0
        voice_streak = 0
        started = bool(audio_chunks)

        with sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32"
        ) as stream:
            while True:
                chunk, _ = stream.read(CHUNK)
                rms = float(np.sqrt(np.mean(chunk**2)))
                is_voice = _is_voice(chunk)

                if is_voice:
                    voice_streak += 1
                    silence_count = 0
                    if not started:
                        pre_buffer.append(chunk.copy())
                        if voice_streak >= _VOICE_STREAK_NEEDED:
                            started = True
                            audio_chunks.extend(pre_buffer)
                            pre_buffer.clear()
                    else:
                        audio_chunks.append(chunk.copy())
                else:
                    voice_streak = 0
                    if not started:
                        pre_buffer = pre_buffer[-(_VOICE_STREAK_NEEDED - 1) :]
                    elif started:
                        silence_count += 1
                        audio_chunks.append(chunk.copy())

                bar = _level_bar(rms, started)
                print(f"\r{' ' * 50}\r", end="", flush=True)
                console.print(bar + "  ", end="\r")

                if rest is not None and rest.resting:
                    print(f"\r{' ' * 50}\r", end="", flush=True)
                    return None

                if started and silence_count >= silence_chunks_needed:
                    print(f"\r{' ' * 50}\r", end="", flush=True)
                    break

        if not audio_chunks:
            return None

        if len(audio_chunks) < _MIN_UTTERANCE_CHUNKS:
            return None

        audio_chunks = _trim_trailing_silence(audio_chunks, silence_chunks_needed)
        audio_np = np.concatenate(audio_chunks, axis=0)
        audio_int16 = (np.clip(audio_np, -1.0, 1.0) * 32767).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())
        return buf.getvalue()

    def _transcribe(conv_id: str, wav_bytes: bytes) -> str | None:
        """Upload the recording and return the transcribed text."""
        try:
            resp = requests.post(
                _base_url() + f"/conversation/{conv_id}/transcribe",
                files={"voice_content": ("audio.wav", wav_bytes, "audio/wav")},
                headers=_workspace_headers(),
                timeout=60,
            )
            resp.raise_for_status()
            return (resp.json().get("data") or {}).get("text") or None
        except requests.exceptions.ConnectionError:
            console.print("\n[red]✗[/red] Cannot connect to the API.")
        except requests.exceptions.HTTPError as e:
            console.print(
                f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}"
            )
        return None

    def _stream_reply(conv_id: str, text: str, audio: "AudioQueue") -> str:
        """Stream the reply, queueing each speech segment as soon as it lands."""
        import json as _json

        reply = ""
        printed_header = False
        try:
            resp = requests.post(
                _base_url() + f"/conversation/{conv_id}/message/stream",
                data={"content": text},
                headers=_workspace_headers(),
                stream=True,
                timeout=900,
            )
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = (
                    raw_line.decode("utf-8")
                    if isinstance(raw_line, bytes)
                    else raw_line
                )
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                try:
                    token = _json.loads(payload)
                except _json.JSONDecodeError:
                    token = payload
                if token == "[DONE]":
                    break
                if isinstance(token, dict):
                    if token.get("type") == "audio" and token.get("url"):
                        audio.add(token["url"])
                    continue
                if not isinstance(token, str):
                    continue
                if not printed_header:
                    console.print(f"\n[bold cyan]{assistant_name}[/bold cyan]")
                    printed_header = True
                reply += token
                sys.stdout.write(token)
                sys.stdout.flush()
        except requests.exceptions.ConnectionError:
            console.print("\n[red]✗[/red] Cannot connect to the API.")
        except requests.exceptions.HTTPError as e:
            console.print(
                f"\n[red]✗[/red] API error {e.response.status_code}: {e.response.text}"
            )
        if printed_header:
            console.print()
        return reply

    def _voice_loop(avatar_proc=None, rest: "SleepToggle | None" = None) -> None:
        carry_over = None
        while True:
            if avatar_proc is not None and avatar_proc.poll() is not None:
                console.print("\n[dim]Avatar closed — leaving listen mode 👋[/dim]")
                return
            try:
                if rest is not None and rest.resting:
                    carry_over = None
                    time.sleep(0.2)
                    continue
                if not carry_over:
                    console.print("[dim]🎙  Ready — speak whenever you like...[/dim]")
                wav_bytes = _record_utterance(carry_over, rest)
                carry_over = None
            except KeyboardInterrupt:
                console.print("\n[dim]Goodbye 👋[/dim]")
                return

            if not wav_bytes:
                continue

            console.print("[dim]⏳ Transcribing...[/dim]  ", end="\r")
            said = _transcribe(current_id, wav_bytes)
            console.print(" " * 40, end="\r")
            if not said:
                console.print("[dim]…no te escuché bien, probá de nuevo.[/dim]")
                carry_over = None
                continue

            _print_user(said)
            audio = AudioQueue()
            watcher = (
                BargeInWatcher(audio, barge_in_level, rest).start()
                if barge_in
                else None
            )
            try:
                _stream_reply(current_id, said, audio)
                audio.wait()
            finally:
                if watcher is not None:
                    watcher.close()

            carry_over = watcher.pre_buffer if watcher and watcher.triggered else None
            if carry_over:
                console.print("[dim]⏹  te escucho...[/dim]")
            console.print(Rule(style="dim"))

    rest = SleepToggle().start()

    if not avatar:
        try:
            _voice_loop(rest=rest)
        finally:
            rest.close()
        return

    from cli.commands import avatar as avatar_cmd

    avatar_proc = avatar_cmd.spawn()
    if not avatar_cmd.wait_for_bridge():
        console.print(
            "[yellow]⚠[/yellow] Avatar did not start; staying in the terminal."
        )
        avatar_proc.terminate()
        try:
            _voice_loop(rest=rest)
        finally:
            rest.close()
        return

    try:
        with avatar_cmd.terminal_hidden() as hidden:
            if not hidden:
                console.print(
                    "[yellow]⚠[/yellow] Cannot hide this terminal "
                    "(needs a wlroots Wayland session with [bold]wlrctl[/bold]); keeping it visible."
                )
            _voice_loop(avatar_proc, rest)
    finally:
        rest.close()
        if avatar_proc.poll() is None:
            avatar_proc.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                avatar_proc.wait(timeout=5)


@app.command("list")
def list_conversations():
    """List all conversations with their ID and title."""
    if not config_exists():
        console.print(
            "[red]✗[/red] Not initialized. Run [bold cyan]gillie init[/bold cyan] first."
        )
        raise typer.Exit(1)

    from rich.table import Table
    from rich import box as rbox

    result = _get("/conversation/user")
    conversations = result.get("data", [])

    if not conversations:
        console.print(
            "[dim]No conversations found. Start one with [bold cyan]gillie agent[/bold cyan].[/dim]"
        )
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
        updated = (conv.get("updated_at") or conv.get("created_at") or "")[:19].replace(
            "T", " "
        )
        table.add_row(cid, title, str(msgs), updated)

    console.print()
    console.print(table)
    console.print()
    console.print(
        f"[dim]Attach to a conversation: [bold cyan]gillie agent --id <ID>[/bold cyan][/dim]"
    )
    console.print()


@app.command("workspace")
def set_workspace(
    path: str = typer.Argument(
        None, help="Directory to set as workspace. Omit to show current."
    ),
):
    """Show or set the persistent workspace directory for file tools."""
    from cli.config.manager import config_exists, load_config, save_config

    if not config_exists():
        console.print(
            "[red]✗[/red] Not initialized. Run [bold cyan]gillie init[/bold cyan] first."
        )
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


def _start_avatar():
    """Open the avatar alongside a typed conversation.

    Unlike listen mode this leaves the terminal visible, because the whole point
    here is that you keep typing into it.
    """
    from cli.commands import avatar as avatar_cmd

    process = avatar_cmd.spawn()
    if avatar_cmd.wait_for_bridge():
        atexit.register(_stop_avatar, process)
        console.print("[dim]🐙 avatar ready[/dim]")
        return process

    console.print(
        "[yellow]⚠[/yellow] Avatar did not answer on its bridge; continuing without it."
    )
    _stop_avatar(process)
    return None


def _stop_avatar(process) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=5)


@app.callback(invoke_without_command=True)
def agent(
    ctx: typer.Context,
    new: bool = typer.Option(False, "--new", "-n", help="Force a new conversation"),
    conv_id: str = typer.Option(
        None, "--id", help="Attach to a specific conversation ID"
    ),
    resume: str = typer.Option(
        None, "--resume", "-r", help="Resume a conversation by ID (alias for --id)"
    ),
    workspace: str = typer.Option(
        None, "--workspace", "-w", help="Set workspace directory for this session"
    ),
    show_workspace: bool = typer.Option(
        False, "--show-workspace", help="Print current workspace and exit"
    ),
    yolo: bool = typer.Option(
        False, "--yolo", help="Auto-approve all tool calls (alias for --mode yolo)"
    ),
    mode_flag: str = typer.Option(
        _Mode.CONFIRM_RISKY,
        "--mode",
        "-m",
        help="Approval mode: plan | default | risky | auto-edit | yolo",
    ),
    avatar: bool = typer.Option(
        False, "--avatar", "-a", help="Show the avatar on screen while you chat"
    ),
):
    """Interactive chat with the assistant from the terminal."""
    if ctx.invoked_subcommand is not None:
        return

    if show_workspace:
        console.print(f"\n[bold]Workspace:[/bold] {_workspace()}\n")
        raise typer.Exit(0)

    if not config_exists():
        console.print(
            "[red]✗[/red] Not initialized. Run [bold cyan]gillie init[/bold cyan] first."
        )
        raise typer.Exit(1)

    initial_mode = _Mode.YOLO if yolo else mode_flag
    if initial_mode not in _MODES_CYCLE:
        console.print(
            f"[red]✗[/red] Unknown mode '{initial_mode}'. "
            f"Valid modes: {' | '.join(_MODES_CYCLE)}"
        )
        raise typer.Exit(1)

    if workspace:
        ws_path = Path(workspace).resolve()
        if not ws_path.is_dir():
            console.print(f"[red]✗[/red] Workspace directory not found: {ws_path}")
            raise typer.Exit(1)
        os.environ["GILLIE_WORKSPACE"] = str(ws_path)

    effective_conv_id = conv_id or resume

    config = _get_config()
    assistant_name = config.profile.assistant_name

    if effective_conv_id:
        result = _get(f"/conversation/{effective_conv_id}")
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

    avatar_proc = _start_avatar() if avatar else None

    mode = [initial_mode]

    always_approved: set = set()
    always_rejected: set = set()

    session_files: list = []
    session_local_files: list = []
    prompt_attached_files: list[str] = []
    prompt_pasted_blocks: list[str] = []

    ws = _workspace()
    agent_md_content = _load_agent_md(ws)

    _print_header(
        assistant_name, current_id, mode[0], agent_md=agent_md_content is not None
    )

    if ws.exists():
        _print_workspace_summary(ws)

    messages = conversation.get("messages", [])
    if messages:
        _maybe_auto_compact(current_id, messages)
        _print_history(messages, assistant_name)

    _agent_md_injected = bool(messages)  # if resuming, skip re-injection

    console.print(f"[dim]Type your message and press Enter. /exit to quit.[/dim]")
    console.print()

    _pt_session = None
    if _PT_AVAILABLE:
        _KNOWN_SLASH_CMDS = {
            "/new",
            "/list",
            "/ls",
            "/clear",
            "/compact",
            "/plan",
            "/mode",
            "/model",
            "/provider",
            "/attach",
            "/files",
            "/id",
            "/exit",
            "/quit",
            "/q",
        }

        class _SlashHighlighter(Processor):
            """Color the input line when it matches (or partially matches) a slash command."""

            def apply_transformation(self, ti):
                text = "".join(t for _, t in ti.fragments)
                stripped = text.strip()
                if any(
                    stripped == cmd or stripped.startswith(cmd + " ")
                    for cmd in _KNOWN_SLASH_CMDS
                ):
                    return Transformation([("class:slash-cmd", text)])
                if stripped.startswith("/") and any(
                    cmd.startswith(stripped) for cmd in _KNOWN_SLASH_CMDS
                ):
                    return Transformation([("class:slash-cmd-partial", text)])
                return Transformation(ti.fragments)

        class _AtCompleter(Completer):
            """Tab-complete @path references from the workspace."""

            _SLASH_CMDS = [
                "/new",
                "/list",
                "/ls",
                "/clear",
                "/compact",
                "/plan",
                "/mode",
                "/model",
                "/provider",
                "/attach",
                "/files",
                "/id",
                "/exit",
            ]

            def get_completions(self, document, complete_event):
                text = document.text_before_cursor
                if text.startswith("/"):
                    for cmd in self._SLASH_CMDS:
                        if cmd.startswith(text):
                            yield Completion(cmd[len(text) :], display=cmd)
                    return
                at_match = re.search(r"@@?([^\s@]*)$", text)
                if not at_match:
                    return
                prefix = at_match.group(0)  # e.g. "@src/co"
                typed = at_match.group(1)  # e.g. "src/co"
                is_glob = prefix.startswith("@@")
                base = _workspace()
                search_path = base / typed
                if not search_path.is_dir():
                    parent = search_path.parent
                    stub = search_path.name
                else:
                    parent = search_path
                    stub = ""
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
                    completion_text = display[len(typed) :]
                    yield Completion(
                        completion_text,
                        display=display,
                        display_meta="dir" if entry.is_dir() else entry.suffix,
                    )

        _pt_session = PromptSession(
            history=InMemoryHistory(),
            completer=_AtCompleter(),
            complete_while_typing=False,  # only on Tab
            input_processors=[_SlashHighlighter()],
            style=PTStyle.from_dict(
                {
                    "prompt": "bold ansicyan",
                    "slash-cmd": "bold ansicyan",
                    "slash-cmd-partial": "ansicyan",
                }
            ),
        )

    def _read_input() -> str:
        prompt_text = _build_prompt(mode[0])
        if _pt_session:
            return _pt_session.prompt(prompt_text).strip()
        return console.input(f"[bold cyan]{prompt_text}[/bold cyan]").strip()

    _last_ctrl_c: float = 0.0  # timestamp of last Ctrl+C at the prompt
    active_audio: AudioQueue | None = None

    def _interrupt_active_audio() -> None:
        """Stop current reply before accepting a new command or message."""
        nonlocal active_audio
        if active_audio is None:
            return
        active_audio.stop()
        active_audio.wait()
        active_audio = None

    while True:
        try:
            user_input = _read_input()
            _last_ctrl_c = 0.0  # reset on successful input
        except KeyboardInterrupt:
            import time as _t

            now = _t.time()
            if now - _last_ctrl_c < 2.0:
                _interrupt_active_audio()
                _print_session_cost()
                console.print("\n[dim]Goodbye 👋[/dim]")
                break
            _last_ctrl_c = now
            console.print(
                "\n[dim]Press Ctrl+C again to exit, or type a message to continue.[/dim]"
            )
            continue
        except EOFError:
            _interrupt_active_audio()
            _print_session_cost()
            console.print("\n[dim]Goodbye 👋[/dim]")
            break

        if not user_input:
            continue

        _interrupt_active_audio()

        cmd = user_input.lower()

        if cmd in ("/exit", "/quit", "/q"):
            _print_session_cost()
            console.print("[dim]Goodbye 👋[/dim]")
            break

        if cmd in ("/id",):
            console.print(f"[dim]Conversation ID: [bold]{current_id}[/bold][/dim]\n")
            continue

        if cmd in ("/model", "/provider"):
            try:
                _opts = _get("/profile/options").get("data", {})
                _active = _opts.get("active_provider", "")
                _providers = _opts.get("providers", [])
                _pinfo = next((p for p in _providers if p.get("key") == _active), None)
                console.print()
                console.print(
                    f"  [bold]Provider:[/bold] [cyan]{_active or '(none)'}[/cyan]"
                )
                if _pinfo:
                    console.print(f"  [bold]Model   :[/bold] {_pinfo.get('model', '')}")
                    console.print(
                        f"  [bold]Base URL:[/bold] [dim]{_pinfo.get('base_url', '')}[/dim]"
                    )
                    _key_status = (
                        "[green]set[/green]"
                        if _pinfo.get("api_key_set")
                        else "[red]missing[/red]"
                    )
                    console.print(f"  [bold]API key :[/bold] {_key_status}")
                console.print()
            except Exception:
                console.print("[dim]Could not reach backend.[/dim]\n")
            continue

        if cmd in ("/list", "/ls", "/conversations", "/convs"):
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
                table.add_row(
                    cid,
                    (c.get("title") or "no title") + marker,
                    str(len(c.get("messages") or [])),
                )
            console.print()
            console.print(table)
            console.print()
            continue

        if cmd in ("/new",):
            conversation = _create_conversation()
            current_id = conversation.get("id") or conversation.get("_id")
            session_files.clear()
            session_local_files.clear()
            prompt_attached_files.clear()
            prompt_pasted_blocks.clear()
            console.print(
                f"[green]✓[/green] New conversation: [bold]{current_id}[/bold]\n"
            )
            _print_header(assistant_name, current_id, mode[0])
            _print_workspace_summary(_workspace())
            continue

        if cmd in ("/clear",):
            _clear_messages(current_id)
            console.print("[green]✓[/green] Messages cleared.\n")
            continue

        if cmd in ("/compact",):
            console.print("[dim]Compacting conversation...[/dim]")
            try:
                result = _post_json(f"/conversation/{current_id}/compact", {})
                if result.get("compacted"):
                    n = result.get("summarized", "?")
                    console.print(
                        f"[green]✓[/green] Conversation compacted: {n} messages → 1 summary\n"
                    )
                else:
                    console.print(
                        f"[yellow]⚠[/yellow] {result.get('reason', 'Could not compact')}\n"
                    )
            except Exception:
                console.print("[red]✗[/red] Error compacting conversation\n")
            continue

        if cmd in ("/plan",):
            mode[0] = _Mode.PLAN
            console.print(
                f"[green]✓[/green] Mode: [bold]plan[/bold] (describe changes, never apply)\n"
            )
            continue

        if cmd in ("/files", "/attachments"):
            from rich.table import Table
            from rich import box as rbox

            has_any = bool(session_files or session_local_files)
            if not has_any:
                console.print(
                    "[dim]No files uploaded or accessed in this conversation.[/dim]\n"
                )
            else:
                console.print()
                if session_files:
                    console.print("[dim]Uploaded (session):[/dim]")
                    table = Table(box=rbox.SIMPLE, border_style="dim", show_lines=False)
                    table.add_column("#", style="dim", justify="right")
                    table.add_column("Name", style="bold")
                    table.add_column("URL", style="dim")
                    for i, f in enumerate(session_files, 1):
                        name = f.get("name", "").split("/")[-1]
                        url = f.get("url", "")
                        table.add_row(str(i), name, url)
                    console.print(table)
                if session_local_files:
                    console.print("[dim]Local (session):[/dim]")
                    ltable = Table(
                        box=rbox.SIMPLE, border_style="dim", show_lines=False
                    )
                    ltable.add_column("#", style="dim", justify="right")
                    ltable.add_column("Path", style="bold")
                    ltable.add_column("Tool", style="dim")
                    for i, f in enumerate(session_local_files, 1):
                        ltable.add_row(str(i), f.get("path", ""), f.get("tool", ""))
                    console.print(ltable)
                console.print()
            continue

        if user_input.lower().startswith("/attach"):
            parts = user_input.split(None, 1)
            if len(parts) < 2:
                console.print("[dim]Usage: /attach <path/to/file>[/dim]\n")
                continue
            attach_path = Path(parts[1].strip()).expanduser().resolve()
            if not attach_path.exists() or not attach_path.is_file():
                console.print(f"[red]✗[/red] File not found: {attach_path}\n")
                continue
            if attach_path.suffix.lower() not in _ATTACH_EXTS:
                console.print(
                    f"[yellow]⚠[/yellow] Extension '{attach_path.suffix}' may not be supported.\n"
                )
            console.print(f"[dim]📎 Uploading {attach_path.name}...[/dim]")
            file_info = _upload_file(attach_path)
            if file_info:
                file_url = file_info.get("url", "")
                file_name = attach_path.name
                session_files.append(file_info)
                console.print(f"[green]✓[/green] Uploaded: [bold]{file_name}[/bold]\n")
                attach_msg = f"I've just uploaded the file '{file_name}' (url: {file_url}). Please use it in our conversation when relevant."
                _print_user(attach_msg)
                active_audio = _stream_assistant(
                    current_id,
                    assistant_name,
                    attach_msg,
                    auto_approve=yolo,
                    mode=mode[0],
                    always_approved=always_approved,
                    always_rejected=always_rejected,
                    session_local_files=session_local_files,
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
                current_idx = (
                    _MODES_CYCLE.index(mode[0]) if mode[0] in _MODES_CYCLE else 1
                )
                mode[0] = _MODES_CYCLE[(current_idx + 1) % len(_MODES_CYCLE)]
                console.print(f"[green]✓[/green] Mode: [bold]{mode[0]}[/bold]")
            console.print()
            continue

        display_input = user_input
        if "\n" in user_input:
            display_input = _attach_paste(user_input, prompt_pasted_blocks)
        else:
            display_input = _replace_file_paths(user_input, prompt_attached_files)

        tagged_expanded = _expand_tagged_refs(
            display_input, prompt_attached_files, prompt_pasted_blocks
        )
        expanded, ref_warnings = _resolve_at_references(tagged_expanded)
        for w in ref_warnings:
            console.print(f"[yellow]Warning:[/yellow] {w}")
        if expanded != tagged_expanded:
            ref_count = len(re.findall(r"(?<!\s)@", tagged_expanded))
            console.print(f"[dim]{ref_count} reference(s) expanded[/dim]")
            if len(expanded) > _WARN_TOTAL:
                console.print(
                    f"[yellow]Warning:[/yellow] Message expanded to {len(expanded)} chars"
                    " — consider using more specific references"
                )
        user_input = expanded

        if not _agent_md_injected and agent_md_content:
            user_input = (
                f"<workspace_context>\n{agent_md_content}\n</workspace_context>\n\n"
                + user_input
            )
            _agent_md_injected = True

        _print_user(display_input)
        prompt_attached_files.clear()
        prompt_pasted_blocks.clear()
        active_audio = _stream_assistant(
            current_id,
            assistant_name,
            user_input,
            auto_approve=yolo,
            mode=mode[0],
            always_approved=always_approved,
            always_rejected=always_rejected,
            session_local_files=session_local_files,
        )

    _interrupt_active_audio()
    _stop_avatar(avatar_proc)

    try:
        requests.post(
            _base_url() + "/browser/close",
            timeout=3,
        )
    except Exception:
        pass
