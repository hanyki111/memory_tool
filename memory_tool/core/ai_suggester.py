"""AI-based connection suggestions and auto-tagging."""

from pathlib import Path
from typing import List, Tuple, Optional, Dict
from ..llm.client import LLMClient


class AIConnectionSuggester:
    """Use LLM to suggest module connections based on content similarity."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize AI suggester.

        Args:
            llm_client: LLM client (optional, creates one if not provided)
        """
        self.llm_client = llm_client or LLMClient()

    def _read_module_content(self, module_path: Path) -> str:
        """Read and combine module content.

        Args:
            module_path: Path to module directory

        Returns:
            Combined content from module files
        """
        content_parts = []

        # Read key files
        for filename in ["module.md", "current.md", "README.md", "interface.md"]:
            file_path = module_path / filename
            if file_path.exists():
                try:
                    text = file_path.read_text(encoding="utf-8")
                    content_parts.append(f"## {filename}\n\n{text}")
                except Exception:
                    pass

        return "\n\n".join(content_parts)

    def suggest_connections(
        self,
        module_path: Path,
        candidate_modules: List[Tuple[str, Path]],
        max_suggestions: int = 5,
    ) -> List[Tuple[str, str, float]]:
        """Suggest connections using LLM-based content analysis.

        Args:
            module_path: Path to the module to analyze
            candidate_modules: List of (module_name, module_path) tuples
            max_suggestions: Maximum number of suggestions

        Returns:
            List of (module_name, reason, confidence) tuples
        """
        # Read target module content
        target_content = self._read_module_content(module_path)

        if not target_content:
            return []

        # Read candidate module contents
        candidates_info = []
        for name, path in candidate_modules[:20]:  # Limit to avoid token limits
            content = self._read_module_content(path)
            if content:
                # Truncate content for efficiency
                content_preview = content[:1000]
                candidates_info.append((name, content_preview))

        if not candidates_info:
            return []

        # Build prompt for LLM
        candidates_text = "\n\n".join([
            f"### Candidate: {name}\n{content}"
            for name, content in candidates_info
        ])

        prompt = f"""Analyze the following module and suggest which other modules it should connect to based on content similarity and relevance.

TARGET MODULE:
{target_content[:2000]}

CANDIDATE MODULES:
{candidates_text}

Task:
1. Identify the top {max_suggestions} most relevant candidate modules for the target module
2. For each suggestion, provide:
   - Module name
   - Reason for connection (one sentence)
   - Confidence score (0.0-1.0)

Format your response as:
MODULE: [name]
REASON: [reason]
CONFIDENCE: [score]

---

Focus on:
- Topical relevance
- Complementary information
- Shared concepts or themes
- Potential dependencies or relationships

Only suggest connections that add real value. If no strong connections exist, suggest fewer modules.
"""

        try:
            # Get LLM response
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=1000,
            )

            # Parse response
            suggestions = self._parse_suggestions(response)

            return suggestions[:max_suggestions]

        except Exception as e:
            # Fall back to empty list on error
            return []

    def _parse_suggestions(self, llm_response: str) -> List[Tuple[str, str, float]]:
        """Parse LLM response into structured suggestions.

        Args:
            llm_response: Raw LLM response text

        Returns:
            List of (module_name, reason, confidence) tuples
        """
        suggestions = []

        # Split by --- or blank lines
        blocks = llm_response.split('---')

        for block in blocks:
            lines = block.strip().split('\n')

            module_name = None
            reason = None
            confidence = 0.5

            for line in lines:
                line = line.strip()

                if line.startswith('MODULE:'):
                    module_name = line.replace('MODULE:', '').strip()
                elif line.startswith('REASON:'):
                    reason = line.replace('REASON:', '').strip()
                elif line.startswith('CONFIDENCE:'):
                    try:
                        conf_str = line.replace('CONFIDENCE:', '').strip()
                        confidence = float(conf_str)
                    except ValueError:
                        confidence = 0.5

            if module_name and reason:
                suggestions.append((module_name, reason, confidence))

        # Sort by confidence descending
        suggestions.sort(key=lambda x: x[2], reverse=True)

        return suggestions

    def suggest_tags(self, module_path: Path, max_tags: int = 5) -> List[str]:
        """Suggest tags for a module based on its content.

        Args:
            module_path: Path to module directory
            max_tags: Maximum number of tags to suggest

        Returns:
            List of suggested tags
        """
        # Read module content
        content = self._read_module_content(module_path)

        if not content:
            return []

        # Build prompt
        prompt = f"""Analyze the following module content and suggest {max_tags} relevant tags.

MODULE CONTENT:
{content[:3000]}

Task:
Suggest {max_tags} concise tags (1-2 words each) that best categorize this module.

Focus on:
- Main topics or themes
- Technologies mentioned
- Problem domains
- Module purpose

Format: Return only the tags, one per line, without numbering or explanations.
"""

        try:
            # Get LLM response
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=200,
            )

            # Parse tags (one per line)
            tags = []
            for line in response.strip().split('\n'):
                tag = line.strip().strip('-•*').strip()
                if tag and len(tag) > 0:
                    tags.append(tag)

            return tags[:max_tags]

        except Exception as e:
            return []

    def analyze_content_similarity(
        self,
        module1_path: Path,
        module2_path: Path,
    ) -> Tuple[float, str]:
        """Analyze similarity between two modules.

        Args:
            module1_path: Path to first module
            module2_path: Path to second module

        Returns:
            Tuple of (similarity_score, explanation)
        """
        content1 = self._read_module_content(module1_path)
        content2 = self._read_module_content(module2_path)

        if not content1 or not content2:
            return (0.0, "Insufficient content to compare")

        prompt = f"""Compare these two modules and assess their similarity.

MODULE 1:
{content1[:1500]}

MODULE 2:
{content2[:1500]}

Task:
1. Assess the similarity between these modules (0.0 = completely unrelated, 1.0 = highly related)
2. Explain the relationship in one sentence

Format:
SIMILARITY: [score 0.0-1.0]
EXPLANATION: [one sentence explanation]
"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=200,
            )

            # Parse response
            lines = response.strip().split('\n')
            similarity = 0.0
            explanation = "No explanation provided"

            for line in lines:
                if line.startswith('SIMILARITY:'):
                    try:
                        sim_str = line.replace('SIMILARITY:', '').strip()
                        similarity = float(sim_str)
                    except ValueError:
                        pass
                elif line.startswith('EXPLANATION:'):
                    explanation = line.replace('EXPLANATION:', '').strip()

            return (similarity, explanation)

        except Exception as e:
            return (0.0, f"Analysis failed: {str(e)}")
