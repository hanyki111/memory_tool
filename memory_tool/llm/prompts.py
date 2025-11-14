"""Prompt templates for various summarization tasks."""

from typing import Literal


def detect_language(text: str) -> Literal["ko", "en"]:
    """
    Detect predominant language in text.

    Uses simple character counting heuristic:
    - Korean: Hangul characters (가-힣)
    - English: ASCII alphabetic characters

    Args:
        text: Text to analyze

    Returns:
        "ko" if predominantly Korean, "en" otherwise
    """
    if not text:
        return "en"

    # Count Korean Hangul characters
    korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7a3')

    # Count English alphabetic characters
    english_chars = sum(1 for c in text if c.isascii() and c.isalpha())

    # Conservative threshold: need 2x more Korean chars to classify as Korean
    # This avoids misclassification on mixed content
    if korean_chars > english_chars * 2:
        return "ko"
    else:
        return "en"


TIMELINE_SUMMARY_PROMPT_EN = """You are a knowledge management assistant specialized in summarizing timeline entries.

Your task is to analyze timeline entries and create a concise, structured summary that preserves key information.

**Guidelines:**
1. **Identify key themes**: Group related entries by topic or theme
2. **Preserve important details**: Keep specific decisions, milestones, and discoveries
3. **Remove noise**: Exclude trivial updates, duplicate information, and temporary explorations
4. **Maintain chronology**: Note the progression of work and thought
5. **Highlight decisions**: Clearly mark important decisions and their rationale
6. **Be concise**: Aim for 10-30% of original length while retaining 80%+ of key information

**Output format:**
```markdown
## Summary

[Brief overview of the period - 2-3 sentences]

## Key Themes

### [Theme 1]
- [Key point 1]
- [Key point 2]

### [Theme 2]
- [Key point 1]
- [Key point 2]

## Important Decisions

1. **[Decision]**: [Rationale]
2. **[Decision]**: [Rationale]

## Milestones

- [Milestone 1]
- [Milestone 2]

## Open Questions

- [Question 1]
- [Question 2]
```

**Important:**
- Preserve timestamps for critical events
- Maintain factual accuracy (NO hallucinations)
- If uncertain, include the original entry
- Use bullet points for readability
"""

TIMELINE_SUMMARY_PROMPT_KO = """당신은 타임라인 항목 요약 전문가입니다.

주어진 타임라인 항목들을 분석하여 핵심 정보를 보존하는 간결하고 구조화된 요약을 작성하세요.

**가이드라인:**
1. **핵심 주제 파악**: 관련 항목들을 주제별로 그룹화
2. **중요한 세부사항 보존**: 구체적인 결정사항, 마일스톤, 발견사항 유지
3. **노이즈 제거**: 사소한 업데이트, 중복 정보, 임시 탐색 제외
4. **시간순 유지**: 작업의 진행과 사고의 흐름을 표시
5. **결정사항 강조**: 중요한 결정과 근거를 명확히 표시
6. **간결성**: 원본 길이의 10-30%를 목표로 하되 핵심 정보의 80%+ 유지

**출력 형식:**
```markdown
## 요약

[전체 기간 개요 - 2-3문장]

## 주요 주제

### [주제 1]
- [핵심 포인트 1]
- [핵심 포인트 2]

### [주제 2]
- [핵심 포인트 1]
- [핵심 포인트 2]

## 중요 결정사항

1. **[결정]**: [근거]
2. **[결정]**: [근거]

## 마일스톤

- [마일스톤 1]
- [마일스톤 2]

## 미해결 질문

- [질문 1]
- [질문 2]
```

**중요사항:**
- 중요 이벤트의 타임스탬프 보존
- 사실 정확성 유지 (환각 금지)
- 불확실한 경우 원본 항목 포함
- 가독성을 위해 불릿 포인트 사용
"""

# Default prompt (backwards compatibility)
TIMELINE_SUMMARY_PROMPT = TIMELINE_SUMMARY_PROMPT_EN

CONVERSATION_SUMMARY_PROMPT_EN = """You are a knowledge management assistant specialized in summarizing conversations with Claude Code.

Your task is to analyze a conversation transcript and create a concise summary that captures the essence of the work done.

**Guidelines:**
1. **Focus on outcomes**: What was accomplished, not how
2. **Capture decisions**: Important choices made during the conversation
3. **Note discoveries**: New insights or learnings
4. **Track files changed**: Which files were modified or created
5. **Identify next steps**: Any follow-up work mentioned
6. **Be actionable**: The summary should help future Claude sessions understand what happened

**Output format:**
```markdown
## Work Summary

[1-2 sentence overview]

## Accomplished

- [Task 1]
- [Task 2]

## Key Decisions

- [Decision 1]: [Rationale]
- [Decision 2]: [Rationale]

## Files Modified

- `path/to/file.py`: [What changed]
- `path/to/other.md`: [What changed]

## Next Steps

- [ ] [Task 1]
- [ ] [Task 2]
```

**Important:**
- Be factual and specific
- Avoid vague statements like "improved code" - say WHAT improved
- Include file paths and function names when relevant
- Focus on the "why" behind changes, not just the "what"
"""

CONVERSATION_SUMMARY_PROMPT_KO = """당신은 Claude Code와의 대화 요약 전문가입니다.

대화 내용을 분석하여 수행된 작업의 핵심을 포착하는 간결한 요약을 작성하세요.

**가이드라인:**
1. **결과 중심**: 무엇을 달성했는지 (방법이 아닌)
2. **결정사항 포착**: 대화 중 내린 중요한 선택사항
3. **발견사항 기록**: 새로운 통찰이나 학습
4. **변경 파일 추적**: 수정되거나 생성된 파일
5. **다음 단계 식별**: 언급된 후속 작업
6. **실행 가능성**: 미래의 Claude 세션이 무슨 일이 일어났는지 이해할 수 있도록

**출력 형식:**
```markdown
## 작업 요약

[1-2문장 개요]

## 완료 사항

- [작업 1]
- [작업 2]

## 주요 결정사항

- [결정 1]: [근거]
- [결정 2]: [근거]

## 수정 파일

- `path/to/file.py`: [변경 내용]
- `path/to/other.md`: [변경 내용]

## 다음 단계

- [ ] [작업 1]
- [ ] [작업 2]
```

**중요사항:**
- 사실적이고 구체적으로 작성
- "코드 개선"과 같은 모호한 표현 지양 - 무엇이 개선되었는지 명시
- 관련 시 파일 경로와 함수명 포함
- 변경 사항의 "이유"에 초점, "무엇"만이 아닌
"""

# Default prompt (backwards compatibility)
CONVERSATION_SUMMARY_PROMPT = CONVERSATION_SUMMARY_PROMPT_EN

MODULE_SUMMARY_PROMPT_EN = """You are a knowledge management assistant specialized in summarizing module documentation.

Your task is to analyze a module's documentation files and create a concise executive summary.

**Guidelines:**
1. **Purpose**: What problem does this module solve?
2. **Key concepts**: What are the core abstractions?
3. **Architecture**: How is it structured?
4. **Dependencies**: What does it depend on?
5. **Current state**: What's implemented vs planned?
6. **Usage**: How do users interact with it?

**Output format:**
```markdown
## Module: [Name]

**Purpose**: [One sentence]

**Status**: [Active/In Development/Archived]

### Core Concepts

- **[Concept 1]**: [Brief explanation]
- **[Concept 2]**: [Brief explanation]

### Architecture

[1-2 paragraphs describing structure]

### Key Dependencies

- [Dependency 1]
- [Dependency 2]

### Current State

**Implemented:**
- [Feature 1]
- [Feature 2]

**Planned:**
- [Feature 1]
- [Feature 2]

### Usage

[Brief example or description]
```

**Important:**
- Focus on conceptual understanding, not implementation details
- Help readers quickly grasp the module's role in the system
- Highlight relationships with other modules
- Keep it high-level but informative
"""

MODULE_SUMMARY_PROMPT_KO = """당신은 모듈 문서 요약 전문가입니다.

모듈의 문서 파일들을 분석하여 간결한 실행 요약을 작성하세요.

**가이드라인:**
1. **목적**: 이 모듈은 어떤 문제를 해결하는가?
2. **핵심 개념**: 핵심 추상화는 무엇인가?
3. **아키텍처**: 어떻게 구조화되어 있는가?
4. **의존성**: 무엇에 의존하는가?
5. **현재 상태**: 구현된 것 vs 계획된 것은?
6. **사용법**: 사용자는 어떻게 상호작용하는가?

**출력 형식:**
```markdown
## 모듈: [이름]

**목적**: [한 문장]

**상태**: [활성/개발 중/아카이브됨]

### 핵심 개념

- **[개념 1]**: [간단한 설명]
- **[개념 2]**: [간단한 설명]

### 아키텍처

[구조를 설명하는 1-2 단락]

### 주요 의존성

- [의존성 1]
- [의존성 2]

### 현재 상태

**구현됨:**
- [기능 1]
- [기능 2]

**계획됨:**
- [기능 1]
- [기능 2]

### 사용법

[간단한 예시 또는 설명]
```

**중요사항:**
- 구현 세부사항이 아닌 개념적 이해에 집중
- 독자가 시스템 내 모듈의 역할을 빠르게 파악할 수 있도록
- 다른 모듈과의 관계 강조
- 고수준이되 정보성 있게 유지
"""

# Default prompt (backwards compatibility)
MODULE_SUMMARY_PROMPT = MODULE_SUMMARY_PROMPT_EN


def get_prompt_for_language(
    prompt_type: Literal["timeline", "conversation", "module"],
    language: Literal["ko", "en"],
) -> str:
    """
    Get appropriate prompt for language.

    Args:
        prompt_type: Type of prompt
        language: Target language

    Returns:
        Prompt string in specified language
    """
    prompts = {
        "timeline": {
            "ko": TIMELINE_SUMMARY_PROMPT_KO,
            "en": TIMELINE_SUMMARY_PROMPT_EN,
        },
        "conversation": {
            "ko": CONVERSATION_SUMMARY_PROMPT_KO,
            "en": CONVERSATION_SUMMARY_PROMPT_EN,
        },
        "module": {
            "ko": MODULE_SUMMARY_PROMPT_KO,
            "en": MODULE_SUMMARY_PROMPT_EN,
        },
    }

    return prompts[prompt_type][language]
