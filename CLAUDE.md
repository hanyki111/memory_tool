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

## 📦 CRITICAL: Module Organization Principles

**When creating or modifying modules, follow these principles:**

```
1. Read .memory/docs/MODULE-ORGANIZATION-PRINCIPLES.md
2. Use .memory/docs/QUICK-REFERENCE-MODULE-ORGANIZATION.md for decisions
```

**Key Rules:**
- **Split modules when:** current.md > 300 lines, >20 decisions, >3 distinct topics
- **Use hierarchy when:** Clear parent-child relationship, shared context
- **Use flat when:** Independent concerns, different lifecycles
- **Single responsibility:** Each module = one clear purpose
- **Check before creating:** Can describe in 1-2 sentences? Size >100 lines? Clear boundaries?

**Quick Decision:**
```
Small enhancement (<100 lines)  → Add to existing module
New feature (>500 lines)        → Create new module
Unrelated topic                 → Create new module
Part of existing project        → Create child module (projects/parent/child)
New project                     → Create new project (projects/new-project)
```

**Before any module operation:**
1. Check module size: `wc -l .memory/modules/[module]/*.md`
2. Review principles: See MODULE-ORGANIZATION-PRINCIPLES.md
3. Use checklist: See QUICK-REFERENCE

**You MUST follow these principles when working with modules.**

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

## 📋 Development Workflow (MANDATORY)

**ALL feature work MUST follow this workflow. No exceptions.**

### Standard Workflow Steps:

```
1. Commit & Push   → Save current state
2. Branch          → Create feature/xxx branch
3. Plan            → Write work plan (or PLAN document for large features)
4. Get Approval    → Ask user for confirmation
5. Record Start    → m "Starting feature X"
6. Implement       → Write code
7. Test            → Verify functionality
8. Complete        → Ensure all works
9. Record End      → m "Completed feature X: details"
10. Merge          → Commit, push, merge to main
```

### Detailed Steps:

#### 1. Commit & Push (현재 상태 저장)
```bash
git add -A
git commit -m "docs: Update before starting new work"
git push origin main
```

**Why:** 현재 작업 상태를 안전하게 저장

#### 2. Branch (브랜치 분기)
```bash
git checkout -b feature/descriptive-name
```

**Naming:**
- `feature/xxx` - New features
- `fix/xxx` - Bug fixes
- `refactor/xxx` - Code refactoring
- `docs/xxx` - Documentation only

**Why:** 독립적인 작업 공간 확보

#### 3. Plan (작업 계획 수립)

**For Large Features (3+ files, complex logic):**
```bash
# Create PLAN document in module directory
Write .memory/modules/memory-system/PLAN-feature-name.md
```

**For Small Features (1-2 files, simple changes):**
```
- Write brief plan in conversation
- List main steps (3-5 items)
- Identify affected files
```

**Why:** 명확한 방향 설정, 사용자와 동의 형성

#### 4. Get Approval (사용자 확인)

**CRITICAL: STOP and ask user:**
```
"다음 계획으로 진행하겠습니다:
[계획 요약]

진행해도 될까요?"
```

**Why:** 사용자 의도와 일치 확인, 불필요한 작업 방지

#### 5. Record Start (메모리 기록 - 시작)
```bash
m "Starting feature X: brief description"
# or
m "작업 시작: 기능 X 구현"
```

**Why:** Timeline에 작업 시작 기록, 컨텍스트 유지

#### 6. Implement (작업 진행)

**During Implementation:**
- Use TodoWrite tool to track progress
- Mark todos as in_progress → completed
- Keep ONE task in_progress at a time

**Code Quality:**
- Follow existing code style
- Add comments for complex logic
- Keep functions focused and testable

**Why:** 체계적 진행, 진행상황 추적

#### 7. Test (테스트)

**Required Tests:**
```bash
# Dry-run tests (if applicable)
python -m memory_tool <command> --dry-run

# Actual execution tests
python -m memory_tool <command>

# Edge cases
python -m memory_tool <command> <edge-case-input>
```

**Why:** 버그 조기 발견, 안정성 확보

#### 8. Complete (작업 완료)

**Checklist:**
- [ ] All tests pass
- [ ] No errors or warnings
- [ ] Code follows project style
- [ ] Documentation updated (if needed)
- [ ] User-facing changes noted

**Why:** 완전성 보장

#### 9. Record End (메모리 기록 - 완료)
```bash
m "Completed feature X: implementation details, key changes"
# or
m "기능 X 완료: 구현 내용, 주요 변경사항"
```

**Include:**
- What was implemented
- Key files changed
- Important decisions made

**Why:** 작업 완료 기록, 미래 참조

#### 10. Merge (커밋, 푸시, 머지)
```bash
# Commit with descriptive message
git add -A
git commit -m "feat: Add feature X

- Implementation detail 1
- Implementation detail 2
- Fixes #issue (if applicable)"

# Push feature branch
git push origin feature/xxx

# Merge to main
git checkout main
git merge feature/xxx
git push origin main

# Update timeline
git add .memory/timeline/
git add .claude/memory-context.md
git commit -m "docs: Update timeline after feature X"
git push origin main
```

**Commit Message Format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code refactoring
- `docs:` - Documentation only
- `test:` - Test additions/changes

**Why:** 깔끔한 git history, 추적 가능한 변경 이력

### Emergency Procedures:

**If user requests immediate work without workflow:**
- Politely remind: "이 작업을 위해 표준 워크플로우를 따르겠습니다"
- Follow steps 1-10 unless user explicitly overrides

**If work is already in progress:**
- Complete current workflow before starting new one
- Or: ask user if they want to abort current work

### Summary:

**Start → Plan → Approve → Record → Work → Test → Record → Merge**

**This workflow ensures:**
- ✅ Safe experimentation (branches)
- ✅ Clear direction (planning)
- ✅ User alignment (approval)
- ✅ Complete history (timeline)
- ✅ Quality assurance (testing)
- ✅ Clean git history (proper commits)

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

**Last Updated:** 2025-11-15
**Next Update:** After 문서 관리 개선 완료

**Important Notes:**
- SKILL.md follows official Claude Skills format (YAML frontmatter + Markdown)
- Skill records at natural breakpoints (after work complete), NOT during conversation
- Session end recording removed (Claude cannot act after session ends)

---

**Remember: Start by reading `.claude/guidelines.md` 🎯**
