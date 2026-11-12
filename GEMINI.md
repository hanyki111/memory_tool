# For Claude Code

> **Read this file first when starting a new session.**

---

## Memory Tool

- At the start of a session, read `.claude/memory-context.md`. If it is missing or stale, run `mcontext`.
- Record to the timeline only with `m`. Never create or edit timeline files by hand.
- When to record: at the start and end of each feature (see Development Workflow), and for decisions (`m "Decision: ..."`).
- Before answering a question about past work, search with `ms`. Do not guess.
- The knowledge base folder is not always `.memory/`. Run `mbase show` instead of assuming a path.

How to do each of these: the `mt-record` skill. Writing documents: `mt-write`
(rules in `.memory/docs/MODULE-ORGANIZATION.md`). Publishing: `mt-publish`.

---

## Project Overview

**Name:** memory_tool

**Purpose:** 시간-공간 통합 지식 체계 (Time-Space Integrated Knowledge System)

- Timeline-based capture (시간축)
- Module-based organization (공간축)
- Claude Code integration (컨텍스트 자동 전달)

**Motto:** "Capture in 0.5 seconds, organize on weekends, use for life."

---

## Dogfooding Principle

**This project uses its own tools:**

- **Timeline:** Use `m` command (don't edit files directly)
- **Small decisions:** Record in the timeline (`m "Decision: ..."`)
- **Documents:** Use Edit tool, for what someone will look up or need explained later. See `mmodule guide`
- **Resuming work:** Read the recent timeline and `git log`. Read Goal Loop as well if it is available; it is a separate program and may be absent

There is no status document to maintain.

---

## Development Workflow

```
1. Commit & Push   → Save current state
2. Branch          → git checkout -b feature/xxx
3. Plan            → Write plan, get user approval
4. Record Start    → m "Starting feature X"
5. Implement       → Write code
6. Test            → Verify functionality
7. Record End      → m "Completed..." + Update affected documents
8. Merge           → Commit, push, merge to main; tag a version bump
```

**Key Points:**
- Always get user approval before implementing
- Record timeline entries with `m` command
- After completion, update the documents the work made wrong. Create a new one only if it will be looked up again
- A merge that raises a version gets an annotated tag: `vX.Y.Z` (memory_tool, on the merge commit) or
  `android-vX.Y.Z` (the app, on the commit that set `versionName`, which the tested APK was built from)

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
.memory/modules/memory-tool/
├── core-system/             # Timeline, initialization
├── search-system/           # Text, vector search
├── module-system/           # Modules, wiki links
├── knowledge-graph-system/  # Connections
├── ui-system/               # CLI, TUI
├── llm-integration/         # LLM features
└── project-management/      # Architecture, decisions
```

---

**Skills are templates:** edit `memory_tool/templates/skills/`, then run
`minit --update-all` to refresh `.claude/skills/` and `.agents/skills/`. A test
fails when the copies drift.
