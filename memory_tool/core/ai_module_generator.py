"""AI-based module generation from text input."""

from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from ..llm.client import LLMClient
from .module import ModuleManager


@dataclass
class GeneratedModule:
    """Result of AI module generation."""

    name: str
    module_type: str  # "projects", "areas", "resources"
    description: str
    module_md: str
    current_md: str
    decisions_md: str
    suggested_connections: List[str]
    reasoning: str


class AIModuleGenerator:
    """Generate modules from text using LLM.

    Features:
    - Analyzes text to determine appropriate module structure
    - Follows module organization principles
    - Suggests module type (projects/areas/resources)
    - Generates module.md, current.md, decisions.md content
    - Suggests connections to existing modules
    """

    # Module organization principles thresholds
    MIN_CONTENT_LINES = 50  # Minimum lines to warrant a new module

    def __init__(
        self,
        base_path: Optional[Path] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        """Initialize generator.

        Args:
            base_path: Base path for project (contains .memory/)
            llm_client: LLM client (creates one if not provided)
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"
        self.modules_path = self.memory_path / "modules"

        self.llm_client = llm_client or LLMClient()
        self.module_manager = ModuleManager(base_path)

    def _get_existing_modules(self) -> List[str]:
        """Get list of existing module names.

        Returns:
            List of module paths (e.g., ["projects/memory-tool", "areas/python"])
        """
        if not self.module_manager.is_initialized():
            return []

        modules = self.module_manager.list_modules(include_archived=False)
        return modules.get("active", [])

    def _build_generation_prompt(
        self,
        text: str,
        existing_modules: List[str],
        language: str = "auto",
    ) -> str:
        """Build prompt for module generation.

        Args:
            text: Input text to convert to module
            existing_modules: List of existing module names
            language: Output language ("ko", "en", "auto")

        Returns:
            Prompt string for LLM
        """
        existing_modules_str = "\n".join(f"- {m}" for m in existing_modules) if existing_modules else "None"

        # Build language instruction with emphasis
        lang_instruction_brief = ""
        lang_instruction_emphasis = ""

        if language == "ko":
            lang_instruction_brief = "OUTPUT LANGUAGE: Korean (한국어)"
            lang_instruction_emphasis = """
LANGUAGE REQUIREMENT (CRITICAL):
- Write ALL content in Korean (한국어로 작성)
- DESCRIPTION, REASONING values must be in Korean
- module.md, current.md, decisions.md content must be in Korean
- Only keep format keywords (MODULE_NAME, MODULE_TYPE, etc.) in English
- Example: DESCRIPTION: 비동기 프로그래밍 학습을 위한 모듈입니다."""
        elif language == "en":
            lang_instruction_brief = "OUTPUT LANGUAGE: English"
            lang_instruction_emphasis = """
LANGUAGE REQUIREMENT (CRITICAL):
- Write ALL content in English
- All descriptions, reasoning, and markdown content must be in English"""
        else:
            lang_instruction_brief = "OUTPUT LANGUAGE: Same as input text"
            lang_instruction_emphasis = """
LANGUAGE REQUIREMENT (CRITICAL):
- Write ALL content in the SAME LANGUAGE as the input text
- If input is in Korean, output in Korean. If input is in English, output in English.
- Only keep format keywords (MODULE_NAME, MODULE_TYPE, etc.) in English"""

        prompt = f"""You are a module structure analyzer. Convert the following text into a well-organized module structure.

{lang_instruction_brief}

INPUT TEXT:
{text}

EXISTING MODULES:
{existing_modules_str}

MODULE ORGANIZATION PRINCIPLES:
1. Single Responsibility: Each module should have one clear purpose
2. Cohesion: All content should relate to a single theme
3. Size Guidelines: 100-500 lines (small), 500-1500 lines (medium)
4. Naming: Use lowercase with dashes (e.g., "my-feature")
5. Types:
   - projects/[name]: Active projects or features
   - areas/[name]: Knowledge domains or disciplines
   - resources/[name]: Reusable templates or references

TASK:
Analyze the input text and generate a module structure.

RESPOND IN EXACTLY THIS FORMAT (keep keywords in English, write values in specified language):

MODULE_NAME: [suggested path like "projects/feature-name" or "areas/topic-name"]
MODULE_TYPE: [projects|areas|resources]
DESCRIPTION: [1-2 sentence description in specified language]
REASONING: [explanation in specified language]

CONNECTIONS: [comma-separated list of existing module names, or "none"]

---MODULE_MD---
[Full content for module.md in specified language - include Purpose, Scope, Architecture sections]
---END_MODULE_MD---

---CURRENT_MD---
[Full content for current.md in specified language - include status, tasks, next steps]
---END_CURRENT_MD---

---DECISIONS_MD---
[Full content for decisions.md in specified language - include initial decision for creating this module]
---END_DECISIONS_MD---
{lang_instruction_emphasis}

IMPORTANT:
- If the input text is too short (<50 lines of meaningful content), suggest adding to an existing module instead
- Follow the exact format above with section markers
- Generate complete, ready-to-use markdown content
"""
        return prompt

    def _parse_generation_response(self, response: str) -> GeneratedModule:
        """Parse LLM response into GeneratedModule.

        Args:
            response: Raw LLM response

        Returns:
            GeneratedModule with parsed content

        Raises:
            ValueError: If response cannot be parsed
        """
        import re

        # Extract metadata
        name_match = re.search(r'MODULE_NAME:\s*(.+)', response)
        type_match = re.search(r'MODULE_TYPE:\s*(.+)', response)
        desc_match = re.search(r'DESCRIPTION:\s*(.+)', response)
        reason_match = re.search(r'REASONING:\s*(.+)', response)
        conn_match = re.search(r'CONNECTIONS:\s*(.+)', response)

        if not name_match:
            raise ValueError("Could not parse MODULE_NAME from response")

        name = name_match.group(1).strip()
        module_type = type_match.group(1).strip() if type_match else "projects"
        description = desc_match.group(1).strip() if desc_match else ""
        reasoning = reason_match.group(1).strip() if reason_match else ""

        # Parse connections
        connections = []
        if conn_match:
            conn_str = conn_match.group(1).strip().lower()
            if conn_str != "none":
                connections = [c.strip() for c in conn_str.split(",") if c.strip()]

        # Extract content sections
        module_md_match = re.search(
            r'---MODULE_MD---\s*\n(.+?)\n---END_MODULE_MD---',
            response,
            re.DOTALL
        )
        current_md_match = re.search(
            r'---CURRENT_MD---\s*\n(.+?)\n---END_CURRENT_MD---',
            response,
            re.DOTALL
        )
        decisions_md_match = re.search(
            r'---DECISIONS_MD---\s*\n(.+?)\n---END_DECISIONS_MD---',
            response,
            re.DOTALL
        )

        module_md = module_md_match.group(1).strip() if module_md_match else self._generate_default_module_md(name, description)
        current_md = current_md_match.group(1).strip() if current_md_match else self._generate_default_current_md()
        decisions_md = decisions_md_match.group(1).strip() if decisions_md_match else self._generate_default_decisions_md(name, description)

        return GeneratedModule(
            name=name,
            module_type=module_type,
            description=description,
            module_md=module_md,
            current_md=current_md,
            decisions_md=decisions_md,
            suggested_connections=connections,
            reasoning=reasoning,
        )

    def _generate_default_module_md(self, name: str, description: str) -> str:
        """Generate default module.md content."""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        return f"""# Module: {name}

**Created:** {timestamp}
**Tags:**

## Purpose

{description if description else "TODO: Describe the purpose of this module"}

## Scope

TODO: Define what is included and excluded from this module

## Architecture

TODO: Describe the high-level architecture and design decisions
"""

    def _generate_default_current_md(self) -> str:
        """Generate default current.md content."""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        return f"""# Current Status

## {timestamp}

### In Progress
- [ ] Initial setup

### Completed
- [x] Module created

### Next Steps
1. Define scope and boundaries
2. Add initial content
"""

    def _generate_default_decisions_md(self, name: str, description: str) -> str:
        """Generate default decisions.md content."""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        return f"""# Decisions

## Decision 1: Module Creation ({timestamp})

**Context:** Initial module setup

**Decision:** Created {name} module

**Rationale:** {description if description else "To organize related content"}

**Consequences:**
- Module structure established
- Ready for content development

**Status:** Accepted
"""

    def generate(
        self,
        text: str,
        language: str = "auto",
    ) -> GeneratedModule:
        """Generate module structure from text.

        Args:
            text: Input text to convert to module
            language: Output language ("ko", "en", "auto")

        Returns:
            GeneratedModule with generated content

        Raises:
            ValueError: If generation fails
        """
        existing_modules = self._get_existing_modules()
        prompt = self._build_generation_prompt(text, existing_modules, language)

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=4000,
            )

            return self._parse_generation_response(response)

        except Exception as e:
            raise ValueError(f"Module generation failed: {str(e)}")

    def save_module(self, generated: GeneratedModule) -> Path:
        """Save generated module to disk.

        Args:
            generated: GeneratedModule to save

        Returns:
            Path to created module directory

        Raises:
            ModuleError: If saving fails
        """
        # Validate module name
        name = generated.name

        # Ensure name follows convention (normalize path separators)
        name = name.replace("\\", "/").strip("/")

        # Check if module already exists
        module_path = self.modules_path / name
        if module_path.exists():
            raise ValueError(f"Module already exists: {name}")

        # Create directory structure
        module_path.mkdir(parents=True, exist_ok=True)

        try:
            # Write module files
            (module_path / "module.md").write_text(generated.module_md, encoding="utf-8")
            (module_path / "current.md").write_text(generated.current_md, encoding="utf-8")
            (module_path / "decisions.md").write_text(generated.decisions_md, encoding="utf-8")

            # Write connections if any
            if generated.suggested_connections:
                deps_content = self._generate_dependencies_md(generated.suggested_connections)
                (module_path / "dependencies.md").write_text(deps_content, encoding="utf-8")

            return module_path

        except Exception as e:
            # Clean up on failure
            import shutil
            shutil.rmtree(module_path, ignore_errors=True)
            raise ValueError(f"Failed to save module: {str(e)}")

    def _generate_dependencies_md(self, connections: List[str]) -> str:
        """Generate dependencies.md content."""
        connections_str = "\n".join(f"- [[{c}]]" for c in connections)
        return f"""# Dependencies

## Internal Dependencies

{connections_str}

## External Dependencies

None yet

## Notes

- Connections suggested by AI module generator
"""

    def format_preview(self, generated: GeneratedModule) -> str:
        """Format generated module for preview display.

        Args:
            generated: GeneratedModule to format

        Returns:
            Formatted string for console output
        """
        lines = [
            "=" * 60,
            "GENERATED MODULE PREVIEW",
            "=" * 60,
            "",
            f"[bold]Module Name:[/bold] {generated.name}",
            f"[bold]Type:[/bold] {generated.module_type}",
            f"[bold]Description:[/bold] {generated.description}",
            "",
            f"[bold]Reasoning:[/bold]",
            f"  {generated.reasoning}",
            "",
        ]

        if generated.suggested_connections:
            lines.append("[bold]Suggested Connections:[/bold]")
            for conn in generated.suggested_connections:
                lines.append(f"  - {conn}")
            lines.append("")

        lines.extend([
            "-" * 60,
            "[bold cyan]module.md[/bold cyan]",
            "-" * 60,
            generated.module_md,
            "",
            "-" * 60,
            "[bold cyan]current.md[/bold cyan]",
            "-" * 60,
            generated.current_md,
            "",
            "-" * 60,
            "[bold cyan]decisions.md[/bold cyan]",
            "-" * 60,
            generated.decisions_md,
            "",
            "=" * 60,
        ])

        return "\n".join(lines)
