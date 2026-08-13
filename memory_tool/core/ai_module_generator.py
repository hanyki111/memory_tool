"""AI-based module generation from text input."""

from pathlib import Path
from typing import Optional, Dict, List, Tuple, Literal
from dataclasses import dataclass
from datetime import datetime
from ..llm.client import LLMClient
from .module import ModuleManager
from memory_tool.utils.paths import base_dir_for_root, get_project_root


@dataclass
class GeneratedModule:
    """Result of AI module generation."""

    name: str
    module_type: str  # "projects", "areas", "resources"
    structure_type: str  # "feature" or "topic"
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
    - Supports Feature-based (software projects) and Topic-based (learning/KB) modules
    - Follows module organization principles
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
            base_path = get_project_root()
        self.base_path = Path(base_path)
        self.memory_path = base_dir_for_root(self.base_path)
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
        structure_type: str = "auto",
    ) -> str:
        """Build prompt for module generation.

        Args:
            text: Input text to convert to module
            existing_modules: List of existing module names
            language: Output language ("ko", "en", "auto")
            structure_type: Module structure type ("feature", "topic", "auto")

        Returns:
            Prompt string for LLM
        """
        existing_modules_str = "\n".join(f"- {m}" for m in existing_modules) if existing_modules else "None"

        # Build language instruction
        lang_instruction_brief = ""
        lang_instruction_emphasis = ""

        if language == "ko":
            lang_instruction_brief = "OUTPUT LANGUAGE: Korean (한국어)"
            lang_instruction_emphasis = """
LANGUAGE REQUIREMENT (CRITICAL):
- Write ALL content in Korean (한국어로 작성)
- DESCRIPTION, REASONING values must be in Korean
- module.md, current.md, decisions.md content must be in Korean
- Only keep format keywords (MODULE_NAME, STRUCTURE_TYPE, etc.) in English
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
- Only keep format keywords (MODULE_NAME, STRUCTURE_TYPE, etc.) in English"""

        # Build structure type instruction
        if structure_type == "feature":
            structure_instruction = """
STRUCTURE TYPE: Feature-based (기능 중심) - FORCED
You MUST create a Feature-based module structure."""
        elif structure_type == "topic":
            structure_instruction = """
STRUCTURE TYPE: Topic-based (주제 중심) - FORCED
You MUST create a Topic-based module structure."""
        else:
            structure_instruction = """
STRUCTURE TYPE: Auto-detect
Analyze the input text and determine the appropriate structure type."""

        prompt = f"""You are a module structure analyzer. Convert the following text into a well-organized module structure.

{lang_instruction_brief}
{structure_instruction}

INPUT TEXT:
{text}

EXISTING MODULES:
{existing_modules_str}

==============================================================================
MODULE STRUCTURE TYPES (IMPORTANT - Read carefully)
==============================================================================

There are TWO distinct module structure types. Choose the appropriate one:

## 1. FEATURE-BASED (기능 중심) Module
**Use when:**
- Software projects or features
- Multiple developers/teams collaborate
- Long-term maintenance required
- Code implementation is the focus

**Characteristics:**
- High cohesion: All elements implementing a specific feature in one module
- Independent evolution: Changes to one feature minimally affect others
- Clear single responsibility: Each module has exactly one reason to change

**Directory pattern:** projects/[project-name]/[feature-name]
**Examples:**
- projects/memory-tool/search-system
- projects/memory-tool/llm-integration
- projects/webapp/auth-system

**module.md template for Feature-based:**
```
# Module: [name]

## Purpose and Goals
[What software feature does this module implement?]

## Responsibility and Scope
- Responsibility: [Single clear responsibility]
- Scope: [What's included and excluded]

## Architecture
[Technical architecture, components, data flow]

## Interface
[Public APIs, commands, data structures]
```

**current.md template for Feature-based:**
```
# Current Status

## Implementation Status
- Phase: [planning/development/testing/stable]
- Progress: [percentage or milestone]

## In Progress
- [ ] [Feature/task being implemented]

## Completed
- [x] [Completed features]

## Technical Debt / Known Issues
- [Issues to address]

## Next Steps
1. [Next implementation task]
```

**decisions.md template for Feature-based:**
```
# Technical Decisions

## Decision [N]: [Title] ([date])

**Context:** [Technical problem or requirement]

**Decision:** [Chosen solution]

**Alternatives Considered:**
- [Alternative 1]: [Why rejected]
- [Alternative 2]: [Why rejected]

**Consequences:**
- [Technical impact]
- [Trade-offs accepted]

**Status:** [Accepted/Superseded/Deprecated]
```

---

## 2. TOPIC-BASED (주제 중심) Module
**Use when:**
- Learning/research projects
- Concept organization
- Personal Knowledge Base (KB) building
- Documentation of understanding

**Characteristics:**
- Knowledge cohesion: Related concepts grouped together
- Evolution tracking: Records how understanding develops over time
- Conceptual clarity: Focuses on explaining and organizing ideas

**Directory pattern:** areas/[knowledge-domain]
**Examples:**
- areas/async-programming
- areas/machine-learning
- areas/system-design

**module.md template for Topic-based:**
```
# [Topic Name]

## Purpose and Goals
[What knowledge does this module capture? What learning objectives?]

## Responsibility and Scope
- Responsibility: [What concepts this module explains]
- Scope:
  - Included: [Topics covered]
  - Excluded: [Related but out-of-scope topics]

## Key Concepts
[Core concepts and their relationships]

## Learning Path
[Suggested order for understanding the material]
```

**current.md template for Topic-based:**
```
# Current Understanding

## Core Concepts
### [Concept 1]
[Definition and explanation]

### [Concept 2]
[Definition and explanation]

## Learning Progress
- [ ] [Topic to study]
- [x] [Topic understood]

## Questions to Explore
- [Open questions]

## Resources
- [Books, articles, courses]
```

**decisions.md template for Topic-based:**
```
# Learning Decisions

## Decision [N]: [Title] ([date])

**Context:** [Learning challenge or conceptual question]

**Decision:** [How to approach or understand the topic]

**Rationale:** [Why this interpretation/approach]

**Insights:**
- [Key learnings]
- [Connections to other concepts]

**Status:** [Active/Revised/Archived]
```

==============================================================================
CORE ORGANIZATION PRINCIPLES (Apply to both types)
==============================================================================
1. Single Responsibility: Each module should have one clear purpose
2. Cohesion: All content should relate to a single theme
3. Size Guidelines: 100-500 lines (small), 500-1500 lines (medium)
4. Naming: Use lowercase with dashes (e.g., "my-feature" or "my-topic")
5. Split when: current.md > 300 lines, >5 distinct topics, >20 decisions

==============================================================================
TASK
==============================================================================
Analyze the input text and generate a module structure.

RESPOND IN EXACTLY THIS FORMAT (keep keywords in English, write values in specified language):

STRUCTURE_TYPE: [feature|topic]
MODULE_NAME: [suggested path - use "projects/xxx" for feature, "areas/xxx" for topic]
MODULE_TYPE: [projects|areas|resources]
DESCRIPTION: [1-2 sentence description in specified language]
REASONING: [Explain why you chose this structure type and path. Reference the criteria above.]

CONNECTIONS: [comma-separated list of existing module names, or "none"]

---MODULE_MD---
[Full content following the appropriate template above]
---END_MODULE_MD---

---CURRENT_MD---
[Full content following the appropriate template above]
---END_CURRENT_MD---

---DECISIONS_MD---
[Full content following the appropriate template above]
---END_DECISIONS_MD---
{lang_instruction_emphasis}

IMPORTANT:
- Choose Feature-based for software/implementation content
- Choose Topic-based for learning/concept/knowledge content
- Follow the exact template for the chosen structure type
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
        structure_match = re.search(r'STRUCTURE_TYPE:\s*(.+)', response)
        name_match = re.search(r'MODULE_NAME:\s*(.+)', response)
        type_match = re.search(r'MODULE_TYPE:\s*(.+)', response)
        desc_match = re.search(r'DESCRIPTION:\s*(.+)', response)
        reason_match = re.search(r'REASONING:\s*(.+)', response)
        conn_match = re.search(r'CONNECTIONS:\s*(.+)', response)

        if not name_match:
            raise ValueError("Could not parse MODULE_NAME from response")

        structure_type = structure_match.group(1).strip().lower() if structure_match else "topic"
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

        module_md = module_md_match.group(1).strip() if module_md_match else self._generate_default_module_md(name, description, structure_type)
        current_md = current_md_match.group(1).strip() if current_md_match else self._generate_default_current_md(structure_type)
        decisions_md = decisions_md_match.group(1).strip() if decisions_md_match else self._generate_default_decisions_md(name, description, structure_type)

        return GeneratedModule(
            name=name,
            module_type=module_type,
            structure_type=structure_type,
            description=description,
            module_md=module_md,
            current_md=current_md,
            decisions_md=decisions_md,
            suggested_connections=connections,
            reasoning=reasoning,
        )

    def _generate_default_module_md(self, name: str, description: str, structure_type: str) -> str:
        """Generate default module.md content based on structure type."""
        timestamp = datetime.now().strftime("%Y-%m-%d")

        if structure_type == "feature":
            return f"""# Module: {name}

**Created:** {timestamp}
**Type:** Feature-based (기능 중심)

## Purpose and Goals

{description if description else "TODO: What software feature does this module implement?"}

## Responsibility and Scope

- **Responsibility:** TODO: Single clear responsibility
- **Scope:** TODO: What's included and excluded

## Architecture

TODO: Technical architecture, components, data flow

## Interface

TODO: Public APIs, commands, data structures
"""
        else:  # topic
            return f"""# {name}

**Created:** {timestamp}
**Type:** Topic-based (주제 중심)

## Purpose and Goals

{description if description else "TODO: What knowledge does this module capture?"}

## Responsibility and Scope

- **Responsibility:** TODO: What concepts this module explains
- **Scope:**
  - Included: TODO
  - Excluded: TODO

## Key Concepts

TODO: Core concepts and their relationships

## Learning Path

TODO: Suggested order for understanding the material
"""

    def _generate_default_current_md(self, structure_type: str) -> str:
        """Generate default current.md content based on structure type."""
        timestamp = datetime.now().strftime("%Y-%m-%d")

        if structure_type == "feature":
            return f"""# Current Status

## {timestamp}

## Implementation Status
- Phase: planning
- Progress: 0%

## In Progress
- [ ] Initial setup

## Completed
- [x] Module created

## Technical Debt / Known Issues
None

## Next Steps
1. Define architecture
2. Begin implementation
"""
        else:  # topic
            return f"""# Current Understanding

## {timestamp}

## Core Concepts

### Concept 1
TODO: Definition and explanation

## Learning Progress
- [ ] Initial study
- [x] Module created

## Questions to Explore
- TODO: Open questions

## Resources
- TODO: Books, articles, courses
"""

    def _generate_default_decisions_md(self, name: str, description: str, structure_type: str) -> str:
        """Generate default decisions.md content based on structure type."""
        timestamp = datetime.now().strftime("%Y-%m-%d")

        if structure_type == "feature":
            return f"""# Technical Decisions

## Decision 1: Module Creation ({timestamp})

**Context:** Need to implement {name}

**Decision:** Created Feature-based module for {name}

**Alternatives Considered:**
- Adding to existing module: Rejected due to single responsibility principle

**Consequences:**
- Clear ownership and responsibility
- Independent development possible

**Status:** Accepted
"""
        else:  # topic
            return f"""# Learning Decisions

## Decision 1: Module Creation ({timestamp})

**Context:** Need to organize knowledge about {name}

**Decision:** Created Topic-based module for learning and concept organization

**Rationale:** {description if description else "To systematically capture and organize understanding"}

**Insights:**
- Starting point for knowledge accumulation
- Will evolve as understanding deepens

**Status:** Active
"""

    def generate(
        self,
        text: str,
        language: str = "auto",
        structure_type: str = "auto",
    ) -> GeneratedModule:
        """Generate module structure from text.

        Args:
            text: Input text to convert to module
            language: Output language ("ko", "en", "auto")
            structure_type: Module structure type ("feature", "topic", "auto")

        Returns:
            GeneratedModule with generated content

        Raises:
            ValueError: If generation fails
        """
        existing_modules = self._get_existing_modules()
        prompt = self._build_generation_prompt(text, existing_modules, language, structure_type)

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
        structure_label = "Feature-based" if generated.structure_type == "feature" else "Topic-based"

        lines = [
            "=" * 60,
            "GENERATED MODULE PREVIEW",
            "=" * 60,
            "",
            f"[bold]Module Name:[/bold] {generated.name}",
            f"[bold]Structure:[/bold] {structure_label} ({generated.structure_type})",
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
