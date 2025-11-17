# Memory Tool

**시간-공간 통합 지식 체계** - Timeline 기반 작업 기록 & Claude Code 자동 컨텍스트 제공

---

## 특징

- ⚡ **0.5초 포착**: `m "message"` - 즉시 timeline에 기록
- 🔍 **통합 검색**: 로컬/KB/전체 프로젝트 검색 (regex 지원)
- 🤖 **Claude Code 통합**: `.claude/memory-context.md` 자동 생성
- 📂 **프로젝트 격리**: 각 프로젝트는 독립적인 `.memory/`
- 🚀 **별칭 시스템**: 배치/PowerShell 프로필 자동 설정
- 🐶 **Dogfooding**: 이 프로젝트 자체가 .memory/로 기록됨

---

## 빠른 시작

### 설치

**요구사항:** Python 3.10+

#### Option 1: 단독 사용 (권장)

```bash
# GitHub에서 설치
pip install git+https://github.com/hanyki111/memory_tool.git

# 또는 로컬 clone 후 설치
git clone https://github.com/hanyki111/memory_tool.git
cd memory_tool
pip install -e .
```

#### Option 2: 다른 프로젝트에서 라이브러리로 사용

```bash
# 프로젝트 구조
your-workspace/
├── memory_tool/          # git clone한 memory_tool
└── your-project/         # 당신의 프로젝트

# your-project/requirements.txt에 추가
-e ../memory_tool

# 설치
cd your-project
pip install -r requirements.txt
```

📚 **자세한 설치 가이드:** [INSTALLATION.md](docs/INSTALLATION.md) | **통합 가이드:** 아래 [다른 프로젝트에서 사용하기](#다른-프로젝트에서-사용하기) 참조

### 기본 사용

```bash
# 1. 프로젝트 초기화 (한 번만)
minit

# 2. 작업 기록
m "OAuth 구현 시작"
m "결정: Passport.js 선택"
m "테스트 통과"

# 3. 검색
ms "OAuth"              # 이 프로젝트만
ms --with-kb "pattern"  # 개인 KB 포함
ms --all "keyword"      # 모든 프로젝트

# 4. 오늘 작업 확인
mtoday

# 5. Claude Code용 컨텍스트 생성
mcontext
```

### 별칭 설치 (선택)

**Windows 배치 파일:**

```bash
python -m memory_tool malias install         # 전체 설치
python -m memory_tool malias install m ms     # 특정 명령어만
```

**PowerShell 프로필 (추천):**

```bash
python -m memory_tool malias install --powershell
```

설치 후 모든 터미널(PowerShell, VSCode, Windows Terminal)에서 작동합니다.

---

## 다른 프로젝트에서 사용하기

memory_tool은 **CLI 도구**로 설계되었습니다. 대부분의 사용자는 명령어를 통해 사용해야 합니다.

### 🎯 권장 사용 방법: CLI 도구로 사용

이 방법은 **모든 일반 프로젝트**에 권장됩니다.

#### 1. memory_tool 설치

```bash
# 방법 A: GitHub에서 clone (권장)
git clone https://github.com/hanyki111/memory_tool.git
cd memory_tool
pip install -e .

# 방법 B: pip로 설치 (출시 후)
pip install memory_tool
```

#### 2. 프로젝트 초기화

```bash
cd your-project

# .memory/ 및 .claude/ 구조 생성
python -m memory_tool.cli init
# 또는 alias 설치 후: minit
```

**자동 생성되는 구조:**

```
your-project/
├── .memory/                  # 📚 지식 저장소
│   ├── timeline/            # 시간순 기록
│   ├── modules/             # 주제별 정리
│   ├── concepts/            # 개념 문서
│   └── config.yaml          # 설정
│
└── .claude/                  # 🤖 Claude Code 통합
    ├── skills/
    │   └── memory-tool/     # ⭐ memory_tool 스킬 자동 복사
    │       ├── SKILL.md
    │       └── ...
    └── guidelines.md         # ⭐ 사고 원칙 자동 복사
```

#### 3. 일상적인 사용

```bash
# 기록
m "작업 내용"

# 검색
ms "검색어"

# Claude Code 컨텍스트 생성
mcontext

# 오늘의 타임라인
mtoday

# 주간 타임라인
mweek
```

#### 4. Claude Code에서 자동 통합

**중요:** `minit`을 실행하면 `.claude/` 구조가 자동 생성됩니다:

- ✅ `.claude/skills/memory-tool/` - memory_tool 자동화 스킬

Claude Code가 자동으로 이 스킬을 사용하여:

- 적절한 시점에 timeline 기록 제안
- 과거 작업 검색 및 분석
- 컨텍스트 업데이트 관리

**세션 시작 전:**

```bash
# 컨텍스트 업데이트 (Claude가 프로젝트 상태 파악)
mcontext
```

### 트러블슈팅

**Q: `minit` 명령을 찾을 수 없습니다**

```bash
# memory_tool이 설치되었는지 확인
pip list | grep memory

# 설치되지 않았다면
pip install -e /path/to/memory_tool

# 또는 alias가 설치되지 않았다면
python -m memory_tool.cli alias install
```

**Q: `.claude/` 폴더가 생성되지 않았습니다**

```bash
# minit을 다시 실행하면 .claude/ 구조 생성
python -m memory_tool.cli init --force
```

---

## 명령어 레퍼런스

### `m` - Timeline 기록

```bash
# 기본 (현재 시간)
m "OAuth 구현 완료"

# 시간 지정
m --time "23:45" "늦게 끝난 작업"

# 과거 날짜
m --date "2025-11-12" --time "14:30" "회고 기록"

# 어제 작업
m --yesterday "자정 넘어서 한 작업"
```

**검증:**

- 미래 시간: 차단 (hard error)
- 1년+ 과거: 경고 + `--force` 필요

### `minit` - 프로젝트 초기화

```bash
# 기본 초기화
minit

# 개인 KB 연결
minit --kb

# 강제 재초기화
minit --force
```

생성 구조:

```
.memory/                      # 지식 저장소
  timeline/                   # 시간순 기록
  modules/                    # 주제별 정리
  concepts/                   # 개념 문서
  docs/                       # 문서
  config.yaml
  README.md

.claude/                      # Claude Code 통합
  skills/memory-tool/         # memory_tool 자동화 스킬
    SKILL.md
    README.md
    TEST_SCENARIOS.md
    TESTING_GUIDE.md
  guidelines.md               # 사고 원칙
```

### `ms` - 검색

```bash
# 기본 검색 (로컬만)
ms "OAuth"

# 개인 KB 포함
ms --with-kb "authentication"

# 모든 프로젝트
ms --all "pattern"

# 옵션
ms "query" --case              # 대소문자 구분
ms "query" --max 50            # 최대 결과 수
ms "query" --no-context        # context 라인 숨김

# Regex 지원
ms "func.*Auth"
ms "TODO|FIXME"
```

### `mcontext` - Claude 컨텍스트 생성

```bash
# 기본 (최근 3일)
mcontext

# 출력 경로 지정
mcontext --output custom-path.md
```

생성 파일: `.claude/memory-context.md`

- 최근 N일 timeline 링크
- 활성 모듈 current.md 링크

### `mtoday` - 오늘 작업 보기

```bash
mtoday
```

### `mweek` - 이번 주 작업 보기

```bash
mweek  # 월요일~오늘
```

### `mstatus` - 프로젝트 통계

```bash
mstatus
```

표시 항목:

- Timeline 날짜 수 / 총 항목 수
- 모듈 수
- 전체 크기

### `msort` - Timeline 정렬 ⭐ NEW

```bash
# 오늘 timeline 정렬
msort today

# 특정 날짜 정렬
msort 2025-11-14

# 모든 timeline 정렬
msort all

# 백업 없이 정렬
msort today --no-backup
```

**기능:**

- Timeline 항목을 시간순으로 자동 재정렬
- 기존 파일 자동 백업 (.bak)
- HH:MM, H:MM 형식 모두 지원

### `module` - 모듈 관리 ⭐ NEW

```bash
# 새 모듈 생성
python -m memory_tool module create auth-system --desc "인증 시스템"

# 모듈 목록 (활성)
python -m memory_tool module list

# 모듈 목록 (아카이브 포함)
python -m memory_tool module list --archived

# 모듈 아카이브 (전체 경로)
python -m memory_tool module archive projects/memory-tool/core-system --reason "Phase 완료"

# 모듈 아카이브 (짧은 이름으로 자동 검색) ⭐ NEW
python -m memory_tool module archive core-system --reason "Phase 완료"
# → 자동으로 'projects/memory-tool/core-system' 찾음

# 모듈 복원
python -m memory_tool module unarchive auth-system
```

**모듈 자동 검색:** ⭐ NEW
- `archive` 액션에서 모듈명만 입력하면 자동 검색
- 상위/하위 모듈 구분 없이 모든 계층 검색
- 정확히 1개 발견 시 자동 사용

**기능:**

- 자동 템플릿 생성 (module.md, current.md, decisions.md, dependencies.md, interface.md)
- 중앙 아카이브 인덱스 (\_index.md)
- 모듈 생명주기 관리

### `malias` - 별칭 관리

```bash
# 배치 파일 설치
malias install              # 전체
malias install m ms         # 특정 명령어
malias uninstall            # 제거
malias list                 # 상태 확인

# PowerShell 프로필 설치
malias install --powershell
malias list --powershell
malias uninstall --powershell
```

설치 경로:

- 배치: `%LOCALAPPDATA%\memory-tool\bin\`
- PowerShell: `$PROFILE.CurrentUserAllHosts`

---

## 고급 명령어 가이드

### `msummary` - LLM 기반 요약 ⚡

Timeline이나 모듈을 AI로 자동 요약합니다.

```bash
# 오늘 작업 요약
msummary today

# 이번 주 작업 요약
msummary week

# 특정 날짜 요약
msummary 2025-11-14

# 날짜 범위 요약
msummary 2025-11-01:2025-11-14

# 특정 모듈 요약 (전체 경로)
msummary --module projects/memory-tool/core-system

# 특정 모듈 요약 (짧은 이름으로 자동 검색) ⭐ NEW
msummary --module core-system
# → 자동으로 'projects/memory-tool/core-system' 찾음

# 언어 지정 (한국어/영어/자동)
msummary today --lang ko
msummary today --lang en

# 파일로 저장
msummary week --output summary.md
```

**설정 방법:**

**Option 1: Anthropic API (Claude)**
```bash
# 환경 변수
export ANTHROPIC_API_KEY="your-api-key"

# 또는 config.yaml
llm:
  api_key: "your-api-key"
  provider: "anthropic"
  model: "claude-3-5-sonnet-20241022"
```

**Option 2: Ollama (로컬, 무료)**
```bash
# config.yaml
llm:
  provider: "ollama"
  model: "llama3"
  base_url: "http://localhost:11434"
```

**사용 시나리오:**
- 장기 작업 후 진행 상황 파악
- 주간/월간 리포트 작성
- 프로젝트 상태 요약
- Claude에게 전달할 컨텍스트 정리

### `marchive` - 문서 아카이브 📦

누적된 `decisions.md`, `current.md`, `PLAN-*.md`를 아카이브하여 파일 크기를 관리합니다.

```bash
# Decisions 아카이브 (최근 10개만 유지)
marchive decisions

# 최근 15개 유지
marchive decisions --keep-recent 15

# 특정 번호까지 아카이브 (#1-#25)
marchive decisions --up-to 25

# Phase 기반 아카이브 (Phase 1-5)
marchive decisions --phase 5

# Dry-run (미리보기)
marchive decisions --keep-recent 10 --dry-run

# Current 아카이브
marchive current --phase 5

# Plans 아카이브
marchive plans

# 특정 모듈 지정 (전체 경로)
marchive decisions --module projects/memory-tool/core-system --keep-recent 10

# 특정 모듈 지정 (짧은 이름으로 자동 검색) ⭐ NEW
marchive decisions --module core-system --keep-recent 10
# → 자동으로 'projects/memory-tool/core-system' 찾음

# 모듈명만으로 검색 (상위/하위 구분 없음)
marchive decisions --module website
# → 'projects/website' 자동 검색
```

**모듈 자동 검색 기능:** ⭐ NEW
- 모듈명만 입력하면 `.memory/modules/`에서 자동 검색
- 정확히 1개 발견: 자동으로 사용하고 경로 표시
- 여러 개 발견: 선택 가능한 목록 표시
- 발견 안 됨: 에러 메시지와 함께 모듈 목록 확인 방법 안내

**예시:**
```bash
# 짧은 이름 입력
marchive decisions --module core-system

# 출력:
# Resolved 'core-system' -> 'projects/memory-tool/core-system'
# [OK] Archived 20 decisions
```

**작동 방식:**
1. 오래된 결정들을 `archive/decisions-1-25.md`로 이동
2. `decisions.md`에는 최근 결정만 유지
3. 원본 파일 자동 백업 (`.bak`)
4. 링크 자동 업데이트

**언제 사용하나:**
- `decisions.md`가 300+ 줄로 길어졌을 때
- Phase 전환 시
- 문서 정리가 필요할 때

### `mplan` - 작업 계획 관리 📋

프로젝트 계획과 작업(Task)을 체계적으로 관리합니다.

```bash
# 새 계획 생성
mplan create "API 개발" --desc "RESTful API 구현" --due 2025-12-31

# 태그 추가
mplan create "인증 시스템" --tag backend --tag security

# 모든 계획 목록
mplan list

# 계획 상세 보기
mplan show api-development

# 작업 추가
mplan add api-development "User CRUD API 구현"
mplan add api-development "인증 미들웨어 추가"

# 작업 완료 표시
mplan done api-development "User CRUD API 구현"

# 계획 삭제
mplan delete api-development
```

**Task 상태:**
- `[ ]` - Pending (대기)
- `[~]` - In Progress (진행 중)
- `[x]` - Completed (완료)
- `[!]` - Blocked (차단됨)

**생성 파일:** `.memory/plans/20251215-api-development.md`

**언제 사용하나:**
- 복잡한 기능 개발 시 작업 추적
- 프로젝트 로드맵 관리
- Timeline과 별도로 구조화된 계획 필요할 때

### `mindex` - SQLite 검색 인덱스 🔍

SQLite FTS5를 사용하여 검색 속도를 **10-100배** 향상시킵니다.

```bash
# 전체 인덱싱 (변경된 파일만)
mindex

# 강제 전체 재인덱싱
mindex --force

# 상태 확인
mindex --check

# 통계 보기
mindex --stats

# 인덱스 최적화
mindex --optimize

# Vacuum (공간 회수)
mindex --vacuum
```

**인덱싱 대상:**
- `.memory/timeline/**/*.md` - Timeline 항목
- `.memory/modules/**/decisions.md` - 주요 결정
- `.memory/modules/**/current.md` - 현재 상태
- `.memory/concepts/**/*.md` - 개념 문서

**성능:**
- 일반 검색 (regex): 100-500ms
- 인덱스 검색 (FTS5): 5-20ms (10-100배 빠름)

**인덱스 파일:** `.memory/.index.db`

**언제 사용하나:**
- Timeline이 1000+ 항목으로 많을 때
- 검색이 느려졌을 때
- 프로젝트 초기 설정 시

---

## 고급 워크플로우

### 주간 정리 워크플로우

```bash
# 1. 이번 주 작업 확인
mweek

# 2. 이번 주 요약 생성
msummary week --output weekly-summary.md

# 3. Timeline 정렬
msort all

# 4. Decisions 아카이브 (20개 이상이면)
marchive decisions --keep-recent 15 --dry-run  # 미리보기
marchive decisions --keep-recent 15            # 실행

# 5. 인덱스 업데이트
mindex
```

### Phase 전환 워크플로우

```bash
# Phase 5 완료 시

# 1. Current 아카이브
marchive current --phase 5

# 2. Decisions 아카이브
marchive decisions --phase 5

# 3. Plans 아카이브
marchive plans

# 4. Phase 5 요약
msummary 2025-10-01:2025-11-15 --output phase5-summary.md

# 5. 인덱스 재구축
mindex --force --optimize
```

### 프로젝트 시작 워크플로우

```bash
# 1. 프로젝트 계획 생성
mplan create "프로젝트 X 개발" --desc "신규 프로젝트 개발" --due 2025-12-31

# 2. 작업 추가
mplan add project-x "아키텍처 설계"
mplan add project-x "API 설계"
mplan add project-x "DB 스키마 설계"

# 3. 인덱스 초기화
mindex

# 4. 작업 시작
m "프로젝트 X 개발 시작"
```

---

## Claude Code 통합

### 초기 설정

**CLAUDE.md 생성 (선택사항, 권장):**

```bash
# 템플릿 복사
cp CLAUDE.md.template CLAUDE.md

# 프로젝트에 맞게 수정
# - 프로젝트 개요, 현재 상태, 중요 파일 등 기입
```

📚 **자세한 가이드:** [docs/CLAUDE_SETUP.md](docs/CLAUDE_SETUP.md)

### 자동 컨텍스트 제공

**1단계: 작업 종료 시**

```bash
mcontext
```

**2단계: Claude Code 시작 시**

Claude Code가 자동으로 다음을 읽습니다:

- `CLAUDE.md` - 프로젝트 가이드라인 및 현재 상태 (사용자 생성)
- `.claude/memory-context.md` - 최근 timeline 자동 요약 (mcontext 생성)

### 수동 업데이트

작업 중 컨텍스트 갱신이 필요하면:

```bash
m "새로운 작업 기록"
mcontext  # 컨텍스트 갱신
```

### 설정

`config.yaml`에서 조정 가능:

```yaml
context:
  recent_days: 3 # memory-context에 포함할 일수
```

---

## 프로젝트 구조

### `.memory/` 디렉토리

```
.memory/
  timeline/             # 시간축: 일별 기록
    2025-11/
      13.md             # - HH:MM | message
      14.md

  modules/              # 공간축: 모듈별 컨텍스트
    my-module/
      module.md         # 모듈 정의
      current.md        # 현재 상태
      decisions.md      # 주요 결정
      dependencies.md   # 의존성
      interface.md      # 인터페이스 설계

  concepts/             # 개념 정리
    architecture.md
    design-patterns.md

  templates/            # 템플릿
    CLAUDE.md.template

  config.yaml           # 설정 파일
  README.md             # 구조 설명
```

### `.claude/` 디렉토리

```
.claude/
  memory-context.md     # 자동 생성 (mcontext)
  guidelines.md         # Claude 사고 지침
```

---

## 설계 철학

### 5대 원칙

1. **Time First**: 먼저 포착, 나중 정리
2. **Lossless**: 모든 것 기록, 아무것도 잃지 않음
3. **Minimal Friction**: 입력 최소, 정리 나중
4. **Loose Coupling**: 프로젝트 격리, 지식 공유
5. **Local First**: 기본 로컬, 확장 명시적

### Motto

**"Capture in 0.5 seconds, organize on weekends, use for life."**

---

## 개발 상태

### Phase 1 Extended + Bonus: 완료 ✅

**구현된 기능:**

- ✅ 8개 명령어: `m`, `minit`, `ms`, `mcontext`, `malias`, `mtoday`, `mweek`, `mstatus`
- ✅ 시간 검증 (미래 차단, 과거 경고)
- ✅ 통합 검색 (로컬/KB/전체, regex)
- ✅ Claude Code 통합 (memory-context 자동 생성)
- ✅ 별칭 시스템 (배치 + PowerShell 프로필)
- ✅ Windows 이모지 처리
- ✅ 설정 파일 (config.yaml)

### Phase 1 Final: 완료 ✅✅✅

**완료 작업:**

- ✅ config.yaml 고급 기능 (auto_update)
- ✅ Claude Skill 개발 (규칙 기반 자동화, 5가지 규칙)
- ✅ PowerShell 프로필 통합
- ✅ README.md 완전 재작성

### Phase 2: 완료 ✅✅✅

**완료:**

- ✅ 고급 검색 (날짜 범위 `--from/--to`, exclude patterns, 파일 크기 제한)
- ✅ msort: Timeline 시간순 재정렬 (today/date/all)
- ✅ 모듈 관리 명령어 (create/list/archive/unarchive)

**날짜 검색 예시:**

```bash
ms "authentication" --from 2025-11-01 --to 2025-11-14
```

### Phase 3: 장기 계획 🔮

**연구 중:**

- MCP Server (Claude Code 네이티브 통합)
- 벡터 검색 (의미 기반)
- 자동 요약 (LLM 기반)

---

## 기술 스택

**Core:**

- Python 3.10+
- typer (CLI 프레임워크)
- rich (터미널 출력)
- PyYAML (설정 파일)

**Optional:**

- ripgrep (빠른 검색, 없으면 Python regex로 대체)

---

## 참고 문서

**사용자 문서:**

- [docs/INSTALLATION.md](docs/INSTALLATION.md) - 설치 가이드
- [docs/QUICKSTART.md](docs/QUICKSTART.md) - 5분 시작 가이드
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) - 완전한 사용자 가이드 (3168줄)
- [docs/FAQ.md](docs/FAQ.md) - 자주 묻는 질문 (1107줄)
- [docs/CLAUDE_SETUP.md](docs/CLAUDE_SETUP.md) - CLAUDE.md 설정 가이드 ⭐

**Claude Code 통합:**

- `CLAUDE.md.template` - Claude Code 프로젝트 설정 템플릿
- `.claude/memory-context.md` - 자동 생성 컨텍스트 (mcontext)

---

## 실사용 예시

### 일일 워크플로우

```bash
# 아침: 오늘 계획 확인
mtoday

# 작업 중: 즉시 기록
m "API 엔드포인트 설계 시작"
m "결정: REST 대신 GraphQL 선택 - 유연성"
m "User resolver 구현 완료"

# 점심 후: 이번 주 진행 확인
mweek

# 저녁: Claude Code 작업 전 컨텍스트 생성
mcontext

# Claude Code에서: 자동으로 최근 작업 파악
# "계속 진행해주세요" → Claude가 GraphQL 작업 이어감
```

### 검색 시나리오

```bash
# 로컬에서 GraphQL 관련 작업 찾기
ms "GraphQL"

# 이전 프로젝트의 auth 패턴 참고
ms --with-kb "authentication"

# 모든 프로젝트에서 특정 에러 검색
ms --all "TypeError.*undefined"
```

---

## FAQ

**Q: 다른 프로젝트와 지식을 공유하려면?**

A: 개인 KB 사용:

```bash
# KB 연결
minit --kb

# KB 포함 검색
ms --with-kb "query"
```

KB 경로: `~/memory/personal/` (config.yaml에서 변경 가능)

**Q: Timeline 시간순 정렬은?**

A: Phase 1은 추가순 유지, Phase 2에 `msort` 명령어 구현 예정. "Capture first, organize later" 철학.

**Q: Claude Skill은 언제?**

A: Phase 1 Final (현재 진행 중). 규칙 기반 자동화, LLM 불필요.

**Q: Windows 외 플랫폼은?**

A: Python은 크로스플랫폼이지만, 별칭 시스템은 Windows 중심. macOS/Linux는 Phase 2에서 고려.

---

## 라이선스

TBD (추후 결정)

---

## 메타

**이 프로젝트는 자신이 정의한 시스템을 사용하여 개발되고 있습니다.**

모든 작업은 `.memory/timeline/`에 기록되고, 주요 결정은 feature별 모듈의 `decisions.md`에 정리됩니다. 프로젝트는 자체 모듈 조직화 원칙을 따라 6개의 feature-based 모듈로 구조화되어 있습니다.

현재 **30+ 주요 결정**과 **200+ timeline 항목**이 기록되어 있으며, 이는 시스템의 실전 검증이자 살아있는 사용 사례입니다.

---

**"0.5초로 포착하고, 주말에 정리하며, 평생 활용한다."**
