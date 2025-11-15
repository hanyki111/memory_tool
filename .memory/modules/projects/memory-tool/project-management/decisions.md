# Key Decisions

> **Architecture and project-level decisions for memory_tool**

---

## Recent Decisions

### 2025-11-15: 모듈 조직화 원칙 수립 ⭐⭐⭐⭐⭐
**결정 #30:** Module Organization Principles 확립 및 문서화

**배경:**
- memory-system이 2000줄, 29개 결정, 7개 Phase로 성장
- 계층적 모듈 시스템 도입 (Phase 6) 이후 조직화 원칙 필요
- 언제 모듈을 분리하고, 계층을 사용하고, 명명하는지 기준 부재
- Claude가 일관되게 따를 수 있는 원칙 필요

**문제:**
- 모듈 분리 시점 불명확 (언제 나눌까?)
- 계층 vs 평면 선택 기준 없음
- 크기/복잡도 임계값 미정의
- God Module 위험 (모든 것을 하나에)

**구현 사항:**

**1. 핵심 원칙 문서 생성**
```
.memory/modules/
├── MODULE-ORGANIZATION-PRINCIPLES.md  # 상세 원칙
├── QUICK-REFERENCE-MODULE-ORGANIZATION.md  # 빠른 참조
└── memory-system/MIGRATION-PLAN.md    # memory-system 분리 계획
```

**2. 분리 기준 (정량적)**
```
🔴 반드시 분리 (High Priority):
  - current.md > 300줄
  - 전체 파일 > 3000줄
  - 결정사항 > 30개
  - 독립 토픽 > 5개

🟡 분리 고려 (Medium Priority):
  - current.md > 200줄
  - 전체 파일 > 2000줄
  - 결정사항 > 20개
  - 독립 토픽 > 3개

🟢 유지 (Low Priority):
  - current.md < 200줄
  - 전체 파일 < 2000줄
  - 결정사항 < 20개
  - 단일 토픽
```

**3. 분리 기준 (정성적)**
- 인지 부하: 이해하는데 >20분
- 변경 영향: 한 변경이 여러 무관한 부분 영향
- 재사용성: 일부만 독립 참조 필요
- 팀 경계: 다른 사람/팀이 다른 부분 소유

**4. 계층 vs 평면 결정**
```
계층 사용 (projects/parent/child):
  ✅ 명확한 포함 관계 (IS-PART-OF)
  ✅ 공통 컨텍스트/프로젝트
  ✅ 동일한 생명주기
  ✅ 점진적 상세화

평면 사용 (projects/module-a):
  ✅ 독립적 관심사
  ✅ 다른 생명주기
  ✅ 교차 참조 관계
  ✅ 여러 잠재적 부모
```

**5. 모듈 크기 가이드**
- **Small** (권장): 100-500줄, 1-5개 결정, 단일 관심사
- **Medium**: 500-1500줄, 5-15개 결정, 2-3개 관련 관심사
- **Large** (분리 고려): 1500-3000줄, 15-30개 결정
- **Too Large** (반드시 분리): >3000줄, >30개 결정

**6. 명명 규칙**
```
projects/[project-name]/[feature]   # 프로젝트 하위 기능
areas/[area-name]                   # 관심 영역
resources/[resource-type]           # 재사용 가능 리소스
archive/[YYYY-MM]/[archived-name]   # 완료된 프로젝트
```

**7. Claude 통합**
- **CLAUDE.md**: Module Organization Principles 섹션 추가
- **.claude/guidelines.md**: 모듈 조직화 원칙 섹션 추가
- 모듈 작업 시 자동으로 크기 확인 및 분리 제안

**memory-system 분석 결과:**
```
현재 상태:
  - 크기: ~2000줄 (Large, 분리 고려 단계)
  - 결정: 29개 (곧 30개 도달)
  - 토픽: 7개 (명확히 >5개)
  - 인지 부하: 25분+ (>20분)

→ 결론: 분리 필요 (모든 기준 충족)
```

**제안 구조:**
```
projects/memory-tool/
├── core-system/          # Timeline, init (안정적)
├── search-system/        # Text, vector, SQLite (독립적)
├── module-system/        # Hierarchy, connections, graph (Phase 6)
├── ui-system/            # CLI, TUI, aliases (프레젠테이션)
├── llm-integration/      # Summarization, AI (외부 통합)
└── project-management/   # Decisions, architecture (거버넌스)
```

**마이그레이션 계획:**
- 7단계, 11시간 예상
- 3세션으로 분할 가능 (4h + 4h + 3h)
- 점진적 접근도 가능 (5주)
- 롤백 계획 포함

**Trade-offs:**

**장점:**
- ✅ 명확한 분리 기준
- ✅ 일관된 모듈 구조
- ✅ 확장성 향상
- ✅ 인지 부하 감소
- ✅ 독립적 발전 가능
- ✅ Claude가 자동으로 적용 가능

**단점:**
- ⚠️ 초기 마이그레이션 노력 필요 (11시간)
- ⚠️ 기존 [[링크]] 업데이트 필요
- ⚠️ 학습 곡선 (새 구조 이해)

**대안 검토:**
- **A**: 원칙 없이 계속 (채택 안 함) - God Module 위험
- **B**: 크기만 고려 (채택 안 함) - 응집도 무시
- **C**: 정량+정성 기준 (채택) - 균형잡힌 접근
- **D**: 즉시 분리 vs 점진적 - 두 옵션 모두 제공

**실천 방법:**
1. 모듈 작업 전 `wc -l .memory/modules/[module]/*.md` 확인
2. MODULE-ORGANIZATION-PRINCIPLES.md 참조
3. QUICK-REFERENCE 체크리스트 사용
4. 분리 기준 충족 시 Claude가 자동 제안

**영향:**
- ✅ 향후 모든 모듈 작업에 적용
- ✅ Claude가 일관되게 따를 수 있는 기준
- ✅ 프로젝트 확장성 크게 향상
- ✅ 새 기여자 온보딩 용이

**참조:**
- [[MODULE-ORGANIZATION-PRINCIPLES]] (상세 원칙)
- [[QUICK-REFERENCE-MODULE-ORGANIZATION]] (빠른 참조)
- [[projects/memory-tool/project-management/MIGRATION-PLAN]] (구체적 실행 계획)
- [[CLAUDE.md]] (통합됨)
- [[.claude/guidelines.md]] (통합됨)

---

### 2025-11-14: 완료된 PLAN 문서 아카이브 정책 ⭐
**결정 #28:** 완료된 PLAN 문서를 archive/plans/로 이동하는 정책 수립

**배경:**
- Phase 5 #2, #4 작업으로 PLAN 문서 2개 생성
  - PLAN-sqlite-indexing.md (7.3KB)
  - PLAN-advanced-summarization.md (22.4KB)
- 작업 완료 후 이 문서들을 어떻게 관리할지 정책 필요

**문제:**
- PLAN 문서가 module 최상위에 계속 쌓임
- decisions.md, current.md와 달리 프로젝트별/일회성 문서
- 완료 후에도 참고 가치 있음 (설계 의도, trade-offs)

**옵션 검토:**

**A. archive/ 직접 이동**
- 장점: 단순
- 단점: decisions, current와 성격 다름

**B. archive/plans/ 하위 (채택)**
- 장점: 타입별 분류, 확장성, 일관성
- 단점: 디렉토리 깊이 증가

**C. completed-plans/ 별도**
- 장점: 독립 관리
- 단점: 최상위 디렉토리 증가

**D. 삭제**
- 장점: 가장 단순
- 단점: 세부 계획 손실

**채택한 정책:**

**구조:**
```
archive/
├── decisions-phase{N}.md   # 완료된 Phase 결정사항
├── current-phase{N}.md     # 완료된 Phase 상태
└── plans/                  # 완료된 구현 계획서
    ├── PLAN-sqlite-indexing.md
    └── PLAN-advanced-summarization.md
```

**이동 시점:**
- PLAN 문서: 작업 완료 후 main 머지 시
- decisions/current: Phase 완료 시

**보존 이유:**
- 설계 의도 참고
- Trade-offs 근거
- 테스트 전략
- 향후 유사 작업 시 템플릿

**효과:**
- module 최상위 정리 (진행 중 작업만)
- 타입별 분류 (decisions, current, plans)
- 완료 문서 찾기 쉬움
- 확장성 (archive/docs/, archive/research/ 추가 가능)

**구현:**
- archive/plans/ 디렉토리 생성
- 완료된 PLAN 2개 이동
- archive/README.md 정책 추가

**교훈:**
- 문서 타입별 lifecycle 고려
- 일관된 정책으로 확장성 확보
- 완료 문서도 가치 있음 (삭제 X)

**컨텍스트:** [[time:2025-11/14#23:38]]

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

## See Also

**Related Modules:**
- [[projects/memory-tool/search-system]] - Search-related decisions
- [[projects/memory-tool/llm-integration]] - LLM-related decisions
- [[projects/memory-tool/ui-system]] - UI-related decisions
- [[projects/memory-tool/core-system]] - Core architecture decisions
- [[projects/memory-tool/module-system]] - Module system decisions

**Archived Decisions:**
- See [[archive/decisions-phase1-4]] for decisions #1-23

---

**Total Decisions:** 4 (recent architectural decisions)
