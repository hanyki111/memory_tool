# Module: projects/memory-tool/core-system

**Created:** 2025-11-15
**Tags:** timeline, initialization, core-infrastructure

## Purpose

Core data structures and infrastructure for memory_tool: Timeline storage, initialization, and basic entry management. This is the stable foundation that other systems depend on.

## Scope

**Included:**
- Timeline entry creation and storage (`.memory/timeline/YYYY-MM/DD.md`)
- Project initialization (`minit` command, `record` command)
- Basic timestamp and formatting utilities
- File structure management
- Date-based organization (ISO format: YYYY-MM/DD)
- Append-only timeline operations

**Excluded:**
- Search functionality → [[projects/memory-tool/search-system]]
- User interfaces → [[projects/memory-tool/ui-system]]
- Module management → [[projects/memory-tool/module-system]]
- LLM features → [[projects/memory-tool/llm-integration]]

## Architecture

**Design Principles:**
- **Stability first**: Core foundation changes infrequently
- **High reliability**: Data integrity is critical
- **Simple interface**: Append-only operations, minimal complexity
- **File-based**: Plain text markdown, human-readable
- **Time-first**: Capture in 0.5 seconds, organize later

**Key Components:**
- `timeline.py`: Timeline entry management
- `init.py`: Project initialization
- `timestamp.py`: Time formatting utilities
- File I/O: Safe write operations with atomic guarantees

**Related Decisions:**
- Decision #1: Timeline-first architecture
- Decision #2: 0.5-second capture principle
- Decision #3: Markdown file format
- Decision #4: ISO date structure

## Related Modules

- [[projects/memory-tool/search-system]] - Searches timeline data
- [[projects/memory-tool/ui-system]] - Displays timeline entries
- [[projects/memory-tool/llm-integration]] - Summarizes timeline
- [[projects/memory-tool/module-system]] - Manages module structure
