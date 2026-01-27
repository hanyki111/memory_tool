"""YAML frontmatter parsing and injection utilities."""

import hashlib
import re
from typing import Dict, Tuple, Any


class Frontmatter:
    """Utility class for YAML frontmatter operations."""

    FRONTMATTER_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n',
        re.DOTALL
    )

    @staticmethod
    def parse(content: str) -> Tuple[Dict[str, Any], str]:
        """Parse YAML frontmatter from content.

        Args:
            content: Content string potentially containing frontmatter

        Returns:
            Tuple of (frontmatter_dict, body_content)
            If no frontmatter found, returns ({}, content)
        """
        import yaml

        match = Frontmatter.FRONTMATTER_PATTERN.match(content)
        if not match:
            return {}, content

        frontmatter_str = match.group(1)
        body = content[match.end():]

        try:
            frontmatter = yaml.safe_load(frontmatter_str) or {}
        except yaml.YAMLError:
            return {}, content

        return frontmatter, body

    @staticmethod
    def inject(content: str, metadata: Dict[str, Any]) -> str:
        """Inject or update YAML frontmatter in content.

        Args:
            content: Content string (may or may not have existing frontmatter)
            metadata: Metadata dictionary to inject

        Returns:
            Content with frontmatter at the beginning
        """
        import yaml

        # Parse existing frontmatter
        existing, body = Frontmatter.parse(content)

        # Merge metadata (new values override existing)
        merged = {**existing, **metadata}

        # Format frontmatter
        frontmatter_str = yaml.dump(
            merged,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        ).strip()

        return f"---\n{frontmatter_str}\n---\n{body}"

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA-256 hash of content for change detection.

        Args:
            content: Content to hash

        Returns:
            First 8 characters of SHA-256 hash
        """
        # Remove frontmatter before hashing (hash only body)
        _, body = Frontmatter.parse(content)
        hash_obj = hashlib.sha256(body.encode('utf-8'))
        return hash_obj.hexdigest()[:8]

    @staticmethod
    def remove(content: str) -> str:
        """Remove frontmatter from content.

        Args:
            content: Content with potential frontmatter

        Returns:
            Content without frontmatter
        """
        _, body = Frontmatter.parse(content)
        return body
