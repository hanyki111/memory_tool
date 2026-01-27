"""Hybrid search combining text and semantic (vector) search."""

from typing import List, Dict
from pathlib import Path
from ..core.search import SearchResult


class HybridSearcher:
    """Combine text and semantic search results with weighted scoring."""

    def __init__(self):
        """Initialize hybrid searcher."""
        pass

    def combine_results(
        self,
        text_results: List[SearchResult],
        semantic_results: List[SearchResult],
        text_weight: float = 0.7,
        semantic_weight: float = 0.3,
    ) -> List[SearchResult]:
        """
        Combine text and semantic search results.

        Uses weighted scoring to merge results from both search types.

        Args:
            text_results: Results from text-based search
            semantic_results: Results from semantic (vector) search
            text_weight: Weight for text search scores (default: 0.7)
            semantic_weight: Weight for semantic search scores (default: 0.3)

        Returns:
            Combined and re-ranked list of search results
        """
        # Normalize weights
        total_weight = text_weight + semantic_weight
        text_weight = text_weight / total_weight
        semantic_weight = semantic_weight / total_weight

        # Build lookup by file path + line number
        result_map: Dict[tuple, SearchResult] = {}

        # Add text results
        for result in text_results:
            key = (str(result.file_path), result.line_number)
            if key not in result_map:
                # Copy result and adjust score
                combined = SearchResult(
                    file_path=result.file_path,
                    line_number=result.line_number,
                    line_content=result.line_content,
                    match_context=result.match_context,
                    score=result.score * text_weight,
                    date=result.date,
                    source=result.source,
                    origin_project=result.origin_project,
                )
                result_map[key] = combined
            else:
                # Already exists, add to score
                result_map[key].score += result.score * text_weight

        # Add semantic results
        for result in semantic_results:
            key = (str(result.file_path), result.line_number)
            if key not in result_map:
                # Copy result and adjust score
                combined = SearchResult(
                    file_path=result.file_path,
                    line_number=result.line_number,
                    line_content=result.line_content,
                    match_context=result.match_context,
                    score=result.score * semantic_weight,
                    date=result.date,
                    source=result.source,
                    origin_project=result.origin_project,
                )
                result_map[key] = combined
            else:
                # Already exists, add to score
                result_map[key].score += result.score * semantic_weight

        # Convert back to list and sort by combined score
        combined_results = list(result_map.values())
        combined_results.sort(key=lambda x: x.score, reverse=True)

        return combined_results

    def search_hybrid(
        self,
        query: str,
        text_searcher,
        semantic_searcher,
        text_weight: float = 0.7,
        semantic_weight: float = 0.3,
        limit: int = 50,
    ) -> List[SearchResult]:
        """
        Perform hybrid search using both text and semantic searchers.

        Args:
            query: Search query
            text_searcher: Text-based searcher instance
            semantic_searcher: Semantic (vector) searcher instance
            text_weight: Weight for text results (default: 0.7)
            semantic_weight: Weight for semantic results (default: 0.3)
            limit: Maximum number of results to return

        Returns:
            Combined and ranked search results
        """
        # Perform both searches
        text_results = text_searcher.search(query, limit=limit)
        semantic_results = semantic_searcher.search(query, limit=limit)

        # Combine results
        combined = self.combine_results(
            text_results,
            semantic_results,
            text_weight,
            semantic_weight,
        )

        # Apply limit
        return combined[:limit]
