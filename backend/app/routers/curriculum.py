# ScholarLab/backend/app/routers/curriculum.py
"""
Curriculum Router
==================
Manages the curriculum knowledge graph lifecycle, including the session-close
workflow that synchronises a physical lecture with the directed curriculum graph.

Endpoint:
    POST /api/curriculum/session/close
        — Atomically marks covered nodes as "completed"
        — Fires a BackgroundTask to re-evaluate absent student risk features

Node ID format note:
    Frontend generates node IDs as plain strings (e.g. "node-1", "node-1746123456789").
    They are stored in MongoDB under the `curriculum` collection as the value of the
    `node_id` field (NOT as the BSON _id), so no ObjectId casting is needed.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app.database import (
    attendance_collection,
    curriculum_collection,
    users_collection,
)
from app.schemas import RoleEnum
from app.security import require_role

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Curriculum Knowledge Graph"])


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class SessionCloseRequest(BaseModel):
    """
    Payload sent by the faculty when closing a session.

    ``node_ids`` — the string IDs of curriculum nodes that were taught during
    this session, as selected by the faculty in the SessionCloseModal graph checklist.
    """

    session_id: str = Field(..., description="The live session being closed")
    node_ids: List[str] = Field(
        ...,
        min_length=0,
        description="IDs of curriculum nodes covered during this session",
    )
    graph_id: Optional[str] = Field(
        None,
        description="Optional: parent curriculum graph ID, for context only",
    )


class SessionCloseResponse(BaseModel):
    """Immediate response returned before the background task completes."""

    session_id: str
    nodes_completed: int = Field(
        description="Number of curriculum nodes atomically marked as completed"
    )
    absent_students: int = Field(
        description="Number of students whose risk features will be updated async"
    )
    background_task_id: str = Field(
        description="UUID for tracing the async risk-feature recomputation task"
    )


# ---------------------------------------------------------------------------
# Background Task: re-evaluate absent student risk features
# ---------------------------------------------------------------------------

async def _update_absent_student_risk_features(
    absent_user_ids: List[str],
    node_ids: List[str],
    session_id: str,
    task_id: str,
) -> None:
    """
    Asynchronously updates the XGBoost feature cache for each absent student.

    Impact model:
        - curriculum_engagement_score  decreases by 0.5 per missed node (floor 0.0)
        - biometric_failures           increments by 1 (student wasn't present to
                                       authenticate, which the model treats as a
                                       biometric signal absence)

    These values are written to ``users_collection`` under a ``risk_features``
    sub-document and are picked up by ``extract_student_features()`` in
    ``routers/analytics.py`` on the next inference call.
    """
    logger.info(
        "[BG task_id=%s] Starting risk feature update for %d absent students "
        "(session=%s, nodes=%d)",
        task_id,
        len(absent_user_ids),
        session_id,
        len(node_ids),
    )

    engagement_penalty = 0.5 * len(node_ids)

    for user_id in absent_user_ids:
        try:
            # Fetch current cached features (or defaults)
            user = await users_collection.find_one({"_id": user_id}) or {}
            existing_features: dict = user.get("risk_features", {})

            current_engagement: float = existing_features.get(
                "curriculum_engagement_score", 6.5
            )
            current_failures: int = existing_features.get("biometric_failures", 0)

            new_engagement = max(0.0, current_engagement - engagement_penalty)
            new_failures = current_failures + 1

            await users_collection.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "risk_features.curriculum_engagement_score": new_engagement,
                        "risk_features.biometric_failures": new_failures,
                        "risk_features.last_updated": datetime.now(timezone.utc).isoformat(),
                        "risk_features.last_missed_session": session_id,
                    }
                },
                upsert=True,
            )

            logger.debug(
                "[BG task_id=%s] Updated user=%s: engagement %.2f→%.2f, failures %d→%d",
                task_id,
                user_id,
                current_engagement,
                new_engagement,
                current_failures,
                new_failures,
            )

        except Exception as exc:  # noqa: BLE001
            # Non-fatal: log and move on — never block other students' updates
            logger.error(
                "[BG task_id=%s] Failed to update risk features for user=%s: %s",
                task_id,
                user_id,
                exc,
            )

    logger.info(
        "[BG task_id=%s] Completed risk feature update for session=%s",
        task_id,
        session_id,
    )


# ---------------------------------------------------------------------------
# Endpoint: POST /api/curriculum/session/close
# ---------------------------------------------------------------------------

@router.post(
    "/session/close",
    response_model=SessionCloseResponse,
    summary="Close a session and sync curriculum coverage",
)
async def close_session_and_sync_curriculum(
    payload: SessionCloseRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin])),
) -> SessionCloseResponse:
    """
    Called by the faculty when a lecture session ends.

    **Immediate (blocking) operations:**
    1. Atomically update all specified ``node_ids`` in ``curriculum_collection``
       to ``status = "completed"`` with a ``completed_at`` timestamp.

    **Asynchronous (non-blocking) operation:**
    2. Identify absent students (those who did NOT submit a verified attendance
       record for this ``session_id``).
    3. Enqueue a ``BackgroundTask`` to decrement their ``curriculum_engagement_score``
       and increment ``biometric_failures`` in their risk feature cache.

    Returns immediately after the DB write and task enqueue — the background
    task runs after the HTTP response is sent.
    """
    faculty_id = str(current_user["_id"])
    task_id = str(uuid.uuid4())

    logger.info(
        "Session close request: faculty=%s  session=%s  nodes=%s",
        faculty_id,
        payload.session_id,
        payload.node_ids,
    )

    # ------------------------------------------------------------------
    # STEP 1: Atomically mark covered nodes as "completed"
    # ------------------------------------------------------------------
    nodes_completed = 0

    if payload.node_ids:
        now_iso = datetime.now(timezone.utc).isoformat()

        # Nodes are stored with their frontend string ID in a `node_id` field.
        # We also try matching against the MongoDB _id field in case nodes were
        # inserted directly (e.g. from the curriculum builder saving to backend).
        update_result = await curriculum_collection.update_many(
            {
                "$or": [
                    {"node_id": {"$in": payload.node_ids}},
                    {"_id": {"$in": payload.node_ids}},
                ]
            },
            {
                "$set": {
                    "status": "completed",
                    "completed_at": now_iso,
                    "completed_by_session": payload.session_id,
                    "completed_by_faculty": faculty_id,
                }
            },
        )
        nodes_completed = update_result.modified_count

        logger.info(
            "Marked %d nodes as completed for session=%s",
            nodes_completed,
            payload.session_id,
        )

    # ------------------------------------------------------------------
    # STEP 2: Identify absent students
    # ------------------------------------------------------------------
    try:
        # All students in the platform
        all_students = await users_collection.find(
            {"role": "student"},
            {"_id": 1},
        ).to_list(None)
        all_student_ids = {str(s["_id"]) for s in all_students}

        # Students who verified attendance for this session
        attended_records = await attendance_collection.find(
            {"session_id": payload.session_id, "status": "verified"},
            {"user_id": 1},
        ).to_list(None)
        attended_ids = {r["user_id"] for r in attended_records}

        # Set difference = absent
        absent_ids = list(all_student_ids - attended_ids)

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to compute absent students for session=%s: %s",
            payload.session_id,
            exc,
        )
        absent_ids = []

    # ------------------------------------------------------------------
    # STEP 3: Enqueue background risk feature update (non-blocking)
    # ------------------------------------------------------------------
    if absent_ids and payload.node_ids:
        background_tasks.add_task(
            _update_absent_student_risk_features,
            absent_user_ids=absent_ids,
            node_ids=payload.node_ids,
            session_id=payload.session_id,
            task_id=task_id,
        )
        logger.info(
            "Enqueued risk update task=%s for %d absent students",
            task_id,
            len(absent_ids),
        )

    return SessionCloseResponse(
        session_id=payload.session_id,
        nodes_completed=nodes_completed,
        absent_students=len(absent_ids),
        background_task_id=task_id,
    )
