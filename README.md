# Memory Tool

**시간-공간 통합 지식 체계** - Timeline 기반 작업 기록 & Claude Code 자동 컨텍스트 제공

---

## 특징

- **0.5초 포착**: `m "message"` - 즉시 timeline에 기록
- **통합 검색**: 로컬/KB/전체 프로젝트 검색 (regex 지원)
- **Claude Code 통합**: `.claude/memory-context.md` 자동 생성
- **Notion 연동**: 타임라인 미러링 & 모듈 양방향 싱크
- **크로스 플랫폼**: Windows (PowerShell/Batch), Linux/macOS (Bash/Zsh)
- **문서 관리 자동화**: 아카이브, LLM 분석, 건강 모니터링

---

## 빠른 시작

### 설치

**요구사항:** Python 3.10+

```bash
git clone https://github.com/hanyki111/memory_tool.git
cd memory_tool
pip install -e .
```

### 별칭 설치

**Windows (PowerShell 권장):**

```bash
malias install --powershell
```

**Linux/macOS (Bash):**

```bash
malias install --bash
```

**Linux/macOS (Zsh):**

```bash
malias install --zsh
```

설치 후 셸을 재시작하거나 프로필을 다시 로드하세요:

```bash
# Windows
. $PROFILE

# Linux/macOS
source ~/.bashrc  # 또는 ~/.zshrc
```

### 기본 사용

```bash
# 1. 프로젝트 초기화
minit

# 2. 작업 기록
m "OAuth 구현 시작"
m "결정: Passport.js 선택"

# 3. 검색
ms "OAuth"

# 4. 오늘 작업 확인
mtoday

# 5. Claude Code용 컨텍스트 생성
mcontext
```

---

## Notion 연동

Memory Tool은 Notion과 완전히 통합됩니다:

- **nm**: 노션에 메시지 기록 (Timeline 미러링)
- **ns**: 노션 페이지 검색
- **nt/nw**: 노션 오늘/이번 주 타임라인
- **nsync**: 로컬 모듈 ↔ 노션 양방향 싱크
- **nwatch**: 파일 변경 감지 시 자동 동기화

### Notion Sync 설정 가이드

#### 1단계: 기본 설치

**Linux/macOS:**

```bash
# 저장소 클론 및 설치
git clone https://github.com/hanyki111/memory_tool.git
cd memory_tool
pip install -e .

# Bash 별칭 설치
python -m memory_tool alias install --bash
source ~/.bashrc

# 또는 Zsh 사용 시
python -m memory_tool alias install --zsh
source ~/.zshrc
```

**Windows (PowerShell 권장):**

```powershell
# 저장소 클론 및 설치
git clone https://github.com/hanyki111/memory_tool.git
cd memory_tool
pip install -e .

# PowerShell 별칭 설치
python -m memory_tool alias install --powershell
. $PROFILE
```

#### 2단계: Notion API 키 발급

1. [Notion Integrations](https://www.notion.so/my-integrations) 접속
2. "New integration" 클릭
3. Integration 이름 입력 (예: "Memory Tool")
4. 권한 설정:
   - Content Capabilities: Read content, Update content, Insert content
   - User Capabilities: No user information
5. "Submit" 클릭
6. **Internal Integration Secret** 복사 (secret_xxx... 형식)

#### 3단계: Notion 페이지 ID 확인

1. Notion에서 연동할 페이지 열기
2. 우측 상단 "..." → "Copy link" 클릭
3. URL에서 페이지 ID 추출:
   ```
   https://www.notion.so/Your-Page-Title-abc123def456...
                                        ^^^^^^^^^^^^^^^^
                                        이 부분이 페이지 ID
   ```

#### 4단계: Integration 연결

1. Notion에서 타임라인/모듈 루트 페이지 열기
2. 우측 상단 "..." → "Connections" 클릭
3. 생성한 Integration 추가

#### 5단계: config.yaml 설정

**Linux/macOS:**

```bash
# 프로젝트 초기화 (아직 안 했다면)
minit

# config.yaml 편집
nano .memory/config.yaml
# 또는 vim, code 등 선호하는 에디터 사용
```

**Windows:**

```powershell
# 프로젝트 초기화 (아직 안 했다면)
minit

# config.yaml 편집
notepad .memory\config.yaml
# 또는 VSCode 사용 시
code .memory\config.yaml
```

다음 내용 추가:

```yaml
notion:
  api_key: "secret_xxx..."           # Integration Secret
  mode: default                      # default 또는 pat (기업용)

  sync:
    conflict_resolution: "last-write-wins"
    exclude_patterns:
      - "archive/**"
    targets:
      - "**"                         # 모든 모듈 (또는 특정 경로)

    # 모듈 동기화 설정
    module:
      enabled: true
      root_page_id: "abc123..."      # 모듈 루트 페이지 ID

    # 타임라인 동기화 설정
    timeline:
      enabled: true
      root_page_id: "def456..."      # 타임라인 루트 페이지 ID
      bidirectional: true
      sync_days: 30

    # 플랜 동기화 설정
    plan:
      enabled: true
      root_page_id: "ghi789..."      # 플랜 루트 페이지 ID
      daily: true
      weekly: true
      monthly: true
```

**레거시 호환:** 기존 `default_page_id`, `sync.root_page_id` 설정도 자동 인식됩니다.

#### 6단계: 사용

```bash
# 노션에 메시지 기록
nm "작업 시작"

# 노션 타임라인 보기
nt          # 오늘
nw          # 이번 주

# 노션 검색
ns "키워드"

# 모듈 싱크
nsync                    # 모든 대상 양방향 싱크
nsync --push             # 로컬 → 노션
nsync --pull             # 노션 → 로컬
nsync --dry-run          # 변경 사항만 확인
nsync --status           # 싱크 상태 확인
nsync --discover         # 노션에서 모듈 다운로드 (첫 설정)
nsync --verbose          # 상세 진행 로그

# 타임라인 일괄 싱크
nsync --timeline                 # 오늘 타임라인 동기화
nsync --timeline --days 7        # 최근 7일 동기화

# 자동 동기화 (파일 변경 감지)
nwatch                           # Local → Notion 단방향
nwatch --bidirectional           # 양방향 (Notion → Local polling 포함)
nwatch -b -i 60                  # 양방향, 60초 polling 간격
nwatch --debounce 5              # 5초 대기 후 동기화
nwatch --modules-only            # 모듈만 감시
nwatch --timeline-only           # 타임라인만 감시
nwatch --dry-run                 # 테스트 모드
```

**nwatch 설치:**

```bash
pip install memory-tool[watch]
```

**플랫폼별 nwatch 실행:**

**Linux/macOS:**
```bash
# 파일 변경 감시 시작
nwatch                           # Local → Notion
nwatch --bidirectional           # 양방향 동기화
```

**Windows (PowerShell):**
```powershell
# 파일 변경 감시 시작
nwatch                           # Local → Notion
nwatch --bidirectional           # 양방향 동기화

# 또는 Python 모듈로 직접 실행
python -m memory_tool nwatch --bidirectional
```

**WSL 사용 시 주의:**
WSL에서 Windows 마운트 드라이브(/mnt/...)를 감시할 경우, 파일 시스템 이벤트가 제대로 전달되지 않을 수 있습니다. 이 경우 Windows PowerShell에서 직접 실행하세요.

### Notion Sync 구조

로컬 모듈이 노션에 다음과 같이 매핑됩니다:

```
[로컬]                              [노션]
.memory/modules/projects/my-app/    📄 my-app (모듈 페이지)
├── current.md                      │  ├── 📄 current.md (하위 페이지)
├── module.md                       │  ├── 📄 module.md
├── decisions.md                    │  ├── 📄 decisions.md
└── sub-module/                     │  └── 📄 sub-module (재귀)
    ├── current.md                  │      ├── 📄 current.md
    └── ...                         │      └── ...
```

- **모듈 페이지**: 하위 파일 페이지들의 컨테이너
- **파일 페이지**: 개별 .md 파일 내용 (편집 가능)
- **충돌 해결**: Last-Write-Wins (마지막 수정이 우선)

---

## Knowledge Federation (KB 연동)

> **"Execution should be isolated, but Knowledge must be federated."**

여러 프로젝트 간 지식을 공유하는 Federation 시스템입니다.

### 기본 개념

```
Project A                    Central KB                    Project B
┌─────────┐                 ┌─────────┐                   ┌─────────┐
│ modules/│   mpublish      │ modules/│     mimport       │ modules/│
│ search/ │ ──────────────▶ │ search/ │ ◀──────────────── │ ref/    │
└─────────┘                 └─────────┘                   └─────────┘
```

- **mpublish**: 로컬 모듈을 KB에 발행
- **mimport**: KB 모듈을 로컬로 가져오기
- **ms --with-kb**: KB 포함 검색

### KB 설정

```yaml
# .memory/config.yaml
kb:
  path: /path/to/your/kb  # 중앙 KB 경로
```

### 사용 예시

```bash
# 모듈 발행
mpublish search-system --tags search,fts5,hybrid
mpublish master --tags project-overview

# KB 목록 확인
mimport --list

# KB 모듈 가져오기
mimport Projects/memory_tool/search-system --target ref/search

# KB 포함 검색
ms "hybrid search" --with-kb
```

### Federation 명령어

| 명령어 | 설명 |
|--------|------|
| `mpublish <module>` | 로컬 모듈을 KB에 발행 |
| `mpublish <module> --dry-run` | 발행 미리보기 |
| `mpublish <module> --tags a,b` | 태그와 함께 발행 |
| `mimport --list` | KB 모듈 목록 |
| `mimport <path>` | KB 모듈 가져오기 |
| `mimport <path> --target <local>` | 지정 경로로 가져오기 |

---

## 명령어 레퍼런스

### 핵심 명령어

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `m` | Timeline 기록 | `m "작업 완료"` |
| `ms` | 검색 | `ms "키워드"` |
| `mcontext` | Claude 컨텍스트 생성 | `mcontext` |
| `mtoday` | 오늘 작업 보기 | `mtoday` |
| `mweek` | 이번 주 작업 보기 | `mweek` |
| `mmonth` | 이번 달 작업 보기 | `mmonth` |
| `mdays` | 최근 N일 작업 보기 | `mdays 7` |
| `mask` | 메모리 기반 Q&A (RAG) | `mask "최근 결정 사항?"` |
| `mconfig` | 설정 관리 | `mconfig get help.language` |
| `mhelp` | 상세 도움말 | `mhelp plan` |

### 기록 명령어

```bash
# 기본 기록
m "OAuth 구현 완료"

# 인라인 태그 (메시지 끝에 #태그)
m "로그인 버그 수정 #bug #auth #urgent"
m "회의 노트 #meeting #team"

# --tags 옵션으로 태그 지정
m "기능 개발 시작" --tags feature,sprint-1,frontend

# 시간 지정
m --time "23:45" "늦게 끝난 작업"

# 과거 날짜
m --date "2025-11-12" --time "14:30" "회고 기록"
```

**태그 작성 팁:**
- 소문자, 하이픈 구분 권장: `feature-request`, `bug-fix`
- 항목당 3-5개 태그로 제한
- 검색 시 `ms "query" --tag 태그명`으로 필터링

### 검색 명령어

```bash
# 기본 검색 (config.yaml 설정에 따라 하이브리드 또는 키워드)
ms "OAuth"

# 하이브리드 검색 (키워드 + 시맨틱, 권장)
ms "authentication" --hybrid

# 하이브리드 비활성화 (키워드만)
ms "OAuth" --no-hybrid

# 시맨틱 검색 (의미 기반)
ms "사용자 인증 방법" --semantic

# 태그로 필터링
ms "bug" --tag auth
ms "feature" --tag sprint-1 --tag frontend

# 개인 KB 포함
ms --with-kb "authentication"

# 모든 프로젝트
ms --all "pattern"

# 날짜 범위
ms "query" --from 2025-11-01 --to 2025-11-14

# 최근 결과 우선
ms "refactor" --boost-recent

# Regex 지원
ms "func.*Auth"
```

**하이브리드 검색 기본 설정 (config.yaml):**

```yaml
search:
  hybrid: true           # 하이브리드 검색 기본 활성화
  text_weight: 0.7       # 키워드 검색 가중치 (70%)
  semantic_weight: 0.3   # 시맨틱 검색 가중치 (30%)
```

### 별칭 관리 (malias)

```bash
# Windows
malias install --powershell     # PowerShell 프로필에 설치
malias uninstall --powershell   # 제거
malias list --powershell        # 상태 확인

# Linux/macOS
malias install --bash           # ~/.bashrc에 설치
malias install --zsh            # ~/.zshrc에 설치
malias uninstall --bash         # Bash에서 제거
malias uninstall --zsh          # Zsh에서 제거
malias list --bash              # Bash 상태 확인
malias list --zsh               # Zsh 상태 확인

# 배치 파일 (Windows 레거시)
malias install                  # 배치 파일 생성
malias list                     # 상태 확인
```

### 이중언어 도움말

도움말이 설정된 언어로 표시됩니다:

```bash
# 언어 설정
mconfig set help.language ko     # 한국어
mconfig set help.language en     # English

# 도움말 보기
mhelp plan                       # 상세 도움말
mplan --help                     # 명령어 도움말 (설정 언어로 표시)
mhelp --list                     # 전체 명령어 목록
```

### 한글 별칭

로컬 타임라인용 한글 별칭:

| 한글 | 영문 | 설명 |
|------|------|------|
| `기` | `m` | 타임라인 기록 |
| `검` | `ms` | 검색 |
| `오늘` | `mtoday` | 오늘 타임라인 |
| `주간` | `mweek` | 이번 주 타임라인 |
| `월간` | `mmonth` | 이번 달 타임라인 |
| `일수` | `mdays` | 최근 N일 타임라인 |

Notion용 한글 별칭:

| 한글 | 영문 | 설명 |
|------|------|------|
| `노` | `nm` | Notion 기록 |
| `노플` | `np` | Notion 플랜 추가 |
| `노검` | `nsi` | Notion 검색 |
| `노오` | `nt` | Notion 오늘 |
| `노주` | `nw` | Notion 주간 |
| `노올` | `ns` | Notion 전체 검색 |

기타:

| 한글 | 영문 | 설명 |
|------|------|------|
| `질문` | `mask` | RAG Q&A |
| `설정` | `mconfig` | 설정 관리 |
| `도움` | `mhelp` | 상세 도움말 |

```bash
# 사용 예시
기 "작업 완료"        # m "작업 완료"
검 "OAuth"           # ms "OAuth"
오늘                 # mtoday
주간                 # mweek
월간                 # mmonth
일수 7               # mdays 7
```

### Notion 명령어

```bash
# 메시지 기록
nm "작업 내용"                   # 노션 타임라인에 기록 (날짜/시간 자동)

# 플랜 추가 (NEW)
np "작업"                        # 오늘 daily plan에 추가
np "목표" --weekly               # 이번 주 weekly plan에 추가
np "프로젝트" --monthly          # 이번 달 monthly plan에 추가

# 타임라인 보기
nt                               # 오늘
nw                               # 이번 주

# 검색
ns "키워드"                      # 노션 페이지 검색
nsi "키워드"                     # Daily 페이지 내용 검색

# 모듈 싱크
nsync                            # 양방향 싱크
nsync --push                     # 로컬 → 노션
nsync --pull                     # 노션 → 로컬
nsync --dry-run                  # 미리보기
nsync --status                   # 상태 확인
nsync --force                    # 타임스탬프 무시, 강제 싱크
nsync --discover                 # 노션에서 모듈 다운로드
nsync --verbose                  # 상세 진행 로그
nsync "projects/my-app"          # 특정 모듈만

# 타임라인 일괄 싱크 (NEW)
nsync --timeline                 # 오늘 타임라인 동기화
nsync --timeline --days 7        # 최근 7일 동기화
nsync --timeline --push          # 로컬 → 노션만
nsync --timeline --pull          # 노션 → 로컬만

# 자동 동기화 (파일 변경 감시)
nwatch                           # 감시 시작 (modules + timeline + plans)
nwatch --bidirectional           # 양방향 감시 (Notion ↔ Local)
nwatch -b -i 60                  # 양방향, 60초 polling 간격
nwatch --debounce 5              # 5초 대기 후 동기화
nwatch --modules-only            # 모듈만 감시
nwatch --timeline-only           # 타임라인만 감시
nwatch --plans-only              # 플랜만 감시
nwatch --no-plans                # 플랜 제외 (모듈 + 타임라인만)
nwatch --dry-run                 # 테스트 모드
nwatch --quiet                   # 간결한 출력
```

### 메모리 기반 Q&A (mask)

LLM을 활용한 Agentic RAG 질의응답:

```bash
mask "최근 어떤 결정을 내렸나요?"
mask "이번 주 작업 내용 요약"
mask "OAuth 관련 기록은?"
```

**작동 방식:**
1. LLM이 질문을 분석
2. 적절한 도구 선택 (timeline, search, module, plan)
3. 컨텍스트 수집 및 답변 생성

### 설정 관리 (mconfig)

config.yaml을 CLI에서 관리:

```bash
mconfig list                     # 전체 설정 보기
mconfig get help.language        # 특정 값 조회
mconfig set help.language ko     # 값 설정
mconfig set notion.sync.plan.enabled true
```

### LLM 기반 요약 (msummary)

```bash
# 타임라인 요약
msummary today                   # 오늘
msummary week                    # 이번 주
msummary 2025-11-01:2025-11-14   # 날짜 범위

# 모듈 요약
msummary --module core-system

# 옵션
msummary today --lang ko         # 한국어
msummary today --force           # 캐시 무시
```

### LLM 설정 (config.yaml)

Memory Tool은 다양한 LLM 제공자를 지원합니다:

| 제공자 | 설명 | API 키 필요 |
|--------|------|-------------|
| `ollama` | 로컬 LLM (기본값, 무료) | ❌ |
| `anthropic` | Claude API | ✅ |
| `claude-cli` | Claude CLI 도구 사용 | ❌ (CLI 설치 필요) |
| `gemini-cli` | Google Gemini CLI 사용 | ❌ (CLI 설치 필요) |

**설정 예시:**

```yaml
llm:
  # === Ollama (로컬, 무료, 기본값) ===
  provider: "ollama"
  ollama_host: "http://localhost:11434"
  ollama_model: "qwen3-vl:8b"    # 또는 llama3, mistral 등

  # === Anthropic API ===
  # provider: "anthropic"
  # anthropic_api_key: "sk-ant-..."
  # anthropic_model: "claude-3-5-sonnet-20241022"

  # === Claude CLI (claude 명령어 사용) ===
  # provider: "claude-cli"
  # (별도 API 키 불필요, Claude CLI가 설치되어 있어야 함)

  # === Gemini CLI (gemini 명령어 사용) ===
  # provider: "gemini-cli"
  # (별도 API 키 불필요, Gemini CLI가 설치되어 있어야 함)

  # 공통 설정
  max_tokens: 4096
  temperature: 0.7
  output_language: "ko"          # 출력 언어 (ko, en)
```

**mask 명령어에서 제공자 직접 지정:**

```bash
mask "어제 무엇을 했나요?"                    # config 기본 제공자 사용
mask "summarize last week" --provider claude-cli  # Claude CLI 사용
mask "what decisions were made?" --provider gemini-cli  # Gemini CLI 사용
```

### 문서 아카이브 (marchive)

```bash
# Decisions 아카이브
marchive decisions --keep-recent 10    # 최근 10개 유지
marchive decisions --older-than 6m     # 6개월 이상 된 것
marchive decisions --interactive       # 직접 선택
marchive decisions --suggest           # 제안 확인

# Current/Plans 아카이브
marchive current --phase 5
marchive plans
```

### 모듈 관리 (mmodule)

```bash
# 모듈 생성 (한글/유니코드 지원)
mmodule create my-module --desc "설명"
mmodule create "한글-모듈" --desc "한글 모듈명 지원"
mmodule create projects/sub-module --tags "tag1,tag2"

# 모듈 목록
mmodule list                     # 활성 모듈
mmodule list --archived          # 아카이브 포함
mmodule tree                     # 트리 구조

# 모듈 이름 변경
mmodule rename old-name --to new-name
mmodule rename "한글-이름" --to "새-이름"

# 모듈 아카이브
mmodule archive my-module --reason "완료"
mmodule unarchive my-module
```

### 계획 관리 (mplan)

```bash
# Daily Plan
mplan daily                      # 조회
mplan daily create               # 생성
mplan daily add "작업 내용"      # 추가
mplan daily done "작업"          # 완료 (Timeline 자동 기록)

# Smart Done (스마트 완료)
mplan daily done 1               # 인덱스로 첫 번째 작업 완료
mplan daily done 2               # 인덱스로 두 번째 작업 완료
mplan daily done "Write"         # Prefix 매칭 (유니크하면 매칭)
mplan weekly done 1              # 주간 목표 인덱스로 완료

# Weekly/Monthly Plan
mplan weekly
mplan monthly

# 미완료 작업 이관
mplan daily carryover            # 어제 미완료 → 오늘
mplan weekly carryover           # 지난주 미완료 → 이번 주
```

**스마트 매칭 우선순위:**
1. 숫자 입력 → 인덱스로 처리 (1=첫 번째, 2=두 번째...)
2. 정확한 일치 (대소문자 무시)
3. 유니크 Prefix 매칭
4. 유니크 Contains 매칭
5. 다중 매칭 시 → 인덱스 목록 표시

### Notion Plan (np)

Notion에 직접 계획 추가:

```bash
np "작업 내용"                   # 오늘 daily plan에 추가
np "목표" --weekly               # 이번 주 weekly plan에 추가
np "프로젝트" --monthly          # 이번 달 monthly plan에 추가
np "작업" --date 2026-01-25      # 특정 날짜에 추가
np "완료된 작업" --done          # 완료 상태로 추가
```

---

## 프로젝트 구조

```
your-project/
├── .memory/                     # 지식 저장소
│   ├── timeline/daily/          # 시간순 기록
│   │   └── YYYY-MM/DD.md
│   ├── modules/                 # 주제별 정리
│   │   └── module-name/
│   │       ├── current.md
│   │       ├── decisions.md
│   │       └── ...
│   ├── concepts/                # 개념 문서
│   └── config.yaml              # 설정
│
└── .claude/                     # Claude Code 통합
    ├── memory-context.md        # 자동 생성 컨텍스트
    └── guidelines.md            # 사고 지침
```

---

## Claude Code 통합

### 워크플로우

1. **작업 전**: `mcontext` 실행하여 컨텍스트 생성
2. **작업 중**: `m "message"` 로 진행 상황 기록
3. **Claude 시작**: 자동으로 `.claude/memory-context.md` 읽음

### 설정

```bash
# CLAUDE.md 템플릿 복사 (선택)
cp CLAUDE.md.template CLAUDE.md
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

**"0.5초로 포착하고, 주말에 정리하며, 평생 활용한다."**

---

## 기술 스택

- **Core**: Python 3.10+, typer, rich, PyYAML
- **Notion**: notion-client
- **Optional**: sentence-transformers (벡터 검색), anthropic/ollama (LLM)

---

## 참고 문서

- [docs/INSTALLATION.md](docs/INSTALLATION.md) - 설치 가이드
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) - 사용자 가이드
- [docs/CLAUDE_SETUP.md](docs/CLAUDE_SETUP.md) - Claude Code 설정

---

## 라이선스

MIT License

---

**"Capture in 0.5 seconds, organize on weekends, use for life."**
