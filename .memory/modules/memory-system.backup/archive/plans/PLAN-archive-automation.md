# Archive Automation Implementation Plan

## Overview

**Goal**: 수동 아카이브 명령어 + 파일 크기 기반 경고 시스템 구현

**Background**: Decision #28에서 PLAN 문서 아카이브 정책 수립 완료. decisions.md, current.md도 자동화 필요.

**Branch**: `feature/archive-command`

**Date**: 2025-11-14

---

## Current State Analysis

### 문제점

1. **수동 아카이브 작업**:
   - LLM이 직접 파일 편집
   - 실수 가능성
   - 매번 반복 작업

2. **아카이브 시점 판단 어려움**:
   - decisions.md가 언제 "너무 큰지" 알기 어려움
   - Phase 전환 시점 놓칠 수 있음

3. **PLAN 문서도 수동**:
   - 완료 후 수동 이동 필요

### 기존 아카이브 작업 (2025-11-14)

```bash
# 수동으로 수행한 작업:
# 1. decisions.md → archive/decisions-phase1-4.md (1250줄)
# 2. current.md → archive/current-phase1-4.md (242줄)
# 3. PLAN-*.md → archive/plans/ (2개 파일)
```

---

## Requirements

### 1. `marchive` 명령어

**User Stories:**
- As a user, I want to archive old decisions with one command
- As a user, I want to archive completed phase status
- As a user, I want to move completed PLAN documents

**Acceptance Criteria:**

**A. `marchive decisions --phase N`**
- [ ] decisions.md에서 Phase N 이전 항목 추출
- [ ] archive/decisions-phase{range}.md 생성
- [ ] decisions.md에서 아카이브된 항목 제거
- [ ] 백업 생성 (.bak)
- [ ] decisions-index.md 자동 업데이트

**B. `marchive current --phase N`**
- [ ] current.md 전체를 archive/current-phaseN.md로 복사
- [ ] current.md 초기화 (템플릿)
- [ ] 백업 생성 (.bak)

**C. `marchive plans`**
- [ ] PLAN-*.md 파일 검색
- [ ] archive/plans/로 이동
- [ ] 이동된 파일 목록 출력

**D. `marchive --dry-run`**
- [ ] 실제 이동 없이 미리보기
- [ ] 아카이브될 항목/파일 목록 출력

### 2. 파일 크기 경고

**User Stories:**
- As a user, I want warnings when documentation files get too large
- As a user, I want recommendations on when to archive

**Acceptance Criteria:**
- [ ] m 명령어 실행 시 파일 크기 체크
- [ ] config.yaml에 threshold 설정
- [ ] 경고 메시지 + 추천 명령어 표시
- [ ] --quiet 플래그로 경고 무시 가능

---

## Design Decisions

### Decision 1: 아카이브 범위 지정 방식

**Options:**
- A) Phase 번호 지정 (`--phase 5`)
- B) 날짜 기반 (`--before 2025-11-14`)
- C) 라인 수 기반 (`--lines 500`)

**Choice: A (Phase 번호)**
- 프로젝트의 자연스러운 구분
- decisions.md에 이미 Phase 표기 있음
- 명확한 경계

**Implementation:**
```python
marchive decisions --phase 5
# → Archive decisions #1-#23 (Phase 1-5)
# → Keep decisions #24+ (Phase 6+)
```

### Decision 2: 파일 이름 형식

**Options:**
- A) `decisions-phase1-5.md` (범위 표시)
- B) `decisions-until-phase5.md`
- C) `decisions-2025-11-14.md` (날짜)

**Choice: A (범위 표시)**
- 기존 형식과 일관성 (decisions-phase1-4.md)
- 어떤 Phase들이 포함되었는지 명확

### Decision 3: 원본 파일 처리

**Options:**
- A) 아카이브 항목 삭제 + Recent 링크 추가
- B) 전체 백업 + 새 파일로 교체
- C) 아카이브만 하고 원본 유지

**Choice: A (삭제 + 링크)**
- 원본 파일 크기 감소 (목적 달성)
- 백업 파일로 안전성 확보
- archive 링크로 접근성 유지

**Example:**
```markdown
# decisions.md (아카이브 후)

> **Recent decisions for Phase 6**

For Phase 1-5 decisions (#1-#23), see [archive/decisions-phase1-5.md](./archive/decisions-phase1-5.md)

---

## Recent Decisions (Phase 6)

### 2025-11-15: ...
```

### Decision 4: 경고 Threshold

**Options:**
- A) 고정값 (500줄)
- B) config.yaml 설정
- C) 적응형 (파일마다 다름)

**Choice: B (config.yaml)**
- 사용자 커스터마이징 가능
- 프로젝트마다 기준 다를 수 있음

**Config:**
```yaml
modules:
  warn_size_decisions: 500  # lines
  warn_size_current: 300    # lines
  warn_on_record: true      # m 명령어 시 경고
  warn_on_status: true      # mstatus 시 경고
```

---

## Implementation Plan

### Phase 1: Core Archiver (2-3 hours)

**Files to create:**
- `memory_tool/core/archiver.py` - Archiver 클래스

**Tasks:**

**1.1. Archiver 클래스 구현**
```python
class Archiver:
    """Handle archiving of module documentation."""

    def archive_decisions(
        self,
        phase: int,
        dry_run: bool = False,
    ) -> tuple[Path, int]:
        """
        Archive decisions up to specified phase.

        Returns:
            (archive_path, num_archived)
        """
        # 1. Read decisions.md
        # 2. Parse decisions (regex: ### YYYY-MM-DD: ... 결정 #N)
        # 3. Filter by phase (Decision #1-#23 for phase 5)
        # 4. Write to archive/decisions-phase{range}.md
        # 5. Update decisions.md (remove archived, add link)
        # 6. Update decisions-index.md

    def archive_current(
        self,
        phase: int,
        dry_run: bool = False,
    ) -> Path:
        """Archive current.md to archive/current-phaseN.md."""
        # 1. Copy current.md → archive/current-phaseN.md
        # 2. Reset current.md with template

    def archive_plans(
        self,
        dry_run: bool = False,
    ) -> list[Path]:
        """Move PLAN-*.md to archive/plans/."""
        # 1. Find PLAN-*.md files
        # 2. Move to archive/plans/
        # 3. Return list of moved files
```

**1.2. Decision 파싱 로직**
```python
def _parse_decisions(self, content: str) -> list[dict]:
    """Parse decisions from markdown content."""
    # Pattern: ### YYYY-MM-DD: ... 결정 #N
    pattern = r'###\s+(\d{4}-\d{2}-\d{2}):\s+(.+?)\n\*\*결정 #(\d+)\*\*'

    decisions = []
    for match in re.finditer(pattern, content, re.DOTALL):
        date_str, title, decision_num = match.groups()

        # Extract full decision text until next ### or ---
        start = match.start()
        end = # find next ### or ---

        decisions.append({
            'number': int(decision_num),
            'date': date_str,
            'title': title,
            'content': content[start:end],
        })

    return decisions
```

**Tests:**
- [ ] Parse decisions correctly
- [ ] Filter by phase number
- [ ] Archive file creation
- [ ] Original file update with link

### Phase 2: CLI Integration (1-2 hours)

**Files to modify:**
- `memory_tool/cli.py` - Add marchive command

**Tasks:**

**2.1. marchive 명령어**
```python
@app.command()
def archive(
    target: str = typer.Argument(..., help="Target: 'decisions', 'current', 'plans'"),
    phase: int = typer.Option(None, "--phase", help="Phase number to archive (required for decisions/current)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be archived without doing it"),
):
    """Archive completed documentation (marchive command).

    Examples:
        marchive decisions --phase 5   # Archive Phase 1-5 decisions
        marchive current --phase 5     # Archive Phase 5 current.md
        marchive plans                 # Move PLAN-*.md to archive
        marchive decisions --dry-run   # Preview what will be archived
    """
    archiver = Archiver()

    if target == "decisions":
        if not phase:
            console.print("[red]ERROR[/red] --phase required for decisions")
            sys.exit(1)

        archive_path, num = archiver.archive_decisions(phase, dry_run)

        if dry_run:
            console.print(f"[cyan]Would archive {num} decisions to:[/cyan]")
            console.print(f"  {archive_path}")
        else:
            console.print(f"[green]OK[/green] Archived {num} decisions")
            console.print(f"  → {archive_path}")

    elif target == "current":
        # Similar for current

    elif target == "plans":
        # Similar for plans
```

**Tests:**
- [ ] CLI argument parsing
- [ ] Error handling (missing --phase)
- [ ] Dry-run mode
- [ ] Success messages

### Phase 3: File Size Warnings (1 hour)

**Files to modify:**
- `memory_tool/cli.py` - Add warnings to record() and status()
- `memory_tool/core/warnings.py` (new) - Warning system

**Tasks:**

**3.1. Warning System**
```python
class FileSizeWarning:
    """Check and warn about large documentation files."""

    def check_sizes(self) -> list[tuple[str, int, int]]:
        """
        Check file sizes against thresholds.

        Returns:
            List of (filename, current_lines, threshold)
        """
        warnings = []

        config = Config()

        # Check decisions.md
        decisions_path = Path(".memory/modules/memory-system/decisions.md")
        if decisions_path.exists():
            lines = len(decisions_path.read_text().splitlines())
            threshold = config.get("modules.warn_size_decisions", 500)

            if lines > threshold:
                warnings.append(("decisions.md", lines, threshold))

        # Check current.md
        # Similar logic

        return warnings

    def format_warning(self, warnings: list) -> str:
        """Format warnings for display."""
        if not warnings:
            return ""

        output = []
        for filename, lines, threshold in warnings:
            output.append(f"[yellow]⚠️  {filename} exceeds {threshold} lines (current: {lines})[/yellow]")

            if filename == "decisions.md":
                # Detect current phase from file
                current_phase = self._detect_phase()
                output.append(f"[dim]💡 Consider: marchive decisions --phase {current_phase - 1}[/dim]")
            elif filename == "current.md":
                current_phase = self._detect_phase()
                output.append(f"[dim]💡 Consider: marchive current --phase {current_phase}[/dim]")

        return "\n".join(output)
```

**3.2. Integrate into commands**
```python
# In record() command
def record(...):
    # ... existing code ...

    # Check file sizes (if enabled)
    config = Config()
    if config.get("modules.warn_on_record", True):
        warning_system = FileSizeWarning()
        warnings = warning_system.check_sizes()
        if warnings:
            console.print()  # Blank line
            console.print(warning_system.format_warning(warnings))

# Similar for status() command
```

**Config:**
```yaml
modules:
  warn_size_decisions: 500
  warn_size_current: 300
  warn_on_record: true
  warn_on_status: true
```

**Tests:**
- [ ] Warning detection
- [ ] Threshold from config
- [ ] Display in m command
- [ ] Display in mstatus command
- [ ] Disable with config

### Phase 4: Testing & Documentation (1 hour)

**Tasks:**

**4.1. Integration Testing**
```bash
# Test 1: Archive decisions
marchive decisions --phase 5 --dry-run
# → Should show decisions #1-#23

marchive decisions --phase 5
# → Should create archive/decisions-phase1-5.md
# → Should update decisions.md

# Test 2: Archive current
marchive current --phase 5
# → Should create archive/current-phase5.md
# → Should reset current.md

# Test 3: Archive plans
marchive plans
# → Should move PLAN-*.md to archive/plans/

# Test 4: File size warnings
# Create large decisions.md (600 lines)
m "Test entry"
# → Should show warning + suggestion
```

**4.2. Documentation Updates**
- [ ] README.md: Add marchive command
- [ ] config.yaml: Add comments for new settings
- [ ] archive/README.md: Update policy with marchive usage

**4.3. Dogfooding**
- [ ] Use marchive on actual files (if any new PLAN docs)
- [ ] Verify warnings work with real data

---

## File Structure

```
memory_tool/
├── core/
│   ├── archiver.py          # (new) Archiver class
│   └── warnings.py          # (new) File size warnings
│
├── cli.py                   # (modify) Add marchive command + warnings
│
└── ...

.memory/
├── config.yaml              # (modify) Add warning thresholds
└── modules/
    └── memory-system/
        ├── archive/
        │   ├── decisions-phase1-5.md  # (generated by marchive)
        │   └── ...
        └── ...
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_archiver.py
def test_parse_decisions():
    content = """
### 2025-11-14: Test Decision ⭐
**결정 #24:** Test content
...
---
### 2025-11-15: Another Decision
**결정 #25:** More content
...
"""
    archiver = Archiver()
    decisions = archiver._parse_decisions(content)

    assert len(decisions) == 2
    assert decisions[0]['number'] == 24
    assert decisions[1]['number'] == 25

def test_filter_by_phase():
    # Test filtering decisions by phase number
    pass

def test_archive_file_creation():
    # Test archive file is created correctly
    pass
```

### Integration Tests

```python
# tests/test_marchive_command.py
def test_marchive_decisions_dry_run():
    result = runner.invoke(app, ["archive", "decisions", "--phase", "5", "--dry-run"])
    assert result.exit_code == 0
    assert "Would archive" in result.stdout

def test_marchive_decisions():
    # Test actual archiving
    pass

def test_file_size_warning():
    # Test warnings appear when files exceed threshold
    pass
```

### Manual Testing Checklist

- [ ] `marchive decisions --phase 5` - Archive works
- [ ] `marchive current --phase 5` - Archive works
- [ ] `marchive plans` - PLAN files moved
- [ ] `marchive --dry-run` - Preview works
- [ ] decisions.md updated with archive link
- [ ] decisions-index.md updated
- [ ] File size warning appears (m command)
- [ ] File size warning appears (mstatus command)
- [ ] Warning threshold configurable
- [ ] Warnings can be disabled

---

## Risk Mitigation

### Risk 1: 잘못된 Phase 번호 입력

**Problem**: 사용자가 잘못된 phase 번호 입력 (예: phase 10 when only 5 exist)

**Mitigation**:
- Phase 번호 검증 (현재 최대 decision number 확인)
- 에러 메시지로 유효 범위 안내
- --dry-run으로 먼저 확인 권장

### Risk 2: Decision 파싱 실패

**Problem**: decisions.md 형식이 예상과 다를 수 있음

**Mitigation**:
- 유연한 regex 패턴
- 파싱 실패 시 명확한 에러 메시지
- 백업 파일 (.bak) 항상 생성

### Risk 3: 파일 손상

**Problem**: 아카이브 중 오류 발생 시 파일 손실

**Mitigation**:
- 원자적 작업 (임시 파일 사용)
- 백업 파일 생성 후 작업
- 트랜잭션 방식 (성공 시에만 원본 수정)

### Risk 4: 경고 피로

**Problem**: 경고가 너무 자주 나와 무시하게 됨

**Mitigation**:
- 적절한 threshold 설정 (500줄)
- config로 비활성화 가능
- 동일 경고 중복 방지 (같은 세션 내)

---

## Success Criteria

### Functional Requirements

- [ ] marchive decisions 동작
- [ ] marchive current 동작
- [ ] marchive plans 동작
- [ ] --dry-run 동작
- [ ] 파일 크기 경고 표시
- [ ] Config로 threshold 설정
- [ ] 백업 파일 생성

### Quality Requirements

- [ ] 데이터 손실 없음 (백업으로 복구 가능)
- [ ] 명확한 에러 메시지
- [ ] 사용자 친화적 출력
- [ ] 빠른 실행 (< 1초)

### Documentation Requirements

- [ ] README.md 업데이트
- [ ] config.yaml 주석 추가
- [ ] archive/README.md 정책 업데이트

---

## Timeline Estimate

| Phase | Tasks | Time Estimate |
|-------|-------|---------------|
| 1. Core Archiver | Archiver class, decision parsing | 2-3 hours |
| 2. CLI Integration | marchive command | 1-2 hours |
| 3. File Size Warnings | Warning system, integration | 1 hour |
| 4. Testing & Docs | Tests, documentation | 1 hour |
| **Total** | | **5-7 hours** |

---

## Future Enhancements (Out of Scope)

- **Auto-archive on phase change**: Phase 전환 감지 시 자동 제안
- **Git integration**: 아카이브 시 자동 커밋
- **Rollback command**: 아카이브 취소 (marchive undo)
- **Archive search**: 아카이브된 항목 검색 (ms --archived)
- **Archive compression**: 오래된 아카이브 압축

---

## Appendix: Example Usage

### Scenario 1: Phase 6 시작 시

```bash
# Phase 6 작업 시작 전
marchive decisions --phase 5 --dry-run
# → Preview: Would archive 23 decisions (#1-#23)

marchive decisions --phase 5
# → ✅ Archived 23 decisions to archive/decisions-phase1-5.md
# → ✅ Updated decisions.md (110 → 30 lines)

marchive current --phase 5
# → ✅ Archived to archive/current-phase5.md
# → ✅ Reset current.md with template
```

### Scenario 2: 작업 완료 후

```bash
# PLAN 문서 2개 완료
ls *.md
# → PLAN-feature-x.md
# → PLAN-feature-y.md

marchive plans
# → ✅ Moved PLAN-feature-x.md → archive/plans/
# → ✅ Moved PLAN-feature-y.md → archive/plans/
```

### Scenario 3: 경고 발생 시

```bash
# decisions.md가 600줄로 증가
m "New entry"
# → OK Recorded at ...
# →
# → ⚠️  decisions.md exceeds 500 lines (current: 610)
# → 💡 Consider: marchive decisions --phase 6
```

---

**Plan Status**: ✅ Ready for Review

**Estimated Effort**: 5-7 hours

**Risk Level**: Low (백업 + dry-run으로 안전성 확보)

**Dependencies**: None

---

*Plan prepared by: Claude Code*
*Date: 2025-11-14*
*Review: Pending user approval*
