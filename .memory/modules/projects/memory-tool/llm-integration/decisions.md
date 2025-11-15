# Key Decisions

> **LLM-related decisions for memory_tool**

---

## Recent Decisions

### 2025-11-14: marchive 명령어 개선 - 결정 번호 기반 아카이브 ⭐⭐⭐
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

## See Also

**Related Modules:**
- [[projects/memory-tool/search-system]] - Vector embeddings and semantic search
- [[projects/memory-tool/core-system]] - Timeline and module data
- [[projects/memory-tool/project-management]] - Architecture decisions

---

**Total Decisions:** 2 (LLM integration and automation decisions)
