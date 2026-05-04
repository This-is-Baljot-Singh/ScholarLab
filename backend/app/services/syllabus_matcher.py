"""
Syllabus Matching Agent: Map topics to curriculum nodes using embeddings.

Pipeline:
1. Load curriculum syllabus tree (MongoDB)
2. Generate embeddings for all syllabus nodes
3. For each extracted topic, find closest syllabus nodes
4. Score using cosine similarity: s_j = cos(E(T_t), e_j)
5. Filter by confidence threshold δ
6. Return scored mappings (ready for verification)

Formula:
  s_j = cos(E(T_t), e_j) = (E(T_t) · e_j) / (||E(T_t)|| * ||e_j||)
  
Where:
  - E(T_t) = embedding of topic T_t from transcription
  - e_j = embedding of curriculum node j
  - s_j ∈ [0, 1] = similarity score
"""

import logging
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId

from app.ml.embeddings import LocalEmbeddingsService
from app.ml.topic_extraction import CandidateTopic

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class SyllabusNodeMatch(BaseModel):
    """Match between topic and syllabus node."""
    topic: str
    topic_confidence: float  # From extraction
    curriculum_node_id: str
    node_title: str
    node_description: Optional[str] = None
    similarity_score: float = Field(ge=0.0, le=1.0)  # Cosine similarity s_j
    rank: int = Field(ge=1)  # Rank among all matches for this topic


class TopicMappingResult(BaseModel):
    """Results of matching extracted topics to syllabus."""
    session_id: str
    course_id: str
    extracted_topics_count: int
    mapped_topics_count: int
    total_matches: int
    matches: List[SyllabusNodeMatch] = []
    below_threshold_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_threshold: float  # δ (delta)


class SyllabusNode(BaseModel):
    """Curriculum node for matching (flattened from tree)."""
    node_id: str
    course_id: str
    title: str
    description: Optional[str] = None
    embedding: Optional[List[float]] = None  # Will be cached
    path: str = ""  # Full path in tree (e.g., "Module 1 > Topic A > Subtopic B")
    level: int = 0  # Depth in tree


# ============================================================================
# SYLLABUS MATCHING AGENT
# ============================================================================

class SyllabusMatchingAgent:
    """
    Maps extracted topics to curriculum nodes using embeddings.
    
    Workflow:
    1. Extract candidate topics from transcription
    2. Load curriculum syllabus tree from DB
    3. Compute embeddings for all nodes (cached)
    4. For each topic, find K-nearest neighbors using cosine similarity
    5. Score matches: s_j = cos(E(topic), E(node))
    6. Filter by confidence threshold δ
    7. Flag below-threshold for manual verification
    """
    
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        embeddings_service: LocalEmbeddingsService,
        confidence_threshold: float = 0.6,  # δ (delta)
    ):
        self.db = db
        self.embeddings_svc = embeddings_service
        self.confidence_threshold = confidence_threshold
        
        # Database collections
        self.mappings_col: AsyncIOMotorCollection = db["curriculum_topic_mappings"]
        self.syllabus_nodes_col: AsyncIOMotorCollection = db["curriculum_nodes"]
        self.embedding_cache_col: AsyncIOMotorCollection = db["curriculum_node_embeddings_cache"]
    
    async def initialize(self):
        """Setup collection indexes."""
        await self.mappings_col.create_index("session_id")
        await self.mappings_col.create_index("course_id")
        await self.mappings_col.create_index("topic")
        await self.mappings_col.create_index("created_at")
        
        await self.embedding_cache_col.create_index("node_id", unique=True)
        await self.embedding_cache_col.create_index("course_id")
        
        logger.info("Syllabus matching agent initialized")
    
    # ========================================================================
    # SYLLABUS LOADING
    # ========================================================================
    
    async def _load_curriculum_tree(self, course_id: str) -> List[SyllabusNode]:
        """
        Load curriculum syllabus tree from DB.
        
        Flattens tree structure into list of nodes with paths.
        
        Args:
            course_id: Course ID
        
        Returns:
            List of SyllabusNode objects
        """
        # Query all nodes for this course
        cursor = self.syllabus_nodes_col.find({"course_id": course_id})
        nodes_raw = await cursor.to_list(length=1000)
        
        # Convert to SyllabusNode objects
        nodes = []
        for node_doc in nodes_raw:
            node = SyllabusNode(
                node_id=str(node_doc.get("_id", "")),
                course_id=course_id,
                title=node_doc.get("title", ""),
                description=node_doc.get("description", ""),
                path=node_doc.get("path", ""),
                level=node_doc.get("level", 0),
            )
            nodes.append(node)
        
        logger.info(f"Loaded {len(nodes)} curriculum nodes for {course_id}")
        return nodes
    
    # ========================================================================
    # EMBEDDING COMPUTATION & CACHING
    # ========================================================================
    
    async def _get_node_embedding(self, node: SyllabusNode) -> List[float]:
        """
        Get embedding for syllabus node (with caching).
        
        Args:
            node: SyllabusNode
        
        Returns:
            Dense embedding vector
        """
        # Check cache first
        cached = await self.embedding_cache_col.find_one({"node_id": node.node_id})
        if cached:
            return cached["embedding"]
        
        # Compute embedding from title + description
        text_to_embed = f"{node.title}. {node.description or ''}"
        embedding_obj = self.embeddings_svc.embed(text_to_embed, normalize=True)
        
        # Cache it
        await self.embedding_cache_col.insert_one({
            "_id": ObjectId(),
            "node_id": node.node_id,
            "course_id": node.course_id,
            "embedding": embedding_obj.embedding,
            "cached_at": datetime.now(timezone.utc),
        })
        
        return embedding_obj.embedding
    
    async def _precompute_node_embeddings(self, nodes: List[SyllabusNode]):
        """Precompute embeddings for all nodes in batch."""
        node_texts = [f"{n.title}. {n.description or ''}" for n in nodes]
        batch_result = self.embeddings_svc.embed_batch(
            node_texts,
            normalize=True,
            batch_size=32,
        )
        
        # Cache all embeddings
        for node, embedding in zip(nodes, batch_result.embeddings):
            existing = await self.embedding_cache_col.find_one({"node_id": node.node_id})
            if not existing:
                await self.embedding_cache_col.insert_one({
                    "_id": ObjectId(),
                    "node_id": node.node_id,
                    "course_id": node.course_id,
                    "embedding": embedding,
                    "cached_at": datetime.now(timezone.utc),
                })
        
        logger.info(f"Precomputed embeddings for {len(nodes)} nodes")
    
    # ========================================================================
    # TOPIC-TO-NODE MATCHING
    # ========================================================================
    
    async def match_topics_to_nodes(
        self,
        session_id: str,
        course_id: str,
        topics: List[CandidateTopic],
        top_k_matches: int = 3,
    ) -> TopicMappingResult:
        """
        Match extracted topics to curriculum nodes using cosine similarity.
        
        Formula: s_j = cos(E(T_t), e_j)
        
        Args:
            session_id: Lecture session ID
            course_id: Course ID
            topics: Extracted candidate topics
            top_k_matches: Return top K matches per topic
        
        Returns:
            TopicMappingResult with all scored mappings
        """
        # Load curriculum tree
        syllabus_nodes = await self._load_curriculum_tree(course_id)
        
        if not syllabus_nodes:
            logger.warning(f"No curriculum nodes found for {course_id}")
            return TopicMappingResult(
                session_id=session_id,
                course_id=course_id,
                extracted_topics_count=len(topics),
                mapped_topics_count=0,
                total_matches=0,
                confidence_threshold=self.confidence_threshold,
            )
        
        # Precompute all node embeddings
        await self._precompute_node_embeddings(syllabus_nodes)
        
        # For each topic, find closest nodes
        all_matches = []
        below_threshold_count = 0
        
        for topic in topics:
            # Embed the topic
            topic_emb_obj = self.embeddings_svc.embed(topic.topic, normalize=True)
            topic_embedding = topic_emb_obj.embedding
            
            # Score against all syllabus nodes
            scores = []
            for node in syllabus_nodes:
                node_embedding = await self._get_node_embedding(node)
                
                # Compute cosine similarity: s_j = cos(E(T_t), e_j)
                similarity = self.embeddings_svc.cosine_similarity(
                    topic_embedding,
                    node_embedding,
                )
                
                scores.append((node, similarity))
            
            # Sort by similarity (descending) and get top K
            scores.sort(key=lambda x: x[1], reverse=True)
            top_scores = scores[:top_k_matches]
            
            # Create match objects
            for rank, (node, similarity) in enumerate(top_scores, start=1):
                match = SyllabusNodeMatch(
                    topic=topic.topic,
                    topic_confidence=topic.confidence,
                    curriculum_node_id=node.node_id,
                    node_title=node.title,
                    node_description=node.description,
                    similarity_score=similarity,  # s_j
                    rank=rank,
                )
                all_matches.append(match)
                
                # Track below-threshold
                if similarity < self.confidence_threshold:
                    below_threshold_count += 1
        
        # Build result
        result = TopicMappingResult(
            session_id=session_id,
            course_id=course_id,
            extracted_topics_count=len(topics),
            mapped_topics_count=len([m for m in all_matches if m.rank == 1]),
            total_matches=len(all_matches),
            matches=all_matches,
            below_threshold_count=below_threshold_count,
            confidence_threshold=self.confidence_threshold,
        )
        
        # Store in DB
        doc = result.dict()
        doc["_id"] = ObjectId()
        await self.mappings_col.insert_one(doc)
        
        logger.info(
            f"Topic matching complete: {len(all_matches)} matches, {below_threshold_count} below threshold",
            extra={
                "session_id": session_id,
                "course_id": course_id,
                "confidence_threshold": self.confidence_threshold,
            }
        )
        
        return result
    
    # ========================================================================
    # FILTERING BY THRESHOLD
    # ========================================================================
    
    def filter_by_confidence(
        self,
        mapping_result: TopicMappingResult,
        threshold: Optional[float] = None,
    ) -> Tuple[List[SyllabusNodeMatch], List[SyllabusNodeMatch]]:
        """
        Split mappings into above/below confidence threshold.
        
        Args:
            mapping_result: Result from match_topics_to_nodes()
            threshold: Override threshold (default: self.confidence_threshold)
        
        Returns:
            Tuple of (above_threshold, below_threshold) matches
        """
        threshold = threshold or self.confidence_threshold
        
        above = [m for m in mapping_result.matches if m.similarity_score >= threshold]
        below = [m for m in mapping_result.matches if m.similarity_score < threshold]
        
        return above, below
    
    # ========================================================================
    # QUERY & ANALYSIS
    # ========================================================================
    
    async def get_mappings_for_session(
        self,
        session_id: str,
    ) -> Optional[TopicMappingResult]:
        """Retrieve stored mapping results for session."""
        doc = await self.mappings_col.find_one({"session_id": session_id})
        if doc:
            doc.pop("_id", None)
            return TopicMappingResult(**doc)
        return None
    
    async def get_matches_by_topic(
        self,
        session_id: str,
        topic: str,
    ) -> List[SyllabusNodeMatch]:
        """Get all matches for a specific topic in a session."""
        mapping = await self.get_mappings_for_session(session_id)
        if mapping:
            return [m for m in mapping.matches if m.topic == topic]
        return []
    
    async def get_below_threshold_matches(
        self,
        session_id: str,
    ) -> List[SyllabusNodeMatch]:
        """Get matches below confidence threshold (need manual verification)."""
        mapping = await self.get_mappings_for_session(session_id)
        if mapping:
            return [
                m for m in mapping.matches
                if m.similarity_score < mapping.confidence_threshold
            ]
        return []
    
    async def get_course_mapping_statistics(self, course_id: str) -> Dict:
        """Get statistics for a course's topic mappings."""
        cursor = self.mappings_col.aggregate([
            {"$match": {"course_id": course_id}},
            {
                "$group": {
                    "_id": "$course_id",
                    "total_sessions": {"$sum": 1},
                    "avg_extracted_topics": {"$avg": "$extracted_topics_count"},
                    "avg_matched_topics": {"$avg": "$mapped_topics_count"},
                    "avg_below_threshold": {"$avg": "$below_threshold_count"},
                }
            },
        ])
        
        result = await cursor.to_list(length=1)
        return result[0] if result else {}
