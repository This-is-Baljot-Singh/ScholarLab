# ScholarLab/backend/app/services/curriculum_engine.py
from app.database import db
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

# Initialize collections
curriculum_graph = db["curriculum_nodes"]
student_progress = db["student_progress"]

async def process_curriculum_unlocks(user_id: str, session_id: str) -> list:
    """
    Traverses the knowledge graph to unlock materials tied to a specific session,
    ensuring all prerequisites are met.
    """
    unlocked_items = []
    
    # 1. Fetch all curriculum nodes linked to this attendance session
    # (In a real scenario, faculty maps session_ids to node_ids during creation)
    potential_nodes = await curriculum_graph.find({"target_session_id": session_id}).to_list(length=100)
    
    if not potential_nodes:
        # Mock behavior for Sprint 3 development: Generate a synthetic node if none exist
        mock_node = {
            "_id": ObjectId(),
            "title": "Advanced Cryptography Notes (Synthetic)",
            "type": "pdf",
            "url": "https://example.com/notes.pdf",
            "target_session_id": session_id,
            "prerequisites": []
        }
        await curriculum_graph.insert_one(mock_node)
        potential_nodes = [mock_node]

    # 2. Fetch student's current progress
    progress_record = await student_progress.find_one({"user_id": user_id})
    if not progress_record:
        progress_record = {"user_id": user_id, "unlocked_node_ids": []}
        await student_progress.insert_one(progress_record)
        
    previously_unlocked = set(progress_record.get("unlocked_node_ids", []))

    # 3. Graph Traversal: Verify Prerequisites
    newly_unlocked_ids = []
    
    for node in potential_nodes:
        node_id_str = str(node["_id"])
        if node_id_str in previously_unlocked:
            continue # Already unlocked
            
        prereqs = set(node.get("prerequisites", []))
        
        # If prereqs is a subset of previously unlocked, or it has no prereqs
        if prereqs.issubset(previously_unlocked):
            newly_unlocked_ids.append(node_id_str)
            unlocked_items.append({
                "id": node_id_str,
                "title": node.get("title", "Lecture Resource"),
                "type": node.get("type", "document"),
                "url": node.get("url", "#")
            })

    # 4. Save new state to database
    if newly_unlocked_ids:
        await student_progress.update_one(
            {"user_id": user_id},
            {"$addToSet": {"unlocked_node_ids": {"$each": newly_unlocked_ids}}}
        )
        logger.info(f"Unlocked {len(newly_unlocked_ids)} nodes for user {user_id}")

    return unlocked_items