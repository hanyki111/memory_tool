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

### Linux에서 Notion Sync 설정 가이드

#### 1단계: 기본 설치

```bash
# 저장소 클론 및 설치
git clone https://github.com/hanyki111/memory_tool.git
cd memory_tool
pip install -e .

# Bash 별칭 설치
python -m memory_tool alias install --bash
source ~/.bashrc
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

```bash
# 프로젝트 초기화 (아직 안 했다면)
minit

# config.yaml 편집
nano .memory/config.yaml
```

다음 내용 추가:

```yaml
notion:
  api_key: "secret_xxx..."           # Integration Secret
  default_page_id: "abc123..."       # Timeline 루트 페이지 ID

  sync:
    enabled: true
    root_page_id: "xyz789..."        # 모듈 싱크 루트 페이지 ID

    targets:                          # 싱크할 모듈 지정
      - "projects/my-project"
      - "projects/my-project/**"      # 하위 모듈 포함

    exclude_patterns:                 # 제외 패턴
      - "archive/**"

    conflict_resolution: "last-write-wins"

    timeline:
      enabled: true
      bidirectional: true
      sync_days: 30
```

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
```

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

- **모듈 페이지**: 모든 .md 파일 내용 통합 뷰 + 하위 페이지 링크
- **파일 페이지**: 개별 파일 편집용
- **충돌 해결**: Last-Write-Wins (마지막 수정이 우선)

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

### 기록 명령어

```bash
# 기본 기록
m "OAuth 구현 완료"

# 시간 지정
m --time "23:45" "늦게 끝난 작업"

# 과거 날짜
m --date "2025-11-12" --time "14:30" "회고 기록"
```

### 검색 명령어

```bash
# 기본 검색
ms "OAuth"

# 개인 KB 포함
ms --with-kb "authentication"

# 모든 프로젝트
ms --all "pattern"

# 날짜 범위
ms "query" --from 2025-11-01 --to 2025-11-14

# Regex 지원
ms "func.*Auth"
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

### Notion 명령어

```bash
# 메시지 기록
nm "작업 내용"                   # 노션 타임라인에 기록

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
nsync "projects/my-app"          # 특정 모듈만
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

**설정 (config.yaml):**

```yaml
llm:
  provider: "anthropic"              # 또는 "ollama"
  api_key: "your-anthropic-api-key"
  model: "claude-3-5-sonnet-20241022"

  # Ollama (로컬, 무료)
  # provider: "ollama"
  # model: "llama3"
  # base_url: "http://localhost:11434"
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

### 계획 관리 (mplan)

```bash
# Daily Plan
mplan daily                      # 조회
mplan daily create               # 생성
mplan daily add "작업 내용"      # 추가
mplan daily done "작업"          # 완료 (Timeline 자동 기록)

# Weekly/Monthly Plan
mplan weekly
mplan monthly
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
