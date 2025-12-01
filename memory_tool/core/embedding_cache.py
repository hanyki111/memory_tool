"""Common embedding cache module for AI features.

Provides:
- Singleton model loading (load once, reuse)
- File-based embedding caching
- Similarity calculation utilities
"""

import json
import hashlib
import math
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta


class EmbeddingModelManager:
    """Singleton manager for sentence-transformers model."""

    _instance = None
    _model = None
    _model_name = "sentence-transformers/all-MiniLM-L6-v2"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_model(self):
        """Get or load the sentence-transformers model.

        Returns:
            SentenceTransformer model or None if not available
        """
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
            except ImportError:
                return None
        return self._model

    def is_available(self) -> bool:
        """Check if sentence-transformers is available."""
        try:
            from sentence_transformers import SentenceTransformer
            return True
        except ImportError:
            return False


class EmbeddingCache:
    """File-based embedding cache with TTL support."""

    def __init__(self, cache_dir: Path, ttl_hours: int = 168):  # 7 days default
        """Initialize embedding cache.

        Args:
            cache_dir: Directory for cache files
            ttl_hours: Time-to-live in hours (default 7 days)
        """
        self.cache_dir = cache_dir
        self.ttl_hours = ttl_hours
        self.cache_file = cache_dir / "embeddings_cache.json"
        self._cache: Dict = {}
        self._load_cache()

    def _load_cache(self):
        """Load cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._cache = {}

    def _save_cache(self):
        """Save cache to file."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    def _content_hash(self, content: str) -> str:
        """Generate hash for content."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _is_valid(self, entry: Dict) -> bool:
        """Check if cache entry is still valid."""
        if "cached_at" not in entry:
            return False
        cached_at = datetime.fromisoformat(entry["cached_at"])
        return datetime.now() - cached_at < timedelta(hours=self.ttl_hours)

    def get(self, content: str) -> Optional[List[float]]:
        """Get cached embedding for content.

        Args:
            content: Text content

        Returns:
            Embedding vector or None if not cached
        """
        content_hash = self._content_hash(content)
        if content_hash in self._cache:
            entry = self._cache[content_hash]
            if self._is_valid(entry):
                return entry.get("embedding")
        return None

    def set(self, content: str, embedding: List[float]):
        """Cache embedding for content.

        Args:
            content: Text content
            embedding: Embedding vector
        """
        content_hash = self._content_hash(content)
        self._cache[content_hash] = {
            "embedding": embedding,
            "cached_at": datetime.now().isoformat(),
            "content_preview": content[:100]
        }
        self._save_cache()

    def get_or_compute(self, content: str, model) -> Optional[List[float]]:
        """Get cached embedding or compute and cache it.

        Args:
            content: Text content
            model: SentenceTransformer model

        Returns:
            Embedding vector or None if computation failed
        """
        # Try cache first
        cached = self.get(content)
        if cached is not None:
            return cached

        # Compute embedding
        if model is None:
            return None

        try:
            embedding = model.encode(content, convert_to_tensor=False).tolist()
            self.set(content, embedding)
            return embedding
        except Exception:
            return None

    def get_many(self, contents: List[str], model) -> List[Optional[List[float]]]:
        """Get embeddings for multiple contents, using cache where possible.

        Args:
            contents: List of text contents
            model: SentenceTransformer model

        Returns:
            List of embedding vectors (None for failed computations)
        """
        embeddings = []
        to_compute = []
        to_compute_indices = []

        # Check cache for each content
        for i, content in enumerate(contents):
            cached = self.get(content)
            if cached is not None:
                embeddings.append(cached)
            else:
                embeddings.append(None)
                to_compute.append(content)
                to_compute_indices.append(i)

        # Batch compute missing embeddings
        if to_compute and model is not None:
            try:
                computed = model.encode(to_compute, convert_to_tensor=False)
                for i, (idx, content) in enumerate(zip(to_compute_indices, to_compute)):
                    embedding = computed[i].tolist()
                    embeddings[idx] = embedding
                    self.set(content, embedding)
            except Exception:
                pass

        return embeddings

    def clear_expired(self):
        """Remove expired entries from cache."""
        valid_entries = {
            k: v for k, v in self._cache.items()
            if self._is_valid(v)
        }
        if len(valid_entries) < len(self._cache):
            self._cache = valid_entries
            self._save_cache()


class SimilarityCalculator:
    """Utility class for similarity calculations."""

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0-1)
        """
        if not vec1 or not vec2:
            return 0.0

        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 > 0 and norm2 > 0:
            return dot / (norm1 * norm2)
        return 0.0

    @staticmethod
    def find_top_k_similar(
        target_embedding: List[float],
        candidate_embeddings: List[List[float]],
        candidate_ids: List[str],
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[Tuple[str, float]]:
        """Find top-k most similar candidates.

        Args:
            target_embedding: Embedding of target content
            candidate_embeddings: Embeddings of candidates
            candidate_ids: IDs/names of candidates
            top_k: Number of top results to return
            threshold: Minimum similarity threshold

        Returns:
            List of (candidate_id, similarity) tuples sorted by similarity
        """
        if not target_embedding or not candidate_embeddings:
            return []

        similarities = []
        for emb, cid in zip(candidate_embeddings, candidate_ids):
            if emb is not None:
                sim = SimilarityCalculator.cosine_similarity(target_embedding, emb)
                if sim >= threshold:
                    similarities.append((cid, sim))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    @staticmethod
    def find_all_pairs_above_threshold(
        embeddings: List[List[float]],
        ids: List[str],
        threshold: float = 0.65
    ) -> List[Tuple[str, str, float]]:
        """Find all pairs of items with similarity above threshold.

        Args:
            embeddings: List of embeddings
            ids: List of IDs corresponding to embeddings
            threshold: Minimum similarity threshold

        Returns:
            List of (id1, id2, similarity) tuples sorted by similarity
        """
        pairs = []
        n = len(embeddings)

        for i in range(n):
            if embeddings[i] is None:
                continue
            for j in range(i + 1, n):
                if embeddings[j] is None:
                    continue
                sim = SimilarityCalculator.cosine_similarity(embeddings[i], embeddings[j])
                if sim >= threshold:
                    pairs.append((ids[i], ids[j], sim))

        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs


# Global instances for convenience
_model_manager: Optional[EmbeddingModelManager] = None
_embedding_cache: Optional[EmbeddingCache] = None


def get_model_manager() -> EmbeddingModelManager:
    """Get the global model manager instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = EmbeddingModelManager()
    return _model_manager


def get_embedding_cache(cache_dir: Path) -> EmbeddingCache:
    """Get or create embedding cache for the given directory.

    Args:
        cache_dir: Cache directory path

    Returns:
        EmbeddingCache instance
    """
    global _embedding_cache
    if _embedding_cache is None or _embedding_cache.cache_dir != cache_dir:
        _embedding_cache = EmbeddingCache(cache_dir)
    return _embedding_cache
