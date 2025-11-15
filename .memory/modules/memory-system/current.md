# Current Status

> **Phase 5 (Practical Improvements) - 2025-11-15**

For Phase 1-4 completed work, see [archive/current-phase1-4.md](./archive/current-phase1-4.md)

---

## Phase Summary

- ✅ **Phase 1:** Complete (8 commands + Skill + PowerShell)
- ✅ **Phase 2:** Complete (Advanced search + msort + module management)
- ✅ **Phase 3:** Complete (Vector search + semantic embeddings)
- ✅ **Phase 4:** Complete (LLM integration + Ollama + msummary)
- ✅ **Phase 5:** Complete (Search improvements + performance optimization + archive automation)
- ✅ **Phase 6:** Complete (Hierarchical modules + wiki connections + AI suggestions + graph versioning)
- ✅ **Phase 7:** Complete (Enhanced TUI with multi-mode browser)

---

## Current Work (2025-11-15)

### Completed Today

- [x] **Enhanced TUI 브라우저 (Phase 7)** ⭐⭐⭐⭐⭐
  - [x] **멀티 모드 탭 인터페이스**
    - [x] 4개 모드: Search, Timeline, Modules, Graph
    - [x] Tab 키로 모드 전환
    - [x] CLI `--mode` 옵션 추가
  - [x] **Search 모드 개선**
    - [x] 필터 토글 (Timeline/Modules/Decisions)
    - [x] 향상된 결과 테이블 (타입 컬럼 추가)
    - [x] vim 스타일 네비게이션 (j/k)
    - [x] 상세 뷰 패널
  - [x] **Timeline 모드 (신규)**
    - [x] 날짜별 엔트리 리스트
    - [x] 날짜 선택으로 엔트리 표시
    - [x] n/p 키로 일간 네비게이션
    - [x] 엔트리 통계 표시
  - [x] **Modules 모드 (신규)**
    - [x] 계층적 모듈 트리 뷰
    - [x] 모듈 상세정보 패널
    - [x] 연결된 모듈 표시 (outgoing/incoming)
    - [x] r 키로 새로고침
  - [x] **Graph 모드 (신규)**
    - [x] 연결 수 기준 모듈 정렬
    - [x] 선택한 모듈의 연결 시각화
    - [x] 그래프 통계 (total/connected/orphaned)
    - [x] s 키로 정렬 전환
  - [x] **새 파일 생성**
    - [x] `tui/browser.py` (메인 브라우저)
    - [x] `tui/search_mode.py` (검색 모드)
    - [x] `tui/timeline_mode.py` (타임라인 모드)
    - [x] `tui/modules_mode.py` (모듈 모드)
    - [x] `tui/graph_mode.py` (그래프 모드)
  - [x] **테스트 완료** ✅
    - [x] 모든 모드 임포트 확인
    - [x] CLI 통합 확인

- [x] **계층적 모듈 시스템 + Wiki 스타일 연결 (Phase 6)** ⭐⭐⭐⭐⭐
  - [x] **계층 구조 (Hierarchical Modules)**
    - [x] 디렉토리 기반 계층 (`projects/website`)
    - [x] `current.md` 마커 패턴
    - [x] `discover_all_modules()`, `build_module_tree()` 구현
    - [x] CLI: `module tree` 명령어
  - [x] **Wiki 스타일 연결 (Wiki-style Connections)**
    - [x] `[[module-name]]` 링크 문법
    - [x] SQLite 기반 연결 그래프 (`.memory/.connections.db`)
    - [x] `ConnectionParser`, `ConnectionGraph` 클래스
    - [x] CLI: `connections`, `graph`, `rebuild-graph`, `check-links`, `suggest-links`
  - [x] **그래프 시각화**
    - [x] Mermaid 다이어그램 내보내기
    - [x] Graphviz DOT 형식 내보내기
    - [x] CLI: `graph --format mermaid/graphviz --output file`
  - [x] **링크 검증**
    - [x] 깨진 링크 감지 (`check_broken_links()`)
    - [x] 고립된 모듈 찾기 (`get_orphaned_modules()`)
    - [x] CLI: `check-links`
  - [x] **역링크 제안**
    - [x] 3가지 전략 (경로 유사도, 카테고리, 공통 대상)
    - [x] CLI: `suggest-links <module>`
  - [x] **Git 훅 통합**
    - [x] Pre-commit/post-checkout 훅 자동 생성
    - [x] `GitHookManager` 클래스
    - [x] CLI: `hooks install/uninstall/list`
  - [x] **AI 기반 제안 (Phase 4 확장)** ⭐⭐⭐
    - [x] `AIConnectionSuggester` 클래스
    - [x] LLM 기반 콘텐츠 유사도 분석
    - [x] 연결 제안 with 신뢰도 점수
    - [x] 자동 태그 생성
    - [x] CLI: `suggest-ai <module>`, `auto-tag <module>`
  - [x] **그래프 버전 관리** ⭐⭐⭐
    - [x] `GraphVersionManager` 클래스
    - [x] SQLite 기반 스냅샷 시스템
    - [x] 버전 비교 및 diff
    - [x] 자동 버전 관리 (rebuild-graph 후)
    - [x] CLI: `graph-snapshot`, `graph-history`, `graph-diff`
  - [x] **별칭 업데이트**
    - [x] `mmodule` 별칭 추가
    - [x] `mhooks` 별칭 추가
    - [x] PowerShell 프로필 업데이트
  - [x] **테스트 완료** ✅
    - [x] 모든 명령어 테스트
    - [x] 버전 생성/조회/비교
    - [x] AI 제안 동작 확인
    - [x] 별칭 설치 확인

- [x] **검색 개선 Phase 1, 2, 3** ⭐⭐⭐⭐
  - [x] **Phase 1: Ranking + Filters + Formatting**
    - [x] BM25 랭킹 알고리즘 (관련성 점수)
    - [x] 날짜 기반 가중치 (exponential decay)
    - [x] 고급 날짜 필터 (today, yesterday, this-week, last-N-days, ranges)
    - [x] 파일 타입 필터 (timeline, modules, decisions, plans, archive)
    - [x] 태그 필터 (#hashtags, **Category:** patterns)
    - [x] 결과 포매팅 (scores, context, highlighting, summary)
    - [x] CLI 통합 (11개 새 옵션)
    - [x] Windows 인코딩 이슈 수정
  - [x] **Phase 2: Hybrid Search**
    - [x] 텍스트 + 벡터 검색 조합
    - [x] 가중치 조정 가능 (--text-weight, --semantic-weight)
    - [x] 결과 병합 및 재정렬
  - [x] **Phase 3: Performance Optimization**
    - [x] Result caching (TTL 기반, 통계)
    - [x] Parallel search processing
    - [x] Index optimization (FTS5 optimize, vacuum, analyze)
    - [x] CLI 통합 (--no-cache, --cache-ttl, mindex --optimize/--vacuum)

- [x] **성능 최적화 (벡터 검색)** ⭐⭐⭐
  - [x] 배치 임베딩 (10-50배 속도 향상)
  - [x] 증분 인덱싱 (파일 수정 시간 추적)
  - [x] 메모리 최적화 (스트리밍 처리)
  - [x] preindex_timeline() 메서드
  - [x] Cache 통계 (get_stats())

- [x] **marchive 명령어 개선** ⭐⭐⭐
  - [x] --up-to N 옵션 (결정 번호 기반)
  - [x] --keep-recent N 옵션 (개수 기반, 기본값)
  - [x] 개선된 파일 크기 경고 (결정 개수 표시)
  - [x] Decision 파싱 버그 수정
  - [x] marchive alias 추가
  - [x] Decision #29 업데이트

### Completed Yesterday (2025-11-14)

- [x] MCP 서버 비판적 검토 및 우선순위 재조정
- [x] **문서 관리 개선 구현** ⭐
  - [x] decisions.md 아카이브 (1250줄 → 110줄, 91% 감소)
  - [x] current.md 아카이브 (242줄 → 간결화)
  - [x] decisions-index.md 생성 (전체 네비게이션)
  - [x] archive/ 구조 생성
  - [x] marchive 명령어 초기 구현 (Phase 기반)
- [x] SQLite FTS5 인덱싱 구현 (검색 속도 10-100배 향상)

### In Progress

없음

### Next Up (Phase 5 Roadmap)

1. ✅ 문서 관리 개선
2. ✅ SQLite 인덱싱 (검색 속도 10-100배)
3. ✅ 검색 개선 (Phase 1, 2, 3 완료)
   - ✅ Phase 1: Ranking + Filters + Formatting
   - ✅ Phase 2: Hybrid search (text + vector combination)
   - ✅ Phase 3: Performance optimization (caching, parallel, index optimize)
4. ✅ 자동 요약 고도화 (맥락, 주제 분류)
5. ✅ 성능 최적화 (벡터 배치 임베딩, 증분 인덱싱, 메모리 최적화)
6. ⏳ 테스트 커버리지 (pytest, 안정성)
7. 🎯 사용성 개선 (GUI/TUI, 플래너) - 다음 작업

---

## Blocked

없음

---

## Key Metrics

**Commands:** 12 operational (m, minit, ms, mcontext, malias, marchive, msummary, mtoday, mweek, mstatus, mmodule, mhooks)

**Module Actions:** 14 actions (create, list, tree, archive, unarchive, connections, graph, rebuild-graph, check-links, suggest-links, suggest-ai, auto-tag, graph-snapshot, graph-history, graph-diff)

**Features:**

- Timeline capture ✅
- Search (text + vector + SQLite FTS5) ✅
- Advanced search (BM25, filters, hybrid, caching) ✅
- Performance optimization (batch embeddings, incremental indexing) ✅
- Claude Skill integration ✅
- LLM summarization (Anthropic + Ollama) ✅
- Hierarchical module system ✅
- Wiki-style connections ([[links]]) ✅
- Graph visualization (Mermaid/Graphviz) ✅
- AI-based connection suggestions ✅
- Graph version management ✅
- Git hooks integration ✅
- Archive automation (3 modes) ✅
- Index optimization (FTS5 optimize, vacuum) ✅
- Enhanced TUI browser (4 modes) ✅

**Documentation:**

- decisions.md: 4 recent + 25 archived
- current.md: Phase 5 focused
- Archive: Complete Phase 1-4 history + plans

---

## Notes

**Decision #29 (2025-11-15):**

- marchive 명령어 개선 (결정 번호/개수 기반)
- 기본값: --keep-recent 10 (config)
- 사용자 피드백: "Phase는 잘 사용하지 않음"

**Decision #24 (2025-11-14):**

- MCP 서버 우선순위 하향
- 실용 개선 우선 (안정성 > 기능)
- 조기 최적화 방지

**Philosophy:**

- 실용성 > 완결성
- 안정성 > 기능
- 검증 > 최적화
- 사용자 피드백 반영

---

**Last Updated:** 2025-11-15 10:28
