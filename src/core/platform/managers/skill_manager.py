"""
Skill Manager

Manages ~/.gillie/memory/ files:
  - memory.md          — root file, always loaded, references other skills
  - *.skill.md         — individual skill files referenced from memory.md

memory.md is auto-created on first use with a default template.
`get_base_context()` loads memory.md and resolves `ver X.skill.md` references
by inlining the content of each referenced skill file.

FAQ format inside faqs.skill.md uses HTML comments for machine-readable IDs:

    <!-- id: abc123 -->
    ## Category Name
    **P:** Question text
    **R:** Answer text

    ---
"""

import re
import logging
from pathlib import Path
from typing import List, Optional, Dict
import uuid

logger = logging.getLogger(__name__)

MEMORY_DIR = Path.home() / ".gillie" / "memory"

_MEMORY_ROOT_TEMPLATE = """\
# Memoria del Asistente

Árbol de conocimiento del asistente. Cada sección puede referenciar skills específicas.

## Preguntas Frecuentes

ver faqs.skill.md

## Conocimiento General

ver general.skill.md
"""


class SkillManager:
    def __init__(self, memory_dir: Path = MEMORY_DIR):
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_memory_root()

    # ─── Generic skill operations ──────────────────────────────────────────────

    def list_skills(self) -> List[str]:
        """Return names (without extension) of all .skill.md files."""
        return [p.stem.replace(".skill", "") for p in sorted(self.memory_dir.glob("*.skill.md"))]

    def skill_exists(self, name: str) -> bool:
        return self._skill_path(name).exists()

    def load_skill(self, name: str) -> str:
        path = self._skill_path(name)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def save_skill(self, name: str, content: str) -> None:
        self._skill_path(name).write_text(content, encoding="utf-8")

    def delete_skill(self, name: str) -> bool:
        path = self._skill_path(name)
        if not path.exists():
            return False
        path.unlink()
        return True

    # ─── Memory root (memory.md) ──────────────────────────────────────────────

    def _memory_root_path(self) -> Path:
        return self.memory_dir / "memory.md"

    def get_memory_root(self) -> str:
        """Return raw content of memory.md."""
        path = self._memory_root_path()
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def update_memory_root(self, content: str) -> None:
        """Overwrite memory.md with new content."""
        self._memory_root_path().write_text(content, encoding="utf-8")

    def _ensure_memory_root(self) -> None:
        """Create memory.md with default template if it does not exist yet."""
        path = self._memory_root_path()
        if not path.exists():
            path.write_text(_MEMORY_ROOT_TEMPLATE, encoding="utf-8")
            logger.info("Created default memory.md at %s", path)

    def _resolve_references(self, content: str) -> str:
        """
        Replace every line matching `ver X.skill.md` with the content of
        the corresponding skill file (if it exists and is non-empty).
        """
        pattern = re.compile(r"^ver\s+([\w\-]+)\.skill\.md\s*$", re.MULTILINE)

        def replace_match(m: re.Match) -> str:
            name = m.group(1)
            skill_content = self.load_skill(name)
            if skill_content.strip():
                return skill_content.strip()
            return f"*(sin contenido en {name}.skill.md)*"

        return pattern.sub(replace_match, content)

    def get_resolved_memory(self) -> str:
        """Return memory.md with all skill references inlined (no wrapper)."""
        self._ensure_memory_root()
        raw = self.get_memory_root()
        if not raw.strip():
            return ""
        return self._resolve_references(raw)

    # ─── Base context (always injected into LLM) ──────────────────────────────

    def get_base_context(self) -> str:
        """
        Loads memory.md, resolves `ver X.skill.md` references, and wraps the
        result in the === CONOCIMIENTO DEL ASISTENTE === block for the LLM.
        """
        resolved = self.get_resolved_memory()
        if not resolved.strip():
            return ""

        return (
            "=== CONOCIMIENTO DEL ASISTENTE ===\n\n"
            + resolved.strip()
            + "\n\n=================================="
        )

    # ─── General memory ───────────────────────────────────────────────────────

    def get_general_memory(self) -> str:
        return self.load_skill("general")

    def update_general_memory(self, content: str) -> None:
        self.save_skill("general", content)

    # ─── FAQs CRUD (operates on faqs.skill.md) ────────────────────────────────

    def get_faqs(self) -> List[Dict]:
        """
        Parse faqs.skill.md and return a list of FAQ dicts:
        [{"id": str, "category": str, "question": str, "answer": str}]
        """
        raw = self.load_skill("faqs")
        return self._parse_faqs(raw)

    def add_faq(self, question: str, answer: str, category: Optional[str] = None) -> str:
        """
        Append a new FAQ section to faqs.skill.md.
        Returns the generated FAQ ID.
        """
        faq_id = uuid.uuid4().hex[:8]
        cat = category or "General"

        raw = self.load_skill("faqs")
        if not raw.strip():
            raw = "# Preguntas Frecuentes\n"

        block = (
            f"\n<!-- id: {faq_id} -->\n"
            f"## {cat}\n"
            f"**P:** {question}\n"
            f"**R:** {answer}\n\n"
            "---"
        )

        raw = raw.rstrip() + "\n" + block + "\n"
        self.save_skill("faqs", raw)
        return faq_id

    def update_faq(self, faq_id: str, question: str, answer: str, category: Optional[str] = None) -> bool:
        """
        Update the question/answer of an existing FAQ by its ID.
        Returns True if found and updated, False if not found.
        """
        raw = self.load_skill("faqs")
        faqs = self._parse_faqs(raw)

        faq = next((f for f in faqs if f["id"] == faq_id), None)
        if not faq:
            return False

        cat = category or faq["category"]
        old_block = self._build_block_regex(faq_id)
        new_block = (
            f"<!-- id: {faq_id} -->\n"
            f"## {cat}\n"
            f"**P:** {question}\n"
            f"**R:** {answer}\n"
        )

        updated = re.sub(old_block, new_block, raw, flags=re.DOTALL)
        self.save_skill("faqs", updated)
        return True

    def delete_faq(self, faq_id: str) -> bool:
        """
        Remove a FAQ block by ID. Returns True if found and deleted.
        """
        raw = self.load_skill("faqs")
        pattern = self._build_block_regex(faq_id)
        if not re.search(pattern, raw, flags=re.DOTALL):
            return False

        updated = re.sub(pattern, "", raw, flags=re.DOTALL)
        # Clean up consecutive separators
        updated = re.sub(r"\n---\n\n---", "\n---", updated)
        updated = updated.strip() + "\n"
        self.save_skill("faqs", updated)
        return True

    # ─── Internal helpers ─────────────────────────────────────────────────────

    def _skill_path(self, name: str) -> Path:
        return self.memory_dir / f"{name}.skill.md"

    def _parse_faqs(self, raw: str) -> List[Dict]:
        """
        Parse FAQ blocks from markdown.
        Each block starts with <!-- id: XXXX --> and ends before the next one or EOF.
        """
        if not raw:
            return []

        results = []
        # Split on id comments
        parts = re.split(r"<!--\s*id:\s*([a-f0-9]+)\s*-->", raw)
        # parts[0] is header, then alternating: id, block_content
        i = 1
        while i < len(parts) - 1:
            faq_id = parts[i].strip()
            block = parts[i + 1]
            i += 2

            # Extract category (## heading)
            cat_match = re.search(r"^##\s+(.+)$", block, re.MULTILINE)
            category = cat_match.group(1).strip() if cat_match else "General"

            # Extract question
            q_match = re.search(r"\*\*P:\*\*\s*(.+)", block)
            question = q_match.group(1).strip() if q_match else ""

            # Extract answer (may be multi-line until --- or next heading)
            a_match = re.search(r"\*\*R:\*\*\s*([\s\S]+?)(?=\n---|\Z)", block)
            answer = a_match.group(1).strip() if a_match else ""

            if question and answer:
                results.append({
                    "id": faq_id,
                    "category": category,
                    "question": question,
                    "answer": answer,
                })

        return results

    def _build_block_regex(self, faq_id: str) -> str:
        """
        Regex that matches a full FAQ block for a given ID,
        from <!-- id: XXX --> up to (but not including) the next <!-- id: or EOF.
        """
        return (
            r"<!--\s*id:\s*"
            + re.escape(faq_id)
            + r"\s*-->[\s\S]*?(?=<!--\s*id:|$)"
        )
