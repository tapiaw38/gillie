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

import sys
import typer
import requests
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule
from rich import box
from rich.text import Text

from cli.config.manager import config_exists, load_config

console = Console()
app = typer.Typer()

_CLI_CONV_TITLE = "CLI Agent"


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _base_url() -> str:
    config = load_config()
    host = config.server.host or "127.0.0.1"
    if host == "0.0.0.0":
        host = "127.0.0.1"
    port = config.server.port or 8000
    return f"http://{host}:{port}"


def _get(path: str) -> dict:
    try:
        resp = requests.get(_base_url() + path, timeout=10)
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
        resp = requests.post(_base_url() + path, json=data, timeout=10)
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
        resp = requests.delete(_base_url() + path, timeout=10)
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

def _print_header(assistant_name: str, conv_id: str) -> None:
    console.print()
    console.print(Panel(
        f"✨🐟 [bold cyan]{assistant_name}[/bold cyan]\n"
        f"[dim]Conversation: {conv_id}[/dim]\n"
        f"[dim]/new · /list · /clear · /id · /compactar · /exit[/dim]",
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


def _stream_assistant(conv_id: str, name: str, content: str) -> str:
    """Stream the assistant reply token by token from the SSE endpoint."""
    import sys
    import threading
    import time

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


@app.callback(invoke_without_command=True)
def agent(
    ctx: typer.Context,
    new: bool = typer.Option(False, "--new", "-n", help="Force a new conversation"),
    conv_id: str = typer.Option(None, "--id", help="Attach to a specific conversation ID"),
):
    """Interactive chat with the assistant from the terminal."""
    if ctx.invoked_subcommand is not None:
        return

    if not config_exists():
        console.print("[red]✗[/red] Not initialized. Run [bold cyan]gillie init[/bold cyan] first.")
        raise typer.Exit(1)

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

    _print_header(assistant_name, current_id)

    # Show recent history if resuming
    messages = conversation.get("messages", [])
    if messages:
        _print_history(messages, assistant_name)

    # ── REPL ─────────────────────────────────────────────────────────────────
    console.print(f"[dim]Type your message and press Enter. /exit to quit.[/dim]")
    console.print()

    while True:
        try:
            user_input = console.input("[bold cyan]You ›[/bold cyan] ").strip()
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
            _print_header(assistant_name, current_id)
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

        # ── send message (streaming) ─────────────────────────────────────
        _print_user(user_input)
        _stream_assistant(current_id, assistant_name, user_input)
