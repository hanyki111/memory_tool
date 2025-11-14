"""Category definitions for timeline and module summaries."""

from typing import Dict, List


# Default categories for memory_tool project
DEFAULT_CATEGORIES = [
    "Phase Implementation",
    "Feature Development",
    "Bug Fixes",
    "Refactoring",
    "Architecture Decisions",
    "Testing & Documentation",
]


# Category hierarchies (for future expansion)
CATEGORY_HIERARCHY = {
    "Development": [
        "Phase Implementation",
        "Feature Development",
        "Bug Fixes",
        "Refactoring",
    ],
    "Planning": [
        "Architecture Decisions",
        "Design Discussions",
        "Requirements Analysis",
    ],
    "Operations": [
        "Testing & Documentation",
        "Deployment",
        "Performance Optimization",
    ],
    "Meta": [
        "Tooling Improvements",
        "Process Refinement",
        "Dogfooding",
    ],
}


def get_default_categories() -> List[str]:
    """
    Get default category list.

    Returns:
        List of default category names
    """
    return DEFAULT_CATEGORIES.copy()


def get_category_hierarchy() -> Dict[str, List[str]]:
    """
    Get hierarchical category structure.

    Returns:
        Dictionary mapping parent categories to child categories
    """
    return CATEGORY_HIERARCHY.copy()


def get_all_categories() -> List[str]:
    """
    Get all categories (flattened from hierarchy).

    Returns:
        List of all category names
    """
    all_cats = []
    for parent, children in CATEGORY_HIERARCHY.items():
        all_cats.extend(children)
    return list(set(all_cats))


def suggest_category(entry_text: str) -> str:
    """
    Suggest category for entry based on keywords.

    Simple keyword-based categorization. For more sophisticated
    categorization, use LLM-based classification.

    Args:
        entry_text: Entry text to categorize

    Returns:
        Suggested category name
    """
    text_lower = entry_text.lower()

    # Keyword mappings
    keywords_map = {
        "Phase Implementation": ["phase", "milestone", "epic"],
        "Feature Development": ["feature", "add", "implement", "create"],
        "Bug Fixes": ["fix", "bug", "error", "issue"],
        "Refactoring": ["refactor", "clean", "restructure", "improve"],
        "Architecture Decisions": ["decision", "architecture", "design", "pattern"],
        "Testing & Documentation": ["test", "doc", "readme", "comment"],
    }

    # Check keywords
    for category, keywords in keywords_map.items():
        for keyword in keywords:
            if keyword in text_lower:
                return category

    # Default category
    return "Feature Development"
