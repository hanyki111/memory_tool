# MemoryWeb - 상세 설계 문서

> **Version:** 1.1 (Updated for local package installation)
> **Date:** 2025-11-15
> **Author:** Claude Code
> **Status:** Design Phase

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [중요 변경사항](#중요-변경사항-v11)
3. [아키텍처](#아키텍처)
4. [기술 스택](#기술-스택)
5. [프로젝트 구조](#프로젝트-구조)
6. [memory_tool 통합 방법](#memory_tool-통합-방법)
7. [데이터 모델](#데이터-모델)
8. [API 설계](#api-설계)
9. [UI 컴포넌트 설계](#ui-컴포넌트-설계)
10. [Phase별 구현 계획](#phase별-구현-계획)
11. [새 세션 시작 가이드](#새-세션-시작-가이드)

---

## 프로젝트 개요

### 프로젝트명
**MemoryWeb** (Personal Notes Web)

### 핵심 목표
- memory_tool의 핵심 기능을 웹 인터페이스로 제공
- 시각적으로 아름답고 현대적인 UI/UX
- 개인 맞춤 워크플로우 지원
- 향후 다중 디바이스 확장 가능한 구조

### 핵심 원칙
1. **재발명 금지:** memory_tool을 라이브러리로 활용
2. **아름다움 우선:** 시각적 완성도가 사용 동기 부여
3. **확장 가능:** 로컬 우선, 나중에 클라우드로 쉽게 전환
4. **레이어드 아키텍처:** 관심사 분리 (Backend/Frontend)

---

## 중요 변경사항 (v1.1)

### ⚠️ Git Submodule → 로컬 패키지 설치

**문제점 발견:**
1. **Submodule 방식의 문제:**
   - `.claude` 폴더 충돌 (`project/.claude` vs `project/memory_tool/.claude`)
   - 복잡한 import 경로 (`sys.path.insert`)
   - 하위 폴더 위치로 인한 동작 우려

2. **해결책:**
   - ✅ **로컬 패키지 설치 방식 채택**
   - Python 표준 방식 (`pip install -e`)
   - .claude 폴더 충돌 없음
   - 깔끔한 import

**변경 내용:**
```diff
- git submodule add ../memory_tool memory_tool
+ pip install -e ../../memory_tool  # requirements.txt에 추가
```

---

## 아키텍처

### 전체 시스템 구조

```
┌─────────────────────────────────────────────────────┐
│                  Frontend Layer                      │
│  React 18 + Vite + shadcn/ui + Tailwind CSS        │
└─────────────────────────────────────────────────────┘
                         ↕ HTTP/REST API
┌─────────────────────────────────────────────────────┐
│                   API Layer                          │
│  FastAPI + Pydantic + CORS                          │
└─────────────────────────────────────────────────────┘
                         ↕ Python Import
┌─────────────────────────────────────────────────────┐
│              Core Layer (memory_tool)                │
│  ✅ Installed as package (pip install -e)           │
│  - Timeline Management                               │
│  - Search Engine (Text + Vector)                    │
│  - Module System                                     │
└─────────────────────────────────────────────────────┘
                         ↕ File I/O
┌─────────────────────────────────────────────────────┐
│            Storage Layer (.memory/)                  │
│  MemoryWeb의 데이터 (memory_tool과 독립)            │
└─────────────────────────────────────────────────────┘
```

---

## 기술 스택

### Backend: FastAPI ⭐⭐⭐⭐⭐

```yaml
Framework: FastAPI 0.104+
Python: 3.10+

Dependencies:
  - fastapi: Web framework
  - uvicorn: ASGI server
  - pydantic: Data validation
  - python-multipart: File uploads
  - memory-tool: Core functionality (로컬 패키지)
```

### Frontend: React 18 + Vite ⭐⭐⭐⭐⭐

```yaml
Framework: React 18.2+ + Vite 5.0+
UI: shadcn/ui (Radix UI + Tailwind CSS)
State: Zustand
Router: React Router
Editor: Tiptap
Visualization: React Flow, Recharts
```

---

## 프로젝트 구조

### 디렉토리 레이아웃 (중요!)

```
E:\code_projects\
├── memory_tool\                    # ✅ 독립 프로젝트
│   ├── memory_tool\                # 패키지
│   │   ├── core\
│   │   ├── cli.py
│   │   └── ...
│   ├── pyproject.toml
│   ├── .memory\                    # memory_tool 자체 개발 데이터
│   └── .claude\                    # memory_tool 설정
│
└── MemoryWeb\                      # ✅ 독립 프로젝트
    ├── backend\
    │   ├── main.py
    │   ├── requirements.txt        # ⭐ memory_tool 여기서 참조
    │   ├── venv\                   # ⭐ memory_tool 여기 설치됨
    │   ├── api\
    │   ├── core\
    │   └── models\
    │
    ├── frontend\
    │   ├── src\
    │   ├── package.json
    │   └── vite.config.ts
    │
    ├── .memory\                    # ⭐ MemoryWeb 데이터 (독립)
    ├── .claude\                    # ⭐ MemoryWeb 설정 (하나만!)
    │
    ├── scripts\
    │   └── dev.sh
    │
    ├── .gitignore
    └── README.md
```

### 핵심 포인트

1. **별도 디렉토리:** memory_tool과 MemoryWeb은 형제 관계
2. **하나의 .claude:** MemoryWeb/.claude만 존재 (충돌 없음)
3. **패키지 설치:** memory_tool은 backend/venv/에 설치
4. **독립 데이터:** 각자의 .memory/ 디렉토리 사용

---

## memory_tool 통합 방법

### ⭐ 로컬 패키지 설치 방식 (채택)

#### Step 1: requirements.txt 설정

**backend/requirements.txt:**
```txt
# FastAPI
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6

# memory_tool (로컬 개발 모드)
# 상대 경로: MemoryWeb/backend/ → memory_tool/
-e ../../memory_tool

# 나중에 PyPI 배포 시:
# memory-tool>=1.0.0
```

#### Step 2: 설치

```bash
cd E:\code_projects\MemoryWeb\backend

# 가상환경 생성
python -m venv venv
venv\Scripts\activate  # Windows

# 패키지 설치 (memory_tool 포함)
pip install -r requirements.txt
```

#### Step 3: 사용

**backend/core/notes_manager.py:**
```python
"""MemoryWeb 비즈니스 로직"""
from pathlib import Path

# ✅ 깔끔한 import (패키지로 설치되어 있음)
from memory_tool.core.timeline import TimelineManager
from memory_tool.core.search import SearchEngine

class NotesManager:
    """노트 관리 클래스"""

    def __init__(self, memory_dir: str = "../.memory"):
        """
        Args:
            memory_dir: MemoryWeb의 .memory/ 경로
        """
        self.memory_dir = Path(memory_dir)
        self.timeline = TimelineManager(self.memory_dir)
        self.search = SearchEngine(self.memory_dir)

    async def add_note(self, content: str, tags: list = None):
        """노트 추가"""
        return self.timeline.add_entry(
            content=content,
            tags=tags or []
        )

    async def search_notes(self, query: str, mode: str = "text"):
        """노트 검색"""
        if mode == "text":
            return self.search.search_text(query)
        elif mode == "semantic":
            return self.search.search_semantic(query)
        else:
            return self.search.search_hybrid(query)
```

**backend/api/notes.py:**
```python
from fastapi import APIRouter, HTTPException
from backend.core.notes_manager import NotesManager
from backend.models.note import NoteCreate, Note

router = APIRouter()
notes_manager = NotesManager()  # ✅ 경로 문제 없음!

@router.post("/notes", response_model=Note)
async def create_note(note: NoteCreate):
    """새 노트 생성"""
    try:
        result = await notes_manager.add_note(
            content=note.content,
            tags=note.tags
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 장점

1. ✅ **.claude 폴더 충돌 없음** - MemoryWeb/.claude만 존재
2. ✅ **깔끔한 import** - `from memory_tool.core import ...`
3. ✅ **Python 표준** - 익숙한 패키지 설치 방식
4. ✅ **개발 편의** - `-e` 옵션으로 수정사항 즉시 반영
5. ✅ **프로덕션 전환** - PyPI 배포 후 한 줄만 수정
6. ✅ **경로 문제 없음** - sys.path 조작 불필요

### 개발 워크플로우

```bash
# memory_tool 수정
cd E:\code_projects\memory_tool
# 코드 수정...

# MemoryWeb에서 즉시 반영됨 (-e 옵션 덕분)
cd E:\code_projects\MemoryWeb\backend
venv\Scripts\activate
python main.py  # ✅ 수정사항 즉시 적용!
```

---

## 데이터 모델

### Backend Models (Pydantic)

**backend/models/note.py:**
```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class NoteBase(BaseModel):
    """노트 기본 모델"""
    content: str = Field(..., min_length=1, max_length=10000)
    tags: List[str] = Field(default_factory=list)
    module: Optional[str] = None

class NoteCreate(NoteBase):
    """노트 생성 요청"""
    pass

class Note(NoteBase):
    """노트 응답"""
    id: str
    timestamp: datetime
    file_path: str

    class Config:
        from_attributes = True
```

---

## API 설계

### Base URL
```
Development: http://localhost:8000
Production:  https://api.yourdomain.com (future)
```

### 핵심 엔드포인트

```yaml
POST /api/notes
  Description: 새 노트 생성
  Request: { "content": "...", "tags": [...] }
  Response: Note 객체

GET /api/notes
  Description: 노트 목록
  Query: ?page=1&page_size=50
  Response: { "notes": [...], "total": 100 }

GET /api/search
  Description: 노트 검색
  Query: ?q=query&mode=text|semantic|hybrid
  Response: { "results": [...] }

GET /api/timeline
  Description: 타임라인 조회
  Query: ?period=today|week|month
  Response: { "days": [...] }
```

---

## UI 컴포넌트 설계

### shadcn/ui 기반

**컴포넌트 구성:**
```tsx
// NoteEditor.tsx
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

export default function NoteEditor({ onSave }) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: '',
  })

  return (
    <Card className="p-4">
      <EditorContent editor={editor} />
      <Button onClick={() => onSave(editor.getText())}>
        Save
      </Button>
    </Card>
  )
}
```

---

## Phase별 구현 계획

### Phase 1: Core Features (1주)

**목표:** 작동하는 MVP

**Backend:**
- ✅ FastAPI 설정
- ✅ memory_tool 패키지 설치 및 통합
- ✅ Notes API (CRUD)
- ✅ Timeline API
- ✅ 기본 검색 API

**Frontend:**
- ✅ React + Vite + shadcn/ui 설정
- ✅ 레이아웃 (Sidebar + Header + Main)
- ✅ NoteEditor (기본)
- ✅ Timeline 조회

### Phase 2: Enhanced UI (5일) ⭐

**목표:** 시각적 완성

- ✅ shadcn/ui 디자인 시스템
- ✅ 리치 텍스트 에디터 (Tiptap)
- ✅ 다크/라이트 테마
- ✅ 애니메이션

### Phase 3-7: (상세 내용은 이전 버전과 동일)

---

## 새 세션 시작 가이드

### 준비사항

```yaml
필수:
  - Python 3.10+
  - Node.js 18+
  - pnpm 8.0+

디렉토리 구조:
  E:\code_projects\
  ├── memory_tool\      # 반드시 존재
  └── MemoryWeb\        # 새로 생성
```

### Step-by-Step

#### Step 1: 프로젝트 디렉토리 생성

```bash
cd E:\code_projects
mkdir MemoryWeb
cd MemoryWeb
git init
```

#### Step 2: memory_tool 연결 (패키지 설치 방식)

**⚠️ Submodule 사용 안 함!**

**backend 구조 생성:**
```bash
mkdir -p backend/api backend/core backend/models
```

**backend/requirements.txt 생성:**
```bash
cat > backend/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6

# memory_tool (로컬 개발 모드)
-e ../../memory_tool
EOF
```

**설치:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

**확인:**
```bash
python -c "from memory_tool.core import timeline; print('✅ Import OK')"
```

#### Step 3: Backend 기본 파일

**backend/main.py:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MemoryWeb API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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

#### Step 4: Frontend 설정

```bash
cd ..  # MemoryWeb/
pnpm create vite frontend --template react-ts
cd frontend
pnpm install

# shadcn/ui
pnpm dlx shadcn-ui@latest init
pnpm dlx shadcn-ui@latest add button card input textarea

# 추가 패키지
pnpm add react-router-dom zustand @tiptap/react @tiptap/starter-kit
```

#### Step 5: .memory/ 디렉토리

```bash
cd ..  # MemoryWeb/
mkdir -p .memory/timeline .memory/modules .memory/docs

cat > .memory/config.yaml << 'EOF'
version: "1.0"
timeline:
  auto_record: false
EOF
```

#### Step 6: 개발 스크립트

**scripts/dev.sh:**
```bash
#!/bin/bash

# Backend
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Frontend
cd ../frontend
pnpm dev &
FRONTEND_PID=$!

echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
```

#### Step 7: .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
venv/
.env

# Node
node_modules/
dist/

# Memory data (optional)
.memory/

# IDE
.vscode/
```

#### Step 8: 첫 커밋

```bash
git add .
git commit -m "Initial commit: MemoryWeb project structure

- Backend: FastAPI + memory_tool (local package)
- Frontend: React + Vite + shadcn/ui
- memory_tool: Installed via pip install -e
- No submodule conflicts"
```

---

## 트러블슈팅

### 문제 1: memory_tool import 실패

```bash
# 확인
pip list | grep memory

# 재설치
pip install -e ../../memory_tool
```

### 문제 2: 상대 경로 오류

```
MemoryWeb/backend/requirements.txt에서:
-e ../../memory_tool  # ✅ 올바름

디렉토리 구조 확인:
E:\code_projects\
├── memory_tool\
└── MemoryWeb\backend\  # 여기서 ../../memory_tool이 맞음
```

### 문제 3: .claude 폴더 충돌

```
✅ 해결됨!
MemoryWeb/.claude만 존재
memory_tool/.claude는 별개 (충돌 없음)
```

---

## 참고 자료

- FastAPI: https://fastapi.tiangolo.com/
- React: https://react.dev/
- shadcn/ui: https://ui.shadcn.com/
- memory_tool: ../memory_tool/README.md

---

## 변경 이력

- 2025-11-15 v1.0: 초안 작성
- 2025-11-15 v1.1: Git Submodule → 로컬 패키지 설치 방식 변경

---

**이 문서는 새 세션 시작 시 반드시 읽어야 합니다!**
