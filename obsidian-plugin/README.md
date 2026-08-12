# Obsidian Memory Tool Integration Plugin

Obsidian 내에서 `memory_tool` CLI 기능을 사용할 수 있는 커뮤니티 플러그인입니다.  
타임라인 빠른 기록, 모듈 생성/탐색, AI 컨텍스트 빌드 등을 Obsidian에서 직접 실행할 수 있습니다.

---

## ✨ 주요 기능

| 단축키 | 기능 |
| :--- | :--- |
| `Ctrl+Alt+M` | ⏱️ 타임라인 0.5초 빠른 기록 |
| `Ctrl+Alt+G` | 🔍 모듈 퍼지 검색 & 즉시 이동 |
| `Ctrl+P` → `Create Module` | 📂 새 모듈 생성 (`mmodule create`) |
| `Ctrl+P` → `Build AI Context` | 🧠 AI 컨텍스트 빌드 (`mcontext`) |
| `Ctrl+P` → `Check Module Path Health` | 🏥 모듈 경로 건강 체크 (`mcheck`) |

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

## 📅 Obsidian Calendar 연동 설정

> 달력에서 날짜를 클릭하면 `memory_tool`의 해당 날짜 타임라인 파일로 자동 이동합니다.

### 필요 플러그인
- [Calendar](https://obsidian.md/plugins?id=calendar) 또는 [Periodic Notes](https://obsidian.md/plugins?id=periodic-notes) 커뮤니티 플러그인 설치

### Daily Notes 설정

Obsidian **설정** → **Daily Notes** 또는 **Periodic Notes**:

| 항목 | 값 |
| :--- | :--- |
| **Date format** | `YYYY-MM/DD` |
| **New file location** | `.memory/timeline/daily` |

설정 완료 후 달력에서 날짜를 클릭하면 `.memory/timeline/daily/2026-08/13.md` 와 같이 `memory_tool` 타임라인 파일로 즉시 이동합니다.

---

## 🛠️ 개발자용: 핫 리로드 (개발 모드)

플러그인 소스 수정 시 자동 리빌드:

```powershell
cd obsidian-plugin
npm run dev
```

파일 변경 감지 시 자동으로 `main.js`가 재빌드됩니다.  
Obsidian에서 플러그인을 **비활성화 → 활성화** 하거나 [Hot Reload](https://obsidian.md/plugins?id=hot-reload) 플러그인을 사용하면 즉시 반영됩니다.
