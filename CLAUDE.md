# For Claude Code 🤖

> **Read this file first when starting a new session.**

---

## ⚠️ IMPORTANT: Read Guidelines & Context First

**Before doing anything, read these files:**

```
1. Read .claude/guidelines.md
2. Read .claude/memory-context.md (if exists)
```

**Guidelines** define how Claude Code should approach problems in this project:
- 정직한 사고 (Honest thinking)
- 심층 사고 (Deep thinking)
- 비판적 검증 (Critical verification)
- 제3의 길 탐색 (Third way exploration)
- 악마의 옹호자 (Devil's advocate)

**Memory Context** provides automatically generated context from:
- Recent timeline entries (what's been happening)
- Current module states (what's active)
- Key decisions and concepts (what matters)

**You MUST follow these principles and use this context in all work on this project.**

---

## 🛠️ CRITICAL: Use This Project's Tools (Dogfooding)

**This project IS a tool for knowledge capture. Claude MUST use it while working on it.**

### When Working on .memory/:

**DO (Use project tools):**
```bash
# Record timeline
m "Completed feature X"
m "Fixed bug Y"

# Search past work
ms "how did we implement Z"

# Update context
mcontext

# View timeline
mtoday
mweek
```

**DON'T (Manual file edits):**
```bash
# ❌ Don't edit Timeline directly
Edit .memory/timeline/2025-11/14.md

# ❌ Don't use Read + manual tracking
Read timeline, manually track changes
```

### Why This Matters:

1. **Dogfooding** - This project practices what it preaches
2. **Testing** - Every use validates the tool works
3. **Real feedback** - Discover usability issues immediately
4. **Consistency** - Commands ensure proper format

### Exceptions (When to use Edit):

- `decisions.md` updates (decision documentation)
- `current.md` updates (status tracking)
- `module.md`, `interface.md` (design docs)
- Bug fixes to the tool itself

**Rule of thumb:** If it's a timeline entry, use `m`. If it's structured documentation, use Edit.

---

## 🎯 Project Overview

**Name:** memory_tool

**Purpose:** 시간-공간 통합 지식 체계 (Time-Space Integrated Knowledge System)
- Timeline-based capture (시간축: 0.5초 포착)
- Module-based organization (공간축: 구조화)
- Claude Code integration (컨텍스트 자동 전달)

**Goal:** Make knowledge capture frictionless and context always available.

---

## 📍 Current Status

**Phase:** 5 Revised (Practical Improvements)

**Stage:** Phase 1-4 COMPLETE, Phase 5 Revised - Focus on Stability & Usability ✅

**Completed:**
- ✅ Design document complete
- ✅ .memory/ structure created
- ✅ memory-system module defined
- ✅ Python CLI plan established
- ✅ .claude/guidelines.md created
- ✅ This file (CLAUDE.md) created
- ✅ Meta Trap diagnosed and resolved (2025-11-14)
- ✅ Python project structure (pyproject.toml, packages) (2025-11-14)
- ✅ CLI framework with typer + rich (2025-11-14)
- ✅ **m command fully implemented** (2025-11-14) ⭐
- ✅ **minit command fully implemented** (2025-11-14) ⭐
- ✅ **ms command fully implemented** (2025-11-14) ⭐
- ✅ **mcontext command fully implemented** (2025-11-14) ⭐
- ✅ **malias command fully implemented** (2025-11-14) ⭐⭐
- ✅ **mtoday, mweek, mstatus bonus commands** (2025-11-14) ⭐
- ✅ **config.yaml advanced features** (2025-11-14) ⭐⭐
- ✅ **README.md complete rewrite** (2025-11-14) ⭐
- ✅ **Claude Skill development** (2025-11-14) ⭐⭐⭐

**Phase 1: COMPLETE** 🎉🎉🎉
- 8 commands operational
- Alias system + PowerShell profile support
- auto_update + config validation
- Claude Skill (rule-based automation)
- Full dogfooding + README

**Phase 2: COMPLETE** 🎉🎉🎉
- ✅ Advanced search features (날짜 필터, exclude patterns, 파일 크기 제한)
- ✅ msort command (Timeline 시간순 재정렬)
- ✅ Module management commands (create/list/archive/unarchive)

**Phase 3: COMPLETE** 🎉🎉🎉
- ✅ Vector search with semantic embeddings (sentence-transformers)
- ✅ --semantic flag for ms command
- ✅ Embeddings caching for performance

**Phase 4: COMPLETE** 🎉
- ✅ LLM integration (Anthropic API + Ollama)
- ✅ Timeline summarization (msummary command)
- ✅ Module summarization
- ✅ Conversation summarization infrastructure
- ✅ Ollama support (local, free, offline)

**Phase 5 Revised: Practical Improvements** 🎯
- ✅ MCP Server 비판적 검토 및 우선순위 재조정
- 🎯 **문서 관리 개선** (최우선, 진행 중)
- ⏳ SQLite 인덱싱 (검색 속도 개선)
- ⏳ 검색 개선, 자동 요약 고도화, 성능 최적화
- ⏳ 테스트 커버리지, 사용성 개선

**MCP Server:** 우선순위 최하위로 이동 (실사용 검증 후 재평가)

---

## 🚀 Immediate Next Actions

**Phase 5 Revised: Practical Improvements** 🎯

**Current Focus (최우선):**
1. **문서 관리 개선** 🎯
   - 문제: current.md, decisions.md가 길어짐 (1250+ 줄)
   - 과제: 아카이브, 요약, 분할 전략 고안
   - 실사용 시 발견된 첫 번째 문제

**Phase 5 Revised Roadmap:**
1. ✅ MCP 서버 비판적 검토 및 우선순위 재조정
2. 🎯 **문서 관리 개선** (진행 중)
3. ⏳ SQLite 인덱싱 (검색 속도 10-100배)
4. ⏳ 검색 개선 (하이브리드, 랭킹)
5. ⏳ 자동 요약 고도화 (맥락, 주제 분류)
6. ⏳ 성능 최적화 (벡터 캐싱, 대용량)
7. ⏳ 테스트 커버리지 (pytest, 안정성)
8. ⏳ 사용성 개선 (GUI/TUI, 플래너)

**Decision Rationale (결정 #24):**
- MCP 서버는 Skill 대비 실질적 개선 제한적
- 조기 최적화 방지 ("Capture first, optimize later")
- 안정성 > 기능, 실용성 > 완결성
- 실사용 검증 후 MCP 필요성 재평가

**Next Step:**
- 문서 관리 전략 토론 및 구현

---

## 📚 Detailed Information

**Design Documents:**
- `시간-공간-통합-지식-체계-v2.0.md` - Full system design (2476 lines)
- `.claude/guidelines.md` - Thinking principles ⭐

**Auto-Generated Context:**
- `.claude/memory-context.md` - **Current session context** (auto-generated by `mcontext`) ⭐⭐
  - Generated from: recent timeline + active modules + key decisions
  - Use this for understanding current project state
  - Regenerate with: `mcontext` command

**Current State (Manual):**
- `.memory/modules/memory-system/current.md` - Detailed status
- `.memory/timeline/2025-11/14.md` - Today's timeline
- `.memory/timeline/2025-11/13.md` - Yesterday's timeline
- `.memory/modules/memory-system/decisions.md` - Key decisions (22 decisions)

**Technical Plans:**
- `.memory/concepts/python-cli-development-plan.md` - 14-day roadmap
- `.memory/modules/memory-system/interface.md` - CLI command design
- `.memory/modules/memory-system/dependencies.md` - Phase dependencies

---

## 🧭 Philosophy (Quick Reminder)

**5 Core Principles:**
1. **Time First** - Capture first, organize later
2. **Lossless** - Record everything, lose nothing
3. **Minimal Friction** - Minimal input, defer organization
4. **Loose Coupling** - Isolate projects, share knowledge
5. **Local First** - Default local, explicit expansion

**Motto:** "Capture in 0.5 seconds, organize on weekends, use for life."

---

## 🔄 Meta Note

**This project practices what it preaches:**
- Development is recorded in `.memory/timeline/`
- Decisions are documented in `.memory/modules/memory-system/decisions.md`
- This is dogfooding - the project is its own use case

---

## ⚡ Quick Command Reference

**Core Commands (Phase 1):**
```bash
m "message"                  # Record to timeline ✅
minit                        # Initialize .memory/ ✅
ms "query"                   # Search local ✅
ms --with-kb "query"         # Search local + KB ✅
ms --all "query"             # Search all projects ✅
mcontext                     # Build Claude context ✅ ⭐
malias install               # Install command aliases (batch) ✅
malias install --powershell  # Install to PowerShell profile ✅ ⭐
malias list                  # List alias status ✅
malias list --powershell     # List PowerShell profile status ✅
malias uninstall             # Remove aliases ✅
```

**Bonus Commands:**
```bash
mtoday                       # Show today's timeline ✅
mweek                        # Show this week's timeline ✅
mstatus                      # Show project statistics ✅
```

**Important:** Run `mcontext` to generate `.claude/memory-context.md` before starting Claude Code session!

**Planned (Phase 2):**
```bash
msort                        # Reorder timeline entries by time
# + Claude Skill integration
# + config.yaml advanced features
```

---

**Last Updated:** 2025-11-14 23:45
**Next Update:** After 문서 관리 개선 완료

**Important Notes:**
- SKILL.md follows official Claude Skills format (YAML frontmatter + Markdown)
- Skill records at natural breakpoints (after work complete), NOT during conversation
- Session end recording removed (Claude cannot act after session ends)

---

**Remember: Start by reading `.claude/guidelines.md` 🎯**
