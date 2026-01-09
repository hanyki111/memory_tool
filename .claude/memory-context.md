# Memory Context

**Generated:** 2026-01-08 08:32

---

## Recent Timeline

*No recent timeline entries found.*

---

## Current Plans

*No active plans found.*

---

## Module Status

- **archive/memory-system**: `./.memory\modules\archive\memory-system\current.md`
- **memory-system.backup**: `./.memory\modules\memory-system.backup\current.md`
- **projects/memory-tool**: `./.memory\modules\projects\memory-tool\current.md`
- **projects/memory-tool/core-system**: `./.memory\modules\projects\memory-tool\core-system\current.md`
- **projects/memory-tool/knowledge-graph-system**: `./.memory\modules\projects\memory-tool\knowledge-graph-system\current.md`
- **projects/memory-tool/llm-integration**: `./.memory\modules\projects\memory-tool\llm-integration\current.md`
- **projects/memory-tool/module-system**: `./.memory\modules\projects\memory-tool\module-system\current.md`
- **projects/memory-tool/project-management**: `./.memory\modules\projects\memory-tool\project-management\current.md`
- **projects/memory-tool/search-system**: `./.memory\modules\projects\memory-tool\search-system\current.md`
- **projects/memory-tool/ui-system**: `./.memory\modules\projects\memory-tool\ui-system\current.md`

---

## Module-Source Mapping

| Module | Source | Status |
|--------|--------|--------|
| archive/memory-system | *none* | ⚠️ no section |
| memory-system.backup | *none* | ⚠️ no section |
| projects/memory-tool | *none* | ⚠️ no section |
| projects/memory-tool/core-system | `memory_tool/core/timeline.py`, `memory_tool/utils/migrate_timeline.py`, `.memory/timeline/daily/YYYY-MM/DD.md`, `.memory/timeline/YYYY-MM/DD.md` | ❌ 2 missing |
| projects/memory-tool/knowledge-graph-system | *none* | ⚠️ no section |
| projects/memory-tool/llm-integration | `memory_tool/llm/base.py`, `memory_tool/llm/anthropic_provider.py`, `memory_tool/llm/ollama_provider.py` | ❌ 3 missing |
| projects/memory-tool/module-system | `memory_tool/core/module.py`, `memory_tool/core/connections.py`, `memory_tool/context/related_files.py`, `memory_tool/utils/path_checker.py` | ✅ |
| projects/memory-tool/project-management | *none* | ⚠️ no section |
| projects/memory-tool/search-system | `memory_tool/search/indexer.py`, `.memory/.search_index.db` | ❌ 2 missing |
| projects/memory-tool/ui-system | `memory_tool/cli.py`, `memory_tool/commands/*.py` | ❌ 1 missing |

### Quick Navigation

**projects/memory-tool/core-system** → Core System - Timeline, Initialization, and Basic Data Structures
- `memory_tool/core/timeline.py`
- `memory_tool/utils/migrate_timeline.py`
- `.memory/timeline/daily/YYYY-MM/DD.md`
- `.memory/timeline/YYYY-MM/DD.md`

**projects/memory-tool/llm-integration** → LLM Integration - AI-Powered Features Using Large Language Models
- `memory_tool/llm/base.py`
- `memory_tool/llm/anthropic_provider.py`
- `memory_tool/llm/ollama_provider.py`

**projects/memory-tool/module-system** → Module System - Hierarchical Modules with Wiki-Style Connections
- `memory_tool/core/module.py`
- `memory_tool/core/connections.py`
- `memory_tool/context/related_files.py`
- `memory_tool/utils/path_checker.py`

**projects/memory-tool/search-system** → Search System - Multi-Backend Search with Text, Vector, and Hybrid Capabilities
- `memory_tool/search/indexer.py`
- `.memory/.search_index.db`

**projects/memory-tool/ui-system** → UI System - Command-Line and Terminal User Interfaces
- `memory_tool/cli.py`
- `memory_tool/commands/*.py`

---

## Document Health

### 🔴 CRITICAL (>600/400 lines)

- **memory-system.backup/decisions.md**: 692 lines - ⚠️ Very large, should archive soon
  - Quick action: `marchive decisions --module memory-system.backup --interactive`
- **archive/memory-system/decisions.md**: 692 lines - ⚠️ Very large, should archive soon
  - Quick action: `marchive decisions --module archive/memory-system --interactive`
- **projects/memory-tool/module-system/current.md**: 641 lines - ⚠️ Very large, should archive soon
  - Quick action: `marchive current --module projects/memory-tool/module-system --interactive`
- **projects/memory-tool/project-management/decisions.md**: 1031 lines - ⚠️ Very large, should archive soon
  - Quick action: `marchive decisions --module projects/memory-tool/project-management --interactive`
- **projects/memory-tool/ui-system/current.md**: 403 lines - ⚠️ Very large, should archive soon
  - Quick action: `marchive current --module projects/memory-tool/ui-system --interactive`

### 🟡 WARNING (300-600/200-400 lines)

- **memory-system.backup/current.md**: 234 lines - Consider reviewing
- **archive/memory-system/current.md**: 234 lines - Consider reviewing
- **projects/memory-tool/current.md**: 337 lines - Consider reviewing
- **projects/memory-tool/core-system/current.md**: 277 lines - Consider reviewing
- **projects/memory-tool/knowledge-graph-system/decisions.md**: 347 lines - Consider archiving
- **projects/memory-tool/llm-integration/decisions.md**: 347 lines - Consider archiving
- **projects/memory-tool/llm-integration/current.md**: 372 lines - Consider reviewing
- **projects/memory-tool/project-management/current.md**: 363 lines - Consider reviewing
- **projects/memory-tool/search-system/current.md**: 262 lines - Consider reviewing

### ✅ Quick Actions

```bash
# 1. View suggestions for all modules
marchive decisions --suggest

# 2. Interactive archive (select which decisions to archive)
marchive decisions --module <module-name> --interactive

# 3. LLM-powered analysis (analyze and categorize)
msummary --module <module-name> --decisions

# 4. Check health anytime
mcontext
```

---

## Module Organization Quick Reference

**When to Split a Module:**
- `current.md` > 300 lines
- Total files > 3000 lines
- More than 20 decisions
- More than 3 distinct topics

**Decision Flow:**
```
Small enhancement (<100 lines)  → Add to existing module
New feature (>500 lines)        → Create new module
Unrelated topic                 → Create new module
Part of existing project        → Child module (projects/parent/child)
New project                     → New project (projects/new-project)
```

**Full Documentation:**
- `.memory/docs/MODULE-ORGANIZATION-PRINCIPLES.md` - Complete principles
- `.memory/docs/QUICK-REFERENCE-MODULE-ORGANIZATION.md` - Quick decisions

---

## Usage

This context file is automatically generated by `mcontext` command.
Use it to quickly understand the current state of the project.

```bash
# Update this file
python -m memory_tool context
```
