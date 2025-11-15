# Module: projects/memory-tool/ui-system

**Created:** 2025-11-15
**Tags:** cli, tui, interface, aliases, browser

## Purpose

Command-line and terminal user interfaces: Provide intuitive, efficient ways to interact with memory_tool through CLI commands, interactive TUI browser, and convenient aliases.

## Scope

**Included:**
- **CLI Framework**: Typer-based commands with rich formatting
- **Command Aliases**: Batch/PowerShell profile integration (`m`, `ms`, `mtoday`, etc.)
- **Interactive TUI**: Textual-based browser with 4 modes (Search, Timeline, Modules, Graph)
- **Output Formatting**: Tables, colors, syntax highlighting
- **Progress Indicators**: Spinners, progress bars for long operations
- **Error Messages**: User-friendly, actionable error reporting
- **Tab Completion**: Shell completion for all commands

**TUI Modes:**
1. **Search Mode**: Query input, result filtering, detail view
2. **Timeline Mode**: Date navigation, entry browsing
3. **Modules Mode**: Tree view, module details, connections
4. **Graph Mode**: Visual connection graph, statistics

**Excluded:**
- Core data operations → [[projects/memory-tool/core-system]]
- Search algorithms → [[projects/memory-tool/search-system]]
- Module logic → [[projects/memory-tool/module-system]]
- LLM calls → [[projects/memory-tool/llm-integration]]

## Architecture

**CLI Structure:**
- `cli.py`: Main command dispatcher
- `commands/`: Individual command implementations
- `formatters/`: Output formatting utilities
- `validators/`: Input validation

**TUI Structure:**
- `browser.py`: Main TUI application
- `search_mode.py`: Search interface
- `timeline_mode.py`: Timeline browser
- `modules_mode.py`: Module tree view
- `graph_mode.py`: Graph visualization

**Alias System:**
- Batch file generation (Windows CMD)
- PowerShell profile integration
- Installation/uninstallation commands
- Status checking

**Related Decisions:**
- Decision #21: Typer for CLI
- Decision #22: Rich for formatting
- Decision #23: Textual for TUI
- Decision #25: Alias system

## Related Modules

- [[projects/memory-tool/core-system]] - Displays timeline data
- [[projects/memory-tool/search-system]] - Shows search results
- [[projects/memory-tool/module-system]] - Renders module tree/graph
- [[projects/memory-tool/llm-integration]] - Shows summaries
