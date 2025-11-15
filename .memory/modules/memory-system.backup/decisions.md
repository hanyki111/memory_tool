# Key Decisions

> **Recent decisions for Phase 5 (Practical Improvements)**

For Phase 1-4 decisions (#1-#23), see [archive/decisions-phase1-4.md](./archive/decisions-phase1-4.md)

---

## Recent Decisions (Phase 5+)

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
- MODULE-ORGANIZATION-PRINCIPLES.md (상세 원칙)
- QUICK-REFERENCE-MODULE-ORGANIZATION.md (빠른 참조)
- memory-system/MIGRATION-PLAN.md (구체적 실행 계획)
- CLAUDE.md (통합됨)
- .claude/guidelines.md (통합됨)

---

### 2025-11-15: marchive 명령어 개선 - 결정 번호 기반 아카이브 ⭐⭐⭐
**결정 #29:** 결정 번호/개수 기반 아카이브 옵션 추가 (--up-to, --keep-recent)

**배경:**
- Decision #28에서 PLAN 문서 아카이브 정책 수립
- 기존 marchive는 Phase 기준만 지원 (--phase)
- 사용자: "Phase는 잘 사용하지 않음, 결정 번호 기준이 더 직관적"

**문제:**
- Phase 번호를 모르거나 신경 쓰지 않음
- "최근 10개만 남기고 싶다"는 요구사항에 Phase는 부적합
- 결정 번호 기준이 훨씬 직관적

**구현 사항:**

**1. 세 가지 아카이브 모드**
```bash
# 모드 A: 개수 기반 (기본값, 가장 편리)
marchive decisions                    # 최근 10개 유지 (config 기본값)
marchive decisions --keep-recent 15   # 최근 15개 유지

# 모드 B: 결정 번호 기반 (명확함)
marchive decisions --up-to 25         # Decision #1-25 아카이브

# 모드 C: Phase 기반 (하위 호환)
marchive decisions --phase 5          # Phase 1-5 아카이브

# 공통
marchive --dry-run                    # 미리보기
marchive current --phase 5            # current.md는 Phase 기준
marchive plans                        # PLAN 문서 아카이브
```

**2. 개선된 파일 크기 경고**
```bash
m "New entry"
→ ⚠️  decisions.md exceeds 500 lines (29 decisions)
→ 💡 Consider: marchive decisions  # keeps recent 10 (default)
→    Or: marchive decisions --keep-recent 15
→    Or: marchive decisions --up-to 19
```

**3. Config 설정**
```yaml
modules:
  archive_keep_recent: 10   # marchive decisions 기본값
  warn_size_decisions: 500  # lines
  warn_size_current: 300    # lines
  warn_on_record: true      # m 명령어 시 경고
```

**구현 구조:**
```
memory_tool/core/
├── archiver.py        # Archiver 클래스
│   - archive_decisions(phase, dry_run)              # Phase 기반
│   - archive_decisions_by_number(up_to, dry_run)   # 번호 기반
│   - archive_decisions_by_count(keep_recent, ...)  # 개수 기반
│   - archive_current(phase, dry_run)
│   - archive_plans(dry_run)
│   - _parse_decisions() - Decision 파싱
│   - _build_archive_content_by_number() - 번호 기반 아카이브
│
└── warnings.py        # FileSizeWarning 클래스
    - check_sizes() - threshold 초과 감지
    - format_warning() - 개선된 경고 메시지 (결정 개수 표시)
    - _count_decisions() - 결정 개수 카운트
```

**Trade-offs:**

**장점:**
- 직관적 사용성 (Phase 번호 몰라도 됨)
- 기본값 제공 (`marchive decisions`만 입력)
- 세 가지 모드로 유연성 확보
- 하위 호환 (기존 --phase 지원)

**단점:**
- 옵션이 많아짐 (3가지 모드)
- 상호 배타성 검증 필요

**대안 검토:**
- A: Phase만 지원 - 사용자 불편
- B: 번호만 지원 - 기존 사용자 호환성 문제
- **C: 세 가지 모두 지원 (채택)** - 유연성 + 하위 호환

**테스트 결과:**
- ✅ marchive plans --dry-run: 미리보기 정상
- ✅ marchive plans: 실제 이동 정상
- ✅ 백업 파일 생성 확인
- ✅ 경고 시스템 통합 완료

**효과:**
- 아카이브 작업 간소화 (명령어 한 줄)
- 실수 방지 (dry-run, 백업)
- 적절한 시점 알림 (파일 크기 경고)
- Phase 전환 시 일관된 프로세스

**사용 예시:**
```bash
# Phase 6 시작 시
marchive decisions --phase 5 --dry-run  # 미리보기
marchive decisions --phase 5            # 실제 아카이브
marchive current --phase 5              # current.md 아카이브

# 작업 완료 후
marchive plans                          # PLAN 문서 정리
```

**교훈:**
- 자동화 ≠ 완전 자동화
- 적절한 지점: 수동 트리거 + 자동 감지
- 안전 장치 중요 (백업, dry-run)

**컨텍스트:** [[time:2025-11/14#23:58]]

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

### 2025-11-14: 고급 요약 시스템 구현 (맥락 기반, 다국어, 카테고리) ⭐⭐⭐
**결정 #27:** Phase 5 #4 - 자동 요약 고도화 구현 (맥락 기반, 주제별 분류, 다국어 지원)

**배경:**
- Phase 4에서 기본 LLM 요약 구현 완료 (Ollama + Anthropic)
- 요약 품질 개선 필요: 프로젝트 맥락 부재, 일관성 없는 카테고리, 단일 언어만 지원

**구현 사항:**

**1. 다국어 지원** (사용자 요청)
- 출력 언어 설정: `llm.output_language` (ko/en/auto)
- CLI 플래그: `msummary --lang ko/en/auto`
- 우선순위: CLI flag > config > auto-detect
- 언어 감지: 한글/영문 문자 비율 기반 (2:1 threshold)

**2. 맥락 기반 요약**
- **ContextGatherer**: 프로젝트 컨텍스트 수집
  - `.claude/memory-context.md`: 프로젝트 전체 상태
  - `decisions.md`: 기간 내 결정사항 (최근 5개)
  - `current.md`: 현재 모듈 상태
- **Smart Context Injection**:
  - today: 최소 컨텍스트 (categories만)
  - week: 전체 컨텍스트 (context + decisions + state)
  - range: 기간별 컨텍스트 (해당 기간 decisions)

**3. 카테고리 시스템**
- 프로젝트 특화 카테고리:
  - Phase Implementation
  - Feature Development
  - Bug Fixes
  - Refactoring
  - Architecture Decisions
  - Testing & Documentation
- config.yaml에서 커스터마이징 가능
- 프롬프트에 카테고리 가이드 주입 → 일관된 분류

**4. PromptBuilder**
- 동적 프롬프트 생성: base prompt + context sections
- 토큰 제한 관리: `llm.max_context_tokens` (기본 2000)
- 언어별 프롬프트: TIMELINE_SUMMARY_PROMPT_KO/EN
- 컨텍스트 truncation (토큰 초과 시)

**구현 구조:**
```
memory_tool/
├── llm/
│   ├── prompts.py         # 다국어 프롬프트, language detection
│   └── prompt_builder.py  # 동적 프롬프트 빌더
├── summary/
│   ├── context.py         # ContextGatherer
│   ├── categories.py      # 카테고리 정의
│   └── timeline_summarizer.py  # 통합
└── config.yaml            # output_language, custom_categories
```

**Trade-offs:**

**장점:**
- 프로젝트 맥락 인식 요약 (결정사항, 현재 상태 반영)
- 일관된 카테고리 분류 (프로젝트 특화)
- 다국어 지원 (한국어 사용자 편의)
- 확장 가능 (custom categories)

**단점:**
- 복잡도 증가 (3개 신규 모듈)
- 토큰 사용량 증가 (컨텍스트 주입)
- 언어 감지 오류 가능성 (단순 휴리스틱)

**대안 검토:**
- A: LLM만으로 모든 것 처리 - 단순하지만 컨텍스트 부족
- B: 고정 프롬프트만 사용 - 빠르지만 유연성 없음
- **C: 동적 프롬프트 + 컨텍스트 (채택)** - 복잡하지만 품질 우수

**테스트 결과:**
- ✅ `msummary today` (한국어) - 정상 작동
- ✅ `msummary today --lang en` (영어) - 정상 작동
- ✅ Context injection - 프로젝트 컨텍스트, 결정사항 반영 확인
- ✅ Categories - Phase Implementation, Feature Development 등 일관된 분류

**효과:**
- 요약 품질 향상 (맥락 기반 분석)
- 한국어 사용자 편의성 (네이티브 언어)
- 프로젝트 일관성 (커스텀 카테고리)
- 확장성 (다른 프로젝트 적용 가능)

**교훈:**
- 사용자 요청 반영 (다국어 지원)
- 점진적 개선 (기본 → 고급)
- 실용성 우선 (단순 휴리스틱도 충분)

**컨텍스트:** [[time:2025-11/14#23:36]]

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
