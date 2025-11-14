"""BM25 ranking algorithm for search results."""

import math
import re
from typing import List, Dict, Set
from collections import Counter


class BM25Ranker:
    """BM25 ranking for text search results."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 ranker.

        Args:
            k1: Term frequency saturation parameter (default: 1.5)
            b: Length normalization parameter (default: 0.75)
        """
        self.k1 = k1
        self.b = b

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into terms.

        Args:
            text: Input text

        Returns:
            List of lowercase terms
        """
        # Simple tokenization: lowercase, split on non-alphanumeric
        terms = re.findall(r'\w+', text.lower())
        return terms

    def compute_idf(self, documents: List[str]) -> Dict[str, float]:
        """
        Compute IDF (Inverse Document Frequency) for all terms.

        IDF(term) = log((N - df(term) + 0.5) / (df(term) + 0.5) + 1)

        Where:
        - N = total number of documents
        - df(term) = number of documents containing term

        Args:
            documents: List of document texts

        Returns:
            Dictionary mapping terms to IDF scores
        """
        N = len(documents)
        df = Counter()  # Document frequency

        # Count documents containing each term
        for doc in documents:
            terms = set(self.tokenize(doc))
            for term in terms:
                df[term] += 1

        # Compute IDF
        idf = {}
        for term, doc_freq in df.items():
            idf[term] = math.log((N - doc_freq + 0.5) / (doc_freq + 0.5) + 1)

        return idf

    def score(
        self,
        query: str,
        document: str,
        idf: Dict[str, float],
        avg_doc_length: float,
    ) -> float:
        """
        Calculate BM25 score for a document given a query.

        BM25(D,Q) = Σ IDF(qi) * (f(qi,D) * (k1+1)) / (f(qi,D) + k1*(1-b+b*|D|/avgdl))

        Where:
        - IDF(qi) = inverse document frequency of query term qi
        - f(qi,D) = frequency of qi in document D
        - |D| = length of document D
        - avgdl = average document length in corpus
        - k1, b = tuning parameters

        Args:
            query: Search query
            document: Document text
            idf: Pre-computed IDF scores
            avg_doc_length: Average document length in corpus

        Returns:
            BM25 score (higher = more relevant)
        """
        query_terms = self.tokenize(query)
        doc_terms = self.tokenize(document)

        # Term frequency in document
        tf = Counter(doc_terms)
        doc_len = len(doc_terms)

        score = 0.0

        for term in query_terms:
            if term not in idf:
                continue

            term_idf = idf[term]
            term_tf = tf.get(term, 0)

            # BM25 formula
            numerator = term_tf * (self.k1 + 1)
            denominator = term_tf + self.k1 * (
                1 - self.b + self.b * doc_len / avg_doc_length
            )

            score += term_idf * (numerator / denominator)

        return score

    def rank_documents(
        self,
        query: str,
        documents: List[str],
    ) -> List[tuple]:
        """
        Rank documents by BM25 score for a query.

        Args:
            query: Search query
            documents: List of document texts

        Returns:
            List of (doc_index, score) tuples, sorted by score (descending)
        """
        if not documents:
            return []

        # Compute IDF
        idf = self.compute_idf(documents)

        # Compute average document length
        avg_doc_length = sum(len(self.tokenize(doc)) for doc in documents) / len(documents)

        # Score each document
        scored_docs = []
        for i, doc in enumerate(documents):
            score = self.score(query, doc, idf, avg_doc_length)
            scored_docs.append((i, score))

        # Sort by score (descending)
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        return scored_docs
