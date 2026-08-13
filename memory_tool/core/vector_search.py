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
from memory_tool.utils.paths import get_base_path

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
    """Manages embedding cache for timeline entries with file modification tracking."""

    def __init__(self, cache_dir: Path):
        """
        Initialize embedding cache.

        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "embeddings.json"
        self.index_file = self.cache_dir / "index.json"
        self._cache = self._load_cache()
        self._index = self._load_index()

    def _load_cache(self) -> Dict[str, Dict]:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _load_index(self) -> Dict[str, float]:
        """
        Load file modification index.

        Returns:
            Dict mapping file paths to modification timestamps
        """
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        """Save cache to disk."""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    def _save_index(self):
        """Save file modification index to disk."""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)

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

    def set_batch(self, contents: List[str], embeddings: List[List[float]]):
        """
        Cache multiple embeddings at once (batch operation).

        Args:
            contents: List of text contents
            embeddings: List of corresponding embeddings
        """
        for content, embedding in zip(contents, embeddings):
            key = self._get_content_hash(content)
            self._cache[key] = {
                'content': content[:100],
                'embedding': embedding,
                'cached_at': datetime.now().isoformat()
            }
        self._save_cache()

    def is_file_indexed(self, file_path: Path) -> bool:
        """
        Check if file needs reindexing based on modification time.

        Args:
            file_path: Path to file

        Returns:
            True if file is up to date in cache, False otherwise
        """
        file_str = str(file_path)
        if file_str not in self._index:
            return False

        try:
            current_mtime = file_path.stat().st_mtime
            cached_mtime = self._index[file_str]
            return current_mtime <= cached_mtime
        except (OSError, KeyError):
            return False

    def mark_file_indexed(self, file_path: Path):
        """
        Mark file as indexed with current modification time.

        Args:
            file_path: Path to file
        """
        try:
            file_str = str(file_path)
            self._index[file_str] = file_path.stat().st_mtime
            self._save_index()
        except OSError:
            pass

    def clear(self):
        """Clear all cached embeddings and index."""
        self._cache = {}
        self._index = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        if self.index_file.exists():
            self.index_file.unlink()

    def get_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (entries, size, files indexed)
        """
        cache_size = self.cache_file.stat().st_size if self.cache_file.exists() else 0
        return {
            'entries': len(self._cache),
            'files_indexed': len(self._index),
            'cache_size_mb': cache_size / (1024 * 1024),
        }


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
        """Find the knowledge base folder.

        Delegates to the central resolver so the configurable base folder
        name (and a base of ".") is honoured.
        """
        return get_base_path()

    def _collect_timeline_entries(
        self,
        force_reindex: bool = False
    ) -> List[Tuple[str, str, Path, int]]:
        """
        Collect timeline entries (incremental indexing support).

        Args:
            force_reindex: If True, reindex all files regardless of modification time

        Returns:
            List of (content, date, file_path, line_number) tuples
        """
        entries = []

        if not self.timeline_path.exists():
            return entries

        # Recursively find all .md files
        for md_file in sorted(self.timeline_path.rglob("*.md")):
            # Skip files that haven't been modified (unless force_reindex)
            if not force_reindex and self.cache.is_file_indexed(md_file):
                continue

            # Extract date from path (timeline/YYYY-MM/DD.md)
            try:
                parts = md_file.parts
                timeline_idx = parts.index("timeline")
                year_month = parts[timeline_idx + 1]
                day_file = parts[timeline_idx + 2]
                date_str = f"{year_month}-{day_file.replace('.md', '')}"
            except (ValueError, IndexError):
                date_str = "unknown"

            # Read file and extract entries (streaming for memory efficiency)
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        # Match timeline entries: - HH:MM | content
                        match = re.match(r'^-\s*\d{1,2}:\d{2}\s*\|\s*(.+)$', line)
                        if match:
                            content = match.group(1).strip()
                            entries.append((content, date_str, md_file, line_num))

                # Mark file as indexed
                self.cache.mark_file_indexed(md_file)
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

    def _get_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Get embeddings for multiple texts (batch processing for performance).

        Args:
            texts: List of texts to embed
            batch_size: Batch size for encoding (default: 32)
            show_progress: Show progress bar (requires tqdm)

        Returns:
            List of embedding vectors
        """
        embeddings = []
        uncached_texts = []
        uncached_indices = []

        # Check cache for each text
        for i, text in enumerate(texts):
            cached = self.cache.get(text)
            if cached is not None:
                embeddings.append(cached)
            else:
                embeddings.append(None)  # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Batch encode uncached texts
        if uncached_texts:
            # Process in batches for memory efficiency
            uncached_embeddings = []
            for i in range(0, len(uncached_texts), batch_size):
                batch = uncached_texts[i:i + batch_size]
                batch_embeddings = self.model.encode(
                    batch,
                    convert_to_tensor=False,
                    show_progress_bar=show_progress and i == 0
                )
                # Convert to list of lists
                for emb in batch_embeddings:
                    uncached_embeddings.append(emb.tolist())

            # Cache batch results
            self.cache.set_batch(uncached_texts, uncached_embeddings)

            # Fill in placeholders
            for idx, emb in zip(uncached_indices, uncached_embeddings):
                embeddings[idx] = emb

        return embeddings

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
        threshold: float = 0.3,
        force_reindex: bool = False,
        batch_size: int = 32
    ) -> List[Dict]:
        """
        Perform semantic search on timeline (optimized with batch processing).

        Args:
            query: Search query
            top_k: Number of results to return
            threshold: Minimum similarity threshold (0-1)
            force_reindex: Force reindexing all files
            batch_size: Batch size for embedding computation

        Returns:
            List of search results with similarity scores
        """
        # Get query embedding
        query_embedding = self._get_embedding(query)

        # Collect timeline entries (incremental indexing)
        entries = self._collect_timeline_entries(force_reindex=force_reindex)

        if not entries:
            return []

        # Extract contents for batch embedding
        contents = [content for content, _, _, _ in entries]

        # Get embeddings in batch (much faster than one-by-one)
        entry_embeddings = self._get_embeddings_batch(
            contents,
            batch_size=batch_size,
            show_progress=False
        )

        # Calculate similarities
        results = []
        for (content, date_str, file_path, line_num), entry_embedding in zip(entries, entry_embeddings):
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

    def preindex_timeline(self, batch_size: int = 32, force: bool = False):
        """
        Pre-index all timeline entries (warm up cache).

        Args:
            batch_size: Batch size for embedding computation
            force: Force reindexing even if files haven't changed

        Returns:
            Dict with indexing statistics
        """
        entries = self._collect_timeline_entries(force_reindex=force)

        if not entries:
            return {
                'entries_indexed': 0,
                'files_processed': 0,
                'cache_stats': self.cache.get_stats()
            }

        # Extract contents
        contents = [content for content, _, _, _ in entries]

        # Batch embed all contents (this caches them)
        self._get_embeddings_batch(contents, batch_size=batch_size, show_progress=True)

        # Get unique files
        files_processed = len(set(file_path for _, _, file_path, _ in entries))

        return {
            'entries_indexed': len(entries),
            'files_processed': files_processed,
            'cache_stats': self.cache.get_stats()
        }

    def clear_cache(self):
        """Clear embedding cache."""
        self.cache.clear()
