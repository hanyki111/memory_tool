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

        # Extract target module name for filtering
        # Try to get name from path relative to modules directory
        target_module_name = None
        try:
            # module_path could be like: .memory/modules/projects/memory-tool/core-system
            parts = module_path.parts
            if "modules" in parts:
                idx = parts.index("modules")
                target_module_name = "/".join(parts[idx + 1 :])
        except (ValueError, IndexError):
            pass

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

        prompt = f"""You are a module connection analyzer. Analyze the TARGET MODULE and suggest connections to CANDIDATE MODULES.

TARGET MODULE:
{target_content[:2000]}

CANDIDATE MODULES:
{candidates_text}

TASK: Suggest up to {max_suggestions} relevant module connections.

IMPORTANT: You MUST respond in EXACTLY this format for each suggestion:

MODULE: <exact module name from candidates>
REASON: <one sentence explanation>
CONFIDENCE: <number between 0.0 and 1.0>

---

Example response format:
MODULE: projects/memory-tool/search-system
REASON: Both modules handle data retrieval and indexing operations.
CONFIDENCE: 0.85

---

MODULE: projects/memory-tool/ui-system
REASON: The UI system displays timeline data managed by core system.
CONFIDENCE: 0.75

---

Now analyze and suggest connections. Use ONLY module names from the CANDIDATE MODULES list.
If no strong connections exist, respond with: NO_SUGGESTIONS
"""

        try:
            # Get LLM response
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=1000,
            )

            # Parse response
            suggestions = self._parse_suggestions(response)

            # Filter and match suggestions to candidate modules
            candidate_names = [name for name, _ in candidate_modules]

            filtered = []
            for module_name, reason, confidence in suggestions:
                # Skip if it's the target module itself
                if target_module_name and module_name == target_module_name:
                    continue

                # Try to match module name to a candidate
                matched_name = self._match_module_name(module_name, candidate_names)

                if matched_name:
                    filtered.append((matched_name, reason, confidence))

            return filtered[:max_suggestions]

        except Exception as e:
            # Fall back to empty list on error
            return []

    def _parse_suggestions(self, llm_response: str) -> List[Tuple[str, str, float]]:
        """Parse LLM response into structured suggestions.

        Handles multiple response formats:
        - Code blocks with simple format: module_name: confidence
        - Standard: MODULE: xxx, REASON: xxx, CONFIDENCE: 0.x
        - Numbered: 1. MODULE: xxx
        - Markdown bold: **MODULE:** xxx
        - Markdown headers: ### 1. **projects/memory-tool** (Top-level module)
        - Backtick wrapped: 1. **`projects/memory-tool`**
        - Various separators: ---, blank lines, numbered lists

        Args:
            llm_response: Raw LLM response text

        Returns:
            List of (module_name, reason, confidence) tuples
        """
        import re

        suggestions = []

        # Check for NO_SUGGESTIONS response
        if "NO_SUGGESTIONS" in llm_response.upper():
            return []

        # Strategy 1: Try to extract from code blocks first (most reliable)
        code_block_suggestions = self._parse_code_blocks(llm_response)
        if code_block_suggestions:
            return code_block_suggestions

        # Strategy 2: Fall back to markdown/text parsing
        # Split by various block separators
        # Try numbered items first (1. **module**)
        blocks = re.split(r'\n(?=\d+\.\s+\*\*)', llm_response)
        if len(blocks) <= 1:
            # Try --- separator
            blocks = re.split(r'\n---+\n', llm_response)
        if len(blocks) <= 1:
            # Try blank line followed by MODULE:
            blocks = re.split(r'\n\n+(?=MODULE:)', llm_response, flags=re.IGNORECASE)

        for block in blocks:
            lines = block.strip().split('\n')

            module_name = None
            reason = None
            confidence = 0.5

            for line in lines:
                line = line.strip()

                # Pattern 1: Backtick wrapped module name (supports both / and \ separators)
                # e.g., "1. **`projects/memory-tool`**" or "**`projects\memory-tool\search-system`**"
                backtick_match = re.search(
                    r'`([a-zA-Z0-9/\\_-]+(?:[/\\][a-zA-Z0-9/\\_-]+)*)`',
                    line
                )
                if backtick_match:
                    match_text = backtick_match.group(1)
                    if '/' in match_text or '\\' in match_text:
                        # Normalize to forward slashes
                        module_name = match_text.replace('\\', '/').strip()

                # Pattern 2: Standard format - MODULE: xxx (supports both / and \ separators)
                module_match = re.match(
                    r'^(?:MODULE|Module|module)[:\s]+([a-zA-Z0-9/\\_-]+(?:[/\\][a-zA-Z0-9/\\_-]+)*)',
                    re.sub(r'\*\*([^*]+)\*\*', r'\1', line), re.IGNORECASE
                )
                if module_match and not module_name:
                    match_text = module_match.group(1).strip().strip('`"\'[]')
                    module_name = match_text.replace('\\', '/').strip()

                # Pattern 3: Markdown header with module name (supports both / and \ separators)
                # e.g., "### 1. **projects/memory-tool/search-system**"
                if not module_name:
                    header_match = re.match(
                        r'^(?:\#{1,6}\s*)?(?:\d+\.\s*)?(?:\*\*)?([a-zA-Z0-9/\\_-]+(?:[/\\][a-zA-Z0-9/\\_-]+)+)(?:\*\*)?\s*(?:\(.*\))?$',
                        line
                    )
                    if header_match:
                        match_text = header_match.group(1)
                        if '/' in match_text or '\\' in match_text:
                            module_name = match_text.replace('\\', '/').strip()

                # Pattern 4: REASON: xxx format (explicit)
                reason_match = re.match(
                    r'^(?:\*\*)?(?:REASON|Reason|reason)[:\s]*(?:\*\*)?\s*(.+)',
                    line, re.IGNORECASE
                )
                if reason_match:
                    reason = self._clean_reason_text(reason_match.group(1))

                # Pattern 5: Extract reason from description lines (if no explicit REASON found)
                # e.g., "- This is the main entry point..." or "Requires core-system to..."
                if module_name and not reason:
                    reason_line = re.sub(r'^\s*[-*]\s*', '', line)  # Remove bullet
                    reason_line = self._clean_reason_text(reason_line)
                    if (reason_line and
                        not reason_line.lower().startswith(('confidence', 'note:', 'why')) and
                        '/' not in reason_line[:20] and  # Not a module path
                        len(reason_line) > 20):  # Substantial text
                        reason = reason_line

                # Pattern 6: CONFIDENCE (various formats)
                # e.g., "- **Confidence: 1.0**", "**Confidence:** 0.85", "- **Confidence**: 0.98"
                conf_match = re.search(
                    r'(?:\*\*)?(?:CONFIDENCE|Confidence|confidence)(?:\*\*)?[:\s]*(?:\*\*)?([0-9.]+)(?:\*\*)?',
                    line, re.IGNORECASE
                )
                if conf_match:
                    try:
                        conf_val = float(conf_match.group(1))
                        if conf_val > 1:
                            conf_val = conf_val / 100
                        confidence = min(1.0, max(0.0, conf_val))
                    except ValueError:
                        pass

            # If still no reason, try to find any descriptive text
            if module_name and not reason:
                for line in lines:
                    line = line.strip()
                    if line.startswith('-') and 'Confidence' not in line:
                        reason_text = self._clean_reason_text(line)
                        if len(reason_text) > 20:
                            reason = reason_text
                            break

            if module_name and reason:
                suggestions.append((module_name, reason, confidence))

        # Sort by confidence descending
        suggestions.sort(key=lambda x: x[2], reverse=True)

        return suggestions

    def _parse_code_blocks(self, llm_response: str) -> List[Tuple[str, str, float]]:
        """Extract suggestions from code blocks in LLM response.

        Handles formats like:
        ```plaintext
        projects/memory-tool: 1.0
        projects/memory-tool/llm-integration: 0.85
        ```

        Or:
        ```
        module_name: confidence
        ```

        Args:
            llm_response: Raw LLM response text

        Returns:
            List of (module_name, reason, confidence) tuples
        """
        import re

        suggestions = []

        # Find all code blocks
        code_block_pattern = r'```(?:plaintext|text|)?\s*\n(.*?)```'
        code_blocks = re.findall(code_block_pattern, llm_response, re.DOTALL)

        for block in code_blocks:
            lines = block.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Pattern: module_path: confidence (e.g., "projects/memory-tool: 1.0" or "projects\memory-tool: 1.0")
                match = re.match(
                    r'^([a-zA-Z0-9/\\_-]+(?:[/\\][a-zA-Z0-9/\\_-]+)*)\s*:\s*([0-9.]+)$',
                    line
                )
                if match:
                    match_text = match.group(1)
                    if '/' in match_text or '\\' in match_text:
                        # Normalize to forward slashes
                        module_name = match_text.replace('\\', '/').strip()
                        try:
                            confidence = float(match.group(2))
                            if confidence > 1:
                                confidence = confidence / 100
                            confidence = min(1.0, max(0.0, confidence))
                        except ValueError:
                            confidence = 0.5

                        # Try to find reason from surrounding text
                        reason = self._find_reason_for_module(llm_response, module_name)
                        suggestions.append((module_name, reason, confidence))

        # Sort by confidence descending
        suggestions.sort(key=lambda x: x[2], reverse=True)

        return suggestions

    def _find_reason_for_module(self, llm_response: str, module_name: str) -> str:
        """Find reason/description for a module from the LLM response.

        Args:
            llm_response: Full LLM response text
            module_name: Module name to find reason for

        Returns:
            Reason string or default message
        """
        import re

        # Look for patterns like:
        # "**module_name** - description"
        # "module_name: description"
        # "- module_name: description"
        # Lines containing the module name followed by description

        # Escape module name for regex
        escaped_name = re.escape(module_name)

        # Pattern 1: Bold module name followed by description
        pattern1 = rf'\*\*`?{escaped_name}`?\*\*[:\s-]+([^\n]+)'
        match = re.search(pattern1, llm_response)
        if match:
            reason = self._clean_reason_text(match.group(1))
            if len(reason) > 10:
                return reason

        # Pattern 2: Backtick module name followed by description
        pattern2 = rf'`{escaped_name}`[:\s-]+([^\n]+)'
        match = re.search(pattern2, llm_response)
        if match:
            reason = self._clean_reason_text(match.group(1))
            if len(reason) > 10:
                return reason

        # Pattern 3: Look for bullet point description after module mention
        pattern3 = rf'{escaped_name}[^\n]*\n\s*[-*]\s*([^\n]+)'
        match = re.search(pattern3, llm_response)
        if match:
            reason = self._clean_reason_text(match.group(1))
            if len(reason) > 10 and 'confidence' not in reason.lower():
                return reason

        # Default reason based on module name
        module_short = module_name.split('/')[-1]
        return f"Related to {module_short} functionality"

    def _match_module_name(
        self, suggested_name: str, candidate_names: List[str]
    ) -> Optional[str]:
        """Match a suggested module name to the best candidate.

        Handles variations in module names:
        - Exact match
        - Case-insensitive match
        - Path separator normalization (forward slash vs backslash)
        - Partial path match (suggested is suffix of candidate or vice versa)
        - Module name (last component) match

        Args:
            suggested_name: Module name from LLM suggestion
            candidate_names: List of valid candidate module names

        Returns:
            Matched candidate name, or None if no match found
        """
        if not suggested_name or not candidate_names:
            return None

        # Normalize the suggested name (convert \ to /, lowercase, strip slashes)
        suggested_normalized = suggested_name.replace('\\', '/').lower().strip('/')

        # Strategy 1: Exact match
        if suggested_name in candidate_names:
            return suggested_name

        # Strategy 2: Normalized exact match (handles / vs \ differences)
        for candidate in candidate_names:
            candidate_normalized = candidate.replace('\\', '/').lower().strip('/')
            if candidate_normalized == suggested_normalized:
                return candidate

        # Strategy 3: Suggested name is a suffix of candidate (or vice versa)
        # e.g., suggested="llm-integration" matches "projects/memory-tool/llm-integration"
        for candidate in candidate_names:
            candidate_normalized = candidate.replace('\\', '/').lower().strip('/')
            if candidate_normalized.endswith('/' + suggested_normalized):
                return candidate
            if suggested_normalized.endswith('/' + candidate_normalized):
                return candidate

        # Strategy 4: Last component (module name) match
        suggested_last = suggested_normalized.split('/')[-1]
        for candidate in candidate_names:
            candidate_normalized = candidate.replace('\\', '/').lower()
            candidate_last = candidate_normalized.split('/')[-1]
            if suggested_last == candidate_last:
                return candidate

        # Strategy 5: Partial path overlap (at least 2 components match)
        suggested_parts = suggested_normalized.split('/')
        for candidate in candidate_names:
            candidate_normalized = candidate.replace('\\', '/').lower()
            candidate_parts = candidate_normalized.split('/')
            # Check if suggested ends with candidate parts or vice versa
            if len(suggested_parts) >= 2 and len(candidate_parts) >= 2:
                # Check suffix overlap
                for i in range(1, min(len(suggested_parts), len(candidate_parts)) + 1):
                    if suggested_parts[-i:] == candidate_parts[-i:]:
                        if i >= 2:  # At least 2 components match
                            return candidate

        return None

    def _clean_reason_text(self, text: str) -> str:
        """Clean up reason text by removing markdown artifacts.

        Args:
            text: Raw reason text

        Returns:
            Cleaned reason text
        """
        import re

        # Remove leading bullet points
        text = re.sub(r'^\s*[-*]\s*', '', text)
        # Remove markdown bold (** around text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        # Remove orphaned ** or *: patterns (e.g., "**:" at start)
        text = re.sub(r'^\*+[:\s]*', '', text)
        # Remove single asterisks (italic markers)
        text = re.sub(r'(?<!\*)\*(?!\*)', '', text)
        # Remove backticks
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # Remove "Reason:" prefix if still present
        text = re.sub(r'^(?:Reason|REASON)[:\s]*', '', text, flags=re.IGNORECASE)
        # Clean up extra whitespace
        text = ' '.join(text.split())

        return text.strip()

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
