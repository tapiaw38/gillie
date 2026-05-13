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
# Assistant Memory

Assistant knowledge tree. Each section can reference specific skills.

## Rules and Behavior

ver rules.skill.md

## Frequently Asked Questions

ver faqs.skill.md

## General Knowledge

Only core facts that must always stay in context.
Do not use this for consolidated conversation memory; that belongs in the soul store.

ver general.skill.md

## Remembered Facts

ver facts.skill.md

## Recorded Solutions

ver solutions.skill.md
"""

BRAIN_SKILL_MARKER = "## Episodic Memory (Brain)"

BRAIN_SKILL_BLOCK = """
## Episodic Memory (Brain)
The system has episodic memory and soul memory enabled. Knowledge is stored in two layers:

**Episodic layer** — recent experiences extracted automatically from each conversation.
**Soul layer** — distilled long-term knowledge promoted from episodic memory.

When the context includes `=== SOUL KNOWLEDGE ===`:
- These are permanent facts about the user synthesized from multiple conversations.
- Use them as background truth to personalize all responses.
- They are more reliable than episodic memories.

When the context includes `=== EPISODIC MEMORIES ===`:
- These are recent user experiences.
- Use them to personalize the current response contextually.
- Mention relevant memories naturally without listing everything.
- Prioritize high-importance memories (importance >= 7).

General rules:
- Do not invent information that is not present in these blocks.
- There is NO `save_memory` command here; extraction is automatic.
"""

_RULES_SKILL_TEMPLATE = """\
# Assistant Rules

## Format and Language
- Always respond in Spanish, clearly and concisely.
- Use plain text in responses; avoid unnecessary Markdown.
- URLs must be clean, with no parentheses, quotes, or brackets before or after them.

## Office Files (Word, Excel, PowerPoint) — CRITICAL RULE
NEVER write Markdown syntax inside `.docx`, `.xlsx`, or `.pptx` documents.
These formats do NOT interpret Markdown — `![alt](url)`, `**text**`, `*text*`, `# Title`, etc.
will be inserted as literal text and break the document.
- For images: use `insert_image_docx`, `insert_image_excel`, or `insert_image_pptx`.
- For content: use `write_docx`, `modify_docx`, and equivalent tools.
- NEVER write an image URL as plain text in the document; that inserts a broken link, not an image.

## Browser Automation — CRITICAL RULE
For ANY task involving a browser (open URL, click, fill forms, send messages, scraping, etc.)
you MUST call `browser_connect` as the FIRST tool, always.
- NEVER use `run_shell` or any other tool to open Chrome/Chromium/Firefox.
- NEVER execute `google-chrome`, `xdg-open`, or any browser command via shell.
- `browser_connect` relaunches Chrome with remote debugging using the real profile, preserving sessions.
- Flow: `browser_connect` → `browser_switch_tab` → `browser_navigate` / `browser_evaluate` / `browser_click` / `browser_type`.
- Never ask the user to do something manually in the browser.

## General Behavior
- Act as a personal assistant: empathetic, direct, and efficient.
- Prefer using available tools before asking the user for information.
- For file, workspace, or shell tasks: act directly without unnecessary confirmation.
"""

_FAQS_SKILL_TEMPLATE = """\
# Frequently Asked Questions

Use this file for stable question/answer pairs that should be reused often.

Example format:

## General
**Q:** Example question
**A:** Example answer
"""

_GENERAL_SKILL_TEMPLATE = """\
# General Knowledge

Use this file only for core facts that must always remain in context.
Do not use it for consolidated conversation memory; that belongs in the soul store.
"""

_FACTS_SKILL_TEMPLATE = """\
# Remembered Facts

This file stores manually remembered facts when the soul store is not available.
Entries may be added automatically by the `save_memory` tool fallback.
"""

_SOLUTIONS_SKILL_TEMPLATE = """\
# Recorded Solutions

Use this file to store recurring fixes, troubleshooting notes, and problem/solution pairs.
"""


class SkillManager:
    def __init__(self, memory_dir: Path = MEMORY_DIR):
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_memory_root()
        self._ensure_rules_skill()

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
        self._ensure_faqs_skill()
        self._ensure_general_skill()
        self._ensure_facts_skill()
        self._ensure_solutions_skill()

    def _ensure_faqs_skill(self) -> None:
        """Create faqs.skill.md with a default header if it does not exist yet."""
        path = self._skill_path("faqs")
        if not path.exists():
            path.write_text(_FAQS_SKILL_TEMPLATE, encoding="utf-8")
            logger.info("Created default faqs.skill.md at %s", path)

    def _ensure_general_skill(self) -> None:
        """Create general.skill.md with a default header if it does not exist yet."""
        path = self._skill_path("general")
        if not path.exists():
            path.write_text(_GENERAL_SKILL_TEMPLATE, encoding="utf-8")
            logger.info("Created default general.skill.md at %s", path)

    def _ensure_facts_skill(self) -> None:
        """Create facts.skill.md with a default header if it does not exist yet."""
        path = self._skill_path("facts")
        if not path.exists():
            path.write_text(_FACTS_SKILL_TEMPLATE, encoding="utf-8")
            logger.info("Created default facts.skill.md at %s", path)

    def _ensure_solutions_skill(self) -> None:
        """Create solutions.skill.md with a default header if it does not exist yet."""
        path = self._skill_path("solutions")
        if not path.exists():
            path.write_text(_SOLUTIONS_SKILL_TEMPLATE, encoding="utf-8")
            logger.info("Created default solutions.skill.md at %s", path)

    def _ensure_rules_skill(self) -> None:
        """Create rules.skill.md with default system rules if it does not exist yet."""
        path = self._skill_path("rules")
        if not path.exists():
            path.write_text(_RULES_SKILL_TEMPLATE, encoding="utf-8")
            logger.info("Created default rules.skill.md at %s", path)

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
            return f"*(no content in {name}.skill.md)*"

        return pattern.sub(replace_match, content)

    def get_resolved_memory(self) -> str:
        """Return memory.md with all skill references inlined (no wrapper)."""
        self._ensure_memory_root()
        raw = self.get_memory_root()
        if not raw.strip():
            return ""
        return self._resolve_references(raw)

    def get_base_context(self) -> str:
        """
        Loads memory.md, resolves `ver X.skill.md` references, and wraps the
        result in the === ASSISTANT KNOWLEDGE === block for the LLM.
        """
        resolved = self.get_resolved_memory()
        if not resolved.strip():
            return ""

        return (
            "=== ASSISTANT KNOWLEDGE ===\n\n"
            + resolved.strip()
            + "\n\n=================================="
        )

    def get_general_memory(self) -> str:
        return self.load_skill("general")

    def update_general_memory(self, content: str) -> None:
        self.save_skill("general", content)

    def append_general_knowledge(self, content: str, category: str = "General") -> str:
        """
        Append a core note to general.skill.md, skipping if a similar note already exists.
        Returns the note ID (existing if duplicate, new if added).
        """
        from datetime import date

        raw = self.load_skill("general")
        if not raw.strip():
            raw = "# Conocimiento General\n"

        existing_id = self._find_similar_note(content, raw)
        if existing_id:
            logger.info("Skipped duplicate note — similar note %s already exists", existing_id)
            return existing_id

        note_id = uuid.uuid4().hex[:8]
        today = date.today().isoformat()
        section_header = "## Notas Importantes"
        note_block = (
            f"\n<!-- note: {note_id} -->\n"
            f"**[{category} — {today}]** {content}\n"
        )

        if section_header in raw:
            raw = raw.rstrip() + "\n" + note_block
        else:
            raw = raw.rstrip() + f"\n\n{section_header}\n" + note_block

        self.save_skill("general", raw)
        logger.info("Appended general knowledge note %s: %s", note_id, content[:80])
        return note_id

    def _find_similar_note(self, content: str, existing_raw: str, threshold: float = 0.45) -> Optional[str]:
        """
        Return the ID of an existing note that is semantically similar to content,
        based on keyword overlap. Returns None if no similar note is found.
        """
        _STOP = {
            "el", "la", "los", "las", "de", "en", "y", "a", "que", "es", "un",
            "una", "su", "se", "lo", "por", "con", "me", "mi", "te", "si",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "i", "my", "me", "you", "your", "he", "she", "it", "we", "they",
        }

        def _keywords(text: str):
            words = re.findall(r"[a-záéíóúñüA-ZÁÉÍÓÚÑÜ]{3,}", text.lower())
            return set(words) - _STOP

        new_kw = _keywords(content)
        if len(new_kw) < 3:
            return None

        pattern = re.compile(
            r"<!--\s*note:\s*([a-f0-9]+)\s*-->\n\*\*\[.+?\]\*\*\s*(.+?)(?=\n<!--\s*note:|\Z)",
            re.DOTALL,
        )
        for m in pattern.finditer(existing_raw):
            note_id, note_text = m.group(1), m.group(2)
            note_kw = _keywords(note_text)
            if not note_kw:
                continue
            overlap = len(new_kw & note_kw) / min(len(new_kw), len(note_kw))
            if overlap >= threshold:
                logger.info(
                    "Found similar note %s (overlap=%.2f): %s", note_id, overlap, note_text[:60]
                )
                return note_id
        return None

    def overwrite_general_memory(self, content: str) -> None:
        """Replace the entire general.skill.md with the given content."""
        self.save_skill("general", content.strip() + "\n")
        logger.info("general.skill.md overwritten (%d chars)", len(content))

    def append_solution(
        self,
        problem: str,
        solution: str,
        context: Optional[str] = None,
        effective: bool = True,
    ) -> str:
        """
        Append a solution block to solutions.skill.md.

        Returns the generated solution ID, or the ID of an existing duplicate
        if a similar problem description was already recorded.
        """
        from datetime import date

        raw = self.load_skill("solutions")
        if not raw.strip():
            raw = "# Soluciones Registradas\n"

        existing_id = self._find_similar_note(problem, raw)
        if existing_id:
            logger.info("Skipped duplicate solution — similar entry %s already exists", existing_id)
            return existing_id

        solution_id = uuid.uuid4().hex[:8]
        today = date.today().isoformat()
        effective_label = "Sí" if effective else "No"

        lines = [
            f"\n<!-- solution: {solution_id} -->",
            f"## [{today}] Problema: {problem}",
            f"**Problema:** {problem}",
            f"**Solución:** {solution}",
        ]
        if context:
            lines.append(f"**Contexto:** {context}")
        lines.append(f"**Efectiva:** {effective_label}")
        lines.append("---")

        block = "\n".join(lines)
        raw = raw.rstrip() + "\n" + block + "\n"
        self.save_skill("solutions", raw)
        logger.info("Saved solution %s: %s", solution_id, problem[:80])
        return solution_id

    def save_memory_fact(self, content: str, category: str = "General") -> str:
        """
        Append a new fact block to facts.skill.md.
        Returns the generated fact ID.
        """
        from datetime import date

        fact_id = uuid.uuid4().hex[:8]
        today = date.today().isoformat()

        raw = self.load_skill("facts")
        if not raw.strip():
            raw = "# Hechos Recordados\n"

        block = (
            f"\n<!-- fact: {fact_id} -->\n"
            f"## {category}\n"
            f"**Hecho:** {content}\n"
            f"**Fecha:** {today}\n\n"
            "---"
        )

        raw = raw.rstrip() + "\n" + block + "\n"
        self.save_skill("facts", raw)
        logger.info("Saved memory fact %s: %s", fact_id, content[:80])
        return fact_id

    def search_memory(self, query: str, max_results: int = 5) -> str:
        """
        Text search across facts.skill.md, general.skill.md, and faqs.skill.md.
        Returns matching sections with source labels; or a 'no results' message.
        """
        query_lower = query.lower()
        window = 3  # lines of context around each match

        sources = [
            ("facts", "facts"),
            ("general", "general"),
            ("faqs", "faqs"),
            ("solutions", "solutions"),
        ]

        all_sections: list[str] = []

        for skill_name, label in sources:
            text = self.load_skill(skill_name)
            if not text:
                continue

            lines = text.splitlines()
            found_indices: list[int] = []
            for idx, line in enumerate(lines):
                if query_lower in line.lower():
                    found_indices.append(idx)

            if not found_indices:
                continue

            merged_ranges: list[tuple[int, int]] = []
            start = max(0, found_indices[0] - window)
            end = min(len(lines) - 1, found_indices[0] + window)
            for idx in found_indices[1:]:
                new_start = max(0, idx - window)
                new_end = min(len(lines) - 1, idx + window)
                if new_start <= end + 1:
                    end = max(end, new_end)
                else:
                    merged_ranges.append((start, end))
                    start, end = new_start, new_end
            merged_ranges.append((start, end))

            snippets: list[str] = []
            for rng_start, rng_end in merged_ranges[: max_results]:
                snippets.append("\n".join(lines[rng_start : rng_end + 1]))

            if snippets:
                all_sections.append(f"[{label}]\n" + "\n...\n".join(snippets))

        if not all_sections:
            return "No se encontró información relevante en la memoria."

        return "\n\n".join(all_sections)

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
        updated = re.sub(r"\n---\n\n---", "\n---", updated)
        updated = updated.strip() + "\n"
        self.save_skill("faqs", updated)
        return True

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
        parts = re.split(r"<!--\s*id:\s*([a-f0-9]+)\s*-->", raw)
        i = 1
        while i < len(parts) - 1:
            faq_id = parts[i].strip()
            block = parts[i + 1]
            i += 2

            cat_match = re.search(r"^##\s+(.+)$", block, re.MULTILINE)
            category = cat_match.group(1).strip() if cat_match else "General"

            q_match = re.search(r"\*\*P:\*\*\s*(.+)", block)
            question = q_match.group(1).strip() if q_match else ""

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
