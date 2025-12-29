# Memory Tool Documentation

Welcome to your memory_tool project! This directory contains essential documentation for organizing your knowledge.

---

## Quick Start

**Core Concept:** memory_tool uses two axes:
- **Time Axis:** `.memory/timeline/` - Capture thoughts instantly (0.5 seconds)
- **Space Axis:** `.memory/modules/` - Organize into structured modules

**Essential Commands:**
```bash
# Record to timeline (instant capture)
m "Your thought, decision, or progress"

# Search everything
ms "search query"

# View today's entries
mtoday

# Build Claude Code context
mcontext
```

---

## Command Reference

### Core Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `m "message"` | `record` | Record to timeline |
| `ms "query"` | `search` | Search timeline and modules |
| `mtoday` | `today` | Show today's timeline |
| `mweek` | `week` | Show this week's timeline |
| `mstatus` | `status` | Show project statistics |

### Module Management

| Command | Description |
|---------|-------------|
| `mmodule create <path>` | Create new module |
| `mmodule list` | List all modules |
| `mmodule tree` | Display hierarchy tree |
| `mmodule archive <name>` | Archive module |
| `mmodule unarchive <name>` | Restore archived module |
| `mmodule connections <name>` | Show module connections |
| `mmodule graph` | Show full connection graph |
| `mmodule check-links` | Find broken wiki links |

### Context & Documentation

| Command | Description |
|---------|-------------|
| `mcontext` | Build Claude Code context |
| `mcontext --structure` | Include module-source mapping |
| `mcheck` | Validate Related Files paths |
| `mcheck --module <name>` | Check specific module |
| `marchive decisions` | Archive old decisions |
| `marchive --suggest` | Get archive suggestions |

### Search & Index

| Command | Description |
|---------|-------------|
| `ms "query"` | Basic text search |
| `ms --semantic "query"` | Semantic (AI) search |
| `ms --date today "query"` | Filter by date |
| `ms --type timeline "query"` | Filter by type |
| `mindex` | Rebuild search index |
| `mindex --optimize` | Optimize index |

### LLM Integration

| Command | Description |
|---------|-------------|
| `msummary` | Summarize today's timeline |
| `msummary --date this-week` | Summarize week |
| `msummary --module <name>` | Summarize module |
| `msummary --provider ollama` | Use local LLM |

### Planning & Review

| Command | Description |
|---------|-------------|
| `mplan daily` | Create/edit daily plan |
| `mplan weekly` | Create/edit weekly plan |
| `mreview weekly` | Create weekly review |
| `mreview monthly` | Create monthly review |

### Utilities

| Command | Description |
|---------|-------------|
| `malias install` | Install command aliases |
| `malias install --powershell` | Install to PowerShell profile |
| `msort` | Sort timeline entries by time |
| `mbrowse` | Interactive TUI browser |
| `mtutorial` | Interactive tutorial |
| `mcompletion` | Shell completion setup |

---

## Related Files Section

**Purpose:** Link modules to source code for navigation and validation.

**Add to top of your module's `current.md`:**

```markdown
## 📂 Related Files

- **Source:** `src/my-feature/`
- **Tests:** `tests/my-feature/`
- **Docs:** `docs/my-feature.md`
- **Other:** `scripts/deploy.sh`
```

**Validate paths:**
```bash
mcheck                      # Check all modules
mcheck --module my-module   # Check specific module
```

**Include in context:**
```bash
mcontext --structure        # Adds module-source mapping to context
```

---

## Module Organization

### When to Create a Module

- New project or major feature (>500 lines expected)
- Independent concern (different topic/lifecycle)
- Reusable component

### When to Split a Module

- `current.md` > 300 lines
- More than 20 decisions
- More than 3 distinct topics

### Quick Decision Flow

```
Small enhancement (<100 lines)  → Add to existing module
New feature (>500 lines)        → Create new module
Unrelated topic                 → Create new module
Part of existing project        → Child module (projects/parent/child)
New project                     → New project (projects/new-project)
```

### Module Structure

```
.memory/modules/
├── projects/
│   └── my-project/
│       ├── current.md       # Current status (required)
│       ├── decisions.md     # Key decisions
│       ├── interface.md     # API/interface docs
│       └── feature-a/       # Child module
│           └── current.md
└── archive/                 # Archived modules
```

---

## Wiki-Style Connections

Link modules together using `[[module-name]]` syntax:

```markdown
See [[projects/my-project/auth-system]] for authentication details.

Related:
- [[projects/my-project/database]] - Data layer
- [[concepts/security-patterns]] - Security guidelines
```

**Check connections:**
```bash
mmodule connections my-module   # Show incoming/outgoing links
mmodule graph                   # Full connection graph
mmodule check-links             # Find broken links
```

---

## Workflows

### Daily Workflow

```bash
# Morning: Check plans
mplan daily
mtoday

# During work: Capture frequently
m "Started working on feature X"
m "Decision: Use approach A because..."
m "Completed: Feature X implementation"

# End of day: Update context
mcontext
```

### Weekly Review

```bash
# Review the week
mweek
mreview weekly

# Summarize with AI
msummary --date this-week

# Check module health
mcheck
marchive --suggest
```

### Starting New Feature

```bash
# Create module
mmodule create projects/my-project/new-feature

# Add Related Files section to current.md
# Edit .memory/modules/projects/my-project/new-feature/current.md

# Record start
m "Starting new-feature implementation"
```

---

## Best Practices

### Timeline Recording
- **Capture first, organize later** (0.5-second principle)
- Record everything, lose nothing
- Use `m "message"` frequently throughout the day

### Module Organization
- Single responsibility per module
- Clear parent-child hierarchy
- Use `[[connections]]` between related modules
- Add Related Files section for source code navigation

### Documentation Maintenance
- Keep `current.md` under 300 lines
- Archive old decisions with `marchive`
- Run `mcheck` regularly to validate paths
- Use `mcontext --structure` for LLM context

---

## Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | This quick start guide |
| `MODULE-ORGANIZATION-PRINCIPLES.md` | Complete module organization principles |
| `QUICK-REFERENCE-MODULE-ORGANIZATION.md` | Quick decision guide |

---

## Getting Help

```bash
# General help
python -m memory_tool --help

# Command-specific help
mmodule --help
ms --help
mcontext --help

# Interactive tutorial
mtutorial
```

---

**Philosophy:** "Capture in 0.5 seconds, organize on weekends, use for life."

**Version:** 2.0 (Updated: 2025-12)
