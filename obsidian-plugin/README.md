# Obsidian Memory Tool Integration Plugin

Obsidian 내에서 `memory_tool` CLI 기능을 사용할 수 있는 커뮤니티 플러그인입니다.  
타임라인 빠른 기록, 모듈 생성/탐색, AI 컨텍스트 빌드 등을 Obsidian에서 직접 실행할 수 있습니다.

---

## ✨ 주요 기능

| 단축키 | 기능 |
| :--- | :--- |
| `Ctrl+Alt+M` | ⏱️ 타임라인 0.5초 빠른 기록 |
| `Ctrl+Alt+A` | 🤔 지식베이스에 질문 (`mask`) |
| `Ctrl+Alt+G` | 🔍 모듈 퍼지 검색 & 즉시 이동 |
| `Ctrl+P` → `Create Module` | 📂 새 모듈 생성 (`mmodule create`) |
| `Ctrl+P` → `Build AI Context` | 🧠 AI 컨텍스트 빌드 (`mcontext`) |
| `Ctrl+P` → `Check Module Path Health` | 🏥 모듈 경로 건강 체크 (`mcheck`) |
| `Ctrl+P` → `Show Knowledge Base Folder` | 📁 인식된 기반 폴더 확인 (`mbase`) |

---

## 🤔 지식베이스에 질문하기 (mask)

`Ctrl+Alt+A` 또는 좌측 리본의 ❓ 아이콘으로 엽니다.

- 답변은 **Markdown 으로 렌더링**됩니다 — 표, 목록, 코드 블록이 그대로 보입니다.
- **경과 시간이 표시**됩니다. LLM 응답은 수십 초가 걸릴 수 있어, 멈춘 것과 구분됩니다.
- **Sources** 를 펼치면 근거 파일 목록이 나오고, vault 안의 파일은 클릭해서 바로 열립니다.
- **Insert into note** 로 질문과 답변을 현재 노트 끝에 callout 형태로 추가합니다.
- **Fast mode** 토글: 도구를 쓰는 에이전트 대신 키워드 검색만 사용합니다. 빠르지만
  찾은 내용을 후속 조사하지는 못합니다.

> LLM 제공자가 설정되어 있어야 합니다. `mconfig get llm.provider` 로 확인하고,
> 사용 가능한 목록은 `mproviders` 로 볼 수 있습니다. 제공자가 없으면 모달에
> 사용 가능한 제공자를 포함한 오류가 표시됩니다.

---

## 🚀 설치 방법

### 사전 요구사항

- [Obsidian](https://obsidian.md/) 설치 (v0.15.0 이상)
- [Node.js](https://nodejs.org/) 설치 (빌드 시 필요)
- `memory_tool` 파이썬 패키지 설치 완료 (`pip install -e .`)

---

### 1단계: 플러그인 빌드

```powershell
# 프로젝트 루트에서
cd obsidian-plugin
npm install
npm run build
```

빌드 완료 시 `obsidian-plugin/main.js` 파일이 생성됩니다.

---

### 2단계: Obsidian Vault에 플러그인 설치

**방법 A: Vault 내부에 설치 (권장)**

Obsidian Vault 루트의 `.obsidian/plugins/` 폴더에 `obsidian-memory-tool` 폴더를 만들고, 아래 3개 파일을 복사합니다.

```
[Vault 루트]/
└── .obsidian/
    └── plugins/
        └── obsidian-memory-tool/
            ├── manifest.json    ← obsidian-plugin/manifest.json
            ├── main.js          ← obsidian-plugin/main.js (빌드 결과물)
            └── styles.css       ← obsidian-plugin/styles.css
```

**파일 복사 명령어 (PowerShell):**

```powershell
# [YourVaultPath]를 실제 Vault 경로로 변경하세요
$pluginDir = "[YourVaultPath]\.obsidian\plugins\obsidian-memory-tool"
New-Item -ItemType Directory -Force -Path $pluginDir

Copy-Item "obsidian-plugin\manifest.json" $pluginDir
Copy-Item "obsidian-plugin\main.js" $pluginDir
Copy-Item "obsidian-plugin\styles.css" $pluginDir
```

**방법 B: memory_tool 프로젝트를 Vault로 사용하는 경우**

`memory_tool` 프로젝트 폴더 자체를 Obsidian Vault로 열어서 사용하는 경우:

```powershell
# 프로젝트 루트에서 실행
$pluginDir = ".obsidian\plugins\obsidian-memory-tool"
New-Item -ItemType Directory -Force -Path $pluginDir

Copy-Item "obsidian-plugin\manifest.json" $pluginDir
Copy-Item "obsidian-plugin\main.js" $pluginDir
Copy-Item "obsidian-plugin\styles.css" $pluginDir
```

---

### 3단계: Obsidian에서 플러그인 활성화

1. Obsidian 실행
2. **설정(⚙️)** → **커뮤니티 플러그인** 클릭
3. `안전 모드`가 켜져 있으면 **끄기** 클릭
4. 플러그인 목록에서 **Memory Tool Integration** 찾기
5. 토글 **활성화**

> 플러그인 목록에 보이지 않으면 Obsidian을 재시작하거나 **설치된 플러그인 새로고침** 버튼을 클릭하세요.

---

### 4단계: Python 경로 설정

1. Obsidian **설정** → **Memory Tool Integration**
2. **Python Executable Path** 항목 확인 및 설정

| 환경 | 경로 예시 |
| :--- | :--- |
| 기본 Python | `python` |
| 가상환경 (venv) Windows | `E:\code_projects\memory_tool\venv\Scripts\python.exe` |
| 가상환경 (venv) macOS/Linux | `/path/to/memory_tool/venv/bin/python` |
| conda | `/opt/anaconda3/envs/myenv/bin/python` |

---

### 5단계: 기반 폴더 확인

플러그인은 지식베이스 폴더를 **자동으로 감지**합니다. 어떤 vault 배치를 쓰든
아래 세 가지 모두 지원됩니다.

| Vault 루트 | 기반 폴더 | 플러그인이 쓰는 경로 |
| :--- | :--- | :--- |
| `프로젝트/.memory` | `.memory` (= vault 루트) | `timeline/…`, `modules/…` |
| `프로젝트` | `.memory` | `.memory/timeline/…` (Obsidian 에서 숨김) |
| `프로젝트` | `memory` | `memory/timeline/…` |
| `프로젝트` | `.` (= vault 루트) | `timeline/…`, `modules/…` |

**`.memory` 폴더 자체를 vault 로 여는 경우**(가장 흔한 설정)에는 아무 설정도 필요
없습니다. vault 루트가 이미 기반 폴더이므로 그 안의 `timeline/`, `modules/` 가
Obsidian 에서 정상적으로 보입니다.

확인 방법:

- 명령 팔레트 → **Show Knowledge Base Folder (mbase)**
- 또는 터미널에서 `mbase show`

자동 감지가 틀렸거나 다른 위치를 쓰고 싶다면:

1. Obsidian **설정** → **Memory Tool Integration**
2. **Knowledge Base Folder** 에 **vault 루트 기준** 상대 경로 입력
   (vault 루트가 곧 기반 폴더이면 `.`)
3. 비워두면 자동 감지

> **주의:** 기반 폴더가 vault **밖**에 있으면 Obsidian 이 그 파일을 열 수 없습니다.
> 이 경우 플러그인이 명확히 경고합니다. 해당 폴더를 vault 로 열거나, vault 안으로
> 옮기세요.

### 폴더 이름을 바꾸고 싶다면 (선택)

`.memory` 라는 이름 자체가 거슬리거나, 프로젝트 루트를 vault 로 쓰면서 지식베이스를
보이게 하고 싶을 때만 필요합니다.

```bash
mbase show                   # 현재 상태
mbase set memory --dry-run   # 미리보기
mbase set memory             # .memory/ → memory/
```

> `mbase set .` 로 프로젝트 루트를 기반 폴더로 쓰는 경우, `timeline`, `modules`,
> `concepts`, `plans`, `reviews`, `summaries`, `docs` 폴더만 검색·색인 대상입니다.

### 문제 해결: 기록은 되는데 Obsidian 에서 안 보임

구버전에서 vault 루트(= `.memory` 폴더) 안에서 명령을 실행하면 `.memory/.memory/`
라는 중첩 폴더가 생기고 기록이 그쪽으로 들어갔습니다. `.` 으로 시작하니 Obsidian 이
숨겨서 보이지 않습니다.

현재 버전은 이 중첩 폴더를 자동으로 무시하고 경고합니다. 확인·정리:

```bash
mbase show     # 중첩 폴더가 있으면 WARNING 으로 알려줍니다
```

경고가 보이면, 남기고 싶은 기록을 진짜 타임라인으로 옮긴 뒤 `<기반폴더>/.memory/`
폴더를 삭제하세요.

---

## 📅 Obsidian Calendar 연동 설정

> 달력에서 날짜를 클릭하면 `memory_tool`의 해당 날짜 타임라인 파일로 자동 이동합니다.

### 필요 플러그인
- [Calendar](https://obsidian.md/plugins?id=calendar) 또는 [Periodic Notes](https://obsidian.md/plugins?id=periodic-notes) 커뮤니티 플러그인 설치

### Daily Notes 설정

Obsidian **설정** → **Daily Notes** (또는 **Periodic Notes**) 에서 3개를 맞춥니다.

| 항목 | 값 |
| :--- | :--- |
| **Date format** | `YYYY-MM/YYYY-MM-DD` |
| **New file location** | `<vault기준 경로>/timeline/daily` |
| **Template file location** | `<vault기준 경로>/templates/obsidian/timeline-daily-note` |

`Date format` 에 슬래시를 넣으면 Obsidian 이 **하위 폴더를 만듭니다.**
`YYYY-MM/YYYY-MM-DD` 는 `2026-08/2026-08-14.md` 를 만듭니다.

### ⚠️ `YYYY-MM/DD` 를 쓰면 안 되는 이유

폴더는 맞지만 **파일명에 월 정보가 없어서** Calendar 가 날짜를 구분하지 못합니다.
플러그인 내부 동작이 비대칭이기 때문입니다:

| 동작 | 사용하는 것 | 결과 |
| :--- | :--- | :--- |
| 파일 **생성** | 전체 포맷 | `2026-08/14.md` ✅ |
| 파일 **탐색** | `format.split("/").pop()` → `DD` | 파일명 `14` 만 봄 ❌ |

탐색이 파일명만 보므로 모든 달의 `14.md` 가 충돌하고, 먼저 발견된 것(보통 가장 이른 달)이
열립니다. **8월 21일을 눌렀는데 1월 21일 문서가 뜨는** 증상이 이것입니다.

`YYYY-MM/YYYY-MM-DD` 는 파일명이 `2026-08-14` 라 고유하므로 정상 동작합니다.

### 기존 파일 변환

memory_tool 은 기본적으로 `14.md` 로 기록하므로, Calendar 를 쓰려면 한 번 변환해야 합니다.

```bash
mmigrate-timeline --filename date --dry-run   # 미리보기
mmigrate-timeline --filename date             # 변환 + config 자동 설정
```

- 폴더 구조는 그대로 두고 **파일 이름만** 바꿉니다 (`2026-08/14.md` → `2026-08/2026-08-14.md`)
- 같은 날짜 파일이 이미 있으면 덮어쓰지 않고 건너뛰고 보고합니다
- 실패 시 자동 롤백되며, 되돌리려면 `--filename day`
- 읽기는 **두 방식 모두** 지원하므로 변환 도중에도 모든 기록이 보입니다

변환 후 `config.yaml` 에 `timeline.filename: date` 가 기록되어 새 기록도 같은 방식을 씁니다.

**New file location** 은 vault 루트 기준입니다 — 기반 폴더가 아니라 **vault 위치**에
따라 달라집니다:

| Vault 루트 | 기반 폴더 | New file location |
| :--- | :--- | :--- |
| `프로젝트/.memory` | `.memory` (= vault 루트) | `timeline/daily` |
| `프로젝트` | `memory` | `memory/timeline/daily` |
| `프로젝트` | `.` (= vault 루트) | `timeline/daily` |

헷갈리면 명령 팔레트 → **Show Knowledge Base Folder (mbase)** 로 확인하세요.
`the vault root` 로 나오면 `timeline/daily`, `memory/` 로 나오면 `memory/timeline/daily` 입니다.

### ⚠️ 템플릿을 반드시 맞춰야 하는 이유

Calendar 로 날짜를 클릭하면 **Obsidian 이 파일을 먼저 만듭니다.** 이때 일반적인
Daily Note 템플릿(할 일 체크박스, 메모 섹션 등)을 쓰면 memory_tool 과 충돌합니다.

`minit` 이 `<기반폴더>/templates/obsidian/timeline-daily-note.md` 를 만들어 둡니다.
내용은 한 줄입니다:

```markdown
# {{date:YYYY-MM-DD}} Timeline
```

이것을 **Template file location** 으로 지정하면 Calendar 가 만든 파일이 곧바로
정상적인 타임라인 파일이 되고, `m` 이 그 뒤에 기록을 이어 붙입니다.

**템플릿을 비워두는 것도 괜찮습니다** — `m` 이 헤더를 자동 생성합니다.

반면 **체크박스가 있는 템플릿은 쓰지 마세요.** 실측 결과:

| 문제 | 증상 |
| :--- | :--- |
| 기록 위치 | 기록이 템플릿 맨 뒤(예: `## 참고자료` 아래)에 붙습니다 |
| 헤더 인식 | 템플릿의 첫 `##` 가 헤더로 인식되어 `# YYYY-MM-DD Timeline` 이 안 생깁니다 |

> `- [ ] 할 일` 같은 체크박스가 타임라인 기록으로 오인되던 문제(`mstatus` 개수 부풀림,
> `msort` 가 템플릿 구조를 뒤섞음)는 수정되었습니다. 이제 `- HH:MM \|` 형식만
> 기록으로 취급하며, 정렬 시 그 외 줄과 들여쓴 하위 항목은 제자리를 지킵니다.

### 정리

설정 후 달력에서 날짜를 클릭하면 memory_tool 타임라인 파일로 바로 이동하고,
`Ctrl+Alt+M` 기록과 Calendar 클릭이 **같은 파일**을 가리킵니다.

---

## 🛠️ 개발자용: 핫 리로드 (개발 모드)

플러그인 소스 수정 시 자동 리빌드:

```powershell
cd obsidian-plugin
npm run dev
```

파일 변경 감지 시 자동으로 `main.js`가 재빌드됩니다.  
Obsidian에서 플러그인을 **비활성화 → 활성화** 하거나 [Hot Reload](https://obsidian.md/plugins?id=hot-reload) 플러그인을 사용하면 즉시 반영됩니다.
