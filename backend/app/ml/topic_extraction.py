"""
Topic Extraction: Extract candidate topics from transcription.

Pipeline:
1. Clean transcription text
2. Extract key phrases (noun phrases, keywords)
3. Cluster similar phrases
4. Rank by frequency and relevance
5. Return top N candidate topics
"""

import logging
from typing import List, Dict, Optional, Set
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import re
from collections import Counter

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class CandidateTopic(BaseModel):
    """Extracted topic from transcription."""
    topic: str
    frequency: int = Field(ge=1)  # How many times mentioned?
    confidence: float = Field(ge=0.0, le=1.0)  # Extraction confidence
    source: str = "transcript"  # Where extracted from


class TopicExtractionResult(BaseModel):
    """Results from topic extraction."""
    session_id: str
    transcript_length: int  # Character count
    candidates: List[CandidateTopic] = []  # Ranked by relevance
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    method: str = "keyword_clustering"  # Extraction method


# ============================================================================
# TOPIC EXTRACTION SERVICE
# ============================================================================

class TopicExtractionService:
    """
    Extract candidate topics from lecture transcription.
    
    Methods:
    1. Keyword extraction (TF-IDF-like)
    2. Phrase extraction (noun phrases, adjective combos)
    3. Clustering (group similar terms)
    4. Ranking (by frequency + relevance)
    
    Privacy: Local processing only, no external APIs.
    """
    
    # Common stopwords (English)
    STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "have", "has", "do", "does", "did", "will", "would", "could", "should",
        "can", "may", "might", "must", "shall", "if", "else", "then", "when",
        "where", "what", "which", "who", "why", "how", "all", "each", "every",
        "both", "either", "neither", "as", "it", "its", "this", "that", "these",
        "those", "i", "you", "he", "she", "we", "they", "me", "him", "her", "us",
        "them", "my", "your", "his", "their", "so", "very", "just", "than",
        "also", "now", "still", "here", "there", "up", "down", "more", "most",
        "less", "few", "many", "some", "any", "no", "not", "only", "even",
    }
    
    # Technical/academic words often not meaningful
    META_WORDS = {
        "say", "said", "tell", "told", "know", "think", "believe", "seem",
        "look", "feel", "get", "got", "give", "given", "make", "made",
        "go", "come", "see", "watch", "hear", "listen", "show", "find",
        "like", "want", "need", "use", "used", "way", "time", "thing",
        "today", "week", "year", "day", "right", "left", "good", "bad",
        "new", "old", "first", "last", "next", "same", "different",
    }
    
    def __init__(self):
        self.stopwords = self.STOPWORDS | self.META_WORDS
        logger.info("Topic extraction service initialized")
    
    # ========================================================================
    # TEXT CLEANING
    # ========================================================================
    
    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean and normalize text."""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove special characters (keep alphanumeric, spaces, hyphens)
        text = re.sub(r'[^a-zA-Z0-9\s\-]', '', text)
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        text = self._clean_text(text).lower()
        tokens = text.split()
        
        # Remove stopwords and very short words
        tokens = [t for t in tokens if t not in self.stopwords and len(t) > 2]
        
        return tokens
    
    # ========================================================================
    # KEYWORD EXTRACTION
    # ========================================================================
    
    def extract_keywords(
        self,
        text: str,
        top_k: int = 20,
        min_frequency: int = 2,
    ) -> Dict[str, int]:
        """
        Extract keywords by frequency.
        
        Args:
            text: Transcription text
            top_k: Return top K keywords
            min_frequency: Minimum appearances
        
        Returns:
            Dict of {keyword: frequency}
        """
        tokens = self._tokenize(text)
        
        # Count frequencies
        word_freq = Counter(tokens)
        
        # Filter by minimum frequency
        keywords = {word: freq for word, freq in word_freq.items() if freq >= min_frequency}
        
        # Sort by frequency and return top K
        keywords = dict(sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:top_k])
        
        return keywords
    
    # ========================================================================
    # PHRASE EXTRACTION (N-GRAMS)
    # ========================================================================
    
    def extract_phrases(
        self,
        text: str,
        n: int = 2,  # Bigrams, trigrams, etc.
        top_k: int = 20,
        min_frequency: int = 1,
    ) -> Dict[str, int]:
        """
        Extract n-grams (multi-word phrases).
        
        Args:
            text: Transcription text
            n: N-gram size (2=bigrams, 3=trigrams)
            top_k: Return top K phrases
            min_frequency: Minimum appearances
        
        Returns:
            Dict of {phrase: frequency}
        """
        tokens = self._tokenize(text)
        
        # Generate n-grams
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = " ".join(tokens[i:i+n])
            ngrams.append(ngram)
        
        # Count frequencies
        ngram_freq = Counter(ngrams)
        
        # Filter by minimum frequency
        phrases = {phrase: freq for phrase, freq in ngram_freq.items() if freq >= min_frequency}
        
        # Sort by frequency and return top K
        phrases = dict(sorted(phrases.items(), key=lambda x: x[1], reverse=True)[:top_k])
        
        return phrases
    
    # ========================================================================
    # TOPIC EXTRACTION (COMBINED)
    # ========================================================================
    
    def extract_topics(
        self,
        transcript: str,
        session_id: str,
        top_k: int = 15,
        include_bigrams: bool = True,
    ) -> TopicExtractionResult:
        """
        Extract candidate topics from transcript.
        
        Combines:
        1. Keywords (single words)
        2. Bigrams (2-word phrases)
        3. Clustering (group synonyms)
        
        Args:
            transcript: Full transcription text
            session_id: Session ID
            top_k: Top K topics to return
            include_bigrams: Include multi-word phrases?
        
        Returns:
            TopicExtractionResult with ranked candidates
        """
        candidates = []
        
        # Extract keywords
        keywords = self.extract_keywords(transcript, top_k=top_k, min_frequency=2)
        for keyword, freq in keywords.items():
            # Normalize confidence by frequency (up to 10 mentions)
            confidence = min(1.0, freq / 10.0)
            candidates.append(CandidateTopic(
                topic=keyword,
                frequency=freq,
                confidence=confidence,
                source="keyword",
            ))
        
        # Extract bigrams if enabled
        if include_bigrams:
            bigrams = self.extract_phrases(transcript, n=2, top_k=top_k, min_frequency=1)
            for bigram, freq in bigrams.items():
                confidence = min(1.0, freq / 5.0)
                candidates.append(CandidateTopic(
                    topic=bigram,
                    frequency=freq,
                    confidence=confidence,
                    source="bigram",
                ))
        
        # Cluster and deduplicate similar topics
        candidates = self._cluster_topics(candidates)
        
        # Sort by confidence * frequency
        candidates.sort(
            key=lambda x: (x.confidence * x.frequency, x.frequency),
            reverse=True
        )
        
        # Keep top K
        candidates = candidates[:top_k]
        
        result = TopicExtractionResult(
            session_id=session_id,
            transcript_length=len(transcript),
            candidates=candidates,
        )
        
        logger.info(
            f"Extracted {len(candidates)} topics from {len(transcript)} chars",
            extra={"session_id": session_id}
        )
        
        return result
    
    # ========================================================================
    # TOPIC CLUSTERING
    # ========================================================================
    
    def _cluster_topics(self, candidates: List[CandidateTopic]) -> List[CandidateTopic]:
        """
        Cluster similar topics (e.g., "machine learning" and "ML").
        
        Returns deduplicated list with merged frequencies.
        """
        # Simple deduplication: if topic is substring of another, merge
        merged = {}
        
        for candidate in candidates:
            topic_lower = candidate.topic.lower()
            
            # Check if this is a substring of an existing topic
            found_parent = False
            for existing in merged.keys():
                if topic_lower in existing or existing in topic_lower:
                    # Merge: keep longer/higher confidence
                    if len(existing) >= len(topic_lower):
                        merged[existing].frequency += candidate.frequency
                    else:
                        # Replace with longer one
                        old_candidate = merged.pop(existing)
                        merged[topic_lower] = CandidateTopic(
                            topic=candidate.topic,
                            frequency=candidate.frequency + old_candidate.frequency,
                            confidence=max(candidate.confidence, old_candidate.confidence),
                            source="merged",
                        )
                    found_parent = True
                    break
            
            if not found_parent:
                merged[topic_lower] = candidate
        
        return list(merged.values())
    
    # ========================================================================
    # TOPIC FILTERING
    # ========================================================================
    
    def filter_topics_by_confidence(
        self,
        topics: TopicExtractionResult,
        min_confidence: float = 0.5,
    ) -> TopicExtractionResult:
        """Filter topics by minimum confidence threshold."""
        filtered = [t for t in topics.candidates if t.confidence >= min_confidence]
        topics.candidates = filtered
        return topics
    
    def filter_topics_by_frequency(
        self,
        topics: TopicExtractionResult,
        min_frequency: int = 2,
    ) -> TopicExtractionResult:
        """Filter topics by minimum frequency."""
        filtered = [t for t in topics.candidates if t.frequency >= min_frequency]
        topics.candidates = filtered
        return topics
