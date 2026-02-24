# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### ✨ Added
- **Primary-Secondary Multi-Backend Notion Sync** - 다중 Notion 워크스페이스 동기화 지원
  - Primary 백엔드: 기존과 동일한 양방향 sync (Local ↔ Notion A)
  - Secondary 백엔드: push-only 미러 (Local → Notion B, C, ...)
  - `additional-backends` config 섹션으로 추가 백엔드 설정
  - `nsync --backend <name>`: 특정 백엔드만 동기화
  - `nsync --secondary-only`: secondary 백엔드만 push
  - `nwatch --no-secondary`: secondary push 비활성화
  - 백엔드별 독립 state/cache 파일 (`notion_sync_state_{name}.json`)
  - Secondary 실패 시 primary에 영향 없음 (실패 격리)
  - 기존 단일 백엔드 config 100% 하위 호환
- **Plan-Timeline Integration (Phase 4)** - Plan 완료 시 Timeline 자동 기록
  - `mplan daily/weekly/monthly done` 실행 시 Timeline에 자동 기록
  - 양방향 참조 (Plan ↔ Timeline)
  - 작업 유형 표시 (Daily Plan / Weekly Plan / Monthly Plan)
- **mcontext improvements** - Current Plans 섹션 추가
  - 오늘/이번 주/이번 달 Plan 진행률 표시
  - Pending Tasks/Goals 표시 (최대 3개)
- **mstatus improvements** - Plans 통계 추가
  - Daily/Weekly/Monthly Plans 수 표시
  - 오늘/이번 주 진행률 표시

### 📝 Changed
- Timeline/Review/Plan 시스템 전체 완료 (Phase 1-5)
- README.md 및 design 문서 최종 업데이트

## [1.0.0-alpha] - 2025-11-15

### 🎉 Initial Alpha Release

**Core Philosophy:**
"0.5초로 포착하고, 주말에 정리하며, 평생 활용한다."

### ✨ Features

#### Timeline System (시간축)
- **m** - Record messages to timeline in 0.5 seconds
- **mtoday** - View today's timeline
- **mweek** - View this week's timeline
- **msort** - Sort timeline entries by time

#### Module System (공간축)
- **module create** - Create hierarchical modules
- **module list/tree** - View module structure
- **module archive/unarchive** - Archive management
- **module connections** - Wiki-style [[links]]
- **module graph** - Visualize connections (Mermaid/Graphviz)
- **module rebuild-graph** - Rebuild connection graph
- **module check-links** - Validate links
- **module suggest-links** - Manual connection suggestions
- **module suggest-ai** - AI-based connection suggestions
- **module auto-tag** - Automatic tagging
- **module graph-history/diff/snapshot** - Graph version management

#### Search System (검색)
- **ms** - Search with multiple backends
  - Text search (BM25 ranking)
  - Semantic search (vector embeddings)
  - Hybrid search (text + semantic)
- Advanced filters (date, type, tags, exclude)
- Result caching for performance
- SQLite FTS5 indexing

#### LLM Integration
- **msummary** - Summarize timeline or modules
- Dual provider support (Anthropic API + Ollama)
- Local-first with Ollama
- Vector embeddings for semantic search
- AI connection suggestions
- Auto-tagging

#### UI/UX
- **CLI** - 16 commands with rich output
- **malias** - Alias management (batch + PowerShell)
- **mbrowse** - Interactive TUI browser
  - Multi-mode: Search/Timeline/Modules/Graph
  - Vim-style navigation
  - Filter toggles
- **mcompletion** - Shell completion support
- **mtutorial** - Interactive tutorial

#### Project Management
- **mstatus** - Project statistics
- **marchive** - Archive completed documentation
- **mplan** - Plan management
- **mcontext** - Generate Claude Code context
- **mhooks** - Git hooks for auto-sync

#### Performance
- Batch embeddings (10-50x improvement)
- Incremental indexing
- Result caching (TTL-based)
- Parallel search processing

### 📦 Architecture

- **6 Feature-Based Modules:**
  - core-system - Timeline, initialization, basic data
  - search-system - Text, vector, hybrid search
  - module-system - Hierarchical modules, wiki links, graph
  - ui-system - CLI, TUI, aliases
  - llm-integration - LLM features, embeddings
  - project-management - Architecture, roadmap, decisions

### 🎯 Design Principles

1. **Time First** - Capture first, organize later
2. **Lossless** - Record everything, lose nothing
3. **Minimal Friction** - 0.5 second capture
4. **Loose Coupling** - Modular architecture
5. **Local First** - Local by default, explicit expansion

### 📚 Documentation

- README.md - Project overview
- INSTALLATION.md - Installation guide
- QUICKSTART.md - 5-minute start guide
- USER_GUIDE.md - Complete user guide
- FAQ.md - Frequently asked questions
- CLAUDE.md - Claude Code integration guide
- 시간-공간-통합-지식-체계-v2.0.md - Full design document (Korean)

### 🧪 Testing

This is an alpha release. The software has been extensively dogfooded during development (200+ timeline entries, 30+ decisions) but lacks formal test coverage. Use with caution and report issues.

### 🔧 Requirements

- Python 3.10+
- Optional: sentence-transformers (vector search)
- Optional: anthropic/ollama (LLM features)
- Optional: textual (TUI browser)

### 📝 Known Limitations

- No automated tests (manual testing only)
- Windows console encoding issues (workaround available)
- Large datasets (10,000+ entries) not extensively tested
- MCP server support postponed (may revisit)

### 🙏 Acknowledgments

This project practices what it preaches - it was built using its own system for knowledge management. All development is recorded in `.memory/timeline/` and decisions in module-specific `decisions.md` files.

---

## [Unreleased]

### Planned
- Automated test coverage
- Performance benchmarks
- PyPI release (pending community feedback)
- Additional language support

---

**Note:** This is an alpha release. APIs may change before v1.0.0 stable.
