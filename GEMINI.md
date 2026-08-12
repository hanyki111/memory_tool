# For Claude Code

> **Read this file first when starting a new session.**

---

## Context Files

**Always read these files:**

1. `.claude/memory-context.md` - Current project state (auto-generated)
2. `.claude/guidelines.md` - memory_tool usage guide

**For module work:**
- `.memory/docs/MODULE-ORGANIZATION.md` - Module organization principles

---

## Project Overview

**Name:** memory_tool

**Purpose:** 시간-공간 통합 지식 체계 (Time-Space Integrated Knowledge System)

- Timeline-based capture (시간축)
- Module-based organization (공간축)
- Claude Code integration (컨텍스트 자동 전달)

**Motto:** "Capture in 0.5 seconds, organize on weekends, use for life."

---

## Quick Commands

```bash
m "message"              # Record to timeline
ms "query"               # Search
mcontext                 # Build context for AI
mcheck                   # Verify module paths
mtoday                   # Today's timeline
mweek                    # This week's timeline
```

---

## Dogfooding Principle

**This project uses its own tools:**

- **Timeline:** Use `m` command (don't edit files directly)
- **Modules:** Use Edit tool for `current.md`, `decisions.md`
- **Context:** Run `mcontext` before AI sessions

---

## Development Workflow

```
1. Commit & Push   → Save current state
2. Branch          → git checkout -b feature/xxx
3. Plan            → Write plan, get user approval
4. Record Start    → m "Starting feature X"
5. Implement       → Write code
6. Test            → Verify functionality
7. Record End      → m "Completed..." + Update modules
8. Merge           → Commit, push, merge to main
```

**Key Points:**
- Always get user approval before implementing
- Record timeline entries with `m` command
- Update module `current.md` and `decisions.md` after completion

---

## Thinking Principles

- 정직한 사고 (Honest thinking)
- 심층 사고 (Deep thinking)
- 비판적 검증 (Critical verification)
- 제3의 길 탐색 (Third way exploration)
- 악마의 옹호자 (Devil's advocate)

---

## Module Structure

```
.memory/modules/projects/memory-tool/
├── core-system/         # Timeline, initialization
├── search-system/       # Text, vector search
├── module-system/       # Modules, wiki links
├── ui-system/           # CLI, TUI
├── llm-integration/     # LLM features
└── project-management/  # Architecture, decisions
```

---

**Remember:** Run `mcontext` to get current project state before starting work.
