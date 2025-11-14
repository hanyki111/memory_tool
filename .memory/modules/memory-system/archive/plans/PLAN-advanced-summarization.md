# Advanced Summarization Implementation Plan

## Overview

**Goal**: 고도화된 자동 요약 시스템 구현 - 맥락 기반, 주제별 분류, 다국어 지원

**Target**: Phase 5 #4 - 자동 요약 고도화

**Branch**: `feature/advanced-summarization`

**Date**: 2025-11-14

---

## Current State Analysis

### Existing Implementation

**LLM Integration:**
- ✅ Dual provider support (Anthropic + Ollama)
- ✅ Factory pattern (LLMClient)
- ✅ Config-based provider selection

**Summarizers:**
- ✅ TimelineSummarizer: today/week/date/range
- ✅ ModuleSummarizer: module documentation
- ✅ ConversationSummarizer: Claude Code sessions

**Prompts:**
- ✅ 3 prompt templates (Timeline, Module, Conversation)
- ❌ Hard-coded in English
- ❌ No context injection
- ❌ Generic topic classification

**Configuration:**
- ✅ llm.provider, llm.ollama_model, llm.anthropic_model
- ❌ No output language setting
- ❌ No context-aware options

### Limitations

1. **Language Lock**: Results always in English regardless of user preference
2. **Context Blindness**: No awareness of project history or previous summaries
3. **Generic Topics**: "Theme 1", "Theme 2" instead of project-specific categories
4. **Static Prompts**: Cannot adapt to different projects or contexts

---

## Requirements

### 1. 출력 언어 설정 (Output Language)

**User Stories:**
- As a user, I want summaries in Korean (my native language)
- As a user, I want to override language per command (--lang flag)
- As a user, I want auto-detection based on timeline content

**Acceptance Criteria:**
- [ ] config.yaml에 `llm.output_language` 설정 (ko/en/auto)
- [ ] CLI에 `--lang` 플래그 추가
- [ ] 프롬프트가 선택된 언어로 결과 요청
- [ ] auto 모드: Timeline 내용의 언어 자동 감지

### 2. 맥락 기반 요약 (Context-Aware)

**User Stories:**
- As a user, I want summaries that understand project context
- As a user, I want references to previous decisions
- As a user, I want continuity between summaries

**Acceptance Criteria:**
- [ ] .claude/memory-context.md 내용을 프롬프트에 주입
- [ ] decisions.md의 최근 결정 참조
- [ ] current.md의 현재 상태 참조
- [ ] 이전 요약 파일 참조 (있다면)

### 3. 주제별 분류 개선 (Enhanced Categorization)

**User Stories:**
- As a user, I want project-specific topic categories
- As a user, I want hierarchical topic organization
- As a user, I want consistent categories across summaries

**Acceptance Criteria:**
- [ ] 프로젝트별 카테고리 정의 (Phase, Feature, Bug, Refactor, etc.)
- [ ] config.yaml에 custom categories 지원
- [ ] 계층적 분류 (Parent topic → Sub topics)
- [ ] 자동 카테고리 제안 (LLM based)

### 4. 프롬프트 시스템 개선 (Dynamic Prompts)

**User Stories:**
- As a developer, I want maintainable prompt templates
- As a developer, I want language-specific prompts
- As a developer, I want context injection without prompt bloat

**Acceptance Criteria:**
- [ ] PromptBuilder 클래스 구현
- [ ] 언어별 base prompt (ko.yaml, en.yaml)
- [ ] Context injection system
- [ ] Template variable substitution

---

## Design Decisions

### Decision 1: 언어 우선순위

**Options:**
- A) CLI flag > config.yaml > auto-detect
- B) config.yaml only
- C) CLI flag only

**Choice: A**
- Most flexible for users
- Allows both default preference and per-command override
- Auto-detect as fallback for new users

**Implementation:**
```python
def get_output_language(cli_lang: Optional[str], content: str) -> str:
    # 1. CLI flag (highest priority)
    if cli_lang:
        return cli_lang

    # 2. Config setting
    config_lang = config.get("llm.output_language", "auto")
    if config_lang != "auto":
        return config_lang

    # 3. Auto-detect from content
    return detect_language(content)
```

### Decision 2: Context Injection Strategy

**Options:**
- A) Always inject all context (memory-context.md, decisions.md, current.md)
- B) Smart selection based on summary scope
- C) User-configurable context sources

**Choice: B (Smart selection)**
- Avoids prompt bloat for simple summaries
- Reduces token cost
- Improves response quality by focusing on relevant context

**Rules:**
- Today summary: Recent context only (last 3 days)
- Week summary: Full memory-context.md + recent decisions
- Range summary: Decisions from that period + module state

### Decision 3: Prompt Architecture

**Options:**
- A) Hard-coded strings with f-string formatting
- B) Jinja2 templates
- C) YAML-based prompt library

**Choice: C (YAML-based)**
- Easy for non-developers to customize
- Language-specific prompts in separate files
- Version control friendly

**Structure:**
```yaml
# prompts/timeline/ko.yaml
base: |
  당신은 타임라인 요약 전문가입니다.

  주어진 타임라인 항목들을 분석하여 핵심 정보를 보존하는 간결한 요약을 작성하세요.

guidelines:
  - key_themes: 관련 항목들을 주제별로 그룹화
  - decisions: 중요한 결정사항과 근거를 명확히 표시
  - chronology: 작업의 진행과 사고의 흐름을 유지

output_format: |
  ## 요약

  [전체 기간 개요 - 2-3문장]

  ## 주요 주제
  ...
```

### Decision 4: Category System

**Options:**
- A) Fixed project-specific categories
- B) LLM-suggested categories
- C) Hybrid (fixed + LLM suggestions)

**Choice: C (Hybrid)**
- Consistency for common categories
- Flexibility for emergent topics
- User can override in config

**Default Categories for memory_tool:**
```yaml
categories:
  development:
    - Phase Implementation
    - Feature Development
    - Bug Fixes
    - Refactoring

  planning:
    - Architecture Decisions
    - Design Discussions
    - Requirements Analysis

  operations:
    - Testing
    - Documentation
    - Deployment

  meta:
    - Tooling Improvements
    - Process Refinement
```

---

## Implementation Plan

### Phase 1: Configuration & Language Support (2-3 hours)

**Files to modify:**
- `.memory/config.yaml` - Add llm.output_language
- `memory_tool/llm/prompts.py` - Add language detection
- `memory_tool/cli.py` - Add --lang flag

**Tasks:**
1. ✅ Add config schema:
```yaml
llm:
  output_language: ko  # ko, en, auto
  custom_categories:   # optional
    - Phase Implementation
    - Feature Development
```

2. ✅ Language detection function:
```python
def detect_language(text: str) -> str:
    """Detect predominant language in text."""
    # Simple heuristic: count Korean vs English chars
    korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7a3')
    english_chars = sum(1 for c in text if c.isascii() and c.isalpha())

    return "ko" if korean_chars > english_chars * 2 else "en"
```

3. ✅ Update CLI:
```python
def summary(
    scope: str,
    output: str = None,
    module_name: str = None,
    lang: str = typer.Option(None, "--lang", help="Output language (ko/en/auto)"),
):
    # Determine output language
    output_lang = get_output_language(lang, content)

    # Pass to summarizer
    summary = summarizer.summarize_today(output_language=output_lang)
```

**Tests:**
- [ ] Config loading with output_language
- [ ] Language detection accuracy (Korean vs English)
- [ ] CLI --lang flag override

### Phase 2: Context Injection System (3-4 hours)

**Files to create:**
- `memory_tool/summary/context.py` - Context gathering
- `memory_tool/llm/prompt_builder.py` - Dynamic prompt building

**Tasks:**
1. ✅ Context gatherer:
```python
class ContextGatherer:
    """Gather relevant context for summarization."""

    def gather_for_timeline(
        self,
        scope: Literal["today", "week", "range"],
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        Gather context for timeline summary.

        Returns:
            {
                "project_context": str,  # from memory-context.md
                "recent_decisions": list[str],
                "module_state": str,
                "previous_summaries": list[str],
            }
        """
        context = {}

        # Project context
        memory_context_path = Path(".claude/memory-context.md")
        if memory_context_path.exists():
            context["project_context"] = memory_context_path.read_text()

        # Recent decisions (from date range)
        decisions_path = Path(".memory/modules/memory-system/decisions.md")
        if decisions_path.exists():
            context["recent_decisions"] = self._extract_decisions_in_range(
                decisions_path, start_date, end_date
            )

        # ... similar for other context sources

        return context
```

2. ✅ Prompt builder:
```python
class PromptBuilder:
    """Build dynamic prompts with context injection."""

    def build_timeline_prompt(
        self,
        language: str,
        context: dict,
        categories: list[str],
    ) -> str:
        """Build timeline summary prompt."""
        # Load base prompt for language
        base = self._load_base_prompt("timeline", language)

        # Inject context
        if context.get("project_context"):
            base += f"\n\n## Project Context\n\n{context['project_context'][:500]}"

        if context.get("recent_decisions"):
            decisions_text = "\n".join(f"- {d}" for d in context["recent_decisions"])
            base += f"\n\n## Recent Decisions\n\n{decisions_text}"

        # Add category guidance
        if categories:
            cats_text = ", ".join(categories)
            base += f"\n\n**Preferred Categories**: {cats_text}"

        return base
```

**Tests:**
- [ ] Context gathering for different scopes
- [ ] Prompt building with/without context
- [ ] Token limit handling (truncate if too long)

### Phase 3: Enhanced Categorization (2-3 hours)

**Files to modify:**
- `memory_tool/llm/prompts.py` - Update prompts with categories
- `memory_tool/summary/timeline_summarizer.py` - Pass categories

**Tasks:**
1. ✅ Update prompts with category system:
```python
# In prompt_builder.py
CATEGORY_INSTRUCTION = {
    "ko": """
## 카테고리 가이드

다음 카테고리를 사용하여 항목을 분류하세요:

**개발:**
- Phase 구현: 계획된 단계의 구현 작업
- 기능 개발: 새로운 기능 추가
- 버그 수정: 오류 수정 및 개선
- 리팩토링: 코드 구조 개선

**계획:**
- 아키텍처 결정: 설계 선택 및 근거
- 디자인 논의: 구현 방향 토론
- 요구사항 분석: 기능 요구사항 정의

**운영:**
- 테스트: 테스트 작성 및 실행
- 문서화: 문서 작성 및 업데이트
- 배포: 릴리스 및 배포 작업

**메타:**
- 도구 개선: 개발 도구 개선
- 프로세스 개선: 작업 방식 개선
""",
    "en": "...",  # English version
}
```

2. ✅ Summarizer integration:
```python
def summarize_today(self, output_language: str = "en") -> str:
    # Gather context
    context_gatherer = ContextGatherer()
    context = context_gatherer.gather_for_timeline("today", today, today)

    # Get categories
    config = Config()
    categories = config.get("llm.custom_categories") or DEFAULT_CATEGORIES

    # Build prompt
    prompt_builder = PromptBuilder()
    system_prompt = prompt_builder.build_timeline_prompt(
        language=output_language,
        context=context,
        categories=categories,
    )

    # Generate summary
    summary = self.llm_client.summarize(
        content=full_content,
        system_prompt=system_prompt,
    )

    return summary
```

**Tests:**
- [ ] Category extraction from summaries
- [ ] Custom categories from config
- [ ] Hierarchical category display

### Phase 4: Testing & Documentation (2 hours)

**Tasks:**
1. ✅ Integration testing:
   - [ ] Korean output with ko setting
   - [ ] English output with en setting
   - [ ] Auto-detect with mixed content
   - [ ] Context injection for week summary
   - [ ] Custom categories from config

2. ✅ Update documentation:
   - [ ] README.md: New flags and config options
   - [ ] config.yaml: Comment all new options
   - [ ] CLAUDE.md: Update current status

3. ✅ Dogfooding:
   - [ ] Use msummary with new features
   - [ ] Record timeline entries with `m` command
   - [ ] Generate week summary in Korean

---

## File Structure

```
memory_tool/
├── llm/
│   ├── client.py              # (existing)
│   ├── prompts.py             # (modify) - Add language detection
│   ├── prompt_builder.py      # (new) - Dynamic prompt building
│   └── prompts/               # (new) - YAML prompt library
│       ├── timeline/
│       │   ├── ko.yaml
│       │   └── en.yaml
│       ├── module/
│       │   ├── ko.yaml
│       │   └── en.yaml
│       └── conversation/
│           ├── ko.yaml
│           └── en.yaml
│
├── summary/
│   ├── timeline_summarizer.py # (modify)
│   ├── module_summarizer.py   # (modify)
│   ├── context.py             # (new) - Context gathering
│   └── categories.py          # (new) - Category definitions
│
└── cli.py                     # (modify) - Add --lang flag

.memory/
└── config.yaml                # (modify) - Add output_language, custom_categories
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_language_detection.py
def test_detect_korean():
    text = "타임라인 요약 테스트"
    assert detect_language(text) == "ko"

def test_detect_english():
    text = "Timeline summary test"
    assert detect_language(text) == "en"

def test_mixed_content():
    text = "Timeline 요약: 50% Korean, 50% English"
    # Should detect based on character count
```

```python
# tests/test_context_gathering.py
def test_gather_context_for_today():
    gatherer = ContextGatherer()
    context = gatherer.gather_for_timeline("today", date.today(), date.today())

    assert "project_context" in context
    assert "recent_decisions" in context

def test_context_truncation():
    # Test that context doesn't exceed token limits
    gatherer = ContextGatherer()
    context = gatherer.gather_for_timeline("week", start, end)

    total_length = sum(len(str(v)) for v in context.values())
    assert total_length < MAX_CONTEXT_LENGTH
```

### Integration Tests

```python
# tests/test_summary_integration.py
def test_korean_summary_output():
    summarizer = TimelineSummarizer()
    summary = summarizer.summarize_today(output_language="ko")

    # Check Korean characters present
    korean_chars = sum(1 for c in summary if '\uac00' <= c <= '\ud7a3')
    assert korean_chars > 100

def test_context_injection():
    # Create test timeline with context
    # Verify context appears in summary
    pass
```

### Manual Testing Checklist

- [ ] `msummary today --lang ko` → Korean output
- [ ] `msummary today --lang en` → English output
- [ ] `msummary today` (with config ko) → Korean output
- [ ] `msummary week` → Context from memory-context.md included
- [ ] `msummary 2025-11-14` → Decisions from that day referenced
- [ ] Custom categories in config → Reflected in summary
- [ ] Auto-detect with Korean timeline → Korean output
- [ ] Auto-detect with English timeline → English output

---

## Risk Mitigation

### Risk 1: Context Bloat

**Problem**: Injecting too much context → exceeds token limits

**Mitigation**:
- Implement smart truncation (keep most recent, most relevant)
- Add config option: `llm.max_context_tokens` (default: 2000)
- Prioritize: recent > decisions > module state

### Risk 2: Language Detection Errors

**Problem**: Mixed content causes wrong language detection

**Mitigation**:
- Use conservative threshold (2:1 ratio)
- Fall back to config language if uncertain
- Allow manual override with --lang flag

### Risk 3: Category Inconsistency

**Problem**: LLM suggests different categories each time

**Mitigation**:
- Provide strong category guidance in prompt
- Use few-shot examples in prompt
- Implement category normalization post-processing

### Risk 4: Performance Degradation

**Problem**: Context gathering and prompt building adds latency

**Mitigation**:
- Cache memory-context.md reads
- Lazy load context only when needed
- Profile and optimize hot paths

---

## Success Criteria

### Functional Requirements

- [x] Config option `llm.output_language` works
- [ ] CLI flag `--lang` overrides config
- [ ] Korean output matches expected format
- [ ] English output matches expected format
- [ ] Context from memory-context.md appears in summaries
- [ ] Recent decisions referenced in summaries
- [ ] Custom categories reflected in output
- [ ] Auto-detect selects correct language

### Performance Requirements

- [ ] Summary generation < 5 seconds (Ollama local)
- [ ] Summary generation < 10 seconds (Anthropic API)
- [ ] Context gathering < 100ms
- [ ] Language detection < 10ms

### Quality Requirements

- [ ] Summaries preserve key information (80%+ retention)
- [ ] Categories match project terminology
- [ ] Context references are relevant
- [ ] No hallucinations (factual accuracy 100%)

---

## Future Enhancements (Out of Scope)

- **Multi-round refinement**: Let user iterate on summary with feedback
- **Template customization**: User-defined output formats
- **Cross-project summaries**: Summarize across multiple .memory/ roots
- **Incremental summaries**: Build on previous summaries instead of full re-summarization
- **Visual summaries**: Generate diagrams, charts from timeline data

---

## Timeline Estimate

| Phase | Tasks | Time Estimate |
|-------|-------|---------------|
| 1. Config & Language | Config schema, detection, CLI flag | 2-3 hours |
| 2. Context Injection | Context gatherer, prompt builder | 3-4 hours |
| 3. Categorization | Category system, integration | 2-3 hours |
| 4. Testing & Docs | Tests, documentation, dogfooding | 2 hours |
| **Total** | | **9-12 hours** |

---

## Appendix: Example Outputs

### Before (Current)

```markdown
## Summary

Timeline entries show development progress on memory_tool project.

## Key Themes

### Theme 1
- Implemented SQLite indexing
- Added search functionality

### Theme 2
- Fixed bugs in timeline
- Updated documentation

## Important Decisions

1. **SQLite FTS5**: Chose FTS5 for full-text search performance
2. **Backward compatibility**: Maintained fallback to file-based search

## Milestones

- SQLite indexing complete
- 172 entries indexed
```

### After (Enhanced - Korean)

```markdown
## 요약

2025-11-14 타임라인: SQLite 인덱싱 기능 완료 및 main 브랜치 머지. 검색 성능 10-100배 개선 달성.

## 주요 활동

### Phase 5 구현
- **SQLite FTS5 인덱싱**: 전문 검색 시스템 구현 (memory_tool/db/indexer.py, search.py)
- **CLI 통합**: mindex 명령어, ms --no-index 플래그 추가
- **자동 인덱싱**: m 명령어 실행 시 타임라인 자동 인덱싱

### 버그 수정
- Database schema 생성 로직 수정 (3건)
- index_meta 테이블 체크 누락 해결
- Schema validation 추가

### 문서화
- PLAN-sqlite-indexing.md 작성
- CLAUDE.md dogfooding 원칙 명시
- archive/ 전략으로 decisions.md 86% 축소

## 중요 결정사항

**Decision #26 (2025-11-14)**: SQLite 인덱싱 구현
- **선택**: FTS5 기반 전문 검색 + 파일 기반 폴백
- **근거**: 대용량 타임라인 검색 성능 개선 필요
- **Trade-off**: 인덱스 관리 복잡도 vs 검색 속도 10-100배 향상

*관련 컨텍스트*: Phase 5 #2 작업 (decisions.md #26)

## 마일스톤

- ✅ SQLite 인덱싱 완료 (172 entries, 0.17 MB)
- ✅ Feature branch → main 머지 (fe2840a, dae1ca2)
- ✅ 검색 성능 10-100배 개선 검증

## 다음 단계

- Phase 5 #3: 검색 개선 (하이브리드 검색, 랭킹)
- Phase 5 #4: 자동 요약 고도화 (맥락 기반, 주제별 분류)
```

### After (Enhanced - English with Context)

```markdown
## Summary

November 14, 2025 timeline: Completed SQLite indexing feature with 10-100x search performance improvement. Successfully merged to main branch.

## Key Activities

### Phase 5 Implementation
- **SQLite FTS5 Indexing**: Implemented full-text search system (memory_tool/db/indexer.py, search.py)
- **CLI Integration**: Added mindex command and ms --no-index flag
- **Auto-indexing**: Timeline entries automatically indexed on `m` command

### Bug Fixes
- Fixed database schema creation logic (3 issues)
- Resolved missing index_meta table check
- Added schema validation

### Documentation
- Wrote PLAN-sqlite-indexing.md
- Updated CLAUDE.md with dogfooding principles
- Reduced decisions.md by 86% using archive/ strategy

## Important Decisions

**Decision #26 (2025-11-14)**: SQLite Indexing Implementation
- **Choice**: FTS5-based full-text search + file-based fallback
- **Rationale**: Need search performance improvement for growing timeline
- **Trade-off**: Index management complexity vs 10-100x faster search

*Related context*: Phase 5 #2 task (decisions.md #26)

## Milestones

- ✅ SQLite indexing complete (172 entries, 0.17 MB)
- ✅ Feature branch merged to main (fe2840a, dae1ca2)
- ✅ Verified 10-100x search performance improvement

## Next Steps

- Phase 5 #3: Enhanced search (hybrid search, ranking algorithms)
- Phase 5 #4: Advanced summarization (context-aware, topic classification)
```

---

**Plan Status**: ✅ Ready for Review

**Estimated Effort**: 9-12 hours

**Risk Level**: Medium (language detection, context injection complexity)

**Dependencies**: None (builds on existing LLM integration)

---

*Plan prepared by: Claude Code*
*Date: 2025-11-14*
*Review: Pending user approval*
