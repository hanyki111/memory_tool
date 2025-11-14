"""
Vector search implementation for semantic timeline search.

Uses sentence-transformers for embeddings and cosine similarity for ranking.
"""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re

try:
    from sentence_transformers import SentenceTransformer
    import torch
    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False


class VectorSearchError(Exception):
    """Base exception for vector search errors."""
    pass


class VectorSearchNotAvailableError(VectorSearchError):
    """Raised when sentence-transformers is not installed."""
    pass


class EmbeddingCache:
    """Manages embedding cache for timeline entries."""

    def __init__(self, cache_dir: Path):
        """
        Initialize embedding cache.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "embeddings.json"
        self._cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Dict]:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        """Save cache to disk."""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def _get_content_hash(self, content: str) -> str:
        """Get hash of content for cache key."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def get(self, content: str) -> Optional[List[float]]:
        """Get cached embedding if available."""
        key = self._get_content_hash(content)
        if key in self._cache:
            return self._cache[key].get('embedding')
        return None

    def set(self, content: str, embedding: List[float]):
        """Cache embedding."""
        key = self._get_content_hash(content)
        self._cache[key] = {
            'content': content[:100],  # Store preview
            'embedding': embedding,
            'cached_at': datetime.now().isoformat()
        }
        self._save_cache()

    def clear(self):
        """Clear all cached embeddings."""
        self._cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()


class VectorSearcher:
    """Semantic search using sentence embeddings."""

    def __init__(
        self,
        base_path: Optional[Path] = None,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize vector searcher.

        Args:
            base_path: Base path for .memory/ (auto-detected if None)
            model_name: Name of sentence-transformers model

        Raises:
            VectorSearchNotAvailableError: If sentence-transformers not installed
        """
        if not VECTOR_SEARCH_AVAILABLE:
            raise VectorSearchNotAvailableError(
                "Vector search requires sentence-transformers. "
                "Install with: pip install memory-tool[vector]"
            )

        self.base_path = base_path or self._find_memory_root()
        self.timeline_path = self.base_path / "timeline"
        self.cache_dir = self.base_path / ".embeddings"

        # Initialize model and cache
        self.model = SentenceTransformer(model_name)
        self.cache = EmbeddingCache(self.cache_dir)

    def _find_memory_root(self) -> Path:
        """Find .memory/ directory in current or parent directories."""
        current = Path.cwd()
        while current != current.parent:
            memory_path = current / ".memory"
            if memory_path.exists() and memory_path.is_dir():
                return memory_path
            current = current.parent

        raise VectorSearchError(
            "No .memory/ directory found. Run 'minit' first."
        )

    def _collect_timeline_entries(self) -> List[Tuple[str, str, Path, int]]:
        """
        Collect all timeline entries.

        Returns:
            List of (content, date, file_path, line_number) tuples
        """
        entries = []

        if not self.timeline_path.exists():
            return entries

        # Recursively find all .md files
        for md_file in sorted(self.timeline_path.rglob("*.md")):
            # Extract date from path (timeline/YYYY-MM/DD.md)
            try:
                parts = md_file.parts
                timeline_idx = parts.index("timeline")
                year_month = parts[timeline_idx + 1]
                day_file = parts[timeline_idx + 2]
                date_str = f"{year_month}-{day_file.replace('.md', '')}"
            except (ValueError, IndexError):
                date_str = "unknown"

            # Read file and extract entries
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        # Match timeline entries: - HH:MM | content
                        match = re.match(r'^-\s*\d{1,2}:\d{2}\s*\|\s*(.+)$', line)
                        if match:
                            content = match.group(1).strip()
                            entries.append((content, date_str, md_file, line_num))
            except Exception:
                continue

        return entries

    def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text (with caching).

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Check cache first
        cached = self.cache.get(text)
        if cached is not None:
            return cached

        # Generate embedding
        embedding = self.model.encode(text, convert_to_tensor=False)
        embedding_list = embedding.tolist()

        # Cache it
        self.cache.set(text, embedding_list)

        return embedding_list

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (0-1)
        """
        if VECTOR_SEARCH_AVAILABLE:
            import torch
            tensor_a = torch.tensor(a)
            tensor_b = torch.tensor(b)
            return torch.cosine_similarity(tensor_a, tensor_b, dim=0).item()
        return 0.0

    def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        threshold: float = 0.3
    ) -> List[Dict]:
        """
        Perform semantic search on timeline.

        Args:
            query: Search query
            top_k: Number of results to return
            threshold: Minimum similarity threshold (0-1)

        Returns:
            List of search results with similarity scores
        """
        # Get query embedding
        query_embedding = self._get_embedding(query)

        # Collect all timeline entries
        entries = self._collect_timeline_entries()

        if not entries:
            return []

        # Calculate similarities
        results = []
        for content, date_str, file_path, line_num in entries:
            entry_embedding = self._get_embedding(content)
            similarity = self._cosine_similarity(query_embedding, entry_embedding)

            if similarity >= threshold:
                results.append({
                    'content': content,
                    'date': date_str,
                    'file': str(file_path),
                    'line': line_num,
                    'similarity': similarity
                })

        # Sort by similarity (descending)
        results.sort(key=lambda x: x['similarity'], reverse=True)

        # Return top-k
        return results[:top_k]

    def clear_cache(self):
        """Clear embedding cache."""
        self.cache.clear()
