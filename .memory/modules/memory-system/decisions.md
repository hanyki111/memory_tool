# Key Decisions

> **Recent decisions for Phase 5 (Practical Improvements)**

For Phase 1-4 decisions (#1-#23), see [archive/decisions-phase1-4.md](./archive/decisions-phase1-4.md)

---

## Recent Decisions (Phase 5)

### 2025-11-14: MCP 서버 우선순위 하향, 실용 개선 우선 ⭐⭐⭐
**결정 #24:** Phase 5 MCP 서버 구현을 연기하고, 실사용 가치가 높은 개선에 집중

**배경:**
- Phase 1-4 완료 (8개 명령어, Skill, 벡터 검색, LLM 통합)
- 설계 문서상 다음은 Phase 5: MCP Server Integration
- 하루 만에 4개 Phase 완료 → 실사용 검증 부족

**비판적 검토 (Guidelines 원칙):**

1. **MCP 서버의 실질적 가치 의문**
   - Skill이 이미 자동화 제공 (규칙 기반)
   - MCP의 추가 가치: 속도 개선, 네이티브 통합
   - 하지만 체감 차이가 클까? 개발 비용(1-2주) 대비 효과는?

2. **조기 최적화 위험**
   - 실제 사용 패턴 파악 전 완전 자동화
   - 문제점 발견 전 고급 기능 추가
   - "Capture first, optimize later" 철학 위배

3. **더 시급한 문제 존재**
   - current.md, decisions.md 파일이 길어짐 (관리 곤란)
   - 검색 성능 (SQLite 인덱싱 없음)
   - 테스트 커버리지 0% (수동 테스트만)
   - 안정성 검증 부족

**대안 검토:**
- A: Phase 5 바로 진행 - 설계 완성, 하지만 조기 최적화
- B: 실사용 후 재평가 - 안전, 하지만 진행 중단
- **C: 실용 개선 우선 (채택)** - 안정성 + 실용성

**새로운 우선순위 (Phase 5 Revised):**

1. **문서 관리 개선** (최우선)
   - module current/decisions 길이 문제 해결
   - 아카이브, 요약, 분할 전략 고안

2. **SQLite 인덱싱**
   - 검색 속도 10-100배 개선
   - 대용량 Timeline 처리

3. **검색 개선**
   - 하이브리드 검색 (키워드 + 벡터)
   - 랭킹 알고리즘

4. **자동 요약 고도화**
   - 맥락 기반 요약
   - 주제별 분류

5. **성능 최적화**
   - 벡터 캐싱
   - 대용량 처리

6. **테스트 커버리지**
   - pytest 기반 자동 테스트
   - 안정성 확보

7. **사용성 개선**
   - GUI/TUI
   - 플래너 기능

**MCP 서버는?**
- 우선순위 최하위로 이동
- 1-7 완료 후 재평가
- 실사용 피드백 수집 후 필요성 판단

**핵심 원칙:**
- **실용성 > 완결성**: 작동하는 것 먼저
- **안정성 > 기능**: 새 기능보다 기존 개선
- **검증 > 최적화**: 실사용 검증 후 자동화

**측정 기준:**
- 다른 프로젝트 3개 이상 적용
- 1개월 실사용 (문제점 발견)
- 사용자 피드백 수집
- 그 후 MCP 필요성 재평가

**효과:**
- 조기 최적화 방지
- 안정성 우선 확보
- 실질적 가치 전달
- Phase 1-4 완성도 극대화

**교훈:**
- 빠른 진행 ≠ 올바른 진행
- 설계 문서도 실사용 기반으로 수정 가능
- 비판적 사고로 방향 전환 가능

**컨텍스트:** [[time:2025-11/14#23:42]]

---

### 2025-11-14: 문서 관리 개선 - 아카이브 전략 ⭐⭐
**결정 #25:** 비대해진 module 문서를 아카이브로 분리, Recent 항목만 메인 파일 유지

**배경:**
- decisions.md: 1250줄 (24개 결정)
- current.md: 242줄 (Phase 1-4 완료 내역)
- Claude Code 세션 시작 시 읽기 부담
- 실사용 중 발견된 첫 번째 문제

**문제:**
- 파일이 너무 길어 찾기 어려움
- 최근 정보와 과거 정보 혼재
- Claude가 읽는 시간 증가

**대안 검토:**
- A: 아카이브 (분리) ✅
- B: LLM 요약 (원본 손실 위험) ❌
- C: 연도별 분할 (주제 접근 어려움)
- D: 태그 + 인덱스 (관리 부담)
- E: 중요도 분리 (주관적 판단)

**선택: A (아카이브 중심) + 인덱스**

**구현:**
```
modules/memory-system/
  ├── current.md (Phase 5만, ~80줄)
  ├── decisions.md (Recent만, ~110줄)
  ├── decisions-index.md (전체 네비게이션)
  ├── archive/
  │   ├── decisions-phase1-4.md (#1-23)
  │   ├── current-phase1-4.md (Phase 1-4 완료)
  │   └── README.md (아카이브 정책)
```

**핵심 원칙:**
1. **원본 100% 보존** - LLM 요약 없음
2. **Recent 명시** - 최근 것만 메인 파일
3. **아카이브 링크** - 접근성 유지
4. **명확한 기준** - Phase 경계로 분할

**결과:**
- decisions.md: 1250줄 → 110줄 (91% 감소)
- current.md: 242줄 → 83줄 (66% 감소)
- 접근 속도 향상
- 이력 완전 보존

**아카이브 정책:**
- Phase 완료 시 아카이브
- 파일이 ~500줄 초과 시
- Recent 항목만 메인 유지

**Trade-offs:**
- 복잡도 약간 증가 (3개 파일 → 6개 파일)
- 하지만: 각 파일 읽기 빠름, 네비게이션 명확

**효과:**
- Claude 세션 시작 속도 향상
- 현재 정보 빠르게 파악
- 과거 이력 필요 시에만 접근
- 확장 가능한 구조

**컨텍스트:** [[time:2025-11/14#23:55]]

---

### 2025-11-14: SQLite 인덱싱 구현 결정 ⭐⭐⭐
**결정 #26:** 검색 성능 개선을 위한 SQLite FTS5 인덱싱 구현

**배경:**
- 현재: 파일 기반 검색 (ripgrep), 매번 전체 파일 읽기
- 문제: Timeline이 길어지면 검색 느려짐
- Phase 5 Revised 우선순위 #2

**목표:**
- 검색 속도 10-100배 개선
- 1000+ 항목에서도 sub-second 응답
- Backward compatible (기존 방식 유지)

**설계 결정:**

1. **Index 위치:** `.memory/.index.db` (hidden, gitignored)
   - 파생 데이터 (재생성 가능)
   - Git 커밋 제외
   - 사용자 직접 수정 불가

2. **SQLite FTS5 사용:**
   - Full-text search with porter tokenizer
   - Unicode61 support
   - Space-efficient (~2x text size)

3. **Backward Compatibility:**
   - SQLite 실패 시 → ripgrep fallback
   - Index 삭제되면 → 자동 재생성
   - 기존 명령어 변경 없음

4. **인덱싱 전략:**
   - `m` 명령어: 즉시 인덱싱
   - `ms` 명령어: Index 신선도 체크, 필요 시 rebuild
   - 새 명령어: `mindex` (수동 reindex)

5. **인덱싱 대상:**
   - ✅ Timeline entries
   - ✅ Decisions
   - ✅ Current state
   - ✅ Concepts
   - ❌ Archive (읽기 전용, 접근 드뭄)

**구현 범위 (4-6시간):**
- Phase 1: Core infrastructure (db/indexer.py, db/search.py)
- Phase 2: Timeline integration (auto-index)
- Phase 3: CLI commands (mindex, ms 개선)
- Phase 4: Testing & validation

**리스크 완화:**
- SQLite 없음 → ripgrep fallback
- Index 손상 → auto-rebuild
- 동시 쓰기 → write lock
- 디스크 공간 → FTS5 효율적

**성공 기준:**
- ✅ 10x 이상 속도 개선 (1000+ 항목)
- ✅ Backward compatible
- ✅ Auto-rebuild on corruption
- ✅ 기존 명령어 동작 유지

**Non-Goals:**
- ❌ Vector search 통합 (별도)
- ❌ Multi-project indexing
- ❌ Real-time index (on-command로 충분)

**효과:**
- 대용량 Timeline 검색 가능
- 사용자 경험 대폭 개선
- 실시간 피드백 가능
- 확장 가능한 아키텍처

**컨텍스트:** [[time:2025-11/14#23:05]]

---

## Archive

**Phase 1-4 Decisions (#1-#23):**
- See [archive/decisions-phase1-4.md](./archive/decisions-phase1-4.md)
- Covers: Platform selection, tech stack, MVP scope, search strategy, Claude Code integration, config strategy, Skill integration, Phase 1-4 completion, and more

**Total Decisions:** 26 (3 recent + 23 archived)
