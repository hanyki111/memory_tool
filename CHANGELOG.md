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

## [1.4.1] - 2026-11-06

### 🐛 수정

- **`~/.memory`를 지식 베이스로 착각하던 문제:** 검색 캐시가 만드는 `~/.memory`를 CLI가 예전 방식의 지식 베이스로 받아들였습니다. 그래서 지식 베이스가 없는 폴더에서 `m`을 실행하면 `~/.memory/timeline`에 기록되었습니다. 이제 `.memory` 폴더에 `config.yaml`, `timeline/`, `modules/` 중 하나가 있어야 지식 베이스로 인정합니다. 지식 베이스가 없는 폴더에서 `m`을 실행하면, 홈 폴더 밖에서와 같이 그 폴더에 `.memory`를 만듭니다.
- **`medit`이 손으로 적은 줄을 지우던 문제:** 저장할 때 파일 전체를 기록 줄만으로 다시 써서, 제목이 바뀌고 손으로 적은 줄이 사라졌습니다. 이제 고친 기록만 바뀝니다. 손으로 적은 줄은 바로 위 기록과 함께 움직이고, 그 기록을 지우면 바로 앞 기록 아래로 옮겨집니다.

### Obsidian 플러그인 1.2.1

- 명령을 셸을 거치지 않고 인수 배열로 실행합니다. 따옴표, `%`, `$`, 역슬래시가 든 기록도 적은 그대로 저장됩니다. Python 설정은 `py -3` 같은 런처나 큰따옴표로 감싼 경로도 그대로 받습니다.

## VS Code 확장 0.1.0 - 2026-11-06

### ✨ 추가

- **Memory Tool Timeline (`vscode/`):** VS Code에서 타임라인에 기록하고, 7일씩 이어 보고, 기간을 골라 보고, 검색합니다. 사이드바와 편집기 탭에 같은 화면을 띄우며, 어디서 기록하든 열린 화면이 모두 새로 고쳐집니다. 검색은 키워드가 기본이고 "의미로 찾기"를 누르면 혼합 검색을 합니다. 리뷰 버튼은 화면에 보이는 가장 오래된 날짜로 `mreview --since`를 터미널에서 실행합니다. memory_tool 1.4 이상이 필요합니다.

## [1.4.0] - 2026-11-06

### ✨ 추가

- **JSON 출력:** 기록, 조회, 검색, AI 명령에 `--json`을 추가했습니다. 편집기와 스크립트가 터미널 출력을 해석하지 않고 결과를 받을 수 있습니다. 형식은 `docs/USER_GUIDE.md`의 "JSON Output"에 정리했습니다.
  - 대상: `m`, `mtoday`, `mday`, `mweek`, `mmonth`, `mdays`, `ms`, `msummary`, `mmodule suggest-links --ai`, `mmodule from-text`
  - 결과는 표준 출력에 UTF-8 JSON 한 줄로만 나옵니다. 실패에는 `code`가 붙고, 리뷰 알림 같은 안내는 `notices`에 담깁니다.
  - 조회와 검색은 기록마다 시각, 원문, 태그를 담습니다. 조회는 파일 원문도 함께 담습니다.
- **기간 조회:** `mdays --from 날짜 --to 날짜`로 원하는 기간의 기록을 봅니다.
- **`mday` 명령 등록:** 도움말에 있었지만 실행 명령으로 등록되어 있지 않았습니다.

### 🔧 변경

- `mask --json`, `mreview --json`의 실패에 `code`를 추가했습니다. 기존 항목은 그대로입니다.

### 🐛 수정

- **의미 검색이 바뀐 파일만 검색하던 문제:** 한 번 색인한 타임라인 파일은 바뀌지 않는 한 검색 대상에서 빠졌습니다. 그래서 두 번째 검색부터는 그사이에 바뀐 파일의 기록만 찾았습니다. `ms --semantic`, 혼합 검색, `mask`의 의미 검색이 영향을 받았습니다. 이제 검색할 때는 모든 파일을 읽고, 바뀌지 않은 파일을 건너뛰는 동작은 미리 색인하기에만 남겼습니다.
- **의미 검색 결과의 날짜:** `daily/` 구조에서 `daily-2026-11`처럼 잘못된 날짜가 나왔습니다.
- `mhelp days`가 기본값을 7일로 안내했지만 실제 기본값은 14일입니다.
- `mhelp today`와 사용자 안내서에 있던, 실제로는 없는 옵션(`--yesterday`, `--reverse`, `--limit`)을 지웠습니다.

## [1.3.0] - 2026-11-05

### ⚠️ 호환 없이 바뀐 동작

- **`mreview weekly`, `monthly` 제거:** 회고 양식을 만들던 기존 기능을 호환 기간 없이 제거했습니다. 이미 만들어진 `reviews/weekly/`, `reviews/monthly/`의 파일은 그대로 두며, `ms`로 검색할 수 있습니다. `mreview`는 패키지 설치 명령에 등록되어 있지 않았으므로, 이제 `pip install -e .` 등으로 다시 설치해야 명령이 생깁니다.

### ✨ 추가

- **`mreview`:** 타임라인에서 남길 내용을 문서로 옮기는 리뷰입니다.
  - 지난 리뷰 이후의 기록을 설정된 LLM 제공자로 보내 제안을 다섯 건까지 받습니다. 첫 리뷰는 최근 14일을 읽고, `--since`로 시작일을 정할 수 있습니다.
  - 제안마다 지금 쓰기, 나중에 쓰기, 거절 중에서 고릅니다. 남은 항목이 다섯 건을 넘는 동안에는 미룰 수 없습니다.
  - 선택은 바로 저장되므로 멈춘 곳부터 이어 갈 수 있고, 이때 LLM을 다시 호출하지 않습니다.
  - 쓰기를 시작할 때 Claude Code, Codex, Antigravity와 혼자 쓰기를 메뉴로 고릅니다. 고르는 것만으로는 문서가 생기지 않습니다.
  - 마지막에 그 기간을 돌아보거나 건너뜁니다.
  - `mreview list`, `write`, `done`과 `--json`, `set`, `reflection`을 제공합니다.
- **리뷰 알림:** 지난 리뷰 후 7일이 지나고 기록이 10건 쌓이면, 그날의 첫 `m`과 `mcontext`에서 한 줄로 알립니다. `review.notice`로 값을 바꾸거나 끌 수 있습니다.
- **편집 가능한 리뷰 가이드:** 제안 기준과 돌아보기 절차는 `guides/review-proposals.md`, `guides/review-reflection.md`로 바꿀 수 있습니다.

### 알려진 제한

- `--date`로 지난 날짜에 추가한 기록은 다음 리뷰 범위에서 빠질 수 있습니다.
- AI는 문서 본문을 받지 않으므로, 이미 반영된 내용을 다시 제안할 수 있습니다.
- Obsidian 플러그인에서 기록하면 알림 문구가 플러그인 쪽 결과에 함께 나타날 수 있습니다. 확인하지 않았습니다.

## [1.2.0] - 2026-11-05

### ⚠️ 호환 없이 바뀐 동작

- **`module auto-tag` 제거:** 대체 기능은 없습니다.
- **`gemini-cli` 제공자 제거:** Gemini CLI가 개인용 Code Assist 계정을 더 이상 지원하지 않습니다. `antigravity-cli`를 사용하십시오. 설정에 `gemini-cli`가 남아 있으면 이 내용을 안내합니다.
- **`mplan module`과 `PLAN.md` 제거:** `mplan`의 나머지 기능은 그대로입니다. 기존 `PLAN.md`는 삭제되지 않으며, 모듈 목록에 더는 나타나지 않습니다.
- **옵션 없는 `mmodule create`의 결과 변경:** 범용 골격 대신 frontmatter와 제목만 있는 파일 하나(`topic.md`)를 만듭니다. `modules.default_kind`를 설정한 프로젝트는 이전처럼 동작합니다.
- **`mmodule from-text`의 결과 변경:** 파일 3개 대신 문서 하나로 저장하며, `generated.by`에 AI 작성으로 표시합니다. `--structure`는 더 이상 효과가 없습니다.
- **Obsidian 플러그인 1.2.0의 `grow` 메뉴 제거:** 생성 화면은 Kind와 Nature 대신 종류를 묻습니다. 이 플러그인은 `--type`을 쓰므로 memory_tool 1.2 이상이 필요합니다. 이전 플러그인은 1.2에서 경고와 함께 계속 작동합니다.
- **LLM 제공자 기본값 변경:** `llm.provider`가 없으면 `anthropic`으로 고정하지 않고, `anthropic`, `claude-cli`, `codex-cli`, `antigravity-cli`, `ollama` 순서로 사용 가능한 제공자를 고릅니다.
- **CLI 제공자의 실행 위치 변경:** `claude-cli`를 포함한 CLI 제공자는 빈 임시 폴더에서 실행합니다. 프로젝트 파일을 건드리지 않고 프로젝트 지침도 읽지 않습니다.
- **`mmodule rename`의 대상 제한:** 대상 폴더가 이미 있으면 합치지 않고 거부합니다.

### 🗑️ Deprecated

다음 기능은 경고와 함께 계속 작동하며, 이후 버전에서 제거될 수 있습니다. 이 기능으로 만든 문서는 계속 읽을 수 있습니다.

- `--kind`, `--nature`, `--draft`, `mmodule grow`, `--part`, `merge-templates`, `modules.default_kind`
- `mmodule ai-organize` (`mmodule audit`으로 대체)
- `mmodule suggest-ai` (`mmodule suggest-links --ai`로 대체)

### ✨ Added

- **LLM 제공자 추가:** `codex-cli`(별칭 `codex`), `antigravity-cli`(별칭 `agy`, `antigravity`), `glm`. Codex는 `read-only`, Antigravity는 `plan` 모드로 실행합니다.
- **`glm`:** Claude CLI를 GLM에 연결합니다. `llm.glm.env_from_ps1` 또는 `llm.glm.env_from_env`로 연결 값이 있는 곳을 지정하며, 값은 설정 파일에 적지 않습니다. 자동으로 선택되지 않습니다.
- **새 문서 형식:** `mmodule create --type <종류>`. 종류는 참고, 이해, 방법, 판단이며 선택 사항입니다. 첫 하위 문서를 만들면 `topic.md`가 `topic/topic.md`로 옮겨지고, `[[topic]]` 링크는 유지됩니다.
- **작성 지원:** `mmodule guide [종류]`와 `mt-write` 스킬. 기본적으로 AI는 질문하고 지적하며, 요청할 때만 본문을 씁니다. `<기반폴더>/guides/`의 파일이 번들 가이드보다 우선합니다.
- **`mmodule audit`:** 분리와 병합 후보를 보여 줍니다. LLM을 쓰지 않으며 문서를 바꾸지 않습니다.
- **`mmodule suggest-links --ai`:** 내용을 읽고 관련 문서를 제안합니다.
- **`mask`의 기간 조회:** 시작일과 종료일을 지정해 타임라인을 읽습니다.
- **연결 그래프의 Markdown 링크:** 위키 링크와 함께 읽습니다.
- **`mcheck`의 `sources` 검증:** frontmatter의 로컬 경로를 확인합니다.

### 🐛 Fixed

- **`mask`:** 날짜형 파일명의 타임라인과 단일 문서 모듈을 읽지 못하던 문제를 고쳤습니다. 읽을 수 없는 날짜를 오늘로 처리해 다른 날의 기록으로 답하던 문제도 고쳤습니다.
- **`msummary`:** 타임라인과 모듈 요약이 `AttributeError`로 중단되던 문제를 고쳤습니다. `--decisions`는 단일 문서의 결정 절도 읽습니다. 도움말의 없는 옵션(`--week`, `--days`)도 바로잡았습니다.
- **`claude-cli`:** 긴 프롬프트가 Windows 명령줄 길이 제한에 걸리지 않도록 표준 입력으로 전달합니다.
- **`PLAN.md`:** CLI가 모듈로 나열하던 문제를 고쳤습니다.
- **플러그인 모듈 목록:** `AI.md`, `MIGRATION-PLAN.md`처럼 대문자로 된 파일명을 숨기던 문제를 고쳤습니다.
- **`mmodule rename`:** 하위 문서를 남겨 두거나 잘못된 위치로 옮기던 문제를 고쳤습니다.
- **`mmodule archive`, `unarchive`, 연결 그래프, `mpublish`:** 단일 파일 모듈을 처리합니다. 하위 문서를 남겨 두거나, 하위 문서의 링크를 상위 문서의 것으로 집계하던 문제도 고쳤습니다.
- **`suggest-links`, `check-links`:** 문서 이름이 빈 괄호로 출력되던 문제를 고쳤습니다.

### 📚 Documentation

- 도움말, README, 사용자 가이드, 튜토리얼, 스킬을 새 문서 형식 기준으로 수정했습니다.
- `minit`은 `MODULE-ORGANIZATION-PRINCIPLES.md`와 `QUICK-REFERENCE-MODULE-ORGANIZATION.md`를 더 이상 만들지 않습니다.

### ⚠️ 알려진 제한

- `mcontext -i`는 단일 문서 모듈에서 동작하지 않습니다.
- 플러그인 1.2.0은 빌드와 단위 테스트만 거쳤고, Obsidian 안에서 화면을 직접 확인하지 않았습니다.

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
