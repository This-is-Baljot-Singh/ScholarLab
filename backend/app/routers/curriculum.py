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

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.database import (
    attendance_collection,
    curriculum_collection,
    users_collection,
)
from app.schemas import RoleEnum
from app.security import require_role
from app.utils.minio_client import MINIO_BUCKET, ensure_bucket_exists, get_minio_client
from app.services.verification_agent import VerificationAgent, VerificationStatus, VerificationTask
from app.services.syllabus_matcher import SyllabusNodeMatch
from app.database import db as motor_db, sessions_collection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Curriculum Knowledge Graph"])

# Provision the audio bucket once when this module is first imported.
# Uses a best-effort approach: failure is logged but does not prevent startup
# so the backend remains available even if MinIO is temporarily unreachable.
try:
    ensure_bucket_exists(MINIO_BUCKET)
except Exception as _bucket_err:  # noqa: BLE001
    logger.warning(
        "Could not provision MinIO bucket '%s' at startup: %s — "
        "audio upload endpoint will fail until MinIO is reachable.",
        MINIO_BUCKET,
        _bucket_err,
    )


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class AudioUploadResponse(BaseModel):
    """Response returned after a successful audio upload to MinIO."""

    object_key: str = Field(description="MinIO object key for downstream Celery task")
    bucket: str = Field(description="MinIO bucket the object was stored in")
    session_id: str
    size_bytes: int = Field(description="Number of bytes received and stored")


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


class CurriculumGraphSchema(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    nodes: List[dict]
    edges: List[dict]
    createdAt: str
    updatedAt: str


class VerifyActionRequest(BaseModel):
    action: str  # "approve" | "reject" | "correct"
    notes: Optional[str] = None
    corrected_node_id: Optional[str] = None
    corrected_node_title: Optional[str] = None


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
    task_id = "async-risk-recompute-" + payload.session_id
    if absent_ids and payload.node_ids:
        background_tasks.add_task(
            _update_absent_student_risk_features,
            absent_user_ids=absent_ids,
            node_ids=payload.node_ids,
            session_id=payload.session_id,
            task_id=task_id,
        )

    # Mark session as completed in DB
    await sessions_collection.update_one(
        {"id": payload.session_id},
        {"$set": {"status": "completed", "endTime": datetime.now(timezone.utc).isoformat()}}
    )

    return SessionCloseResponse(
        session_id=payload.session_id,
        nodes_completed=nodes_completed,
        absent_students=len(absent_ids),
        background_task_id=task_id,
    )


# ---------------------------------------------------------------------------
# Endpoint: POST /api/curriculum/audio/upload
# ---------------------------------------------------------------------------

@router.post(
    "/audio/upload",
    response_model=AudioUploadResponse,
    summary="Stream classroom audio directly to on-premises MinIO",
)
async def upload_audio_to_minio(
    session_id: str,
    audio: UploadFile = File(..., description="Raw classroom audio file (WAV/MP3/M4A)"),
    current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin])),
) -> AudioUploadResponse:
    """
    Accepts an audio file upload and streams it **directly** to the campus-hosted
    MinIO bucket without writing to the local filesystem (no ``/tmp`` touch).

    **Privacy guarantee**: the audio never leaves the campus trust boundary —
    MinIO runs inside the Docker ``backend`` network with no public internet
    egress. Raw audio is stored ephemerally; the Celery worker deletes the
    object from MinIO immediately after successful transcription.

    Returns an ``object_key`` for the caller to pass to the Celery
    ``curriculum_pipeline`` task.
    """
    faculty_id = str(current_user["_id"])

    # Deterministic, collision-resistant key:  <session>/<uuid>.<ext>
    suffix = (audio.filename or "audio").rsplit(".", 1)[-1].lower()
    object_key = f"{session_id}/{uuid.uuid4()}.{suffix}"

    logger.info(
        "Audio upload: faculty=%s session=%s key=%s content_type=%s",
        faculty_id,
        session_id,
        object_key,
        audio.content_type,
    )

    try:
        s3 = get_minio_client()

        # Stream the upload directly from the request body into MinIO.
        # audio.file is a SpooledTemporaryFile backed by the FastAPI UploadFile;
        # we never call .read() to avoid materialising the whole file in RAM.
        s3.upload_fileobj(
            audio.file,
            MINIO_BUCKET,
            object_key,
            ExtraArgs={"ContentType": audio.content_type or "application/octet-stream"},
        )

        # Retrieve stored size for the response (head_object is cheap)
        head = s3.head_object(Bucket=MINIO_BUCKET, Key=object_key)
        size_bytes: int = head.get("ContentLength", 0)

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "MinIO upload failed for session=%s key=%s: %s",
            session_id,
            object_key,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                f"Audio storage unavailable: could not write to MinIO bucket "
                f"'{MINIO_BUCKET}'. Ensure the MinIO service is running within the "
                "campus network."
            ),
        ) from exc

    logger.info(
        "Audio stored in MinIO: key=%s size=%d bytes",
        object_key,
        size_bytes,
    )

    return AudioUploadResponse(
        object_key=object_key,
        bucket=MINIO_BUCKET,
        session_id=session_id,
        size_bytes=size_bytes,
    )


# ---------------------------------------------------------------------------
# Curriculum Graph Management
# ---------------------------------------------------------------------------

@router.get("/graphs", response_model=List[dict])
async def list_curriculum_graphs(
    current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin])),
):
    """Returns all stored curriculum knowledge graphs."""
    # Note: frontend expects 'id' instead of '_id'
    cursor = curriculum_collection.find({})
    graphs = await cursor.to_list(length=100)
    for g in graphs:
        g["id"] = str(g.pop("_id"))
    return graphs


@router.post("/graph")
async def save_curriculum_graph(
    graph: dict,
    current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin])),
):
    """Saves or updates a curriculum knowledge graph."""
    graph_id = graph.get("id")
    if not graph_id:
        raise HTTPException(status_code=400, detail="Graph ID is required")

    # Upsert by graph_id (our custom ID, not BSON _id)
    await curriculum_collection.update_one(
        {"id": graph_id},
        {"$set": graph},
        upsert=True
    )
    return {"message": "Graph synchronized successfully", "id": graph_id}


# ---------------------------------------------------------------------------
# Curriculum Verification Queue
# ---------------------------------------------------------------------------

@router.get("/verification-queue", response_model=List[VerificationTask])
async def get_verification_queue(
    course_id: Optional[str] = None,
    current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin])),
):
    """Returns the list of pending manual-review tasks for the curriculum pipeline."""
    agent = VerificationAgent(motor_db)
    # We don't filter by faculty_id here as any faculty can review for now
    tasks = await agent.get_pending_tasks(course_id=course_id)
    return tasks


@router.post("/verify/{task_id}")
async def process_verification_decision(
    task_id: str,
    payload: VerifyActionRequest,
    current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin])),
):
    """Faculty decision (approve/reject/correct) for a low-confidence mapping."""
    agent = VerificationAgent(motor_db)
    faculty_id = str(current_user["_id"])

    try:
        if payload.action == "approve":
            result = await agent.approve_mapping(task_id, faculty_id, payload.notes)
        elif payload.action == "reject":
            result = await agent.reject_mapping(task_id, faculty_id, payload.notes)
        elif payload.action == "correct":
            if not payload.corrected_node_id or not payload.corrected_node_title:
                raise HTTPException(status_code=400, detail="Corrected node details required for 'correct' action")
            result = await agent.correct_mapping(
                task_id, 
                payload.corrected_node_id, 
                payload.corrected_node_title, 
                faculty_id, 
                payload.notes
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {payload.action}")
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sessions/{session_id}/process-audio")
async def process_lecture_audio_trigger(
    session_id: str,
    course_id: str,
    audio: UploadFile = File(...),
    current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin])),
):
    """
    Combines upload + pipeline trigger.
    Uploads audio to MinIO and immediately enqueues the Celery curriculum_pipeline.
    """
    # 1. Upload to MinIO (reuse existing logic)
    upload_result = await upload_audio_to_minio(session_id, audio, current_user)
    
    # 2. Trigger Celery pipeline
    from app.jobs.celery_app import curriculum_pipeline
    task = curriculum_pipeline.delay(
        session_id=session_id,
        course_id=course_id,
        minio_object_key=upload_result.object_key,
        minio_bucket=upload_result.bucket
    )
    
    return {
        "message": "Audio uploaded and processing pipeline started",
        "task_id": task.id,
        "object_key": upload_result.object_key,
        "privacy_mode": "local-only (Ollama/MinIO)"
    }


# ---------------------------------------------------------------------------
# Session Life-cycle
# ---------------------------------------------------------------------------

@router.post("/sessions", response_model=dict)
async def start_lecture_session(
    payload: dict,
    current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin])),
):
    """Initializes a new live lecture session."""
    session_id = f"session-{int(datetime.now(timezone.utc).timestamp())}"
    
    new_session = {
        "id": session_id,
        "lectureId": payload.get("lectureId"),
        "currentCurriculumNodeId": payload.get("curriculumNodeId"),
        "geofenceId": payload.get("geofenceId"),
        "facultyId": str(current_user["_id"]),
        "startTime": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "attendanceCount": 0
    }
    
    await sessions_collection.insert_one(new_session)
    return new_session


@router.get("/sessions/active", response_model=List[dict])
async def list_active_sessions(
    current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin])),
):
    """Returns all currently active lecture sessions."""
    cursor = sessions_collection.find({"status": "active"})
    sessions = await cursor.to_list(length=100)
    for s in sessions:
        s.pop("_id", None)
    return sessions
@router.get("/resources/{session_id}", response_model=List[dict])
async def get_session_resources(
    session_id: str,
    current_user: dict = Depends(require_role([RoleEnum.student, RoleEnum.faculty, RoleEnum.admin])),
):
    """
    Returns curriculum resources unlocked by a specific session.
    Mock implementation for frontend demo.
    """
    # For now, return mock resources if session matches our demo session
    if session_id == "session_67890":
        return [
            {
                "id": "res_1",
                "title": "Data Structures - Part 1: Linked Lists",
                "type": "pdf",
                "description": "Comprehensive guide to singly and doubly linked lists with implementation details.",
                "unlockedAt": datetime.now(timezone.utc).isoformat(),
                "url": "/curriculum/ds-linked-lists.pdf",
                "metadata": {"pages": 12}
            },
            {
                "id": "res_2",
                "title": "Visualising Algorithm Complexity",
                "type": "video",
                "description": "A 10-minute deep dive into Big O notation and common complexity classes.",
                "unlockedAt": datetime.now(timezone.utc).isoformat(),
                "url": "https://example.com/complexity-viz",
                "metadata": {"duration": 10}
            }
        ]
    return []


@router.get("/unlocked", response_model=List[dict])
async def get_all_unlocked_resources(
    current_user: dict = Depends(require_role([RoleEnum.student, RoleEnum.faculty, RoleEnum.admin])),
):
    """
    Returns all curriculum resources unlocked for the current student.
    Mock implementation for frontend demo.
    """
    # Return a collection of mock resources
    return [
        {
            "id": "res_1",
            "title": "Data Structures - Part 1: Linked Lists",
            "type": "pdf",
            "description": "Comprehensive guide to singly and doubly linked lists with implementation details.",
            "unlockedAt": datetime.now(timezone.utc).isoformat(),
            "url": "/curriculum/ds-linked-lists.pdf",
            "metadata": {"pages": 12}
        },
        {
            "id": "res_2",
            "title": "Visualising Algorithm Complexity",
            "type": "video",
            "description": "A 10-minute deep dive into Big O notation and common complexity classes.",
            "unlockedAt": datetime.now(timezone.utc).isoformat(),
            "url": "https://example.com/complexity-viz",
            "metadata": {"duration": 10}
        },
        {
            "id": "res_3",
            "title": "Intro to Binary Trees",
            "type": "slides",
            "description": "Foundational concepts for hierarchical data structures.",
            "unlockedAt": (datetime.now(timezone.utc)).isoformat(),
            "url": "/curriculum/binary-trees.pdf",
            "metadata": {"pages": 45}
        }
    ]
