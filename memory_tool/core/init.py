"""Initialization functionality for the knowledge base structure."""

from datetime import datetime
from pathlib import Path
from typing import Optional
import shutil
import yaml

from memory_tool.utils.paths import (
    DEFAULT_BASE,
    ROOT_BASE,
    InvalidBaseNameError,
    read_pointer,
    validate_base_name,
    write_pointer,
)


class InitializationError(Exception):
    """Base exception for initialization operations."""
    pass


class AlreadyInitializedError(InitializationError):
    """Raised when .memory/ already exists."""
    pass


class MemoryInitializer:
    """Initializer for .memory/ structure."""

    def __init__(
        self,
        base_path: Optional[Path] = None,
        base_name: Optional[str] = None,
    ):
        """Initialize memory initializer.

        Args:
            base_path: Project root. Defaults to current directory.
            base_name: Name for the knowledge base folder. Defaults to an
                existing project's configured name, else ".memory". Use "." to
                make the project root itself the base folder.

        Raises:
            InitializationError: If base_name is unusable.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)

        if base_name is None:
            # Respect an already-configured base folder so --force and
            # --update-docs keep working on existing projects.
            self.base_name = read_pointer(self.base_path) or DEFAULT_BASE
        else:
            try:
                self.base_name = validate_base_name(base_name)
            except InvalidBaseNameError as e:
                raise InitializationError(str(e)) from e

        self.memory_path = (
            self.base_path
            if self.base_name == ROOT_BASE
            else self.base_path / self.base_name
        )
        self.claude_path = self.base_path / ".claude"
        # Get memory_tool's installation directory
        self.memory_tool_root = Path(__file__).parent.parent.parent

    @property
    def is_root_base(self) -> bool:
        """True when the project root itself is the knowledge base folder."""
        return self.base_name == ROOT_BASE

    def is_initialized(self) -> bool:
        """Check whether the knowledge base already exists.

        A root base always "exists" as a directory, so it is judged by markers
        Memory Tool itself creates. ``config.yaml`` is deliberately not one of
        them -- it is far too common a filename in an ordinary project.

        Returns:
            True if the knowledge base is already set up
        """
        if self.is_root_base:
            return (
                read_pointer(self.base_path) == ROOT_BASE
                or (self.memory_path / "timeline").is_dir()
            )
        return self.memory_path.exists()

    def root_base_collisions(self) -> list:
        """Files a root-base init would overwrite in an existing project.

        With ``--base .`` the knowledge base shares a directory with the
        project, so ``README.md`` and ``config.yaml`` would land on top of the
        project's own files. Those are not ours to overwrite.

        Returns:
            Existing paths that this initialization would otherwise clobber.
        """
        if not self.is_root_base:
            return []

        candidates = ["README.md", "config.yaml", "timeline", "modules", "concepts",
                      "templates", "docs"]
        return [
            self.memory_path / name
            for name in candidates
            if (self.memory_path / name).exists()
        ]

    def get_structure(self) -> dict:
        """Get the directory structure to create.

        Paths are relative to the project root and built from the configured
        base folder name, so they follow a renamed or root-level base.

        Returns:
            Dictionary mapping paths to types ('dir' or 'file')
        """
        base = self.base_name

        def under(*parts: str) -> str:
            """Join a path under the base folder, flattening a root base."""
            segments = [p for p in ((base,) if base != ROOT_BASE else ()) + parts]
            return "/".join(segments)

        structure = {}

        if base != ROOT_BASE:
            structure[base] = "dir"
            structure[under(".gitkeep")] = "file"

        for name in ("timeline", "modules", "concepts", "templates", "docs"):
            structure[under(name)] = "dir"
            structure[under(name, ".gitkeep")] = "file"

        structure[".claude"] = "dir"
        structure[".claude/skills"] = "dir"
        structure[".claude/skills/mt-publish"] = "dir"
        structure[".claude/skills/mt-master-module"] = "dir"

        return structure

    def create_config_yaml(self) -> Path:
        """Create initial config.yaml.

        Returns:
            Path to created config.yaml
        """
        config_path = self.memory_path / "config.yaml"

        # Write YAML with comments for better documentation
        config_content = '''# ============================================================
# Memory Tool Configuration
# ============================================================
version: "1.0"

# ------------------------------------------------------------
# Timeline Settings
# ------------------------------------------------------------
timeline:
  auto_record: false           # Auto-record on certain events
  granularity: medium          # low, medium, high
  warn_old_days: 365           # Warn if recording to old dates

# ------------------------------------------------------------
# Context Settings (for Claude Code integration)
# ------------------------------------------------------------
context:
  auto_update: false           # Auto-update .claude/memory-context.md
  recent_days: 3               # Days of timeline to include

# ------------------------------------------------------------
# Help & Language Settings
# ------------------------------------------------------------
help:
  language: en                 # Help language: en, ko (affects --help output)
  # Change with: python -m memory_tool config set help.language ko

# ------------------------------------------------------------
# Module Settings
# ------------------------------------------------------------
modules:
  auto_update_current: false   # Auto-update current.md on changes

# ------------------------------------------------------------
# Search Settings
# ------------------------------------------------------------
search:
  default_scope: local         # local, kb, all
  include_archived: false      # Include archived content
  max_file_size: 1048576       # Max file size to search (1MB)
  exclude_patterns: []         # Patterns to exclude from search

# ------------------------------------------------------------
# Code Map Settings (mmap command)
# ------------------------------------------------------------
codemap:
  default_depth: structure     # overview, structure, api, docs
  include_private: false       # Include private members
  include_tests: false         # Include test files
  exclude_patterns:
    - __pycache__
    - .venv
    - venv
    - node_modules
    - .git

# ============================================================
# LLM Integration (Optional)
# ============================================================
# Configure LLM provider for summary, Q&A (mask), and AI features
#
# Uncomment ONE provider section to enable:

# llm:
#   provider: gemini-cli       # Options: anthropic, ollama, claude-cli, gemini-cli
#
#   # --- Claude CLI (recommended, uses CLI auth) ---
#   claude_cli:
#     command: claude          # CLI command name
#     model: null              # null = use CLI default
#
#   # --- Gemini CLI (uses CLI auth) ---
#   gemini_cli:
#     command: gemini          # CLI command name
#     model: null              # null = use CLI default
#
#   # --- Anthropic API (requires API key) ---
#   # anthropic:
#   #   api_key: null          # Or set ANTHROPIC_API_KEY env var
#   #   model: claude-3-5-sonnet-20241022
#
#   # --- Ollama (local LLM) ---
#   # ollama:
#   #   host: http://localhost:11434
#   #   model: llama3.2
#
# Commands:
#   mask "question"            - Ask questions about memory (RAG)
#   mproviders                 - List available LLM providers
#   msummary                   - Summarize timeline or module

# ============================================================
# Notion Integration (Optional)
# ============================================================
# Enable sync between local memory and Notion
#
# Two modes available:
#   - "default": Standard Notion Integration (api_key required)
#   - "pat": Personal Access Token via proxy (for enterprise)

# notion:
#   mode: "default"            # "default" or "pat"
#
#   # --- Default Mode (Standard Notion Integration) ---
#   api_key: "secret_xxx..."             # Notion Integration Secret
#   default_page_id: "abc123..."         # Timeline mirror page ID
#
#   # --- PAT Mode (Enterprise/Proxy) ---
#   # pat:
#   #   api_key: "PAT_xxx..."            # Personal Access Token
#   #   notion_version: "2022-06-28"     # API version
#   #   base_url: "https://proxy.example.com/v1"  # Proxy URL
#   #   default_page_id: "xyz789..."     # Default page for PAT mode
#
#   # --- Module Sync Settings ---
#   sync:
#     enabled: true
#     root_page_id: "xyz789..."          # Module sync root page ID
#
#     # Sync targets (glob patterns supported)
#     targets:
#       # - "projects/my-project"        # Specific module
#       # - "projects/my-project/**"     # Module + all children
#       - "**"                           # All modules (caution: may be many)
#
#     # Exclude patterns
#     exclude_patterns:
#       - "archive/**"
#       - "*.backup"
#
#     # Conflict resolution policy
#     conflict_resolution: "last-write-wins"  # or "manual"
#
#     # Timeline sync settings
#     timeline:
#       enabled: true
#       bidirectional: true              # Notion <-> Local both directions
#       sync_days: 30                    # Days of timeline to sync
#
#     # Plan sync settings (daily/weekly plans)
#     plan:
#       enabled: false
#       root_page_id: null               # Plans root page ID
#       daily: true
#       weekly: true
#       monthly: false
#
# Commands:
#   nm "message"               - Record to Notion timeline
#   ns "query"                 - Search Notion
#   nt                         - Show Notion today
#   nw                         - Show Notion week
#   nsi "query"                - Search inside Notion pages
#   nsync                      - Sync all (modules + timeline + plans)
#   nsync --module             - Sync modules only
#   nsync --timeline           - Sync timeline only
#   nsync --plan               - Sync plans only
#   nwatch                     - Watch and auto-sync on changes
'''

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_content)

        return config_path

    def set_kb_path(self, kb_path: Optional[str] = None) -> bool:
        """Set knowledge base path in config.yaml.

        Args:
            kb_path: Path to knowledge base (optional)

        Returns:
            True if set, False if kb_path is None
        """
        if kb_path is None:
            return False

        from memory_tool.utils.config import Config
        config = Config(self.memory_path)
        config.set_kb_path(kb_path)
        return True

    # Legacy method for backward compatibility
    def create_kb_lock(self, kb_path: Optional[str] = None) -> Optional[Path]:
        """[DEPRECATED] Use set_kb_path instead.

        This method now sets kb.path in config.yaml.

        Args:
            kb_path: Path to knowledge base (optional)

        Returns:
            None (no longer creates kb.lock file)
        """
        if kb_path:
            self.set_kb_path(kb_path)
        return None

    def create_readme(self) -> Path:
        """Create README.md explaining the structure.

        Returns:
            Path to created README.md
        """
        readme_path = self.memory_path / "README.md"

        content = f"""# .memory/

This directory contains the memory structure for this project.

**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Structure

- `timeline/` - Time-based records (YYYY-MM/DD.md)
- `modules/` - Module-based organization
- `concepts/` - Standalone concept documents
- `config.yaml` - Configuration settings

## Usage

```bash
# Record to timeline
m "Your message here"

# Search
ms "query"

# Build context for Claude Code
mcontext

# Generate code structure map
mmap src/

# Build context with code map and update interfaces
mcontext --with-map --update-interfaces

# Verify Related Files paths
mcheck
```

## Knowledge Federation (KB)

Share knowledge across projects via central Knowledge Base.

```bash
# Setup: mconfig set kb.path /path/to/kb

# Publish module to KB
mpublish <module>

# Browse and import from KB
mimport --list
mimport <path> --preview
mimport <path>

# Search including KB
ms "query" --with-kb
```

## Philosophy

**Time First** - Capture first, organize later
**Lossless** - Record everything, lose nothing
**Minimal Friction** - Minimal input, defer organization

---

Generated by Memory Tool v0.1.0
"""

        readme_path.write_text(content, encoding="utf-8")
        return readme_path

    def create_claude_template(self) -> Path:
        """Create CLAUDE.md template for Claude Code integration.

        Returns:
            Path to created template file
        """
        template_path = self.memory_path / "templates" / "CLAUDE.md.template"

        content = """# For AI Agent

> **Project-specific configuration for AI coding assistants**
>
> Copy this template to your project's `CLAUDE.md` file and customize.

---

## Context Files

**Always read these files first:**
- `.claude/memory-context.md` - Current project state (run `mcontext` to update)
- `.claude/guidelines.md` - memory_tool usage guide

**For module work:**
- `.memory/docs/MODULE-ORGANIZATION.md` - Module organization principles

---

## Quick Commands

```bash
m "message"              # Record to timeline
mcontext                 # Build context for AI
ms "query"               # Search project
mcheck                   # Verify module paths
```

**Tip:** Run `mcontext` before starting AI session.

---

## Project Customization

**Add your project-specific content below:**

### Project Overview
<!-- Describe your project purpose and goals -->

### Current Status
<!-- Current phase, active work, blockers -->

### Development Workflow
<!-- Your team's workflow, branching strategy, PR process -->

### Technical Conventions
<!-- Code style, patterns, naming conventions -->

---

**Generated by Memory Tool**
"""

        template_path.write_text(content, encoding="utf-8")
        return template_path

    def _copy_docs_templates(self) -> list[Path]:
        """Copy documentation templates from templates/docs/ to .memory/docs/.

        Returns:
            List of paths to created documentation files
        """
        created_files = []

        # Source: memory_tool's templates/docs/
        source_docs_dir = Path(__file__).parent.parent / "templates" / "docs"
        # Destination: project's .memory/docs/
        dest_docs_dir = self.memory_path / "docs"

        if not source_docs_dir.exists():
            # Templates directory doesn't exist, fall back to old methods
            return created_files

        # Ensure destination directory exists
        dest_docs_dir.mkdir(parents=True, exist_ok=True)

        # Copy documentation templates (consolidated into single file)
        template_files = [
            "MODULE-ORGANIZATION.md",
        ]

        for filename in template_files:
            source_file = source_docs_dir / filename
            if source_file.exists():
                dest_file = dest_docs_dir / filename
                shutil.copy2(source_file, dest_file)
                created_files.append(dest_file)

        return created_files

    def create_module_organization_principles(self) -> Path:
        """Create MODULE-ORGANIZATION-PRINCIPLES.md documentation.

        DEPRECATED: Use _copy_docs_templates() instead.
        This method is kept for backward compatibility.

        Returns:
            Path to created documentation file
        """
        doc_path = self.memory_path / "docs" / "MODULE-ORGANIZATION-PRINCIPLES.md"

        content = """# Module Organization Principles

> Principles and guidelines for organizing modules in memory_tool

**Version:** 1.0
**Created:** {created}
**Status:** Active

---

## Core Principles

### 1. Single Responsibility Principle (SRP)

Each module should have one, and only one, reason to change.

**Good:**
```
projects/memory-tool/search-engine/
projects/memory-tool/tui-browser/
```

**Bad:**
```
projects/memory-tool/search-and-ui-and-llm/  # Too many responsibilities
```

### 2. Cohesion Over Size

Module boundaries should be drawn by **topic cohesion**, not arbitrary size limits.

- High cohesion: All parts strongly related
- Low coupling: Minimal dependencies on other modules

### 3. Lifecycle Alignment

Parts that change together should stay together.

- If Feature A and B always update together → Same module
- If Feature A updates weekly, B monthly → Separate modules

---

## When to Split a Module

### Quantitative Triggers

Split when ANY of these conditions are met:

1. **Size Threshold**
   - `current.md` > 300 lines
   - Total module files > 3000 lines
   - More than 20 decisions

2. **Complexity Threshold**
   - More than 5 distinct topics
   - More than 10 outgoing [[connections]]
   - Archive size > 5MB

3. **Activity Threshold**
   - 3+ sections updated 3+ times per week
   - More than 50 timeline entries per month referencing this module

### Qualitative Indicators

Consider splitting when:

1. **Cognitive Load Test**
   - New person needs >20 minutes to understand module
   - Module description requires >3 sentences

2. **Change Impact Test**
   - Changes frequently affect multiple unrelated parts
   - Hard to isolate changes to one area

3. **Reusability Test**
   - Need to reference only part of module frequently
   - Other projects could use subset independently

4. **Team Boundary Test**
   - Different people/teams own different parts
   - Merge conflicts common in same module

---

## When to Use Hierarchical Modules

### Use Parent/Child Structure When:

✅ **Clear containment relationship**
```
projects/memory-tool/
├── core-system/           # Parent
│   ├── timeline/         # Child
│   └── search/           # Child
```

✅ **Shared context**
- All children relate to same project/area
- Common lifecycle (start/end together)
- Natural navigation path

✅ **Progressive disclosure**
- High-level understanding at parent
- Drill down for details in children

### Use Flat Structure When:

✅ **Independent concerns**
```
projects/
├── memory-tool/
├── personal-website/
└── blog/
```

✅ **Cross-cutting relationships**
- Modules connect in graph, not tree
- Multiple parents possible

✅ **Different lifecycles**
- Modules start/end independently

---

## Module Size Guidelines

### Small Module (Recommended)
- **Size:** 100-500 lines
- **Decisions:** 1-5
- **Topics:** Single concern
- **Example:** `projects/memory-tool/cli-commands/`

### Medium Module
- **Size:** 500-1500 lines
- **Decisions:** 5-15
- **Topics:** 2-3 related concerns
- **Example:** `projects/memory-tool/search-engine/`

### Large Module (Consider Splitting)
- **Size:** 1500-3000 lines
- **Decisions:** 15-30
- **Topics:** Multiple concerns
- **Warning:** May become hard to maintain

### Too Large (Must Split)
- **Size:** >3000 lines
- **Decisions:** >30
- **Topics:** Many unrelated concerns
- **Action Required:** Break into smaller modules

---

## Naming Conventions

### Project Modules
```
projects/[project-name]/[feature-or-subsystem]/
```
Examples:
- `projects/memory-tool/core-system/`
- `projects/memory-tool/module-system/`
- `projects/website/frontend/`

### Area Modules
```
areas/[domain-or-discipline]/
```
Examples:
- `areas/python-development/`
- `areas/ai-machine-learning/`
- `areas/productivity/`

### Resource Modules
```
resources/[resource-type]/
```
Examples:
- `resources/templates/`
- `resources/tools/`
- `resources/references/`

### Archive Modules
```
archive/[YYYY-MM]/[completed-project]/
```
Examples:
- `archive/2025-11/phase-1-implementation/`

---

## Cohesion Checklist

Before finalizing module boundaries, verify:

- [ ] Can describe module purpose in 1-2 sentences
- [ ] All content relates to single theme
- [ ] Changes to one file often require changing related files (high cohesion)
- [ ] Changes rarely require modifying other modules (low coupling)
- [ ] Someone can understand module independently
- [ ] Module has clear interfaces (well-defined [[connections]])
- [ ] No "god module" containing everything

---

## Anti-Patterns to Avoid

### ❌ God Module
One module containing everything
```
memory-system/  # Contains: CLI, search, TUI, LLM, modules, decisions...
```

### ❌ Premature Splitting
Creating modules before understanding boundaries
```
projects/memory-tool/feature-a/
projects/memory-tool/feature-b/
# Later: A and B always change together → Should be one module
```

### ❌ Deep Nesting
More than 3 levels of hierarchy
```
projects/memory-tool/system/subsystem/component/subcomponent/  # Too deep!
```

### ❌ Artificial Boundaries
Splitting by arbitrary criteria (file type, date)
```
modules-created-in-november/  # Bad: Not cohesive
typescript-modules/           # Bad: Technology not topic
```

---

## Decision Framework

When deciding module structure, ask:

1. **Purpose:** What is this module's single responsibility?
2. **Scope:** What's included? What's explicitly excluded?
3. **Lifecycle:** When does it start? When is it complete?
4. **Owners:** Who maintains this? (can be same person/team)
5. **Dependencies:** What does it depend on? What depends on it?
6. **Size:** Is it the right size for its purpose?
7. **Navigation:** Can users easily find and understand it?

---

**Generated by Memory Tool**
**Last Updated:** {created}
""".format(created=datetime.now().strftime("%Y-%m-%d"))

        doc_path.write_text(content, encoding="utf-8")
        return doc_path

    def create_quick_reference(self) -> Path:
        """Create QUICK-REFERENCE-MODULE-ORGANIZATION.md documentation.

        DEPRECATED: Use _copy_docs_templates() instead.
        This method is kept for backward compatibility.

        Returns:
            Path to created documentation file
        """
        doc_path = self.memory_path / "docs" / "QUICK-REFERENCE-MODULE-ORGANIZATION.md"

        content = """# Quick Reference: Module Organization

> Quick decision guide for module organization

---

## When to Create a New Module?

### ✅ Create New Module When:

1. **Starting a new project**
   ```bash
   mmodule create projects/new-project
   ```

2. **New major feature (>500 lines expected)**
   ```bash
   mmodule create projects/main-project/new-feature
   ```

3. **Independent concern** (different topic, lifecycle, or team)

4. **Reusable component**
   ```bash
   mmodule create resources/templates/api-design
   ```

### ❌ Don't Create New Module When:

1. **Small enhancement (<100 lines)**
   → Add to existing module

2. **Tightly coupled** to existing module
   → Extend existing module

3. **Temporary experiment**
   → Use timeline or scratch space

4. **Just organizing files**
   → Use subdirectories within module

---

## When to Split an Existing Module?

### 🔴 Must Split (High Priority):
- [ ] current.md > 300 lines
- [ ] Total files > 3000 lines
- [ ] >30 decisions
- [ ] >5 unrelated topics
- [ ] Multiple people frequently conflict

### 🟡 Consider Splitting (Medium Priority):
- [ ] current.md > 200 lines
- [ ] Total files > 2000 lines
- [ ] >20 decisions
- [ ] >3 topics
- [ ] Takes >20min to understand

### 🟢 Keep As-Is (Low Priority):
- [ ] current.md < 200 lines
- [ ] Total files < 2000 lines
- [ ] <20 decisions
- [ ] Single topic
- [ ] Clear and focused

---

## Module Hierarchy vs Flat?

### Use Hierarchy (projects/parent/child) When:
```
✅ Clear containment (child IS-PART-OF parent)
✅ Shared context/project
✅ Same lifecycle
✅ Progressive disclosure needed
```

**Example:**
```
projects/memory-tool/
├── core-system/
├── search-system/
└── ui-system/
```

### Use Flat (projects/module-a, projects/module-b) When:
```
✅ Independent concerns
✅ Different lifecycles
✅ Cross-cutting relationships
✅ Multiple potential parents
```

**Example:**
```
projects/
├── memory-tool/
├── personal-blog/
└── portfolio-site/
```

---

## Naming Quick Guide

| Type | Pattern | Example |
|------|---------|---------|
| Project feature | `projects/[project]/[feature]` | `projects/memory-tool/search-system` |
| Area of interest | `areas/[domain]` | `areas/python-development` |
| Reusable resource | `resources/[type]` | `resources/api-templates` |
| Completed project | `archive/[YYYY-MM]/[name]` | `archive/2025-11/phase-1` |

---

## Quick Checklist Before Creating Module

- [ ] Can describe purpose in 1-2 sentences?
- [ ] Does it have single responsibility?
- [ ] Is it the right size (not too small, not too large)?
- [ ] Does it have clear boundaries?
- [ ] Will it have >100 lines of content?
- [ ] Is it independent enough?
- [ ] Does hierarchy make sense (if nested)?

If all ✅ → Create module
If mostly ❌ → Add to existing module or reconsider

---

## Quick Commands

```bash
# Create flat module
mmodule create projects/my-project

# Create hierarchical module
mmodule create projects/my-project/feature-a

# Check if module should split (manual check)
wc -l .memory/modules/my-module/*.md

# View module tree
mmodule tree

# View connections
mmodule graph

# Check for issues
mmodule check-links
```

---

## Decision Tree

```
Need to track something?
│
├─ Is it part of existing module?
│  ├─ Yes → Add to existing
│  └─ No ↓
│
├─ Is it >100 lines?
│  ├─ No → Use timeline
│  └─ Yes ↓
│
├─ Single topic?
│  ├─ No → Split into multiple
│  └─ Yes ↓
│
├─ Part of existing project?
│  ├─ Yes → Create child module (projects/parent/child)
│  └─ No → Create new project (projects/new-project)
│
└─ Create module!
```

---

## Red Flags

### 🚩 Module Too Large
```
Symptoms:
- Hard to navigate
- Many unrelated topics
- Frequent conflicts
- Long current.md

Action: Split by topic/feature
```

### 🚩 Too Many Small Modules
```
Symptoms:
- Lots of <50 line modules
- Frequent cross-module references
- Unclear boundaries

Action: Merge related modules
```

### 🚩 Deep Nesting (>3 levels)
```
Symptoms:
- projects/a/b/c/d/e/
- Hard to navigate
- Unclear relationships

Action: Flatten or reorganize
```

### 🚩 Unclear Purpose
```
Symptoms:
- Can't explain in 1 sentence
- "Miscellaneous" in name
- Everything goes here

Action: Split by clear criteria
```

---

## Resources

- Full principles: `.memory/docs/MODULE-ORGANIZATION-PRINCIPLES.md`
- Module commands: `mmodule --help`

---

**Generated by Memory Tool**
**Last Updated:** {created}
""".format(created=datetime.now().strftime("%Y-%m-%d"))

        doc_path.write_text(content, encoding="utf-8")
        return doc_path

    def create_claude_skills(self) -> list[Path]:
        """Copy memory_tool skills to project's .claude/skills/.

        Copies mt-publish and mt-master-module skills for KB federation workflow.
        Skills are stored inside the package at memory_tool/templates/skills/.

        Returns:
            List of paths to created skill files
        """
        created_files = []

        # Skills to copy
        skill_names = ["mt-publish", "mt-master-module"]

        # Source: memory_tool package's templates/skills/
        package_dir = Path(__file__).parent.parent  # memory_tool/
        source_base = package_dir / "templates" / "skills"

        for skill_name in skill_names:
            source_skills_dir = source_base / skill_name
            # Destination: project's .claude/skills/<skill>/
            dest_skills_dir = self.claude_path / "skills" / skill_name

            if not source_skills_dir.exists():
                # If skill doesn't exist in package, skip
                continue

            # Ensure destination directory exists
            dest_skills_dir.mkdir(parents=True, exist_ok=True)

            # Copy SKILL.md (the only required file for Claude Skills)
            source_file = source_skills_dir / "SKILL.md"
            if source_file.exists():
                dest_file = dest_skills_dir / "SKILL.md"
                shutil.copy2(source_file, dest_file)
                created_files.append(dest_file)

        return created_files

    def create_claude_guidelines(self) -> Optional[Path]:
        """Copy guidelines.md template to project's .claude/guidelines.md.

        Only creates if guidelines.md doesn't exist (preserves user customizations).

        Returns:
            Path to created guidelines.md, or None if already exists or template not found
        """
        dest_file = self.claude_path / "guidelines.md"

        # Don't overwrite existing guidelines (user may have customized)
        if dest_file.exists():
            return None

        # Source: memory_tool's templates/claude/guidelines.md
        source_file = Path(__file__).parent.parent / "templates" / "claude" / "guidelines.md"

        if not source_file.exists():
            return None

        # Ensure .claude/ directory exists
        self.claude_path.mkdir(parents=True, exist_ok=True)

        # Copy template
        shutil.copy2(source_file, dest_file)
        return dest_file

    def initialize(
        self,
        force: bool = False,
        kb_path: Optional[str] = None,
    ) -> dict:
        """Initialize .memory/ structure.

        Args:
            force: If True, reinitialize even if already exists
            kb_path: Optional path to knowledge base

        Returns:
            Dictionary with created paths

        Raises:
            AlreadyInitializedError: If already initialized and force=False
        """
        already = self.is_initialized()

        # Check if already initialized
        if already and not force:
            raise AlreadyInitializedError(
                f"A knowledge base already exists at {self.memory_path}. "
                f"Use --force to reinitialize."
            )

        # A fresh root-base init must not write over the project's own files.
        # --force deliberately does NOT override this: it is meant for
        # reinitializing a knowledge base, not for overwriting a project.
        if not already:
            collisions = self.root_base_collisions()
            if collisions:
                names = ", ".join(sorted(p.name for p in collisions))
                raise InitializationError(
                    f"Cannot use the project root as the base folder: these already "
                    f"exist and would be overwritten or merged into: {names}.\n"
                    f"Use a subfolder instead (minit --base memory), or move the "
                    f"conflicting entries aside first."
                )

        created = {
            "directories": [],
            "files": [],
        }

        # Record the base folder name so every command can find it, regardless
        # of what the folder is called (or that it is the project root).
        pointer_path = write_pointer(self.base_path, self.base_name)
        created["files"].append(pointer_path)
        created["base_name"] = self.base_name

        # Create directory structure
        structure = self.get_structure()
        for rel_path, type_ in structure.items():
            full_path = self.base_path / rel_path

            if type_ == "dir":
                full_path.mkdir(parents=True, exist_ok=True)
                created["directories"].append(full_path)
            elif type_ == "file":
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.touch()
                created["files"].append(full_path)

        # Create config.yaml
        config_path = self.create_config_yaml()
        created["files"].append(config_path)

        # Create README.md
        readme_path = self.create_readme()
        created["files"].append(readme_path)

        # Create CLAUDE.md template
        template_path = self.create_claude_template()
        created["files"].append(template_path)

        # Copy documentation templates from templates/docs/
        docs_files = self._copy_docs_templates()
        if docs_files:
            # Successfully copied from templates
            created["files"].extend(docs_files)
        else:
            # Fallback to old methods if templates don't exist
            module_org_path = self.create_module_organization_principles()
            created["files"].append(module_org_path)

            quick_ref_path = self.create_quick_reference()
            created["files"].append(quick_ref_path)

        # Create .claude/ structure with skills and guidelines
        skill_files = self.create_claude_skills()
        created["files"].extend(skill_files)

        # Create guidelines.md (only if not exists)
        guidelines_path = self.create_claude_guidelines()
        if guidelines_path:
            created["files"].append(guidelines_path)

        # Set KB path in config.yaml if requested
        if kb_path:
            self.set_kb_path(kb_path)
            created["kb_path"] = kb_path

        return created

    def update_docs(self, include_guidelines: bool = False) -> dict:
        """Update documentation templates in existing .memory/ project.

        This updates .memory/docs/ with the latest templates without
        affecting other project data (timeline, modules, etc.).

        Args:
            include_guidelines: Also update .claude/guidelines.md and skills

        Returns:
            Dictionary with updated paths

        Raises:
            InitializationError: If .memory/ doesn't exist
        """
        if not self.is_initialized():
            raise InitializationError(
                f".memory/ not found at {self.memory_path}. "
                f"Run 'minit' to initialize first."
            )

        updated = {
            "files": [],
            "skipped": [],
            "backed_up": [],
        }

        # Update documentation templates
        docs_files = self._copy_docs_templates()
        if docs_files:
            updated["files"].extend(docs_files)
        else:
            # Fallback: templates directory doesn't exist
            raise InitializationError(
                "Template files not found. Memory tool may be incorrectly installed."
            )

        # Optionally update guidelines.md and skills
        if include_guidelines:
            dest_file = self.claude_path / "guidelines.md"
            source_file = Path(__file__).parent.parent / "templates" / "claude" / "guidelines.md"

            if source_file.exists():
                # Ensure .claude/ directory exists
                self.claude_path.mkdir(parents=True, exist_ok=True)

                if dest_file.exists():
                    # Backup existing file
                    backup_path = dest_file.with_suffix(".md.backup")
                    shutil.copy2(dest_file, backup_path)
                    updated["backed_up"].append(backup_path)

                shutil.copy2(source_file, dest_file)
                updated["files"].append(dest_file)

            # Also update skills
            skill_files = self.create_claude_skills()
            updated["files"].extend(skill_files)

        return updated
