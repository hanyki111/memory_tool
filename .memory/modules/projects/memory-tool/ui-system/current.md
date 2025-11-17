# Current Status

> **UI System - Command-Line and Terminal User Interfaces**

Last Updated: 2025-11-15

---

## Overview

User interface layers for memory_tool:
- **CLI:** Command-line interface with typer + rich
- **TUI:** Terminal UI browser with textual (4 modes)
- **Aliases:** Shell integration (batch + PowerShell)

**Status:** ✅ COMPLETE (Phases 1, 2, 7)

---

## Phase 1: Core CLI (COMPLETE)

### Command Framework ✅

**Implementation:**
- Framework: typer (Python CLI builder)
- Formatting: rich (colors, tables, syntax highlighting)
- Auto-completion: shell completion support

**Core Commands:**
- `m "message"` - Record to timeline
- `minit` - Initialize .memory/
- `ms "query"` - Search
- `mcontext` - Build Claude context
- `mtoday` - Show today's timeline
- `mweek` - Show this week's timeline
- `mstatus` - Project statistics
- `msummary` - Timeline summarization
- `marchive` - Archive decisions/content
- `mmodule` - Module management (14 actions)
- `mhooks` - Git hooks management

**Key Files:**
- `memory_tool/cli.py` (main CLI entry)
- `memory_tool/commands/*.py` (command implementations)

### Alias System ✅

**Batch Aliases (.bat files):**
- Created in user directory
- Added to PATH
- Cross-platform (Windows cmd)

**PowerShell Profile Integration:**
- Function-based aliases
- Auto-loaded on PowerShell start
- Preserves existing profile

**Commands:**
```bash
malias install                      # Install batch aliases
malias install --powershell         # Install to PowerShell profile
malias list                         # List batch alias status
malias list --powershell            # List PowerShell status
malias uninstall                    # Remove batch aliases
malias uninstall --powershell       # Remove from PowerShell
```

**Supported Aliases:**
- `m`, `minit`, `ms`, `mcontext`
- `malias`, `mtoday`, `mweek`, `mstatus`
- `msummary`, `marchive`
- `mmodule`, `mhooks` (Phase 6)

**Key Files:**
- `memory_tool/utils/alias.py`

---

## Phase 7: Enhanced TUI Browser (COMPLETE)

### Multi-Mode Interface ✅

**4 Modes:**
1. **Search Mode** - Text/semantic/hybrid search with filters
2. **Timeline Mode** - Browse daily timeline entries
3. **Modules Mode** - Hierarchical module tree
4. **Graph Mode** - Connection graph visualization

**Mode Switching:**
- Tab key: Cycle through modes
- Number keys: 1-4 for direct mode selection
- CLI: `--mode search|timeline|modules|graph`

**Key Files:**
- `memory_tool/tui/browser.py` (main TUI controller)
- `memory_tool/tui/search_mode.py`
- `memory_tool/tui/timeline_mode.py`
- `memory_tool/tui/modules_mode.py`
- `memory_tool/tui/graph_mode.py`

### Search Mode ✅

**Features:**
- Query input field
- Filter toggles (Timeline, Modules, Decisions)
- Search type selection (Text, Semantic, Hybrid)
- Results table with:
  - File path
  - Type (timeline/module/decision)
  - Date
  - Match preview
- Detail panel (shows full context on selection)

**Navigation:**
- `j`/`k` - vim-style up/down
- `Enter` - Open in detail panel
- `/` - Focus search input
- `f` - Toggle filters

### Timeline Mode ✅

**Features:**
- Date list (recent → old)
- Entry count per date
- Entry list for selected date
- Entry detail panel

**Navigation:**
- `n` - Next day (newer)
- `p` - Previous day (older)
- `j`/`k` - Navigate entries
- `Enter` - Show entry detail

**Statistics:**
- Total days
- Total entries
- Average entries per day
- Date range

### Modules Mode ✅

**Features:**
- Hierarchical tree view (expandable/collapsible)
- Module detail panel:
  - Purpose
  - Status
  - File count
  - Last modified
- Connected modules display:
  - Outgoing links
  - Incoming links (backlinks)

**Navigation:**
- `j`/`k` - Navigate tree
- `Enter` - Expand/collapse or select
- `r` - Refresh tree

**Tree Rendering:**
- Indentation shows hierarchy
- Icons for expanded/collapsed
- Color coding by status

### Graph Mode ✅

**Features:**
- Module list sorted by connection count
- Selected module's connections:
  - Outgoing (modules it links to)
  - Incoming (modules linking to it)
- Graph statistics:
  - Total modules
  - Connected modules
  - Orphaned modules (no connections)
  - Total connections

**Navigation:**
- `j`/`k` - Navigate module list
- `Enter` - Show connections
- `s` - Toggle sort (connections vs. alphabetical)

**Visualization:**
- ASCII art connection diagram
- Connection strength indicators
- Orphaned module highlighting

---

## Phase 2: Advanced CLI Features (COMPLETE)

### Search Command Enhancements ✅

**Options:**
```bash
# Search backends
--semantic                          # Vector search
--hybrid                            # Text + semantic
--text-weight 0.7                   # Hybrid text weight
--semantic-weight 0.3               # Hybrid semantic weight

# Ranking
--rank bm25                         # BM25 ranking
--boost-recent                      # Boost recent results
--decay-days 30                     # Date decay period

# Filters
--date today|yesterday|this-week    # Date filters
--date 2025-11-01..2025-11-15       # Date ranges
--type timeline|modules|decisions   # File type filters
--tag feature|bugfix                # Tag filters
--exclude-tag archived              # Exclude tags

# Formatting
--show-score                        # Show relevance scores
--context 3                         # Context lines
--summary                           # Summary statistics

# Performance
--no-cache                          # Disable result cache
--cache-ttl 7200                    # Custom cache TTL
--no-index                          # Bypass SQLite FTS5
```

### Module Commands ✅

**14 Module Actions:**
```bash
mmodule create <path>               # Create module
mmodule list                        # List all modules
mmodule tree                        # Display hierarchy
mmodule archive <name>              # Archive module
mmodule unarchive <name>            # Unarchive module
mmodule connections <module>        # Show connections
mmodule graph                       # Full graph
mmodule rebuild-graph               # Rebuild connection DB
mmodule check-links                 # Find broken links
mmodule suggest-links <module>      # Suggest connections
mmodule suggest-ai <module>         # AI suggestions
mmodule auto-tag <module>           # Generate tags
mmodule graph-snapshot              # Create version snapshot
mmodule graph-history               # Version history
mmodule graph-diff <v1> <v2>        # Compare versions
```

### Archive Command ✅

**Three Archive Modes:**
```bash
marchive --up-to 25                 # Archive decisions #1-25
marchive --keep-recent 10           # Keep last 10 decisions
marchive --phase 1-4                # Archive by phase (legacy)
```

**Features:**
- Decision parsing and extraction
- Archive directory creation
- Index file generation
- File size warnings

---

## Configuration

**config.yaml settings:**
```yaml
cli:
  auto_complete: true               # Shell completion
  color_output: true                # Rich formatting
  verbose: false                    # Verbose output

tui:
  default_mode: search              # Default TUI mode
  vim_keybindings: true             # j/k navigation
  refresh_interval: 5               # Auto-refresh (seconds)
```

---

## Dependencies

**Depends on:**
- [[projects/memory-tool/core-system]] - Timeline, modules
- [[projects/memory-tool/search-system]] - Search backends
- [[projects/memory-tool/module-system]] - Module operations
- [[projects/memory-tool/llm-integration]] - Summarization

**Depended on by:**
- None (presentation layer)

---

## Key Decisions

See [[projects/memory-tool/project-management/decisions]]:
- Decision #21: Typer for CLI framework
- Decision #22: Rich for terminal formatting
- Decision #23: Textual for TUI
- Decision #25: Alias system for convenience

---

## Metrics

**CLI:**
- Command count: 12 main commands
- Module actions: 14 actions
- Average response time: <1s for most commands

**TUI:**
- Launch time: <2s
- Mode switch: <100ms
- Search results: Display up to 1000 results
- Memory usage: ~50-100MB

**Aliases:**
- Installation time: <5s
- PowerShell profile: <1KB addition

---

## Known Issues

**TUI:**
- Large result sets (>1000) may cause lag (pagination planned)
- Terminal resize requires restart (textual limitation)

**Workarounds:**
- Use `--limit` flag for large searches
- Restart TUI after terminal resize

---

## Recent Updates (2025-11-17)

### Module Auto-Search Feature ✅

**Implementation:**
- Helper function: `_resolve_module_name()` in cli.py
- Searches all modules by name (short or full path)
- Handles ambiguous matches (shows selection list)
- Clear error messages for not found

**Updated Commands:**
- `marchive --module <name>` - Archive with module search
- `msummary --module <name>` - Summarize with module search
- `module archive <name>` - Archive module with search

**Usage:**
```bash
# Before: Full path required
marchive decisions --module projects/memory-tool/core-system

# After: Short name works
marchive decisions --module core-system
# → Resolved 'core-system' -> 'projects/memory-tool/core-system'
```

**Benefits:**
- 90% reduction in typing
- No need to remember full paths
- Works across all hierarchy levels
- Safe (ambiguous matches require confirmation)

---

## Future Enhancements

**CLI:**
- Interactive mode (REPL)
- Command history with `history` command
- Custom command plugins

**TUI:**
- Edit mode (modify entries in-place)
- Split-screen view (multiple modes simultaneously)
- Export selected results
- Customizable key bindings

See [[projects/memory-tool/project-management]] for roadmap.

---

## Notes

**Architecture:**
- CLI: Command pattern (one command = one function)
- TUI: Mode pattern (each mode is a screen)
- Aliases: Shell integration layer

**Design Principles:**
- Immediate feedback (rich progress indicators)
- Discoverable (--help for all commands)
- Composable (commands can be piped)
- Accessible (keyboard-only TUI)

**Best Practices:**
- Use CLI for automation/scripts
- Use TUI for exploration/browsing
- Use aliases for frequent commands

**Testing:**
- CLI commands tested manually
- TUI modes tested interactively
- Alias installation tested on Windows (cmd + PowerShell)
