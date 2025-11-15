# 🚀 새 세션 빠른 시작 가이드

> **MemoryWeb 프로젝트 시작하기**
>
> 이 가이드는 새 Claude Code 세션에서 프로젝트를 시작할 때 사용합니다.

---

## 📝 새 세션 첫 메시지 (복사해서 사용)

```
새 프로젝트 MemoryWeb을 시작하려고 합니다.

1. 먼저 이 파일을 읽어주세요:
   E:\code_projects\memory_tool\personal-notes-web-design.md

2. 이 파일도 읽어주세요:
   E:\code_projects\memory_tool\QUICKSTART-NEW-SESSION.md

3. memory_tool 프로젝트를 라이브러리로 활용합니다.

4. Phase 1 (Core Features)부터 시작합니다.

준비되었으면 시작해주세요.
```

---

## 📋 프로젝트 개요 (요약)

### 프로젝트명
**MemoryWeb** (Personal Notes Web)

### 목표
- memory_tool의 웹 인터페이스
- 시각적으로 아름다운 UI (shadcn/ui)
- 로컬 우선, 나중에 다중 디바이스

### 기술 스택
```
Backend:  FastAPI (Python)
Frontend: React + Vite + shadcn/ui (TypeScript)
Core:     memory_tool (로컬 패키지 설치)
```

---

## ⚠️ 중요: memory_tool 통합 방법

### Git Submodule 사용 안 함! ❌

**문제점:**
- `.claude` 폴더 충돌 (프로젝트/.claude vs memory_tool/.claude)
- 복잡한 import 경로
- 하위 폴더 위치 문제

### ✅ 로컬 패키지 설치 방식 채택

**방법:**
```bash
# requirements.txt에 추가
-e ../../memory_tool

# pip로 설치
pip install -r requirements.txt
```

**장점:**
- ✅ .claude 폴더 충돌 없음
- ✅ 깔끔한 import
- ✅ Python 표준 방식
- ✅ 개발 편의성

---

## 🎯 Phase 1: Core Features (첫 시작)

### 목표
작동하는 최소 제품 (MVP)

### 작업 항목 (1주)

#### Backend (2-3일)
```
□ 프로젝트 구조 생성
□ FastAPI 기본 설정
□ memory_tool 패키지 설치 (pip install -e)
□ Notes API (CRUD)
□ Timeline API
□ 기본 검색 API
```

#### Frontend (3-4일)
```
□ React + Vite 프로젝트 생성
□ shadcn/ui 설정
□ 레이아웃 (Sidebar + Header + Main)
□ NoteEditor (기본)
□ NoteList
□ Timeline 조회
□ 기본 검색
```

---

## 📂 프로젝트 구조 (최종)

```
E:\code_projects\
├── memory_tool\              # 기존 프로젝트 (독립)
│   ├── memory_tool\          # 패키지
│   ├── .memory\              # memory_tool 개발 데이터
│   └── .claude\              # memory_tool 설정
│
└── MemoryWeb\                # 🆕 새 프로젝트 (독립)
    ├── backend\
    │   ├── main.py
    │   ├── requirements.txt  # ⭐ memory_tool 여기서 참조
    │   ├── venv\             # ⭐ memory_tool 여기 설치됨
    │   ├── api\
    │   ├── core\
    │   └── models\
    │
    ├── frontend\             # React + Vite
    │   ├── src\
    │   └── package.json
    │
    ├── .memory\              # ⭐ MemoryWeb 데이터 (독립)
    ├── .claude\              # ⭐ MemoryWeb 설정 (하나만!)
    │
    ├── scripts\
    │   └── dev.sh
    │
    └── README.md
```

---

## 🔧 Step-by-Step 시작 가이드

### Step 1: 프로젝트 디렉토리 생성

```bash
cd E:\code_projects
mkdir MemoryWeb
cd MemoryWeb
git init
```

### Step 2: memory_tool 연결 (패키지 설치 방식)

**⚠️ 중요: Submodule 사용 안 함!**

#### backend 구조 생성
```bash
mkdir -p backend/api backend/core backend/models backend/tests
touch backend/__init__.py
```

#### backend/requirements.txt 생성
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6

# memory_tool (로컬 개발 모드)
# 상대 경로: MemoryWeb/backend/ → memory_tool/
-e ../../memory_tool
```

#### 설치
```bash
cd backend

# 가상환경 생성
python -m venv venv
venv\Scripts\activate  # Windows: venv\Scripts\activate

# 패키지 설치 (memory_tool 포함)
pip install -r requirements.txt
```

#### 확인
```bash
python -c "from memory_tool.core.timeline import TimelineManager; print('✅ Import OK')"
```

### Step 3: Backend 기본 파일

**backend/main.py:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MemoryWeb API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "MemoryWeb API"}

@app.get("/health")
async def health():
    return {"status": "ok"}
```

**backend/core/notes_manager.py:**
```python
"""MemoryWeb 비즈니스 로직"""
from pathlib import Path

# ✅ 깔끔한 import (패키지로 설치됨)
from memory_tool.core.timeline import TimelineManager
from memory_tool.core.search import SearchEngine

class NotesManager:
    """노트 관리 클래스"""

    def __init__(self, memory_dir: str = "../.memory"):
        self.memory_dir = Path(memory_dir)
        self.timeline = TimelineManager(self.memory_dir)
        self.search = SearchEngine(self.memory_dir)

    async def add_note(self, content: str, tags: list = None):
        """노트 추가"""
        return self.timeline.add_entry(content, tags=tags or [])

    async def search_notes(self, query: str, mode: str = "text"):
        """노트 검색"""
        return self.search.search(query, mode=mode)
```

### Step 4: Frontend 설정

```bash
cd ..  # MemoryWeb/

# Vite 프로젝트 생성
pnpm create vite frontend --template react-ts
cd frontend

# 의존성 설치
pnpm install

# shadcn/ui 초기화
pnpm dlx shadcn-ui@latest init

# 컴포넌트 추가
pnpm dlx shadcn-ui@latest add button card input textarea dialog

# 추가 패키지
pnpm add react-router-dom zustand @tiptap/react @tiptap/starter-kit date-fns lucide-react
```

### Step 5: .memory/ 디렉토리

```bash
cd ..  # MemoryWeb/
mkdir -p .memory/timeline .memory/modules .memory/docs

cat > .memory/config.yaml << 'EOF'
mode: local
local:
  data_path: .memory/
  auth_required: false
EOF
```

### Step 6: 개발 스크립트

**scripts/dev.sh (Windows: dev.bat):**
```bash
#!/bin/bash

# Backend
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Frontend
cd frontend
pnpm dev &
FRONTEND_PID=$!
cd ..

echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "API Docs: http://localhost:8000/docs"

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
```

### Step 7: .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
venv/
.env

# Node
node_modules/
dist/

# Memory data (선택사항)
.memory/

# IDE
.vscode/
.idea/
```

### Step 8: 첫 커밋

```bash
git add .
git commit -m "Initial commit: MemoryWeb project structure

- Backend: FastAPI + memory_tool (local package)
- Frontend: React + Vite + shadcn/ui
- memory_tool: Installed via pip install -e
- No submodule conflicts"
```

---

## ✅ Phase 1 완료 기준

### Backend
- [x] Notes API 작동 (POST, GET)
- [x] Timeline API 작동
- [x] Search API 작동 (기본)
- [x] memory_tool 통합 (import 성공)
- [x] API 문서 (Swagger)

### Frontend
- [x] 레이아웃 완성
- [x] 노트 작성 가능
- [x] 노트 목록 조회
- [x] 타임라인 조회
- [x] 기본 검색

### 통합
- [x] Backend ↔ Frontend 통신
- [x] 데이터 .memory/에 저장
- [x] 에러 핸들링

---

## 🎨 Phase 2: Enhanced UI (다음 단계)

Phase 1 완료 후 새 세션에서:

```
Phase 2 (Enhanced UI) 구현을 시작합니다.

personal-notes-web-design.md의
"Phase 2: Enhanced UI" 섹션을 참고해주세요.

목표:
- shadcn/ui 디자인 시스템 완성
- 리치 텍스트 에디터 (Tiptap)
- 타임라인 시각화
- 애니메이션 & 폴리시

시작합니다.
```

---

## 🆘 트러블슈팅

### 문제 1: memory_tool import 실패

```bash
# 확인
pip list | grep memory

# 재설치
cd backend
pip install -e ../../memory_tool
```

### 문제 2: 상대 경로 오류

**확인 사항:**
```
디렉토리 구조:
E:\code_projects\
├── memory_tool\
└── MemoryWeb\
    └── backend\requirements.txt  # 여기서 ../../memory_tool
```

**requirements.txt:**
```txt
-e ../../memory_tool  # ✅ 올바름
```

### 문제 3: CORS 오류

**backend/main.py 확인:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 문제 4: .claude 폴더 충돌

```
✅ 해결됨!
MemoryWeb/.claude만 존재
memory_tool/.claude는 별개 (충돌 없음)
```

---

## 📚 중요 문서

1. **상세 설계 문서:** `personal-notes-web-design.md`
   - 전체 아키텍처
   - API 설계
   - UI 컴포넌트 설계
   - Phase별 구현 계획

2. **이 문서:** `QUICKSTART-NEW-SESSION.md`
   - 빠른 시작
   - 단계별 가이드

---

## 🔄 Phase 진행 순서

```
Phase 1: Core Features          (1주)   ← 시작
Phase 2: Enhanced UI            (5일)   ← 시각적 완성
Phase 3: Enhanced Search        (5일)
Phase 4: Visualization          (5일)
Phase 5: Personalization        (1주)
Phase 6: Multi-device Foundation (5일)
Phase 7: Advanced               (추후)
```

---

## 💡 Claude에게 요청 예시

### 프로젝트 시작
```
새 프로젝트를 시작합니다.
personal-notes-web-design.md와
QUICKSTART-NEW-SESSION.md를 읽고
Phase 1부터 시작해주세요.
```

### Phase 진행
```
Phase 1 완료되었습니다.
Phase 2 (Enhanced UI)를 시작합니다.
설계 문서의 Phase 2 섹션을 참고해주세요.
```

### 특정 기능 구현
```
Notes API를 구현해주세요.
설계 문서의 "API 설계 > Notes API" 섹션을 참고해주세요.
```

---

## 🎯 핵심 차이점 (v1.0 → v1.1)

### 변경 전 (Submodule)
```
MemoryWeb/
├── memory_tool/     # ❌ Git submodule
│   └── .claude/     # ❌ 충돌!
└── .claude/
```

### 변경 후 (패키지 설치)
```
E:\code_projects\
├── memory_tool/     # 독립 프로젝트
└── MemoryWeb/
    ├── .claude/     # ✅ 하나만!
    └── backend/
        └── venv/
            └── memory_tool/  # ✅ 설치됨
```

---

## ✨ 완료!

이제 새 세션에서 이 가이드를 따라 시작하면 됩니다!

**다음 단계:**
1. 새 Claude Code 세션 시작
2. 위의 "새 세션 첫 메시지" 복사
3. Claude에게 붙여넣기
4. 구현 시작!

**Good luck! 🚀**
