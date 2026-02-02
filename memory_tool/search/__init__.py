"""Search functionality for timeline and modules."""

from .bm25 import BM25Ranker
from .ranking import SearchRanker, DateWeightRanker
from .filters import DateFilter, FileTypeFilter, TagFilter, FilterChain, TagCollector
from .formatter import ResultFormatter, deduplicate_results
from .hybrid import HybridSearcher
from .cache import SearchCache
from .parallel import ParallelSearcher
from .optimize import IndexOptimizer

__all__ = [
    "BM25Ranker",
    "SearchRanker",
    "DateWeightRanker",
    "DateFilter",
    "FileTypeFilter",
    "TagFilter",
    "TagCollector",
    "FilterChain",
    "ResultFormatter",
    "deduplicate_results",
    "HybridSearcher",
    "SearchCache",
    "ParallelSearcher",
    "IndexOptimizer",
]
