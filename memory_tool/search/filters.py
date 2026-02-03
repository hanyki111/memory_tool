"""Advanced filtering for search results."""

import re
from datetime import datetime, date, timedelta
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional, Tuple, List, Set, Dict
from ..core.search import SearchResult


class DateFilter:
    """Advanced date filtering for timeline files."""

    @staticmethod
    def parse_date_expression(expr: str) -> Tuple[Optional[date], Optional[date]]:
        """
        Parse date expressions into date range.

        Supported formats:
        - "today" -> Today's date
        - "yesterday" -> Yesterday
        - "this-week" -> Current week (Mon-Sun)
        - "this-month" -> Current month
        - "last-7-days" -> Last 7 days
        - "last-30-days" -> Last 30 days
        - "2025-11-15" -> Specific date (start=end=date)
        - "2025-11" -> Specific month
        - "2025-11-01..2025-11-15" -> Date range

        Args:
            expr: Date expression string

        Returns:
            Tuple of (from_date, to_date), both can be None

        Raises:
            ValueError: If expression format is invalid
        """
        expr = expr.lower().strip()
        today = datetime.now().date()

        # "today"
        if expr == "today":
            return (today, today)

        # "yesterday"
        if expr == "yesterday":
            yesterday = today - timedelta(days=1)
            return (yesterday, yesterday)

        # "this-week"
        if expr == "this-week":
            # Monday of current week
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)
            return (week_start, week_end)

        # "this-month"
        if expr == "this-month":
            month_start = today.replace(day=1)
            # Last day of month
            if today.month == 12:
                month_end = today.replace(day=31)
            else:
                next_month = today.replace(month=today.month + 1, day=1)
                month_end = next_month - timedelta(days=1)
            return (month_start, month_end)

        # "last-N-days"
        last_days_match = re.match(r'last-(\d+)-days?', expr)
        if last_days_match:
            n_days = int(last_days_match.group(1))
            start_date = today - timedelta(days=n_days - 1)
            return (start_date, today)

        # "YYYY-MM-DD..YYYY-MM-DD" (date range)
        if ".." in expr:
            parts = expr.split("..")
            if len(parts) != 2:
                raise ValueError(f"Invalid range format: {expr}")

            start_str, end_str = parts
            start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d").date()
            end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d").date()
            return (start_date, end_date)

        # "YYYY-MM-DD" (specific date)
        if re.match(r'\d{4}-\d{2}-\d{2}', expr):
            specific_date = datetime.strptime(expr, "%Y-%m-%d").date()
            return (specific_date, specific_date)

        # "YYYY-MM" (month)
        if re.match(r'\d{4}-\d{2}', expr):
            year, month = map(int, expr.split("-"))
            month_start = date(year, month, 1)

            # Last day of month
            if month == 12:
                month_end = date(year, 12, 31)
            else:
                next_month_start = date(year, month + 1, 1)
                month_end = next_month_start - timedelta(days=1)

            return (month_start, month_end)

        raise ValueError(
            f"Unrecognized date expression: {expr}\n"
            "Supported: today, yesterday, this-week, this-month, last-N-days, "
            "YYYY-MM-DD, YYYY-MM, YYYY-MM-DD..YYYY-MM-DD"
        )

    @staticmethod
    def filter_by_date(
        results: List[SearchResult],
        date_expr: Optional[str],
    ) -> List[SearchResult]:
        """
        Filter results by date expression.

        Args:
            results: Search results
            date_expr: Date expression (None = no filter)

        Returns:
            Filtered results
        """
        if not date_expr:
            return results

        from_date, to_date = DateFilter.parse_date_expression(date_expr)

        filtered = []
        for result in results:
            if result.date is None:
                # No date, skip
                continue

            result_date = result.date.date()

            # Check range
            if from_date and result_date < from_date:
                continue
            if to_date and result_date > to_date:
                continue

            filtered.append(result)

        return filtered


class FileTypeFilter:
    """Filter search results by file type."""

    # File type patterns
    TYPE_PATTERNS = {
        "timeline": ["timeline/**/*.md"],
        "modules": ["modules/**/*.md"],
        "concepts": ["concepts/**/*.md"],
        "decisions": ["**/decisions*.md"],
        "current": ["**/current*.md"],
        "plans": ["**/PLAN-*.md"],
        "archive": ["**/archive/**/*.md"],
    }

    @staticmethod
    def matches_type(file_path: Path, file_type: str, base_path: Path) -> bool:
        """
        Check if file matches type pattern.

        Args:
            file_path: File path to check
            file_type: File type name
            base_path: Base path for relative matching

        Returns:
            True if matches
        """
        patterns = FileTypeFilter.TYPE_PATTERNS.get(file_type.lower(), [])

        if not patterns:
            return False

        try:
            rel_path = file_path.relative_to(base_path)
            rel_path_str = str(rel_path).replace("\\", "/")  # Unix-style

            from fnmatch import fnmatch

            for pattern in patterns:
                if fnmatch(rel_path_str, pattern):
                    return True

            return False
        except (ValueError, Exception):
            return False

    @staticmethod
    def filter_by_type(
        results: List[SearchResult],
        file_type: Optional[str],
        base_path: Path,
    ) -> List[SearchResult]:
        """
        Filter results by file type.

        Args:
            results: Search results
            file_type: File type name (None = no filter)
            base_path: Base path for relative matching

        Returns:
            Filtered results
        """
        if not file_type:
            return results

        return [
            r for r in results
            if FileTypeFilter.matches_type(r.file_path, file_type, base_path)
        ]


class TagFilter:
    """Filter by tags or categories."""

    @staticmethod
    def extract_tags(content: str, preserve_case: bool = True) -> Set[str]:
        """
        Extract tags from content.

        Extracts:
        - [bracket tags] (including Korean)
        - #hashtags (including Korean)
        - **Category:** patterns
        - YAML frontmatter tags (if present)

        Args:
            content: Document content
            preserve_case: If True, preserve original case; if False, convert to lowercase

        Returns:
            Set of tags
        """
        tags = set()

        # Extract [bracket tags] (supports Korean, alphanumeric, hyphens, underscores, spaces)
        bracket_tags = re.findall(r'\[([\w가-힣\s-]+)\]', content)
        if preserve_case:
            tags.update(tag.strip() for tag in bracket_tags)
        else:
            tags.update(tag.strip().lower() for tag in bracket_tags)

        # Extract #hashtags (supports Korean, alphanumeric, hyphens, underscores)
        hashtags = re.findall(r'#([\w가-힣-]+)', content)
        if preserve_case:
            tags.update(hashtags)
        else:
            tags.update(tag.lower() for tag in hashtags)

        # Extract **Category:** patterns
        categories = re.findall(r'\*\*([^:]+):\*\*', content)
        if preserve_case:
            tags.update(cat.strip() for cat in categories)
        else:
            tags.update(cat.strip().lower() for cat in categories)

        # TODO: YAML frontmatter parsing (future enhancement)

        return tags

    @staticmethod
    def filter_by_tags(
        results: List[SearchResult],
        required_tags: Optional[List[str]],
    ) -> List[SearchResult]:
        """
        Filter results by tags (case-insensitive matching).

        Args:
            results: Search results
            required_tags: List of required tags (None = no filter)

        Returns:
            Filtered results (must have ALL required tags)
        """
        if not required_tags:
            return results

        # Lowercase required tags for case-insensitive comparison
        required_tags_lower = set(tag.lower() for tag in required_tags)

        filtered = []
        for result in results:
            # Extract tags preserving case, then lowercase for comparison
            content_tags = TagFilter.extract_tags(result.match_context)
            content_tags_lower = set(tag.lower() for tag in content_tags)

            # Check if all required tags are present (case-insensitive)
            if required_tags_lower.issubset(content_tags_lower):
                filtered.append(result)

        return filtered


class FilterChain:
    """Chain multiple filters together."""

    def __init__(self, base_path: Path):
        """
        Initialize filter chain.

        Args:
            base_path: Base path for file type filtering
        """
        self.base_path = base_path

    def apply_filters(
        self,
        results: List[SearchResult],
        date_expr: Optional[str] = None,
        file_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """
        Apply all filters to results.

        Args:
            results: Search results
            date_expr: Date expression filter
            file_type: File type filter
            tags: Tag filters

        Returns:
            Filtered results
        """
        # Apply filters in sequence
        if date_expr:
            results = DateFilter.filter_by_date(results, date_expr)

        if file_type:
            results = FileTypeFilter.filter_by_type(results, file_type, self.base_path)

        if tags:
            results = TagFilter.filter_by_tags(results, tags)

        return results


class TagCollector:
    """Collect and analyze tags from .memory files."""

    # File type patterns for tag collection
    FILE_TYPE_PATTERNS = {
        "timeline": ["timeline/**/*.md"],
        "modules": ["modules/**/*.md"],
        "plans": ["**/PLAN-*.md", "**/plans/**/*.md"],
    }

    def __init__(self, memory_path: Path):
        """
        Initialize tag collector.

        Args:
            memory_path: Path to .memory directory
        """
        self.memory_path = memory_path

    def _get_files_for_types(self, file_types: List[str]) -> List[Path]:
        """
        Get list of files matching the specified file types.

        Args:
            file_types: List of file type names (timeline, modules, plans)

        Returns:
            List of matching file paths
        """
        files = []
        seen = set()

        for file_type in file_types:
            patterns = self.FILE_TYPE_PATTERNS.get(file_type.lower(), [])
            for pattern in patterns:
                for path in self.memory_path.glob(pattern):
                    if path.is_file() and path not in seen:
                        seen.add(path)
                        files.append(path)

        return files

    def _extract_tags_from_file(self, file_path: Path) -> Set[str]:
        """
        Extract tags from a single file.

        Args:
            file_path: Path to the file

        Returns:
            Set of tags found in the file
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            raw_tags = TagFilter.extract_tags(content)

            # Filter out invalid tags:
            # - Pure numbers (likely from markdown references like [1], [23])
            # - Tags longer than 50 characters (likely malformed)
            # - Tags containing newlines
            filtered_tags = set()
            for tag in raw_tags:
                # Skip pure numbers
                if tag.isdigit():
                    continue
                # Skip tags that are too long
                if len(tag) > 50:
                    continue
                # Skip tags with newlines
                if "\n" in tag:
                    continue
                filtered_tags.add(tag)

            return filtered_tags
        except Exception:
            return set()

    def _count_tags_from_file(self, file_path: Path) -> Dict[str, int]:
        """
        Count all tag occurrences from a single file.

        Unlike _extract_tags_from_file which returns unique tags,
        this method counts every occurrence of each tag.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary mapping tags to their occurrence counts
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            tag_counts: Dict[str, int] = {}

            # Extract [bracket tags] (supports Korean, alphanumeric, hyphens, underscores, spaces)
            bracket_tags = re.findall(r'\[([\w가-힣\s-]+)\]', content)
            for tag in bracket_tags:
                tag = tag.strip()
                # Skip invalid tags
                if tag.isdigit() or len(tag) > 50 or "\n" in tag:
                    continue
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            # Extract #hashtags (supports Korean, alphanumeric, hyphens, underscores)
            hashtags = re.findall(r'#([\w가-힣-]+)', content)
            for tag in hashtags:
                # Skip invalid tags
                if tag.isdigit() or len(tag) > 50 or "\n" in tag:
                    continue
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            # Extract **Category:** patterns
            categories = re.findall(r'\*\*([^:]+):\*\*', content)
            for tag in categories:
                tag = tag.strip()
                # Skip invalid tags
                if tag.isdigit() or len(tag) > 50 or "\n" in tag:
                    continue
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            return tag_counts
        except Exception:
            return {}

    def collect(self, file_types: List[str]) -> Dict[str, int]:
        """
        Collect tags with counts from specified file types.

        Counts every occurrence of each tag, not just unique tags per file.

        Args:
            file_types: List of file type names to search

        Returns:
            Dictionary mapping tag names to usage counts
        """
        tag_counts: Dict[str, int] = {}
        files = self._get_files_for_types(file_types)

        for file_path in files:
            file_tag_counts = self._count_tags_from_file(file_path)
            for tag, count in file_tag_counts.items():
                tag_counts[tag] = tag_counts.get(tag, 0) + count

        return tag_counts

    def collect_by_type(self, file_types: List[str]) -> Dict[str, Dict[str, int]]:
        """
        Collect tags grouped by file type.

        Args:
            file_types: List of file type names to search

        Returns:
            Dictionary mapping file types to their tag counts
        """
        result: Dict[str, Dict[str, int]] = {}

        for file_type in file_types:
            tag_counts: Dict[str, int] = {}
            patterns = self.FILE_TYPE_PATTERNS.get(file_type.lower(), [])

            for pattern in patterns:
                for file_path in self.memory_path.glob(pattern):
                    if file_path.is_file():
                        tags = self._extract_tags_from_file(file_path)
                        for tag in tags:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1

            if tag_counts:
                result[file_type] = tag_counts

        return result


class TagManager:
    """Manage tags in .memory files (replace, delete)."""

    # Reuse patterns from TagCollector
    FILE_TYPE_PATTERNS = TagCollector.FILE_TYPE_PATTERNS

    def __init__(self, memory_path: Path):
        """
        Initialize tag manager.

        Args:
            memory_path: Path to .memory directory
        """
        self.memory_path = memory_path

    def _get_files_for_types(self, file_types: List[str]) -> List[Path]:
        """Get list of files matching the specified file types."""
        files = []
        seen = set()

        for file_type in file_types:
            patterns = self.FILE_TYPE_PATTERNS.get(file_type.lower(), [])
            for pattern in patterns:
                for path in self.memory_path.glob(pattern):
                    if path.is_file() and path not in seen:
                        seen.add(path)
                        files.append(path)

        return files

    def _replace_tag_in_content(
        self,
        content: str,
        old_tag: str,
        new_tag: Optional[str] = None,
    ) -> Tuple[str, int]:
        """
        Replace or delete a tag in content.

        Args:
            content: File content
            old_tag: Tag to find (case-insensitive matching)
            new_tag: New tag (None = delete)

        Returns:
            Tuple of (modified content, number of replacements)
        """
        count = 0
        old_tag_lower = old_tag.lower()

        # Replace [bracket tags]
        def replace_bracket(match):
            nonlocal count
            tag = match.group(1)
            if tag.lower() == old_tag_lower:
                count += 1
                if new_tag is None:
                    return ""  # Delete
                return f"[{new_tag}]"
            return match.group(0)

        content = re.sub(r'\[([\w가-힣\s-]+)\]', replace_bracket, content)

        # Replace #hashtags
        def replace_hashtag(match):
            nonlocal count
            tag = match.group(1)
            if tag.lower() == old_tag_lower:
                count += 1
                if new_tag is None:
                    return ""  # Delete
                return f"#{new_tag}"
            return match.group(0)

        content = re.sub(r'#([\w가-힣-]+)', replace_hashtag, content)

        # Clean up double spaces from deletions
        if new_tag is None:
            content = re.sub(r'  +', ' ', content)
            # Clean up space at start of line
            content = re.sub(r'^\s+$', '', content, flags=re.MULTILINE)

        return content, count

    def replace_tag(
        self,
        old_tag: str,
        new_tag: str,
        file_types: List[str],
        dry_run: bool = False,
    ) -> Dict[str, any]:
        """
        Replace a tag with another in all matching files.

        Args:
            old_tag: Tag to replace
            new_tag: New tag value
            file_types: File types to search
            dry_run: If True, don't modify files

        Returns:
            Dictionary with results (files_modified, total_replacements, details)
        """
        files = self._get_files_for_types(file_types)
        results = {
            "files_modified": 0,
            "total_replacements": 0,
            "details": [],
            "dry_run": dry_run,
        }

        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
                new_content, count = self._replace_tag_in_content(content, old_tag, new_tag)

                if count > 0:
                    results["files_modified"] += 1
                    results["total_replacements"] += count
                    rel_path = file_path.relative_to(self.memory_path)
                    results["details"].append({
                        "file": str(rel_path),
                        "count": count,
                    })

                    if not dry_run:
                        file_path.write_text(new_content, encoding="utf-8")

            except Exception as e:
                results["details"].append({
                    "file": str(file_path),
                    "error": str(e),
                })

        return results

    def delete_tag(
        self,
        tag: str,
        file_types: List[str],
        dry_run: bool = False,
    ) -> Dict[str, any]:
        """
        Delete a tag from all matching files.

        Args:
            tag: Tag to delete
            file_types: File types to search
            dry_run: If True, don't modify files

        Returns:
            Dictionary with results
        """
        files = self._get_files_for_types(file_types)
        results = {
            "files_modified": 0,
            "total_deletions": 0,
            "details": [],
            "dry_run": dry_run,
        }

        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
                new_content, count = self._replace_tag_in_content(content, tag, None)

                if count > 0:
                    results["files_modified"] += 1
                    results["total_deletions"] += count
                    rel_path = file_path.relative_to(self.memory_path)
                    results["details"].append({
                        "file": str(rel_path),
                        "count": count,
                    })

                    if not dry_run:
                        file_path.write_text(new_content, encoding="utf-8")

            except Exception as e:
                results["details"].append({
                    "file": str(file_path),
                    "error": str(e),
                })

        return results

    def find_tag(
        self,
        tag: str,
        file_types: List[str],
    ) -> List[Dict[str, any]]:
        """
        Find all occurrences of a tag.

        Args:
            tag: Tag to find
            file_types: File types to search

        Returns:
            List of file info with tag occurrences
        """
        files = self._get_files_for_types(file_types)
        tag_lower = tag.lower()
        results = []

        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")

                # Count occurrences
                bracket_matches = re.findall(r'\[([\w가-힣\s-]+)\]', content)
                hashtag_matches = re.findall(r'#([\w가-힣-]+)', content)

                count = sum(1 for t in bracket_matches if t.lower() == tag_lower)
                count += sum(1 for t in hashtag_matches if t.lower() == tag_lower)

                if count > 0:
                    rel_path = file_path.relative_to(self.memory_path)
                    results.append({
                        "file": str(rel_path),
                        "count": count,
                    })

            except Exception:
                pass

        return results
