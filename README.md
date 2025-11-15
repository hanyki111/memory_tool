# Memory Tool

**시간-공간 통합 지식 체계** - Timeline 기반 작업 기록 & Claude Code 자동 컨텍스트 제공

> **For Claude Code:** Read `CLAUDE.md` first 🤖

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
malias install          # 전체 설치
malias install m ms     # 특정 명령어만
```

**PowerShell 프로필 (추천):**

```bash
malias install --powershell
```

설치 후 모든 터미널(PowerShell, VSCode, Windows Terminal)에서 작동합니다.

---

## 다른 프로젝트에서 사용하기

memory_tool을 Python 라이브러리로 활용하여 자신만의 도구를 만들 수 있습니다.

### 프로젝트 구조 설정

```bash
# 작업 공간 구조
your-workspace/
├── memory_tool/              # git clone한 memory_tool
│   ├── memory_tool/          # 패키지
│   ├── .memory/              # memory_tool 자체 개발 데이터
│   └── .claude/              # memory_tool 설정
│
└── your-project/             # 당신의 프로젝트
    ├── .memory/              # 프로젝트 데이터 (독립)
    ├── .claude/              # 프로젝트 설정 (독립)
    ├── requirements.txt      # ⭐ memory_tool 여기서 참조
    └── your_code.py
```

### 통합 방법

#### 1. requirements.txt 설정

```txt
# your-project/requirements.txt

# 다른 의존성들...
fastapi==0.104.1
pydantic==2.5.0

# memory_tool (로컬 개발 모드)
# 상대 경로로 참조
-e ../memory_tool
```

#### 2. 패키지 설치

```bash
cd your-project

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치 (memory_tool 포함)
pip install -r requirements.txt

# 확인
python -c "from memory_tool.core.timeline import TimelineManager; print('✅ OK')"
```

#### 3. 코드에서 사용

```python
# your-project/your_code.py

from pathlib import Path
from memory_tool.core.timeline import TimelineManager
from memory_tool.core.search import SearchEngine

class MyApp:
    def __init__(self):
        # 프로젝트의 .memory/ 디렉토리 사용
        self.memory_dir = Path(".memory")
        self.timeline = TimelineManager(self.memory_dir)
        self.search = SearchEngine(self.memory_dir)

    def log_action(self, message: str):
        """작업 기록"""
        return self.timeline.add_entry(message)

    def search_history(self, query: str):
        """과거 작업 검색"""
        return self.search.search_text(query)

# 사용 예시
app = MyApp()
app.log_action("사용자 인증 기능 구현 시작")
results = app.search_history("인증")
```

### 장점

- ✅ **.claude 폴더 충돌 없음** - 각 프로젝트 독립
- ✅ **깔끔한 import** - `from memory_tool.core import ...`
- ✅ **개발 편의성** - `-e` 옵션으로 수정사항 즉시 반영
- ✅ **데이터 독립** - 각 프로젝트의 .memory/ 분리

### 실제 사례: MemoryWeb

memory_tool을 활용한 웹 애플리케이션 예시:

```python
# MemoryWeb/backend/core/notes_manager.py

from memory_tool.core.timeline import TimelineManager
from memory_tool.core.search import SearchEngine

class NotesManager:
    """웹 UI를 위한 노트 관리"""

    def __init__(self, memory_dir: str = "../.memory"):
        self.timeline = TimelineManager(memory_dir)
        self.search = SearchEngine(memory_dir)

    async def add_note(self, content: str, tags: list = None):
        """노트 추가 (Web API에서 호출)"""
        return self.timeline.add_entry(content, tags=tags or [])

    async def search_notes(self, query: str, mode: str = "text"):
        """노트 검색 (Web API에서 호출)"""
        return self.search.search(query, mode=mode)
```

📚 **전체 예시:** [personal-notes-web-design.md](personal-notes-web-design.md), [QUICKSTART-NEW-SESSION.md](QUICKSTART-NEW-SESSION.md)

### 주의사항

1. **프로젝트 위치:** memory_tool과 your-project는 같은 레벨에 위치
2. **.memory 디렉토리:** 각 프로젝트마다 독립적으로 생성
3. **상대 경로:** requirements.txt의 경로가 올바른지 확인

### 트러블슈팅

**Import 실패 시:**
```bash
# 확인
pip list | grep memory

# 재설치
pip install -e ../memory_tool
```

**경로 문제 시:**
```
확인 사항:
your-workspace/
├── memory_tool/
└── your-project/
    └── requirements.txt  # 여기서 -e ../memory_tool
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
.memory/
  timeline/
  modules/
  concepts/
  config.yaml
  README.md
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

# 모듈 아카이브
python -m memory_tool module archive auth-system --reason "프로젝트 완료"

# 모듈 복원
python -m memory_tool module unarchive auth-system
```

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
