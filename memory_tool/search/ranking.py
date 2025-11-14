"""Ranking algorithms for search results."""

import math
from datetime import datetime
from typing import List
from ..core.search import SearchResult
from .bm25 import BM25Ranker


class DateWeightRanker:
    """Apply date-based weighting to search results."""

    def __init__(self, decay_days: int = 30, boost_factor: float = 2.0):
        """
        Initialize date weight ranker.

        Args:
            decay_days: Number of days for exponential decay (default: 30)
            boost_factor: Boost multiplier for recent results (default: 2.0)
        """
        self.decay_days = decay_days
        self.boost_factor = boost_factor

    def apply_date_weight(
        self,
        results: List[SearchResult],
    ) -> List[SearchResult]:
        """
        Apply date-based weighting to search results.

        Recent results are boosted, older results decay exponentially.

        Weight = base_score * (1 + boost_factor * e^(-days_ago / decay_days))

        Args:
            results: List of search results with scores and dates

        Returns:
            List of search results with updated scores, sorted by score
        """
        if not results:
            return results

        now = datetime.now()

        for result in results:
            if result.date is None:
                # No date info, keep original score
                continue

            # Calculate days ago
            days_ago = (now - result.date).days

            # Exponential decay
            date_weight = 1 + self.boost_factor * math.exp(-days_ago / self.decay_days)

            # Update score
            result.score *= date_weight

        # Sort by score (descending)
        return sorted(results, key=lambda x: x.score, reverse=True)


class SearchRanker:
    """Main ranking system combining BM25 and date weighting."""

    def __init__(
        self,
        use_bm25: bool = True,
        use_date_weight: bool = False,
        bm25_k1: float = 1.5,
        bm25_b: float = 0.75,
        date_decay_days: int = 30,
        date_boost_factor: float = 2.0,
    ):
        """
        Initialize search ranker.

        Args:
            use_bm25: Enable BM25 ranking
            use_date_weight: Enable date-based weighting
            bm25_k1: BM25 k1 parameter
            bm25_b: BM25 b parameter
            date_decay_days: Date decay days
            date_boost_factor: Date boost factor
        """
        self.use_bm25 = use_bm25
        self.use_date_weight = use_date_weight

        if use_bm25:
            self.bm25_ranker = BM25Ranker(k1=bm25_k1, b=bm25_b)

        if use_date_weight:
            self.date_ranker = DateWeightRanker(
                decay_days=date_decay_days,
                boost_factor=date_boost_factor,
            )

    def rank(
        self,
        query: str,
        results: List[SearchResult],
    ) -> List[SearchResult]:
        """
        Rank search results using enabled algorithms.

        Args:
            query: Search query
            results: List of search results

        Returns:
            Ranked list of search results
        """
        if not results:
            return results

        # Apply BM25 ranking
        if self.use_bm25:
            # Extract documents
            documents = [r.line_content for r in results]

            # Rank documents
            ranked = self.bm25_ranker.rank_documents(query, documents)

            # Update scores
            for doc_idx, score in ranked:
                results[doc_idx].score = score

        # Apply date weighting
        if self.use_date_weight:
            results = self.date_ranker.apply_date_weight(results)
        elif self.use_bm25:
            # Sort by BM25 score if date weighting not enabled
            results = sorted(results, key=lambda x: x.score, reverse=True)

        return results
