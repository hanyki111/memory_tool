# Interface

## CLI Commands

### m - 기록 (Memory Record)

**용도:** Timeline에 즉시 기록

**문법:**
```bash
m "메시지"
m "여러 줄
메시지도
가능"
```

**동작:**
1. 현재 프로젝트에서 `.memory/` 찾기
2. 오늘 날짜 파일 열기: `timeline/YYYY-MM/DD.md`
3. 타임스탬프와 함께 추가: `- HH:MM | 메시지`

**출력:**
```
✓ Recorded to timeline/2025-11/13.md
```

**에러:**
```
❌ Not in a project with .memory/
Run: minit
```

---

### ms - 검색 (Memory Search)

**용도:** 기록된 내용 검색

**문법:**
```bash
ms "키워드"                  # 로컬만
ms --with-kb "키워드"        # 로컬 + KB
ms --all "키워드"            # 모든 프로젝트 + KB
ms --type concept "패턴"     # 타입 필터 (Phase 2)
```

**동작:**
1. 검색 범위 결정
2. ripgrep 또는 Python regex로 검색
3. 파일 경로와 매칭 라인 출력

**출력:**
```
🔍 Searching: local only

timeline/2025-11/13.md
  22:50 | 결정: 플랫폼 = Python CLI
  22:52 | 결정: 기술 스택 = Python

modules/memory-system/decisions.md
  ## 2025-11-13: 플랫폼 선택 - Python CLI
```

---

### minit - 초기화 (Memory Initialize)

**용도:** 현재 프로젝트에 .memory/ 생성

**문법:**
```bash
minit
```

**동작:**
1. `.memory/` 존재 확인 (이미 있으면 경고)
2. 디렉토리 구조 생성:
   - `timeline/`
   - `modules/`
   - `concepts/`
   - `.index/`
3. `kb.lock` 생성
4. `.gitignore` 업데이트

**출력:**
```
✓ Initialized .memory/
  - timeline/  (daily logs)
  - modules/   (module contexts)
  - concepts/  (project concepts)

Try: m 'first entry'
```

---

### mcontext - 컨텍스트 생성 (Memory Context)

**용도:** Claude Code용 컨텍스트 마크다운 생성

**문법:**
```bash
mcontext                     # 기본 (최근 7일)
mcontext --days 3            # 최근 3일만
mcontext --query "OAuth"     # 특정 주제 관련
mcontext --output ctx.md     # 커스텀 출력 경로
```

**동작:**
1. Timeline 최근 N일 로드
2. 모든 모듈 로드 (module.md, current.md, decisions.md)
3. 프로젝트 개념 로드
4. 마크다운으로 통합
5. `.claude/memory-context.md`에 출력 (기본)

**출력:**
```
🔄 Building context...
  ✓ Timeline: 7 days, 142 entries
  ✓ Modules: 3 modules, 15 files
  ✓ Concepts: 2 concepts

✓ Context built: .claude/memory-context.md
```

---

### mstatus - 상태 확인 (Memory Status)

**용도:** 현재 프로젝트 메모리 상태 확인

**문법:**
```bash
mstatus
```

**출력:**
```
📊 Memory Status
━━━━━━━━━━━━━━━━━━━━

📝 Timeline:
  Files: 45
  Lines: 1,234

🧩 Modules:
  Count: 5

💡 Concepts:
  Count: 8

🕐 Recent (7 days):
  Active: 6 days
```

---

### mtoday - 오늘 보기 (Memory Today)

**용도:** 오늘 Timeline 출력

**문법:**
```bash
mtoday
```

**출력:**
```
- 22:30 | 프로젝트 생성
- 22:35 | 문서 읽기 시작
- 22:50 | 결정: Python CLI
...
```

---

### mweek - 이번 주 보기 (Memory Week)

**용도:** 최근 7일 Timeline 출력

**문법:**
```bash
mweek
```

**출력:**
```
📅 This Week's Timeline
━━━━━━━━━━━━━━━━━━━━━━

## 2025-11-07
...

## 2025-11-13
...
```

---

## Python API (Phase 2+)

```python
from memory_tool import Memory

# 초기화
mem = Memory()  # 현재 디렉토리에서 .memory/ 찾기

# 기록
mem.record("OAuth 구현 시작")

# 검색
results = mem.search("OAuth", scope="local")
results = mem.search("pattern", scope="kb")
results = mem.search("keyword", scope="all")

# 컨텍스트
context = mem.build_context(days=7)
print(context.to_markdown())

# 상태
status = mem.get_status()
print(f"Timeline files: {status.timeline_files}")
```

---

## File Format

### Timeline Entry
```markdown
- HH:MM | 메시지 내용
```

### Module File (YAML frontmatter)
```yaml
---
type: module
created: YYYY-MM-DD
status: active | deprecated | archived
---

# 마크다운 내용
```

### Concept File
```yaml
---
type: concept
domain: category
tags: [tag1, tag2]
timeline_refs:
  - [[time:YYYY-MM/DD#HH:MM]]
---

# 개념 내용
```

---

## Integration with Claude Code

### Manual (Phase 1)
```bash
# 컨텍스트 생성
mcontext

# Claude에게 읽어달라고 요청
"Read .claude/memory-context.md and help me with OAuth"
```

### Automatic (Phase 2 - Hook)
```bash
# .claude/hooks/pre-command.sh
#!/bin/bash
mcontext --quiet
```

### MCP Server (Phase 3)
```json
// claude_desktop_config.json
{
  "mcpServers": {
    "memory": {
      "command": "memory-tool",
      "args": ["mcp-server"]
    }
  }
}
```

Claude Code가 자동으로 다음 도구 사용 가능:
- `memory_search(query)`
- `memory_record(message)`
- `memory_get_context(days)`
