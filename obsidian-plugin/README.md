# Obsidian Memory Tool Integration Plugin

Obsidian 내에서 `memory_tool` CLI 기능을 사용할 수 있는 커뮤니티 플러그인입니다.  
타임라인 빠른 기록, 모듈 생성/탐색, AI 컨텍스트 빌드 등을 Obsidian에서 직접 실행할 수 있습니다.

---

## ✨ 주요 기능

### 버튼으로 (단축키 없이)

**모든 기능은 탭만으로 도달할 수 있습니다.** 휴대폰에는 누를 조합키가 없으므로,
단축키는 데스크톱의 추가 수단일 뿐 유일한 경로가 아닙니다.

| 위치 | 버튼 | 기능 |
| :--- | :--- | :--- |
| 좌측 리본 | ✏️ 연필 | 타임라인 기록 (빠른 입력창) |
| 좌측 리본 | ⏱️ 시계 | Memory Tool 패널 열기 |
| 패널 안 | **기록** | 입력한 내용을 타임라인에 저장 |
| 패널 헤더(우측) | ✏️ / 🔄 | 입력창으로 이동 / 새로 고침 |
| 패널 섹션 헤더 | 🔄 | 오늘 타임라인·모듈 각각 새로 고침 |

> **모바일에서 `Enter` 는 줄바꿈입니다.** 휴대폰 키보드에는 `Shift` 가 없어
> `Shift+Enter` 로 줄을 바꿀 수 없으므로, 모바일에서는 `Enter` 가 줄바꿈으로 남고
> **기록은 버튼으로만** 합니다. 데스크톱에서는 `Enter` 기록 / `Shift+Enter` 줄바꿈이
> 그대로 동작합니다.

### 단축키 (데스크톱)

| 단축키 | 기능 |
| :--- | :--- |
| `Ctrl+Shift+M` | 📋 사이드 패널 열기 (캡처 + 오늘 타임라인 + 모듈) |
| `Ctrl+Shift+J` | ⏱️ 타임라인 빠른 기록 (모달) |
| `Ctrl+Shift+G` | 🔍 모듈 퍼지 검색 & 즉시 이동 |
| `Ctrl+P` → `모듈 생성` | 📂 새 모듈 생성 + 템플릿 자동 적용 |
| `Ctrl+P` → `기억에 질문하기` | 🤔 지식베이스에 질문 (`mask`) |
| `Ctrl+P` → `AI 컨텍스트 생성` | 🧠 AI 컨텍스트 빌드 (`mcontext`) |
| `Ctrl+P` → `모듈 경로 점검` | 🏥 모듈 경로 건강 체크 (`mcheck`) |
| `Ctrl+P` → `검색 인덱스 동기화` | 🔄 직접 기록분을 검색 인덱스에 반영 |
| `Ctrl+P` → `지식 베이스 폴더 확인` | 📁 인식된 기반 폴더 확인 (`mbase`) |

> **단축키가 `Ctrl+Alt` 에서 `Ctrl+Shift` 로 바뀌었습니다.** Windows 에서 `Ctrl+Alt` 는
> AltGr 로 해석되어, 한글 IME 나 다른 앱의 전역 단축키가 Obsidian 보다 먼저 키를
> 가로챕니다. 설정 화면에는 정상으로 보이는데 눌러도 아무 일이 없는 증상이 이것입니다.
>
> 업데이트 후에도 예전 조합이 남아 있으면, **설정 → 단축키**에서 해당 명령의
> `Ctrl+Alt` 조합을 지우고 다시 지정하세요. 한 번이라도 직접 지정한 단축키는
> 플러그인 기본값보다 우선하므로 자동으로 바뀌지 않습니다.

---

## 📋 사이드 패널

`Ctrl+Shift+M` 또는 좌측 리본의 ⏱️ 아이콘으로 우측 사이드바에 엽니다.
한 패널 안에 접이식 섹션으로 쌓여 있어 **여러 정보를 동시에** 봅니다.

| 섹션 | 내용 |
| :--- | :--- |
| **캡처** | 항상 떠 있는 입력창 + **기록** 버튼 (데스크톱은 `Enter` 도 가능) |
| **오늘 타임라인** | 방금 기록한 항목이 바로 아래 쌓입니다 |
| **모듈 검색** | 검색어를 입력해야 결과가 나옵니다 → 클릭 한 번으로 이동 |
| **도구** | 컨텍스트 생성 / 경로 점검 / 인덱스 동기화 |

입력창이 상시 노출되므로 **모달을 여는 동작 자체가 사라집니다.** 캡처의 실제 마찰은
타이핑이 아니라 "기록 창을 띄우는" 한 단계였고, 패널은 그 단계를 없앱니다.

모듈 섹션은 **목록이 아니라 검색창입니다.** 좁은 사이드바에서 전체 모듈 목록은 수십 줄의
잡음이 되고, 정작 계속 바뀌는 오늘 타임라인을 화면 밖으로 밀어냅니다. 검색어를 입력하기
전에는 아무것도 불러오지 않으므로, 패널을 열기만 할 때 파이썬이 실행되지도 않습니다.

---

## ⚡ Python 없이 기록

타임라인 기록은 기본적으로 플러그인이 **파일에 직접 씁니다.** CLI 경유는 항목마다
파이썬 인터프리터를 새로 띄우기 때문에 실측 **약 1.6초**가 걸립니다 — 0.5초 캡처라는
목표의 3배가 넘습니다. 직접 쓰기는 밀리초 단위입니다.

파일 형식은 `memory_tool/core/timeline.py` 와 정확히 같습니다:

```markdown
# 2026-08-17 Timeline
- 14:30 | 기록 내용
```

- 이미 그 날짜의 파일이 있으면 **어떤 방식으로 이름 붙어 있든 그 파일에 이어 붙입니다.**
  하루 기록이 두 파일로 갈라지지 않습니다.
- 새 파일의 이름은 다음 순서로 정합니다: **플러그인 설정 → `config.yaml` 의
  `timeline.filename` → 이미 쓰고 있는 파일명 → 기본값(`14.md`)**.

  세 번째 단계가 핵심입니다. `config.yaml` 은 의도를 적어 둔 곳이지만 플러그인이 항상
  읽을 수 있지는 않습니다. 휴대폰에서는 그 파일이 동기화되지 않았을 수 있고, 기반 폴더를
  잘못 잡으면 애초에 다른 자리를 읽습니다. 그럴 때 곧장 기본값으로 떨어지면, 나머지 파일이
  전부 `2026-08-20.md` 인 지식 베이스에 혼자 `20.md` 가 생겨서 하루가 두 파일로 갈라지고
  Calendar 플러그인에서도 보이지 않게 됩니다. 그래서 **주변 파일명을 먼저 따릅니다.**

  지금 어떤 이름으로 만들어지는지는 `Ctrl+P` → **타임라인 파일명 규칙 확인** 으로 근거와
  함께 확인할 수 있고, 설정 → **타임라인 파일명** 에서 고정할 수도 있습니다.
- 태그 형식(`[tag]` / `#tag`)도 `tag.storage_format` 을 따릅니다.
- 직접 쓰기가 실패하면 (권한, 예상 밖 기반 폴더 등) **자동으로 CLI 로 넘어가고**
  어느 경로로 기록됐는지 알려줍니다. 기록이 사라지지는 않습니다.

### 검색 인덱스

직접 쓰기는 CLI 가 기록과 함께 수행하던 SQLite 색인 단계를 건너뜁니다. 그래서
미반영 건수를 세다가 일정 개수(기본 10)가 쌓이면 자동으로 `index` 를 돌립니다.

- 즉시 반영하려면: `Ctrl+P` → **검색 인덱스 동기화**
- 자동 기준 변경: 설정 → **인덱스 자동 동기화 기준** (`0` 이면 수동만)
- 직접 쓰기가 싫다면: 설정 → **Python 없이 직접 기록** 을 끄면 항상 CLI 를 씁니다

---

## 📱 안드로이드 / iOS

**캡처 전용으로 동작합니다.** 모바일에는 파이썬이 없으므로 CLI 기반 기능은 쓸 수 없지만,
기록은 플러그인이 직접 파일에 쓰므로 그대로 됩니다.

| 기능 | 모바일 |
| :--- | :--- |
| 타임라인 기록 (패널·모달) | ✅ |
| 오늘 타임라인 보기 | ✅ |
| 모듈 검색·이동 | ✅ (vault 스캔) |
| 기반 폴더 자동 감지 | ✅ (`timeline/`+`modules/` 탐색) |
| 컨텍스트·경로 점검·질문·모듈 생성 | ❌ 파이썬 필요 |
| 검색 인덱스 | ⏸ 데스크톱에서 따라잡음 |

동작 방식:

- **단축키 없이 전부 탭으로** 됩니다. 좌측 리본의 ✏️ 로 바로 기록하거나, ⏱️ 로 패널을
  열어 입력창과 **기록** 버튼을 씁니다. 위의 "버튼으로" 표를 참고하세요.
- CLI 가 필요한 명령은 **모바일에서 아예 등록되지 않습니다.** "여기서는 안 됩니다"만
  말하는 팔레트 항목은 없느니만 못합니다. 패널의 도구 섹션도 설명으로 대체됩니다.
- 기반 폴더는 `mbase` 대신 vault 안에서 `timeline/` 과 `modules/` 를 **둘 다** 가진
  폴더를 찾아 판별합니다. 못 찾으면 추측하지 않고 알립니다 — 엉뚱한 폴더에 기록하면
  어떤 명령으로도 찾을 수 없게 되기 때문입니다. 데스크톱에서도 `mbase` 호출이 실패하거나
  그 결과가 vault 밖을 가리키면 같은 방식으로 다시 찾습니다.
- `config.yaml` 이 동기화되지 않은 기기에서도 파일명 방식은 **이미 있는 타임라인 파일의
  이름을 보고** 맞춥니다.
- 모바일에서 기록한 항목은 인덱스에 반영되지 않은 채 쌓이고, **데스크톱에서 vault 를
  열면 자동으로 따라잡습니다.**

> 동기화(iCloud/Obsidian Sync/Syncthing 등)는 별도로 설정해야 합니다. 이 플러그인은
> vault 안의 파일만 다룹니다.

---

## 📂 모듈 생성 + 템플릿 자동 적용

`Ctrl+P` → **모듈 생성** 은 MOP 의 판별 절차를 그대로 물어봅니다.

1. **Kind** — "이 문서가 서술하는 대상이 이미 존재하는가? 존재한다면 틀렸을 때
   틀린 것은 *지식*인가 *문서*인가?"
   → `intent` / `knowledge` / `implementation`
2. **Nature** (`implementation` 에는 없음) — "무엇이 이 모듈을 갱신시키는가?"
   → `knowledge` 는 `concept` / `reference` / `analysis` / `tracker` / `method`
   → `intent` 는 `idea` / `inquiry` / `plan`

Kind 를 바꾸면 Nature 목록도 그 Kind 의 것으로 다시 채워집니다.

**초안으로 시작** 을 켜면 전체 골격 대신 40줄짜리 씨앗 문서가 생깁니다. 처음 쓰기
시작하는 시점에는 신뢰도도 경계도 인용 결론도 아직 없으므로, 그날 채울 수 있는 것만
담고 다음에 채울 항목을 문서 끝에 순서대로 적어 둡니다. 나중에 데스크톱에서
`mmodule grow <경로>` 를 실행하면 없는 절만 덧붙습니다.

선택한 답은 `mmodule create --kind --nature` 로 그대로 넘어갑니다. **조립은 memory_tool 이
합니다** — 플러그인은 두 질문을 모듈 생성 시점에 반드시 묻게 만드는 역할만 합니다.
그 시점이 답하기 가장 싸고, 동시에 가장 건너뛰기 쉬운 순간이기 때문입니다.

결과물은 다섯 문서(`module`/`current`/`decisions`/`dependencies`/`interface`)를 `---` 로
이어 붙인 완성된 단일 파일이고, 고른 Nature 의 목차가 `## 2. 본문` 자리에 들어갑니다.

- 템플릿을 고치려면 `<기반폴더>/templates/<kind>/` 에 두면 번들 기본값보다 우선합니다
  (자세한 내용은 그 폴더의 README, 또는 `mhelp module`)
- **신뢰도·대상 버전·근거 데이터는 채우지 않습니다.** 그럴듯하게 자동으로 채운
  검증 상태는, 명백히 비어 있는 칸보다 나쁩니다

> 모듈 생성은 CLI 가 필요하므로 **데스크톱 전용**입니다.

---

## 🤔 지식베이스에 질문하기 (mask)

`Ctrl+P` → **기억에 질문하기** 로 엽니다.

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

#### 여러 프로젝트 한 번에

파일명 방식은 프로젝트마다 설정되므로, 여러 지식베이스를 Obsidian 과 함께 쓴다면
모두 변환해야 합니다.

```bash
# 특정 프로젝트 (반복 지정 가능)
mmigrate-timeline --filename date --root ../other-project --root ../another

# 폴더 아래 모든 지식베이스를 찾아서
mmigrate-timeline --filename date --scan E:/code_projects --dry-run
mmigrate-timeline --filename date --scan E:/code_projects
```

- 이름을 바꾸기 **전에 전체 계획을 먼저 보여줍니다**
- 프로젝트마다 독립적으로 적용되므로, 하나가 실패해도 그 프로젝트만 롤백되고
  나머지는 그대로 완료됩니다
- `--scan` 은 바로 아래 폴더만 확인하며, 상위로 거슬러 올라가지 않습니다
  (지식베이스가 없는 폴더가 부모 것을 잘못 물려받지 않도록)

#### 파일명 중복 경고

폴더가 달라도 **파일명이 같으면** Obsidian 은 하나만 엽니다. 변환 후 그런 쌍이 남으면
경고합니다:

```
Duplicate filenames (1): Obsidian identifies notes by filename...
  project_name 2026-01-08.md
    timeline/2026-01-08.md
    timeline/daily/2026-01/2026-01-08.md
```

보통 구조 마이그레이션이 중간에 멈춰 같은 날짜가 두 곳에 남은 경우입니다.
내용을 확인해 병합하거나 하나를 지우면 해결됩니다.

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
패널·모달 기록과 Calendar 클릭이 **같은 파일**을 가리킵니다.

---

## 🛠️ 개발자용: 핫 리로드 (개발 모드)

플러그인 소스 수정 시 자동 리빌드:

```powershell
cd obsidian-plugin
npm run dev
```

파일 변경 감지 시 자동으로 `main.js`가 재빌드됩니다.  
Obsidian에서 플러그인을 **비활성화 → 활성화** 하거나 [Hot Reload](https://obsidian.md/plugins?id=hot-reload) 플러그인을 사용하면 즉시 반영됩니다.
