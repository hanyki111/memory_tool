"""Turn text into a document, on explicit request, using an LLM.

The document format is defined once: the prompt reads the same writing guides a
person or an AI uses in conversation. It used to carry its own copy of an old
format, which went stale when the format changed.

Writing for the user is not the default way to create a document. This runs only
when the user asks for it with ``mmodule from-text``, and the result is marked as
AI-written in ``generated.by``.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from memory_tool import __version__

from ..llm.client import LLMClient
from .module import ModuleManager
from .writing_guides import DOCUMENT_TYPES, read_all_guides

_FIELD = re.compile(r"^(NAME|TYPE|DESCRIPTION|CONNECTIONS|REASONING):[ \t]*(.*)$", re.MULTILINE)
_BODY = re.compile(r"<<<BODY\s*\n(.*?)\n?\s*BODY>>>", re.DOTALL)
_OUTER_FENCE = re.compile(r"\A```[a-zA-Z]*\n(.*)\n```\s*\Z", re.DOTALL)


@dataclass
class GeneratedModule:
    """Result of generating a document from text."""

    name: str
    doc_type: Optional[str]
    description: str
    body: str
    suggested_connections: List[str] = field(default_factory=list)
    reasoning: str = ""


class AIModuleGenerator:
    """Generate a document from text using an LLM."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        base_path: Optional[Path] = None,
    ):
        """Initialize generator.

        Args:
            llm_client: LLM client (optional, creates one if not provided)
            base_path: Project root. Defaults to the current project.
        """
        self.llm_client = llm_client or LLMClient()
        self.manager = ModuleManager(base_path)

    def _existing_modules(self) -> List[str]:
        return [path.as_posix() for path in self.manager.discover_all_modules()]

    def _build_prompt(self, text: str, language: str) -> str:
        if language == "ko":
            language_rule = "Write in Korean."
        elif language == "en":
            language_rule = "Write in English."
        else:
            language_rule = "Write in the same language as the input text."

        existing = "\n".join(f"- {name}" for name in self._existing_modules()) or "(none)"

        return f"""Turn the input text into one knowledge document.

The user has explicitly asked you to write this document, so write the body
yourself instead of asking the guides' questions. Use the guides below to choose
a type and to decide what a good document of that type holds.

{read_all_guides(self.manager.memory_path)}

---

Rules:
- {language_rule}
- Use only what the input text says. Do not add facts, and do not invent dates or sources.
- Write no empty sections, placeholders or TODO markers. If the text does not cover something, leave it out.
- Things the text leaves unresolved go under a "## 열린 질문" heading.
- Do not start the body with a title. One is added for you.
- TYPE is one of: {", ".join(DOCUMENT_TYPES)}. Leave it empty if none fits.
- NAME is a short document name. It may use a folder path taken from the existing documents. Use only letters, numbers, spaces, dashes and underscores.
- CONNECTIONS lists only names from the existing documents, comma-separated. Leave it empty if none is clearly related.

Existing documents:
{existing}

Input text:
<<<INPUT
{text}
INPUT>>>

Answer in exactly this format:

NAME: <name>
TYPE: <type>
DESCRIPTION: <one sentence>
CONNECTIONS: <names>
REASONING: <why this type, one sentence>
<<<BODY
<document body in Markdown>
BODY>>>"""

    def _parse_response(self, response: str) -> GeneratedModule:
        """Parse the LLM's answer.

        Raises:
            ValueError: If the answer has no name or no body.
        """
        cleaned = response.strip()
        fenced = _OUTER_FENCE.match(cleaned)
        if fenced:
            cleaned = fenced.group(1)

        body_match = _BODY.search(cleaned)
        if not body_match or not body_match.group(1).strip():
            raise ValueError("The LLM's answer has no document body")

        # Fields come before the body; a line in the body must not overwrite one.
        header = cleaned[: body_match.start()]
        fields = {key: value.strip() for key, value in _FIELD.findall(header)}

        name = fields.get("NAME", "").replace("\\", "/").strip("/ ")
        if not name:
            raise ValueError("The LLM's answer has no document name")

        existing = set(self._existing_modules())
        connections = [
            item.strip()
            for item in fields.get("CONNECTIONS", "").split(",")
            if item.strip() in existing
        ]

        return GeneratedModule(
            name=name,
            doc_type=fields.get("TYPE") or None,
            description=fields.get("DESCRIPTION", ""),
            body=body_match.group(1).strip(),
            suggested_connections=connections,
            reasoning=fields.get("REASONING", ""),
        )

    def generate(self, text: str, language: str = "auto") -> GeneratedModule:
        """Generate a document from text.

        Args:
            text: Input text
            language: Output language: 'ko', 'en' or 'auto'

        Returns:
            The generated document, not yet saved.

        Raises:
            ValueError: If the input is empty or the answer cannot be read.
        """
        if not text or not text.strip():
            raise ValueError("Input text is empty")

        response = self.llm_client.generate(
            prompt=self._build_prompt(text, language),
            system_prompt="You turn notes into one knowledge document, in the requested format.",
        )
        return self._parse_response(response)

    def save_module(self, generated: GeneratedModule) -> Path:
        """Save a generated document.

        Args:
            generated: The generated document

        Returns:
            Path to the saved document.

        Raises:
            ValueError: If it cannot be saved, for example because the name is taken.
        """
        try:
            path = self.manager.create(
                generated.name,
                description=generated.description,
                doc_type=generated.doc_type,
                generated_by=f"memory-tool/{__version__}",
            )
        except Exception as e:
            raise ValueError(f"Failed to save module: {e}")

        content = path.read_text(encoding="utf-8").rstrip("\n")
        content += f"\n\n{generated.body}\n"

        if generated.suggested_connections:
            links = "\n".join(f"- [[{name}]]" for name in generated.suggested_connections)
            content += f"\n## 관련 문서\n\n{links}\n"

        path.write_text(content, encoding="utf-8")
        return path

    def format_preview(self, generated: GeneratedModule) -> str:
        """Format a generated document for display, without markup in its text."""
        from rich.markup import escape

        lines = [
            f"[bold]Name:[/bold] {escape(generated.name)}",
            f"[bold]Type:[/bold] {escape(generated.doc_type or '(none)')}",
            f"[bold]Description:[/bold] {escape(generated.description)}",
            f"[bold]Reasoning:[/bold] {escape(generated.reasoning)}",
        ]

        if generated.suggested_connections:
            lines.append("[bold]Connections:[/bold]")
            lines.extend(f"  - {escape(name)}" for name in generated.suggested_connections)

        lines.extend(["", escape(generated.body)])
        return "\n".join(lines)

