"""
System Monitor & Executor Tool

Allows the AI to run Linux commands on behalf of the user with:
  - Blacklist validation (hardcoded base + configurable via integration)
  - Two-step confirmation before any execution
  - Output sanitization (strips secrets/tokens)
"""

import asyncio
import logging
import re
import secrets
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_MAX_OUTPUT_CHARS = 2000

# Pending confirmations: { code → command }
# Module-level so it persists across tool calls within the same process.
_pending: Dict[str, str] = {}

# These patterns are ALWAYS blocked regardless of integration config.
_HARDCODED_BLACKLIST: List[str] = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=",
    ":(){ :|:& };:",   # fork bomb
    "> /dev/sda",
    "shred",
    "fdisk",
    "parted",
    "wipefs",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
]

_SECRET_RE = re.compile(
    r"(password|passwd|secret|token|api_key|apikey|auth)\s*[=:]\s*\S+",
    re.IGNORECASE,
)


def _get_blacklist(profile) -> List[str]:
    """Return combined blacklist: hardcoded base + integration config."""
    combined = list(_HARDCODED_BLACKLIST)
    if not profile or not profile.integrations:
        return combined
    for integration in profile.integrations:
        if integration.name == "system_commands" and integration.activated:
            config_blacklist = integration.config.get("blacklist", [])
            if isinstance(config_blacklist, list):
                combined.extend(config_blacklist)
    return combined


def _requires_confirmation(profile) -> bool:
    """Return True only if the integration is activated AND require_confirmation is enabled."""
    if not profile or not profile.integrations:
        return False
    for integration in profile.integrations:
        if integration.name == "system_commands":
            if not integration.activated:
                return False
            return integration.config.get("require_confirmation", True) is not False
    return False


def _is_blacklisted(command: str, blacklist: List[str]) -> Optional[str]:
    """Return the matched blacklist entry if command is blocked, else None."""
    cmd_lower = command.lower().strip()
    for entry in blacklist:
        if entry.lower().strip() in cmd_lower:
            return entry
    return None


def _sanitize(output: str) -> str:
    """Redact secret-looking lines and truncate."""
    lines = []
    for line in output.splitlines():
        if _SECRET_RE.search(line):
            lines.append("[redacted]")
        else:
            lines.append(line)
    result = "\n".join(lines)
    if len(result) > _MAX_OUTPUT_CHARS:
        result = result[:_MAX_OUTPUT_CHARS] + "\n...(truncated)"
    return result


async def propose_command(command: str, profile) -> Dict[str, Any]:
    """
    Validate command against blacklist.

    If require_confirmation is enabled: store pending and ask for code.
    If disabled: execute directly and return the result.
    """
    blacklist = _get_blacklist(profile)
    blocked = _is_blacklisted(command, blacklist)
    if blocked:
        return {
            "allowed": False,
            "message": f"El comando fue bloqueado porque coincide con una entrada de la lista negra: `{blocked}`.",
        }

    if not _requires_confirmation(profile):
        logger.info(f"[system] Executing directly (no confirmation required): {command}")
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            raw = stdout.decode(errors="replace")
            output = _sanitize(raw)
            exit_code = proc.returncode
            logger.info(f"[system] Command exit_code={exit_code}, output_len={len(output)}")
            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "command": command,
                "output": output or "(sin salida)",
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "El comando superó el tiempo límite de 30 segundos."}
        except Exception as e:
            logger.error(f"[system] Execution error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    code = secrets.token_hex(3).upper()  # e.g. "A3F9C1"
    _pending[code] = command
    logger.info(f"[system] Pending command [{code}]: {command}")

    return {
        "allowed": True,
        "pending": True,
        "code": code,
        "command": command,
        "message": (
            f"Propongo ejecutar:\n```\n{command}\n```\n"
            f"Respondé con el código **{code}** para confirmar, o ignorá este mensaje para cancelar."
        ),
    }


async def confirm_command(code: str) -> Dict[str, Any]:
    """
    Execute the command stored under the given confirmation code.
    """
    code = code.strip().upper()
    command = _pending.pop(code, None)
    if command is None:
        return {
            "success": False,
            "error": f"Código `{code}` no encontrado o ya expiró. Pedí el comando nuevamente.",
        }

    logger.info(f"[system] Executing confirmed command [{code}]: {command}")
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        raw = stdout.decode(errors="replace")
        output = _sanitize(raw)
        exit_code = proc.returncode

        logger.info(f"[system] Command exit_code={exit_code}, output_len={len(output)}")
        return {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "command": command,
            "output": output or "(sin salida)",
        }

    except asyncio.TimeoutError:
        return {"success": False, "error": "El comando superó el tiempo límite de 30 segundos."}
    except Exception as e:
        logger.error(f"[system] Execution error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def add_to_blacklist(pattern: str, profile) -> Dict[str, Any]:
    """Add a pattern to the integration blacklist (returns updated list)."""
    if not profile or not profile.integrations:
        return {"success": False, "error": "Integración system_commands no encontrada."}
    for integration in profile.integrations:
        if integration.name == "system_commands" and integration.activated:
            bl = integration.config.get("blacklist", [])
            if pattern not in bl:
                bl.append(pattern)
                integration.config["blacklist"] = bl
            return {"success": True, "blacklist": bl}
    return {"success": False, "error": "Integración system_commands no activa."}


def remove_from_blacklist(pattern: str, profile) -> Dict[str, Any]:
    """Remove a pattern from the integration blacklist."""
    if not profile or not profile.integrations:
        return {"success": False, "error": "Integración system_commands no encontrada."}
    for integration in profile.integrations:
        if integration.name == "system_commands" and integration.activated:
            bl = integration.config.get("blacklist", [])
            if pattern in bl:
                bl.remove(pattern)
                integration.config["blacklist"] = bl
            return {"success": True, "blacklist": bl}
    return {"success": False, "error": "Integración system_commands no activa."}
