"""Dynamic prompt building with context injection."""

from typing import Dict, List, Literal, Optional
from .prompts import get_prompt_for_language


class PromptBuilder:
    """Build dynamic prompts with context injection."""

    def __init__(self, max_context_tokens: int = 2000):
        """
        Initialize prompt builder.

        Args:
            max_context_tokens: Maximum tokens for injected context
        """
        self.max_context_tokens = max_context_tokens

    def build_timeline_prompt(
        self,
        language: Literal["ko", "en"],
        context: Optional[Dict[str, any]] = None,
    ) -> str:
        """
        Build timeline summary prompt with context.

        Args:
            language: Output language
            context: Context dictionary from ContextGatherer

        Returns:
            Complete system prompt
        """
        # Get base prompt
        base_prompt = get_prompt_for_language("timeline", language)

        # If no context, return base prompt
        if not context:
            return base_prompt

        # Build context sections
        context_sections = []

        # Project context
        if context.get("project_context"):
            project_ctx = context["project_context"]
            if language == "ko":
                context_sections.append(
                    f"\n\n## 프로젝트 컨텍스트\n\n{project_ctx}"
                )
            else:
                context_sections.append(
                    f"\n\n## Project Context\n\n{project_ctx}"
                )

        # Recent decisions
        if context.get("recent_decisions"):
            decisions = context["recent_decisions"]
            if decisions:
                decisions_text = "\n".join(f"- {d}" for d in decisions)
                if language == "ko":
                    context_sections.append(
                        f"\n\n## 최근 결정사항\n\n{decisions_text}"
                    )
                else:
                    context_sections.append(
                        f"\n\n## Recent Decisions\n\n{decisions_text}"
                    )

        # Module state
        if context.get("module_state"):
            state = context["module_state"]
            if language == "ko":
                context_sections.append(
                    f"\n\n## 현재 프로젝트 상태\n\n{state}"
                )
            else:
                context_sections.append(
                    f"\n\n## Current Project State\n\n{state}"
                )

        # Custom categories
        if context.get("categories"):
            categories = context["categories"]
            cats_text = ", ".join(categories)

            if language == "ko":
                category_guide = f"""

## 카테고리 가이드

다음 프로젝트 특화 카테고리를 우선적으로 사용하세요:

{cats_text}

항목을 분류할 때 이 카테고리들을 활용하여 일관성 있는 구조를 유지하세요.
"""
            else:
                category_guide = f"""

## Category Guide

Use these project-specific categories preferentially:

{cats_text}

Use these categories when classifying entries to maintain consistent structure.
"""
            context_sections.append(category_guide)

        # Combine all sections
        full_prompt = base_prompt + "".join(context_sections)

        # Truncate if too long (rough estimate: 1 token ≈ 4 chars)
        estimated_tokens = len(full_prompt) // 4
        if estimated_tokens > self.max_context_tokens:
            # Truncate context sections proportionally
            max_chars = self.max_context_tokens * 4
            base_chars = len(base_prompt)
            context_chars = max_chars - base_chars

            # Truncate context sections
            if context_sections:
                context_text = "".join(context_sections)
                if len(context_text) > context_chars:
                    context_text = context_text[:context_chars] + "\n\n[... context truncated to fit token limit ...]"
                    full_prompt = base_prompt + context_text

        return full_prompt

    def build_module_prompt(
        self,
        language: Literal["ko", "en"],
        context: Optional[Dict[str, any]] = None,
    ) -> str:
        """
        Build module summary prompt with context.

        Args:
            language: Output language
            context: Context dictionary from ContextGatherer

        Returns:
            Complete system prompt
        """
        # Get base prompt
        base_prompt = get_prompt_for_language("module", language)

        # If no context, return base prompt
        if not context:
            return base_prompt

        # Build context sections
        context_sections = []

        # Project context
        if context.get("project_context"):
            project_ctx = context["project_context"]
            if language == "ko":
                context_sections.append(
                    f"\n\n## 프로젝트 컨텍스트\n\n{project_ctx}"
                )
            else:
                context_sections.append(
                    f"\n\n## Project Context\n\n{project_ctx}"
                )

        # Related modules
        if context.get("related_modules"):
            modules = context["related_modules"]
            if modules:
                modules_text = ", ".join(modules)
                if language == "ko":
                    context_sections.append(
                        f"\n\n## 관련 모듈\n\n{modules_text}"
                    )
                else:
                    context_sections.append(
                        f"\n\n## Related Modules\n\n{modules_text}"
                    )

        # Recent decisions
        if context.get("recent_decisions"):
            decisions = context["recent_decisions"]
            if decisions:
                decisions_text = "\n".join(f"- {d}" for d in decisions)
                if language == "ko":
                    context_sections.append(
                        f"\n\n## 최근 결정사항\n\n{decisions_text}"
                    )
                else:
                    context_sections.append(
                        f"\n\n## Recent Decisions\n\n{decisions_text}"
                    )

        # Combine all sections
        full_prompt = base_prompt + "".join(context_sections)

        # Truncate if too long
        estimated_tokens = len(full_prompt) // 4
        if estimated_tokens > self.max_context_tokens:
            max_chars = self.max_context_tokens * 4
            base_chars = len(base_prompt)
            context_chars = max_chars - base_chars

            if context_sections:
                context_text = "".join(context_sections)
                if len(context_text) > context_chars:
                    context_text = context_text[:context_chars] + "\n\n[... context truncated ...]"
                    full_prompt = base_prompt + context_text

        return full_prompt

    def build_conversation_prompt(
        self,
        language: Literal["ko", "en"],
    ) -> str:
        """
        Build conversation summary prompt.

        Args:
            language: Output language

        Returns:
            System prompt
        """
        # Conversation summaries don't need extra context
        return get_prompt_for_language("conversation", language)
