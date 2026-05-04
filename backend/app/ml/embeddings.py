"""
Local Embeddings: Sentence-Transformers (Privacy-Preserving).

NO cloud APIs. All embeddings computed locally.

Uses sentence-transformers to generate dense vector embeddings.
Default model: all-MiniLM-L6-v2 (fast, good quality, ~22MB)

Supports:
- Single text embedding
- Batch embeddings
- Cosine similarity computation
- Embedding caching (in-memory or Redis)
"""

import logging
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import numpy as np
from functools import lru_cache

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class TextEmbedding(BaseModel):
    """Single text embedding with metadata."""
    text: str
    embedding: List[float] = Field(...)  # Dense vector
    model: str = "all-MiniLM-L6-v2"
    dimension: int = 384  # all-MiniLM-L6-v2 output dimension
    normalized: bool = False  # Is vector L2-normalized?


class EmbeddingBatch(BaseModel):
    """Batch of embeddings."""
    texts: List[str]
    embeddings: List[List[float]]  # N x D matrix
    model: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    batch_size: int = 32
    inference_time_seconds: float = 0.0


class SimilarityResult(BaseModel):
    """Cosine similarity result."""
    text_1: str
    text_2: str
    similarity: float = Field(ge=0.0, le=1.0)  # Cosine similarity [0, 1]
    distance: float = Field(ge=0.0, le=2.0)  # Euclidean distance [0, 2]


# ============================================================================
# LOCAL EMBEDDINGS SERVICE
# ============================================================================

class LocalEmbeddingsService:
    """
    Generate embeddings locally using sentence-transformers.
    
    Privacy guarantee: NO network calls to cloud APIs.
    All computation on local hardware.
    
    Requirements:
    - sentence-transformers installed: pip install sentence-transformers
    - First run downloads ~22MB model from HuggingFace (cached locally)
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding service.
        
        Args:
            model_name: HuggingFace model (cached locally after first download)
        """
        self.model_name = model_name
        self.model = None
        self.dimension = 384
        self._embedding_cache: Dict[str, List[float]] = {}
        
        # Lazy-load model (on first embedding call)
        logger.info(f"Local embeddings service initialized (model: {model_name})")
    
    def _load_model(self):
        """Lazy-load sentence-transformers model."""
        if self.model is not None:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading {self.model_name}...")
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"✓ Model loaded (dimension: {self.dimension})")
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    # ========================================================================
    # SINGLE EMBEDDING
    # ========================================================================
    
    def embed(self, text: str, normalize: bool = True) -> TextEmbedding:
        """
        Generate embedding for single text.
        
        Args:
            text: Text to embed
            normalize: L2-normalize the vector?
        
        Returns:
            TextEmbedding with dense vector
        """
        # Check cache first
        cache_key = f"{text}:{normalize}"
        if cache_key in self._embedding_cache:
            embedding_list = self._embedding_cache[cache_key]
        else:
            # Load model if needed
            self._load_model()
            
            # Generate embedding
            embedding_array = self.model.encode(text, normalize_embeddings=normalize)
            embedding_list = embedding_array.tolist()
            
            # Cache it
            self._embedding_cache[cache_key] = embedding_list
        
        return TextEmbedding(
            text=text,
            embedding=embedding_list,
            model=self.model_name,
            dimension=self.dimension,
            normalized=normalize,
        )
    
    # ========================================================================
    # BATCH EMBEDDINGS
    # ========================================================================
    
    def embed_batch(
        self,
        texts: List[str],
        normalize: bool = True,
        batch_size: int = 32,
    ) -> EmbeddingBatch:
        """
        Generate embeddings for batch of texts.
        
        Args:
            texts: List of texts to embed
            normalize: L2-normalize vectors?
            batch_size: Process in chunks of this size
        
        Returns:
            EmbeddingBatch with all embeddings
        """
        # Load model if needed
        self._load_model()
        
        # Generate embeddings
        import time
        start = time.time()
        
        embeddings_array = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize,
            show_progress_bar=False,
        )
        
        inference_time = time.time() - start
        
        return EmbeddingBatch(
            texts=texts,
            embeddings=embeddings_array.tolist(),
            model=self.model_name,
            dimension=self.dimension,
            batch_size=batch_size,
            inference_time_seconds=inference_time,
        )
    
    # ========================================================================
    # SIMILARITY COMPUTATION
    # ========================================================================
    
    @staticmethod
    def cosine_similarity(embedding_1: List[float], embedding_2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Formula: s_j = cos(E(T_t), e_j) = (E1 · E2) / (||E1|| * ||E2||)
        
        Args:
            embedding_1, embedding_2: Two embedding vectors
        
        Returns:
            Similarity score in [0, 1]
        """
        arr1 = np.array(embedding_1, dtype=np.float32)
        arr2 = np.array(embedding_2, dtype=np.float32)
        
        # Cosine similarity
        dot_product = np.dot(arr1, arr2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        # Clamp to [0, 1] in case of numerical errors
        return max(0.0, min(1.0, float(similarity)))
    
    @staticmethod
    def euclidean_distance(embedding_1: List[float], embedding_2: List[float]) -> float:
        """
        Compute Euclidean distance between two embeddings.
        
        Args:
            embedding_1, embedding_2: Two embedding vectors
        
        Returns:
            Distance in [0, 2] (max distance for normalized unit vectors)
        """
        arr1 = np.array(embedding_1, dtype=np.float32)
        arr2 = np.array(embedding_2, dtype=np.float32)
        distance = np.linalg.norm(arr1 - arr2)
        return float(distance)
    
    def similarity(
        self,
        text_1: str,
        text_2: str,
        normalize: bool = True,
    ) -> SimilarityResult:
        """
        Compute similarity between two texts.
        
        Args:
            text_1, text_2: Texts to compare
            normalize: Use L2-normalized embeddings?
        
        Returns:
            SimilarityResult with cosine similarity and distance
        """
        emb1 = self.embed(text_1, normalize=normalize)
        emb2 = self.embed(text_2, normalize=normalize)
        
        cos_sim = self.cosine_similarity(emb1.embedding, emb2.embedding)
        euc_dist = self.euclidean_distance(emb1.embedding, emb2.embedding)
        
        return SimilarityResult(
            text_1=text_1,
            text_2=text_2,
            similarity=cos_sim,
            distance=euc_dist,
        )
    
    # ========================================================================
    # SIMILARITY TO BATCH (CORPUS SEARCH)
    # ========================================================================
    
    def similarity_batch(
        self,
        query_text: str,
        corpus_texts: List[str],
        normalize: bool = True,
        top_k: Optional[int] = None,
    ) -> List[Tuple[str, float]]:
        """
        Find most similar texts in corpus.
        
        Args:
            query_text: Query to search for
            corpus_texts: Corpus to search in
            normalize: Use L2-normalized embeddings?
            top_k: Return only top K results (if None, return all sorted)
        
        Returns:
            List of (text, similarity_score) tuples, sorted by similarity DESC
        """
        query_emb = self.embed(query_text, normalize=normalize).embedding
        corpus_batch = self.embed_batch(corpus_texts, normalize=normalize)
        
        # Compute similarities
        similarities = []
        for text, emb in zip(corpus_batch.texts, corpus_batch.embeddings):
            sim = self.cosine_similarity(query_emb, emb)
            similarities.append((text, sim))
        
        # Sort by similarity DESC
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top K if specified
        if top_k:
            similarities = similarities[:top_k]
        
        return similarities
    
    # ============================================================================
    # CACHE MANAGEMENT
    # ============================================================================
    
    def clear_cache(self):
        """Clear embedding cache."""
        self._embedding_cache.clear()
        logger.info("Embedding cache cleared")
    
    def cache_size(self) -> int:
        """Get number of cached embeddings."""
        return len(self._embedding_cache)
