# Key Decisions

## 2025-11-13: 플랫폼 선택 - Python CLI
**결정:** Python CLI + 파일 기반

**대안 검토:**
- Bash CLI: 빠르지만 Windows 제한적, 확장 어려움
- MCP 서버: Claude 네이티브 통합이지만 초기 복잡도 높음
- VSCode Extension: 강력하지만 TypeScript 필요, 개발 시간 길음

**선택 이유:**
1. 사용자가 Python 선호
2. Windows 환경에서 안정적 (PowerShell 네이티브)
3. 확장성 우수 (나중에 MCP 추가 가능)
4. 테스트 가능하고 유지보수 쉬움
5. 단기간 내 작동 가능

**트레이드오프:**
- 초기 설정 시간 (1-2일) vs Bash (30분)
- 수용: 장기적 유지보수가 더 중요

**컨텍스트:** [[time:2025-11/13#22:50]]

---

## 2025-11-13: 기술 스택 - Python + Typer
**결정:** Python 3.10+ with typer

**대안 검토:**
- Click: 성숙하지만 보일러플레이트 많음
- argparse: 표준 라이브러리지만 타입 힌트 약함
- Fire: 간단하지만 제어 부족

**선택 이유:**
1. Typer: 타입 힌트 기반, 자동 완성, 깔끔한 API
2. FastAPI 개발자 작품 (품질 보증)
3. 문서 자동 생성
4. 점진적 복잡도 (간단하게 시작 가능)

**컨텍스트:** [[time:2025-11/13#22:52]]

---

## 2025-11-13: MVP 범위 - Phase 1 핵심 기능
**결정:** Phase 1만 구현 (m, ms, minit, mcontext)

**범위:**
- m: Timeline 기록
- ms: 검색 (로컬/KB/전체)
- minit: 프로젝트 초기화
- mcontext: Claude용 컨텍스트 빌더

**제외 (Phase 2+):**
- Atomic write + flock
- SQLite 인덱싱
- 벡터 검색
- 자동 요약
- MCP 서버

**이유:**
1. Claude Code Context 제공이 핵심 목표
2. 습관 형성이 우선 (기술보다)
3. 2주 내 작동 가능한 시스템
4. 점진적 개선 가능

**측정 기준:**
- 일일 캡처 ≥ 5
- 주간 검색 ≥ 20
- Claude Code 작업 시 자동 컨텍스트 로딩

**컨텍스트:** [[time:2025-11/13#22:54]]

---

## 2025-11-13: 검색 전략 - 점진적 개선
**결정:** Phase 1 파일+regex → Phase 2 SQLite → Phase 3 벡터

**로드맵:**
- Week 1-2: pathlib + 정규식 (또는 subprocess ripgrep)
- Week 3-4: SQLite 인덱스 (성능 개선)
- Month 2+: ChromaDB/FAISS (의미 검색)

**이유:**
1. 조기 최적화 방지
2. 실제 사용 패턴 파악 후 개선
3. 파일 기반은 디버깅 쉽고 Git 친화적

**컨텍스트:** [[time:2025-11/13#23:04]]

---

## 2025-11-13: 메타 결정 - 자기 기록
**결정:** 이 프로젝트 개발을 .memory/로 기록

**이유:**
1. 시스템 사용 사례가 됨 (dogfooding)
2. 설계 검증 (직접 사용하면서 개선)
3. 개발 과정 자체가 문서화

**방법:**
- 매 작업마다 Timeline 기록
- 주요 결정은 decisions.md에
- 진행 상황은 current.md 업데이트

**컨텍스트:** [[time:2025-11/13#23:08]]

---

## 2025-11-13: Claude Code 컨텍스트 로딩 전략
**결정:** Phase 1은 README.md + .claude/memory-context.md

**문제:**
- Claude Code 새 세션 시작 시 프로젝트 상황을 모름
- .memory/ 내용을 자동으로 읽지 않음
- 사용자가 매번 "Read X" 해야 함 (불편)

**해결 방안 검토:**
- **A: README + .claude/ (채택)** - 간단, 즉시 가능, Phase 1부터
- B: Hook (pre-command.sh) - 완전 자동, Phase 2+
- C: MCP 서버 - 네이티브 통합, Phase 3

**선택 이유:**
1. README.md의 "For Claude Code" 섹션
   - Claude가 README를 자주 읽음
   - 명시적 가이드 제공
2. .claude/memory-context.md
   - 통합 컨텍스트 파일
   - Claude Code가 주목하는 디렉토리
   - 최근 Timeline + 현재 상태 + 결정사항
3. 즉시 적용 가능 (Phase 1)

**사용 패턴:**
```bash
# 사용자 작업 종료 시
mcontext  # .claude/memory-context.md 생성

# Claude Code 재시작 시
"Read .claude/memory-context.md and continue"
```

**Phase 2+ 개선:**
- Hook으로 자동 갱신
- m 명령어 실행 시 자동 업데이트
- MCP 서버로 완전 자동화

**컨텍스트:** [[time:2025-11/13#23:47]]

---

## 2025-11-13: memory-context.md 컨텐츠 전략
**결정:** 최근 3일 링크만 제공, 상세 내용 제외

**문제:**
- Timeline을 memory-context.md에 복사하면 중복 데이터
- 파일이 비대해지면 가독성 저하
- 동기화 문제 (Single Source of Truth 위배)

**대안 검토:**
- A: 최근 7일 상세 내용 포함 - 비대함, 중복
- B: 요약 생성 - Phase 1에 LLM 없음
- **C: 링크만 제공 (채택)** - 간결, 명확, 중복 없음

**선택 이유:**
1. Timeline 원본 파일이 Single Source of Truth
2. Claude가 필요한 날짜만 선택적으로 읽음
3. 파일 크기 일정 (비대화 방지)
4. Phase 2에서 LLM 요약 추가 가능

**구현:**
```markdown
## 🕐 Recent Timeline
- 2025-11-13: .memory/timeline/2025-11/13.md
- 2025-11-12: .memory/timeline/2025-11/12.md
- 2025-11-11: .memory/timeline/2025-11/11.md
```

**컨텍스트:** [[time:2025-11/13#23:30]]

---

## 2025-11-13: m 명령어 시간 정책
**결정:** 기본 엄격(현재 시간) + 고급 옵션 Phase 1부터 제공

**문제:**
- 자정 넘어 작업 시 날짜 경계 처리
- 회고 기록 필요성 (과거 시점 기록)
- 미래 기록 방지 (플래너는 별도 고려)

**정책:**
1. **기본 (엄격):** 항상 현재 시간 사용
   ```bash
   m "OAuth 구현 완료"  # 자동으로 현재 시각
   ```

2. **고급 옵션 (유연성):**
   ```bash
   m --time "23:45" "늦게 끝난 작업"
   m --date "2025-11-12" --time "14:30" "회고"
   m --yesterday "자정 넘어서 한 작업"
   ```

3. **검증:**
   - 미래 시점: hard error (절대 불가)
   - 1년+ 과거: 경고 + 확인 (실수 방지)

**플래너 기능:**
- Phase 2로 연기
- 별도 설계 필요 (timeline vs plans 분리)
- Phase 1은 과거/현재 기록만

**컨텍스트:** [[time:2025-11/13#23:30]]

---

## 2025-11-13: Timeline 기록 전략 (메타)
**결정:** Claude가 직접 기록, 마일스톤마다 + 사용자 요청 시

**문제:**
- Claude와 대화 중 timeline 기록을 어떻게?
- 0.5초 원칙은 solo work용, 대화는 다른 전략 필요
- 너무 세밀하면 noise, 너무 거칠면 정보 손실

**전략:**
1. **기록 주체:** Claude가 Edit 도구로 직접
2. **기록 시점:**
   - A: 중요 마일스톤마다 (채택)
   - C: 사용자 요청 시 (채택)
3. **기록 입도:** 의미 있는 마일스톤만
   - ✓ "README 정적화 + guidelines 생성"
   - ✗ "README Line 18 수정"

**실천:**
- Claude가 큰 결정 후 자동 제안
- 사용자: "지금까지 기록해줘" 명시 가능
- 대화 끝에 한번에 요약 기록

**CLI 완성 후:**
```bash
m "README 리팩토링 + guidelines.md 생성"
```

**컨텍스트:** [[time:2025-11/13#23:30]]

---

## 2025-11-13: 설정 파일 전략
**결정:** Phase 1부터 config.yaml 포함, 기본값 중심

**문제:**
- 사용자마다 다른 기록 패턴
- 자동화 수준 선호도 차이
- 설정 vs 단순함 트레이드오프

**대안 검토:**
- A: Phase 1부터 설정 파일 (채택)
- B: Phase 1 고정, Phase 2부터 설정
- C: 영원히 고정

**선택 이유:**
1. 유연성 제공 (사용자 선택권)
2. 대부분은 기본값 사용 (Convention over Configuration)
3. 확장성 확보 (나중에 추가 옵션)

**Phase 1 설정 항목:**
```yaml
timeline:
  auto_record: false        # 기본값: 수동
  granularity: medium       # low/medium/high

context:
  auto_update: false        # m 실행 시 자동 mcontext
  recent_days: 3            # memory-context 링크 일수

modules:
  auto_update_current: false
```

**철학:**
- 기본값 = 최선의 관행
- 설정 = 예외적 필요
- 80%는 기본값 사용

**컨텍스트:** [[time:2025-11/13#23:55]]

---

## 2025-11-13: Claude Skill 통합
**결정:** Phase 1에 Claude Skill 포함, 중간 범위 (규칙 기반)

**배경:**
- Claude Skills = 공식 기능 (폴더 기반 도구)
- 자동 로드, 실행 가능 코드 포함
- Claude Code/API 모두 호환

**대안 검토:**
- A: Slash Command (간단하지만 수동)
- B: Hook (자동화지만 Phase 2+)
- **C: Skill (채택)** - 자연스럽고 강력
- D: MCP Server (Phase 3)

**선택 이유:**
1. Claude와 자연스러운 대화 가능
   - "오늘 작업 기록해줘" → 자동 실행
2. CLI 독립성 유지
   - Skill은 CLI 위의 래퍼
3. 점진적 확장 가능
   - Phase 1: 규칙 기반
   - Phase 2+: LLM 기반

**Skill 범위 (중간):**
- ✅ 규칙 기반 판단 (LLM 불필요)
- ✅ 자동 갱신 (설정 시)
- ✅ 스마트 래퍼
- ❌ LLM 기반 요약 (Phase 2+)
- ❌ 의미 기반 검색 (Phase 2+)

**구현:**
```
.claude/skills/memory-tool/
  SKILL.md              # 지침 및 로직
  scripts/
    record.py           # m 래퍼 + 자동 갱신
    search.py           # ms 래퍼
    context.py          # mcontext 래퍼
```

**작동 예시:**
```
사용자: "오늘 README 리팩토링 완료"
Claude: [skill 자동 로드]
        [record.py 실행]
        "✓ 기록: 23:45 | README 리팩토링 완료"
```

**일정:**
- Day 12-14: Skill 개발
- 추가 작업 2-3일
- 사용자 경험 대폭 개선

**컨텍스트:** [[time:2025-11/13#23:55]]

---

## 2025-11-13: Phase 1 로드맵 최종 확정
**결정:** 14일 일정, CLI → config → Skill

**전체 로드맵:**
```
Day 1-3:   pyproject.toml + 기본 패키지 구조
Day 4-6:   m 명령어 (Timeline 기록)
Day 7-8:   minit 명령어 (프로젝트 초기화)
Day 9-10:  ms, mcontext 명령어 (검색, 컨텍스트)
Day 11:    config.yaml (설정 파일) ⭐
Day 12-14: Claude Skill (중간 범위) ⭐
```

**우선순위:**
1. **핵심 (Day 1-10):** CLI 도구 완성
2. **개선 (Day 11):** 설정 파일
3. **통합 (Day 12-14):** Claude Skill

**측정 기준:**
- CLI 명령어 모두 작동
- config.yaml 로드/적용
- Claude Skill로 자연스러운 대화
- .claude/memory-context.md 자동 갱신

**리스크:**
- Skills 베타 버그 가능성
- → Skill 없이도 CLI 독립 작동

**컨텍스트:** [[time:2025-11/13#23:55]]

---

## 2025-11-14: CLAUDE.md 단일 진입점 전략
**결정:** 프로젝트 루트에 CLAUDE.md 생성, 모든 컨텍스트의 진입점

**문제:**
- Claude Code 새 세션 시 6개 이상의 파일을 읽어야 상황 파악 가능
- 정보 분산: README, memory-context, current.md, timeline, decisions.md...
- "지식을 쉽게 찾게 하는 도구"를 만드는데 정작 이 프로젝트 상태 파악이 어려움
- **메타 함정 (Meta Trap)**: 도구 없이 도구의 방법론을 따르려다 복잡도 증가
- Single Source of Truth 부재

**대안 검토:**
- A: .claude/START_HERE.md - 숨겨진 디렉토리, 가시성 낮음
- B: README.md 확장 - 사용자용 vs AI용 혼재
- **C: CLAUDE.md (채택)** - 명확한 시그널, 루트에서 가시성

**선택 이유:**
1. **가시성**: 루트 디렉토리에서 즉시 발견 가능
2. **관례**: README.md (사람), CLAUDE.md (AI) - 명확한 역할 분리
3. **단순성**: 경로가 짧고 명확 (CLAUDE.md vs .claude/START_HERE.md)
4. **우선순위**: 알파벳순으로 상단 배치
5. **명확성**: "이 파일은 Claude를 위한 것"이라는 명확한 메시지

**구현:**
```markdown
# For Claude Code 🤖
> **Read this file first when starting a new session.**

## ⚠️ IMPORTANT: Read Guidelines First
Read .claude/guidelines.md (사고 원칙)

## 📍 Current Status
- Phase, Stage, Next 한눈에

## 🚀 Next Actions
1-2-3 단계

## 📚 More Info
- 상세 정보 링크
```

**효과:**
- Before: 6+ 파일 탐색 필요
- After: 1개 파일로 시작, 필요시 링크
- 상황 파악 시간: 5분 → 30초
- "0.5초 포착" 철학을 프로젝트 자체에 적용

**부수 효과:**
- README.md 간소화 (For Claude Code 섹션 제거)
- .claude/ 디렉토리 역할 재정의 (도구 및 자동 생성 파일)
- 정보 계층 구조 명확화

**원칙:**
- **단일 진입점 (Single Entry Point)**
- **즉시 가시성 (Immediate Visibility)**
- **명확한 역할 분리 (Clear Separation of Concerns)**

**컨텍스트:** [[time:2025-11/14#08:20]]

---

## 2025-11-14: Timeline 정렬 전략 - 추가순 유지
**결정:** Phase 1은 추가순 유지, Phase 2에 msort 명령어로 정렬

**문제:**
- Timeline에 기록 시 추가순으로 쌓임 (시간순 아님)
- 예: `08:53 → 08:35 → 08:45 → 08:53` (시간 역전)
- 사용자가 과거 시간 기록 시 순서 뒤바뀜

**대안 검토:**
- A: 추가 시 자동 정렬 - 0.5초 위배, 복잡도 증가
- B: 추가순 유지 (현재) - 단순, 빠름
- **C: Phase 2에 msort (채택)** - 정렬은 주말에

**선택 이유:**
1. **철학 일치**: "Capture in 0.5 seconds, organize on weekends"
2. **단순성**: 추가 시 파일 끝에 append만
3. **성능**: 정렬 오버헤드 없음
4. **유연성**: 사용자가 원할 때 정렬 (msort)

**구현 (Phase 2):**
```bash
msort                      # 오늘 timeline 정렬
msort --date 2025-11-14    # 특정 날짜 정렬
msort --week               # 이번 주 전체 정렬
```

**원칙:**
- **Capture ≠ Organize**: 기록과 정리는 분리
- **Defer Optimization**: 조기 최적화 방지
- **User Control**: 정렬 시점은 사용자가 결정

**Phase 1 동작:**
- 파일 끝에 추가만
- 시간 검증만 (미래 차단, 과거 경고)
- 정렬은 사용자가 수동 또는 Phase 2 msort

**컨텍스트:** [[time:2025-11/14#08:55]]

---

## 2025-11-14: PowerShell 프로필 지원 추가
**결정:** malias에 --powershell 플래그 추가, 프로필 직접 수정

**문제:**
- 일반 PowerShell에서는 배치 파일 alias 작동
- VSCode PowerShell에서는 작동 안 함
- 원인: 서로 다른 프로필 사용, PATH 인식 차이

**대안 검토:**
- A: VSCode 재시작으로 해결 - 임시방편
- B: 수동으로 프로필 수정 - 번거로움
- **C: --powershell 플래그 (채택)** - 자동화, 안전

**선택 이유:**
1. **호환성**: 모든 PowerShell 터미널 지원 (일반, VSCode, Windows Terminal)
2. **PATH 불필요**: 프로필에 직접 추가하므로 PATH 설정 필요 없음
3. **명시적**: 배치 vs 프로필 선택권
4. **안전**: CurrentUserAllHosts 프로필 사용, 기존 내용 존중

**구현:**
```bash
malias install --powershell    # 프로필에 function 추가
malias list --powershell       # 프로필 상태 확인
malias uninstall --powershell  # 프로필에서 제거
```

**기술:**
- `$PROFILE.CurrentUserAllHosts` 경로 자동 탐지
- 섹션 마커로 memory_tool 영역 관리
- 중복 방지, 스마트 제거

**효과:**
- VSCode에서도 즉시 작동
- 터미널 재시작 또는 `. $PROFILE` 만으로 적용

**컨텍스트:** [[time:2025-11/14#13:33]]

---

## 2025-11-14: CLAUDE.md 자동 생성 반대 결정 ⭐⭐
**결정:** minit이 CLAUDE.md를 자동 생성/수정하지 않음. 템플릿만 제공.

**제안:**
- minit 실행 시 CLAUDE.md 존재 확인
- 없으면: 자동 생성
- 있으면: 내용 추가
- 편리하고 통합이 쉬움

**비판적 검토 (5가지 관점):**

1. **침투성 문제 (Invasiveness)**
   - memory_tool = 도구 (Tool)
   - CLAUDE.md = 프로젝트 전체 설정
   - 도구가 프로젝트 설정을 수정하는 것은 월권

2. **Loose Coupling 원칙 위반** ⚠️⚠️
   - memory_tool의 5대 원칙 중 하나
   - 자동 수정 = 프로젝트와 강결합
   - 자기 철학 위배

3. **기존 파일 덮어쓰기 위험**
   - 사용자가 정성스럽게 작성한 CLAUDE.md
   - 나중에 minit 실행 시 내용 변경
   - 데이터 손실 가능성

4. **사용자 의도 무시**
   - 프로젝트 A: 통합 원함
   - 프로젝트 B: memory는 보조 도구로만
   - 자동 생성은 B의 의도 무시

5. **의존성 역전**
   - 올바름: 프로젝트 → memory_tool 사용
   - 잘못됨: memory_tool → 프로젝트 제어

**최종 결정:**
```bash
minit
# → .memory/templates/CLAUDE.md.template 생성
# → 안내 메시지: "Copy sections to your CLAUDE.md"
```

**원칙:**
- memory_tool은 **도구**이지 **프레임워크**가 아님
- 도구는 자기 영역(.memory/)에만 관여
- 프로젝트 설정은 사용자가 완전히 제어

**교훈:**
- 편의성 < 안전성
- 단기 편리함 < 장기 올바름
- 비판적 사고의 중요성

**컨텍스트:** [[time:2025-11/14#13:33]]

---

## 2025-11-14: 보너스 명령어 우선 구현
**결정:** Phase 2 전에 mtoday, mweek, mstatus 구현

**상황:**
- Phase 1 Extended 완료 (5개 core 명령어)
- 사용자: 실사용 프로젝트 부족 → 피드백 수집 곤란
- 제안: Phase 2로 바로 진행 vs 보너스 명령어 먼저

**대안 검토:**
- A: 보너스 명령어 먼저 (채택)
- B: Phase 2로 바로 진행
- C: 실사용 후 피드백 수집

**선택 이유:**
1. **사용성 향상**: mtoday/mweek는 실제로 자주 쓰임
2. **구현 간단**: 총 2시간 예상 (Timeline 확장만)
3. **dogfooding 강화**: 더 많은 사용 사례
4. **Phase 2 준비**: 완성도 높은 상태로 진입

**구현 내용:**
- mtoday: 오늘 timeline 표시
- mweek: 이번 주 timeline 표시 (월요일~오늘)
- mstatus: 프로젝트 통계 (날짜 수, 항목 수, 모듈 수, 크기)

**기술적 개선:**
- Timeline.get_today(), get_week() 추가
- Windows 이모지 문제 해결 (sanitize_output)
- 통계 수집 로직

**결과:**
- Phase 1 Extended + Bonus 완료
- 총 8개 명령어 작동 (5 core + 3 bonus)

**컨텍스트:** [[time:2025-11/14#13:42]]

---

## 2025-11-14: config.yaml 고급 기능 구현 ⭐
**결정:** utils/config.py 모듈 생성, auto_update 기능 활성화

**구현:**
- **utils/config.py**: Config 클래스, 설정 로드/검증/기본값
- **auto_update**: m 명령어 실행 시 자동으로 mcontext 실행
- **설정 검증**: 잘못된 값 차단 (granularity, recent_days 등)
- **기본값 우선**: config.yaml 없어도 작동

**기술적 세부사항:**
```python
# Config 클래스 주요 기능
- load(): 설정 로드 (기본값 + 파일 병합)
- _validate(): 설정 값 검증
- get(key_path): 점 표기법으로 설정 접근
- auto_update_enabled: 편의 속성
```

**통합:**
- cli.py: record 함수에서 auto_update 확인
- context/builder.py: Config 사용하도록 리팩토링
- utils/__init__.py: Config export

**효과:**
- 매번 mcontext 수동 실행 불필요
- 설정 중앙화 및 검증
- 확장 가능한 구조 (Phase 2 기능 추가 용이)

**설정 항목 (config.yaml):**
```yaml
context:
  auto_update: true      # m 실행 시 자동 mcontext
  recent_days: 3         # memory-context 링크 일수

timeline:
  granularity: medium    # low/medium/high
  warn_old_days: 365     # N일 이상 과거 경고

search:
  max_file_size: 1048576 # 1MB
  exclude_patterns: []
```

**테스트 완료:**
- ✅ auto_update false: 자동 업데이트 없음
- ✅ auto_update true: .claude/memory-context.md 자동 갱신
- ✅ recent_days 변경: 7일로 확장 작동
- ✅ 잘못된 설정: 검증 에러 발생

**컨텍스트:** [[time:2025-11/14#14:49]]

---

## 2025-11-14: Claude Skill 개발 완료 ⭐⭐⭐
**결정:** 규칙 기반 Claude Skill 구현, Phase 1 Final 완성

**구현:**
- **.claude/skills/memory-tool/**: Skill 디렉토리 생성
- **SKILL.md**: 핵심 Skill 정의 (300+ 줄)
  - 자동 기록 트리거 (명시적 요청, 결정, 마일스톤)
  - 검색 트리거 (명시적, 과거 작업 질문)
  - 컨텍스트 업데이트 규칙
  - 5가지 자동화 규칙
- **README.md**: 사용 가이드 및 트러블슈팅
- **TEST_SCENARIOS.md**: 15개 테스트 케이스

**핵심 기능:**
1. **자동 기록**: 중요한 결정/마일스톤 감지 시 제안
2. **검색 우선**: 과거 작업 질문 시 자동 검색
3. **컨텍스트 인식**: 세션 시작 시 최신 상태 확인
4. **선택적 기록**: 중요한 항목만 (over-recording 방지)

**자동화 규칙 (Rule-based, Phase 1):**
```
Rule 1: Proactive Recording
  - 결정 감지 → 기록 제안 (자동 실행 아님, 투명성)

Rule 2: Search Before Answering
  - 과거 작업 질문 → ms 실행 → 답변

Rule 3: Context-Aware
  - 세션 시작 시 context 신선도 확인
  - 오래되었으면 mcontext 실행

Rule 4: Batch Recording
  - 여러 항목 → 사용자 확인 후 일괄 기록

Rule 5: Don't Over-Record
  - 기록 대상: 결정, 완성, 발견, 선택, 리팩토링
  - 기록 제외: 잡담, 질문, 임시 탐색, 구현 세부사항
```

**통합 포인트:**
- config.yaml: auto_update 설정 인식
- CLI 명령어: m, ms, mcontext, mtoday, mweek 활용
- 에러 처리: 실패 시 graceful degradation

**테스트 시나리오 (15개):**
1. 명시적 기록 요청
2. 결정 기록
3. 검색 요청
4. 세션 시작
5. 세션 종료 요약
6. 마일스톤 완성
7. 배치 기록
8. Over-recording 방지 (negative test)
9. KB 검색
10. 오늘 요약
11. auto_update 설정 테스트
12. manual context 업데이트
13. 에러 핸들링
14. Regex 검색
15. 주간 요약

**Phase 1 vs Phase 2+:**
- Phase 1 (현재): 규칙 기반, 명시적 패턴 매칭
- Phase 2+: LLM 기반 중요도 판단, 의미 기반 검색

**효과:**
- Claude가 자연스럽게 memory_tool 사용
- 사용자는 명령어 외우지 않아도 됨
- 대화 흐름 방해 없이 지식 포착
- "0.5초 포착" 철학을 대화형 환경에 적용

**검증 방법:**
- 새 Claude Code 세션에서 테스트
- TEST_SCENARIOS.md의 15개 케이스 실행
- Skill 로드 확인 (.claude/skills/ 경로)

**컨텍스트:** [[time:2025-11/14#15:04]]

---

## 2025-11-14: SKILL.md 공식 형식 수정 ⭐
**결정:** Claude Skills 공식 스펙 준수 (YAML frontmatter + Markdown)

**문제:**
- 초기 SKILL.md: 순수 Markdown (공식 형식 미준수)
- 공식 문서 확인: YAML frontmatter 필수

**공식 요구사항:**
```yaml
---
name: skill-name  # lowercase, numbers, hyphens only (max 64 chars)
description: Brief description  # what + when to use (max 1024 chars)
---
```

**수정 내용:**
1. **YAML frontmatter 추가:**
   ```yaml
   name: memory-tool
   description: Integrates with memory_tool CLI to record important
                decisions and milestones to timeline, search past work,
                and maintain project context. Use when user makes decisions,
                completes features, asks about past work, or at session
                start/end. Commands are m (record), ms (search),
                mcontext (update context), mtoday/mweek (view timeline).
   ```

2. **Markdown 구조 재구성:**
   - **## Instructions**: 명확한 단계별 지침 (7개 섹션)
     1. When to Record (A-D 트리거)
     2. When to Search (명시적/암묵적)
     3. Context Management (세션 시작/종료)
     4. Timeline Review (mtoday/mweek)
     5. Batch Recording (3단계)
     6. Error Handling (graceful degradation)
     7. Response Format (일관성)

   - **## Examples**: 8개 구체적 예시
     1. Decision Recording
     2. Milestone Recording
     3. Search Before Answering
     4. Session Start
     5. Session End Summary
     6. Batch Recording
     7. Don't Over-Record (negative)
     8. Search with No Results

   - **## Configuration Awareness**: config.yaml 연동
   - **## Best Practices**: 7가지 원칙
   - **## Testing**: TEST_SCENARIOS.md 참조

**변경 전 vs 후:**
- Before: 순수 Markdown (300+ 줄)
- After: YAML frontmatter + Markdown (327 줄)

**장점:**
- Claude Code가 Skill을 올바르게 인식
- description에 명확한 트리거 포함 (discovery 개선)
- 공식 스펙 준수로 안정성 확보
- 향후 Claude Code 업데이트 호환성

**참고:**
- 공식 문서: https://code.claude.com/docs/en/skills
- allowed-tools 필드: 현재 불필요 (모든 도구 사용)

**컨텍스트:** [[time:2025-11/14#15:20]]

---

## 2025-11-14: Skill 작업 흐름 개선 ⭐⭐
**결정:** 자연스러운 중단점 후 기록 제안, 세션 종료 시 기록 제거

**문제:**
- 초기 SKILL.md: 대화 중 즉시 기록 제안 → 작업 흐름 방해
- 세션 종료 시 기록: 불가능 (세션 이미 종료됨)

**개선:**
1. **핵심 원칙 추가:**
   ```
   Do NOT interrupt workflow with recording.
   Record at natural breakpoints or when explicitly requested.
   ```

2. **자연스러운 중단점 정의:**
   - ✅ 파일 저장 완료 후
   - ✅ 코드/테스트 실행 완료 후
   - ✅ 기능 구현 완료 후
   - ✅ 버그 수정 검증 후
   - ✅ 리팩토링 완료 후

3. **올바른 패턴:**
   ```
   [Complete the work first]
   → Show results to user
   → THEN suggest: "Shall I record this?"
   ```

4. **명시적 요청 시:**
   - "기록해줘", "record this" → 즉시 기록

5. **제거된 트리거:**
   - ❌ 세션 종료 시 기록 (불가능)
   - ❌ 대화 중간 기록 제안 (방해)
   - ❌ "That's all for today" 패턴

**Before vs After:**

Before (문제):
```
User: "Let's use PostgreSQL"
Claude: [즉시] "Let me record this decision..."  ← 방해
```

After (개선):
```
User: "Add authentication"
Claude: [구현 → 테스트 → 완료]
Claude: "I've completed JWT authentication. Tests passing.

         Shall I record this milestone?  ← 완료 후 제안
         - Feature complete: JWT authentication"
```

**Best Practices 추가:**
1. Don't Interrupt Workflow (최우선)
2. Respect User Focus (flow state 존중)

**효과:**
- 작업 흐름 방해 없음
- 자연스러운 대화 흐름 유지
- 사용자가 집중 상태일 때 방해하지 않음
- 실제로 작동 가능한 패턴만 포함

**참고:**
- 사용자 지적으로 발견된 중요한 UX 문제
- 세션 종료 시 Claude는 이미 작업 불가능

**컨텍스트:** [[time:2025-11/14#16:08]]

---

## 2025-11-14: 모듈 아카이브 구조 결정 (중앙 _index.md) ⭐⭐
**결정:** 아카이브된 모듈은 `archive/_index.md`에 중앙 집중 방식으로 기록

**배경:**
- Phase 2 module 명령어 개발 중
- 아카이브된 모듈 정보를 어디에 기록할지 선택 필요

**고려한 옵션:**

**A. 모듈별 archive.md** (분산)
```
archive/
  ├── memory-system/
  │   └── archive.md  ← 이 모듈의 아카이브 정보
  └── load-system/
      └── archive.md  ← 이 모듈의 아카이브 정보
```
- ✅ 각 모듈이 자체 완결적
- ❌ 전체 아카이브 목록 확인 어려움

**B. 중앙 _index.md** (집중) ← 선택
```
archive/
  ├── _index.md      ← 모든 아카이브 기록
  ├── memory-system/
  └── load-system/
```
- ✅ 모든 아카이브 이력을 한눈에 확인
- ✅ Timeline 방식과 일관성 (중앙 집중)
- ✅ `module list --archived` 구현 쉬움
- ❌ 모듈별 정보가 분리됨

**C. 둘 다** (중복)
- ❌ 중복 데이터, 동기화 문제

**최종 선택: 옵션 B**

**근거:**
1. **일관성:** Timeline도 중앙 집중식 (날짜별 파일)
2. **사용 패턴:** "어떤 것들이 아카이브되었는지" 목록으로 확인
3. **단순성:** 정보가 한 곳에, 관리 쉬움
4. **구현 용이:** 단일 파일 읽기/쓰기만 필요

**구현:**
```yaml
# archive/_index.md
## memory-system
- **Archived:** 2025-11-20
- **Reason:** Project completed
- **Location:** ./memory-system/
```

**Trade-offs:**
- 모듈 디렉토리만으로는 아카이브 이유를 모름
- But: 아카이브 조회는 `module list --archived`로 한 번에

**효과:**
- 깔끔한 아카이브 관리
- 빠른 목록 조회
- 유지보수 간단

**컨텍스트:** [[time:2025-11/14#17:34]]

---

## 2025-11-14: Phase 2 범위 확정 (원 계획 유지) ⭐
**결정:** Phase 2 원 계획대로 진행 - 고급 검색, msort, 모듈 관리 모두 구현

**배경:**
- Phase 2 시작 시점에서 범위 재검토
- 점진적 확장 vs 빅뱅 릴리스 논의

**제안된 대안:**
1. 고급 검색만 우선 구현 → 실사용 → 다음 결정
2. 원 계획대로 3가지 모두 구현

**사용자 결정:** "원 계획대로 갑니다"

**근거 (사용자 관점):**
- msort: 사용자가 사용할 때 중요함
- module 자동화: 사용자가 사용할 때 중요함
- 완전한 Phase 2 완성 선호

**결과:**
- 3가지 기능 모두 구현 및 테스트 완료
- Phase 2 목표 100% 달성
- 일관된 릴리스

**효과:**
- 사용자 요구사항 명확히 반영
- 완전한 기능 세트 제공
- Phase 3 준비 완료

**컨텍스트:** [[time:2025-11/14#16:53]]

---

## 2025-11-14: msort alias 추가 ⭐
**결정:** msort를 malias에 포함, module은 제외

**배경:**
- Phase 2에서 msort, module 명령어 추가
- alias 필요성 검토

**결정:**
- ✅ msort: alias 추가
- ❌ module: alias 없음

**근거:**

**msort alias 추가:**
- 단순한 인자 구조 (`msort today`, `msort all`)
- 자주 사용 가능 (timeline 정리)
- 명확한 의미
- 짧고 기억하기 쉬움

**module alias 제외:**
- 서브커맨드 구조 (`module create`, `module list`, `module archive`)
- 사용 빈도 낮음 (모듈 관리는 가끔만)
- 짧은 alias 어려움 (`mmodule` 너무 길고, `mm`/`mod`는 불명확)
- 풀 커맨드 사용 권장: `python -m memory_tool module ...`

**구현:**
```python
ALIASES = {
    # ...
    "msort": ("sort", "Sort timeline by time"),  # 추가
    # ...
}
```

**효과:**
- 자주 쓰는 msort는 빠르게 접근
- module은 명확성 유지
- alias 개수 적정 (8개)

**컨텍스트:** [[time:2025-11/14#17:39]]

---

## 2025-11-14: 자동 요약 시스템 통합 구현 ⭐⭐⭐
**결정:** Phase 4로 전체 통합 자동 요약 시스템 구현

**배경:**
- Phase 3 벡터 검색 완료
- 지식 포착은 완성, 이제 자동 요약으로 효율성 극대화
- Timeline 누적 시 수동 요약의 한계

**구현 범위:**
1. **Claude 대화 요약** - 세션 후 대화 내용을 LLM으로 요약하고 Timeline에 기록
2. **Timeline 요약 (msummary)** - 주간/일일 Timeline을 분석하여 핵심 내용 추출
3. **모듈 자동 요약** - 모듈 문서를 분석하여 요약 자동 생성

**기술 스택:**
- Anthropic API (Claude API 직접 사용)
- 프롬프트 엔지니어링 (요약 품질 최적화)
- config.yaml 통합 (API 키, 모델 설정)

**대안 검토:**
- A: Claude 대화 요약만 (부분)
- B: Timeline 요약만 (부분)
- **C: 전체 통합 (채택)** - 완전한 자동 요약 생태계

**선택 이유:**
1. **시너지 효과**: 3가지 기능이 유기적으로 연결
2. **완전한 자동화**: 포착 → 정리 → 요약 전체 흐름
3. **장기적 가치**: 누적된 지식의 효율적 활용
4. **차별화**: 단순 기록이 아닌 지능형 지식 관리

**설계 원칙:**
- **선택적 사용**: LLM 없어도 기본 기능 작동
- **비용 인식**: API 호출 최소화, 사용자 제어
- **품질 우선**: 정확한 요약 > 빠른 요약
- **투명성**: 요약 과정 사용자에게 명시

**구현 계획:**
1. llm/ 모듈 생성 (Anthropic API 통합)
2. summary/ 모듈 생성 (요약 로직)
3. msummary 명령어 (Timeline 요약)
4. Skill 통합 (Claude 대화 자동 요약)
5. 모듈 요약 자동화

**측정 기준:**
- 요약 품질: 원본 대비 핵심 보존율 > 80%
- 길이: 원본 대비 10-30% 수준
- 정확성: 사실 오류 0건
- 사용성: 명령어 1회로 즉시 생성

**리스크 및 완화:**
- 리스크: API 비용 증가
  - 완화: 사용자 명시적 호출만, 캐싱 활용
- 리스크: 요약 품질 저하
  - 완화: 프롬프트 최적화, few-shot 예시
- 리스크: API 장애 시 기능 마비
  - 완화: graceful degradation, 기본 기능 독립

**Phase 4 목표:**
- LLM 통합 완성
- 3가지 요약 기능 모두 작동
- config.yaml LLM 설정 추가
- Skill에서 자동 요약 지원
- README 업데이트

**컨텍스트:** [[time:2025-11/14#21:37]]

---
