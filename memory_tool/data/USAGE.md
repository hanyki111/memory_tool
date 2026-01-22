# Memory Tool - Complete Usage Guide

> This document provides comprehensive documentation for all Memory Tool features.
> Used by `mask` command to answer questions about Memory Tool usage.

---

## Quick Start

```bash
minit                    # Initialize in current directory
m "First entry"          # Record to timeline
mtoday                   # View today's entries
ms "keyword"             # Search
mhelp                    # Show all commands
```

---

## 1. Timeline Recording (m / record)

The most frequently used command. Records timestamped entries to your timeline.

### Basic Usage
```bash
m "Fixed login bug in auth.py"
m "Decision: Using PostgreSQL for the database"
m "Started working on feature X"
```

### With Tags

Two ways to add tags:

**1. Inline tags (recommended)** - add #tags at end of message:
```bash
m "Fixed auth issue #bug #auth #urgent"
m "Meeting notes #meeting #team"
```

**2. --tags option** - comma-separated:
```bash
m "Fixed auth issue" --tags bug,auth,urgent
```

**Combined** - both methods can be used together:
```bash
m "Fixed bug #critical" --tags sprint-1,backend
# Result: #critical #sprint-1 #backend
```

Tags are stored as `#tag1 #tag2` at the end of the entry.
Search with tags: `ms "bug" --tag auth`

### Other Options
```bash
m "Past entry" --date 2026-01-20              # Specific date
m "Timed entry" --time 14:30                  # Specific time
m "Old entry" --date 2025-01-01 --force       # Skip old date warning
```

### Timeline File Structure
```
.memory/timeline/daily/
  2026-01/
    20.md   # Contains entries for Jan 20, 2026
    21.md
  2026-02/
    01.md
```

Entry format: `- HH:MM | Message here #tag1 #tag2`

---

## 2. Search (ms / search)

Search through timeline, modules, and plans.

### Basic Search
```bash
ms "bug fix"                     # Keyword search
ms "authentication"              # Find all related entries
```

### Search Modes
```bash
ms "query" --semantic            # Semantic (meaning-based) search
ms "query" --hybrid              # Keyword + semantic combined (recommended)
ms "query" --boost-recent        # Prioritize recent results
```

### Filtering
```bash
ms "query" --date today          # Today only
ms "query" --date this-week      # This week
ms "query" --date last-7-days    # Last 7 days
ms "query" --type timeline       # Timeline only
ms "query" --type modules        # Modules only
ms "query" --tag bug             # Filter by tag
ms "query" --module myproject    # Specific module only
```

### Advanced Options
```bash
ms "query" --max-results 20      # Limit results
ms "query" --show-score          # Show relevance scores
ms "query" --summary             # AI-generated summary of results
```

---

## 3. Timeline Views

### Daily Views
```bash
mtoday                           # Today's entries
mtoday --yesterday               # Yesterday's entries
```

### Period Views
```bash
mweek                            # This week (Mon-today)
mmonth                           # This month
mdays 7                          # Last 7 days
mdays 30                         # Last 30 days
```

### Sorting
```bash
msort                            # Sort today's entries by time
msort --date 2026-01-20          # Sort specific date
msort --all                      # Sort all timeline files
```

---

## 4. Modules (mmodule)

Modules organize knowledge spatially. Each module is a folder with standardized files.

### Module Structure
```
.memory/modules/
  projects/
    my-project/
      module.md       # Metadata (name, description, tags)
      current.md      # Current state, ongoing work
      decisions.md    # Important decisions & rationale
      archive/        # Historical records
```

### Commands
```bash
mmodule list                     # List all modules
mmodule show myproject           # Show module details
mmodule create newproject        # Create new module
mmodule create proj --tags dev,web  # Create with tags
mmodule edit myproject           # Edit module files
```

### Wiki Links
Connect modules using `[[double brackets]]`:

```markdown
# In current.md
See [[auth-system]] for authentication details.
Related to [[projects/website]].
```

Validate links: `mcheck`

---

## 5. Plans (mplan)

Manage daily and weekly plans with task tracking.

### Daily Plans
```bash
mplan daily                      # Show/create today's plan
mplan daily add "Write docs"     # Add task
mplan daily done 1               # Complete task by index
mplan daily done "Write"         # Complete by text match
mplan daily yesterday            # View yesterday's plan
mplan daily carryover            # Carry incomplete tasks to today
```

### Weekly Plans
```bash
mplan weekly                     # Show/create this week's plan
mplan weekly add "Ship feature"  # Add weekly goal
mplan weekly done 1              # Complete goal
mplan weekly lastweek            # View last week's plan
```

### Plan File Location
```
.memory/plans/
  daily/
    2026-01-20.md
  weekly/
    2026-W04.md
```

---

## 6. AI Features (mask / ask)

Ask questions about your memory using AI.

### Basic Questions
```bash
mask "What did I work on yesterday?"
mask "Summarize decisions about the database"
mask "What modules are related to authentication?"
```

### Options
```bash
mask --verbose "query"           # Show agent reasoning
mask --simple "query"            # Use simple keyword search (faster)
mask --provider ollama "query"   # Specify LLM provider
```

### Available Tools (for AI agent)
- `get_timeline`: Retrieve timeline for date range
- `search`: Search memory content
- `get_plan`: Get daily/weekly plan
- `get_module`: Get module content
- `list_modules`: List all modules
- `get_help`: Get command help
- `get_config_guide`: Get config.yaml guide

---

## 7. Summarization (msummary)

Generate AI summaries of your content.

```bash
msummary                         # Summarize today
msummary --week                  # Summarize this week
msummary --module myproject      # Summarize module
msummary --days 7                # Summarize last 7 days
```

---

## 8. Context Generation (mcontext)

Generate context file for Claude Code integration.

```bash
mcontext                         # Generate .claude/memory-context.md
mcontext --days 7                # Include last 7 days
```

The generated file includes:
- Recent timeline entries
- Active plans
- Module status
- Recent decisions

---

## 9. Configuration (mconfig)

Manage settings in `.memory/config.yaml`.

### Commands
```bash
mconfig list                     # Show all settings
mconfig get help.language        # Get specific setting
mconfig set help.language ko     # Change setting
```

### Key Settings

```yaml
# Help language
help:
  language: en                   # en or ko

# LLM provider
llm:
  provider: ollama               # ollama, claude-cli, gemini-cli
  ollama_model: qwen3-vl:8b
  anthropic_model: claude-3-5-sonnet-20241022

# Timeline
timeline:
  auto_record: false
  granularity: medium            # low, medium, high
  warn_old_days: 365

# Search
search:
  default_scope: local
  include_archived: false

# Context auto-update
context:
  auto_update: true
  recent_days: 3
```

---

## 10. Notion Integration

Sync with Notion for cloud backup and access.

### Setup
1. Get Notion API key from https://www.notion.so/my-integrations
2. Configure in config.yaml:
   ```yaml
   notion:
     api_key: secret_xxx
     sync:
       enabled: true
       timeline:
         enabled: true
         root_page_id: <page_id>
   ```

### Commands
```bash
nm "Message"                     # Record to Notion
ns "query"                       # Search Notion
nt                               # Today's Notion entries
nw                               # This week's Notion entries
nsync                            # Sync all
nsync --module                   # Sync modules only
nsync --timeline                 # Sync timeline only
nwatch                           # Watch and auto-sync
nwatch -b                        # Bidirectional sync
```

---

## 11. System Commands

### Help
```bash
mhelp                            # Command list
mhelp record                     # Specific command help
mhelp --guide                    # Advanced features guide
mhelp --set-lang ko              # Set help language
```

### Aliases
```bash
malias list                      # Show all aliases
malias install                   # Install to system
malias install --bash            # Install to bash profile
```

### Shell Completion
```bash
mcompletion status               # Check status
mcompletion install bash         # Install for bash
mcompletion install zsh          # Install for zsh
```

### Status
```bash
mstatus                          # Show memory statistics
mcheck                           # Validate wiki links
```

---

## 12. Tags System

Tags help categorize and filter entries.

### Adding Tags
```bash
# Timeline entries
m "Fixed bug" --tags bug,auth

# Module creation
mmodule create myproject --tags dev,web
```

### Tag Format
- Tags are stored as `#tag1 #tag2` at end of timeline entries
- Module tags in `module.md` header

### Searching by Tag
```bash
ms "bug" --tag auth              # Filter search by tag
```

### Best Practices
- Use lowercase, hyphen-separated: `feature-request`, `bug-fix`
- Keep tags consistent across entries
- Limit to 3-5 tags per entry

---

## 13. Archive System

Keep modules clean by archiving old content.

```bash
marchive decisions               # Archive old decisions
marchive --module myproject      # Archive specific module
marchive --interactive           # Interactive selection
marchive --suggest               # Show archiving suggestions
```

---

## 14. Initialization

Set up Memory Tool in a new project.

```bash
minit                            # Initialize .memory/ structure
minit --force                    # Reinitialize (overwrites)
minit --update-docs              # Update docs templates only
```

Creates:
- `.memory/` directory with timeline, modules, plans, docs
- `.claude/` directory for Claude Code integration
- `config.yaml` with default settings

---

## Command Reference

| Command | Alias | Description |
|---------|-------|-------------|
| `m` | `record` | Record to timeline |
| `ms` | `search` | Search memory |
| `mtoday` | `today` | Today's timeline |
| `mweek` | `week` | This week's timeline |
| `mmonth` | `month` | This month's timeline |
| `mdays` | `days` | Last N days |
| `msort` | `sort` | Sort timeline |
| `mplan` | `plan` | Manage plans |
| `mmodule` | `module` | Manage modules |
| `marchive` | `archive` | Archive content |
| `mcontext` | `context` | Generate context |
| `mask` | `ask` | AI Q&A |
| `msummary` | `summary` | AI summary |
| `mhelp` | `help` | Show help |
| `mconfig` | `config` | Manage config |
| `minit` | `init` | Initialize |
| `mstatus` | `status` | Show stats |
| `mcheck` | `check` | Validate links |

---

## Korean Aliases

| Korean | Command |
|--------|---------|
| `기` | `m` (record) |
| `검` | `ms` (search) |
| `질문` | `mask` (ask) |
| `오늘` | `mtoday` |
| `주간` | `mweek` |
| `월간` | `mmonth` |

---

*Last updated: 2026-01-22*
