"""
Background job queue boilerplate: Celery + Redis.

Tasks include:
- Audio transcription (local via Ollama)
- SHAP inference
- Risk score batch computation
- Audit log archival

Run: celery -A app.jobs.celery_app worker --loglevel=info
Run scheduler: celery -A app.jobs.celery_app beat --loglevel=info
"""

from celery import Celery, Task
from celery.result import AsyncResult
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging
import json
import io
import asyncio
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


# ============================================================================
# CELERY APP INITIALIZATION
# ============================================================================

class ContextTask(Task):
    """Task that tracks audit context (actor, request_id)."""
    
    def apply_async(self, *args, **kwargs):
        """Store context in task kwargs."""
        from app.logging.audit import get_actor, get_request_id
        kwargs['actor_id'] = get_actor()
        kwargs['request_id'] = get_request_id()
        return super().apply_async(*args, **kwargs)


def create_celery_app(broker_url: str, result_backend: str) -> Celery:
    """Create and configure Celery app."""
    app = Celery(
        'scholarlab_jobs',
        broker=broker_url,
        backend=result_backend,
    )
    
    app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
    )
    
    app.Task = ContextTask
    return app


# Initialize from config
from app.config.environment import settings
celery_app = create_celery_app(
    broker_url=settings.job_queue.broker_url,
    result_backend=settings.job_queue.result_backend,
)

# Dev fallback: run tasks synchronously if Redis is missing
if settings.environment == "dev":
    import socket
    from urllib.parse import urlparse
    try:
        url = urlparse(settings.job_queue.broker_url)
        host = url.hostname or "localhost"
        port = url.port or 6379
        with socket.create_connection((host, port), timeout=0.5):
            logger.info("✓ Redis broker reachable")
    except (socket.timeout, ConnectionRefusedError, socket.gaierror):
        logger.warning("⚠ Redis unreachable. Enabling Celery 'task_always_eager' mode.")
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True


# ============================================================================
# TASK: AUDIO TRANSCRIPTION
# ============================================================================

@celery_app.task(
    name='tasks.transcribe_audio',
    max_retries=3,
    default_retry_delay=60,
    bind=True,
)
def transcribe_audio(
    self,
    session_id: str,
    audio_file_path: str,
    model: str = "ollama-whisper",
    **context
) -> Dict[str, Any]:
    """
    Transcribe audio locally using Ollama/Whisper.
    
    NEVER upload raw audio to cloud APIs.
    
    Args:
        session_id: Reference to classroom session
        audio_file_path: Local path to audio file
        model: Ollama model name (default: whisper)
        context: {actor_id, request_id} from caller
    
    Returns:
        {
            "session_id": str,
            "transcription": str,
            "confidence": float,
            "model": str,
            "generated_at": datetime,
        }
    """
    try:
        logger.info(f"Transcribing audio for session {session_id}")
        
        # Import here to avoid hard dependency
        try:
            import ollama
        except ImportError:
            logger.error("ollama package not installed. Install with: pip install ollama")
            raise
        
        # Call Ollama locally
        response = ollama.generate(
            model=model,
            prompt=f"Transcribe this audio file: {audio_file_path}",
            stream=False,
        )
        
        transcription = response['response']
        
        # Store result in database
        # (Implementation: write to curriculum_events collection)
        
        result = {
            "session_id": session_id,
            "transcription": transcription,
            "confidence": 0.95,  # Placeholder
            "model": model,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
        }
        
        logger.info(f"✓ Transcription completed for {session_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Transcription failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


# ============================================================================
# TASK: SHAP INFERENCE (Explainability)
# ============================================================================

@celery_app.task(
    name='tasks.compute_risk_with_shap',
    max_retries=2,
    default_retry_delay=120,
    bind=True,
)
def compute_risk_with_shap(
    self,
    user_id: str,
    course_id: str,
    lookback_days: int = 30,
    **context
) -> Dict[str, Any]:
    """
    Compute student risk score with SHAP explainability.
    
    Args:
        user_id: Student ID
        course_id: Course ID
        lookback_days: Historical window
        context: {actor_id, request_id}
    
    Returns:
        {
            "user_id": str,
            "course_id": str,
            "risk_score": float,
            "risk_level": str,
            "shap_values": {feature_name: importance},
            "contributing_factors": [...],
            "model_version": str,
            "generated_at": datetime,
        }
    """
    try:
        logger.info(f"Computing risk score for {user_id} in {course_id}")
        
        # Import here
        try:
            import joblib
            import shap
            import numpy as np
        except ImportError:
            logger.error("Required packages not installed: joblib, shap, numpy")
            raise
        
        # Load trained XGBoost model
        model_path = "/app/ml/models/xgboost_risk_model.joblib"
        try:
            model = joblib.load(model_path)
        except FileNotFoundError:
            logger.error(f"Model not found: {model_path}")
            raise
        
        # Fetch features from database
        # (Implementation: query attendance_events, curriculum_events, etc.)
        features = async_to_sync(fetch_student_features)(user_id, course_id, lookback_days)
        
        # Predict
        X = np.array([features])
        risk_score = float(model.predict_proba(X)[0][1])  # Probability of high risk
        
        # SHAP explainability
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        
        # Format SHAP output
        feature_names = [
            "absence_rate", "engagement_score", "biometric_anomaly",
            "curriculum_gap", "recent_participation"
        ]
        shap_dict = {
            name: float(shap_values[0][i])
            for i, name in enumerate(feature_names)
        }
        
        # Determine risk level
        if risk_score >= 0.8:
            risk_level = "critical"
        elif risk_score >= 0.6:
            risk_level = "high"
        elif risk_score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        result = {
            "user_id": user_id,
            "course_id": course_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "shap_values": shap_dict,
            "contributing_factors": [
                {"name": name, "value": shap_dict[name]}
                for name in sorted(shap_dict.keys(), key=lambda k: abs(shap_dict[k]), reverse=True)[:3]
            ],
            "model_version": "xgboost_v1.3",
            "formula_version": "2.1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
        }
        
        # Store result in database
        # (Implementation: write to risk_events collection)
        
        logger.info(f"✓ Risk score computed: {user_id} = {risk_score:.2f}")
        return result
        
    except Exception as exc:
        logger.error(f"SHAP inference failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


# ============================================================================
# TASK: BATCH RISK COMPUTATION
# ============================================================================

@celery_app.task(
    name='tasks.batch_compute_risk',
    max_retries=1,
    bind=True,
)
def batch_compute_risk(
    self,
    course_id: str,
    **context
) -> Dict[str, Any]:
    """
    Compute risk scores for all students in a course.
    
    Called daily as scheduled task.
    """
    try:
        logger.info(f"Starting batch risk computation for {course_id}")
        
        # Fetch all enrolled students (from database)
        # for each student: call compute_risk_with_shap as subtask
        
        result = {
            "course_id": course_id,
            "students_processed": 0,
            "errors": 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        logger.info(f"✓ Batch computation completed for {course_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Batch computation failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


# ============================================================================
# TASK: AUDIT LOG ARCHIVAL
# ============================================================================

@celery_app.task(
    name='tasks.archive_audit_logs',
    max_retries=1,
)
def archive_audit_logs(days_old: int = 90) -> Dict[str, Any]:
    """
    Archive old audit logs to cold storage.
    
    Called weekly.
    """
    try:
        logger.info(f"Archiving audit logs older than {days_old} days")
        
        # Query audit_logs older than threshold
        # Compress and move to S3/GCS
        # Delete from MongoDB
        
        result = {
            "archived_count": 0,
            "archive_location": "s3://scholarlab-audit/2026-05/",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        logger.info(f"✓ Archived {result['archived_count']} audit logs")
        return result
        
    except Exception as exc:
        logger.error(f"Audit archival failed: {exc}", exc_info=True)
        raise


# ============================================================================
# TASK: CURRICULUM PIPELINE (Audio → Topics → Mappings → Unlock)
# ============================================================================

@celery_app.task(
    name='tasks.curriculum_pipeline',
    max_retries=3,
    default_retry_delay=60,
    bind=True,
)
def curriculum_pipeline(
    self,
    session_id: str,
    course_id: str,
    minio_object_key: str,
    minio_bucket: str = "scholarlab-audio",
    **context
) -> Dict[str, Any]:
    """
    Full curriculum pipeline: MinIO audio → BytesIO → Transcription → Topic
    Extraction → Syllabus Matching.

    PRIVACY: NO cloud APIs. NO disk writes. All audio processing is local.

    Args:
        session_id: Classroom session ID
        course_id: Course ID
        minio_object_key: Object key in the campus MinIO bucket (returned by
                          POST /api/curriculum/audio/upload)
        minio_bucket: MinIO bucket name (default: scholarlab-audio)
        context: {actor_id, request_id}

    Returns:
        {
            "session_id": str,
            "stage": "completed" | "verification_needed",
            "topics_extracted": int,
            "mapped_topics": int,
            "below_threshold": int,
            "verification_tasks_created": int,
        }
    """
    try:
        import io
        from app.ml.local_whisper import LocalWhisperService
        from app.ml.topic_extraction import TopicExtractionService
        from app.services.syllabus_matcher import SyllabusMatchingAgent
        from app.services.verification_agent import VerificationAgent
        from app.ml.embeddings import LocalEmbeddingsService
        from app.utils.minio_client import get_minio_client

        logger.info(f"Starting curriculum pipeline for {session_id}")

        # Connect to database
        from app.database import db

        # ===== Stage 0: Stream audio from MinIO into memory =====
        logger.info(f"[0/4] Fetching audio from MinIO key={minio_object_key}...")
        s3 = get_minio_client()
        audio_buffer = io.BytesIO()
        s3.download_fileobj(minio_bucket, minio_object_key, audio_buffer)
        audio_buffer.seek(0)  # Rewind for reading
        logger.info(
            f"✓ Audio loaded into memory buffer "
            f"({audio_buffer.getbuffer().nbytes} bytes)"
        )

        # ===== Stage 1: Transcription (in-memory, no disk) =====
        logger.info(f"[1/4] Transcribing audio...")
        whisper_svc = LocalWhisperService()
        # Use asyncio.run to call async method from sync task
        transcript_result = async_to_sync(whisper_svc.transcribe_audio)(
            audio_buffer=audio_buffer,  # Pass BytesIO directly
            session_id=session_id,
            language="en",
        )
        transcript_text = transcript_result.transcript
        logger.info(f"✓ Transcription: {len(transcript_text)} chars")

        # ===== Ephemeral cleanup: delete audio from MinIO immediately =====
        try:
            s3.delete_object(Bucket=minio_bucket, Key=minio_object_key)
            logger.info(f"✓ Ephemeral audio deleted from MinIO: key={minio_object_key}")
        except Exception as del_exc:  # noqa: BLE001
            # Non-fatal — log and continue; audio will expire naturally if
            # a MinIO lifecycle policy is configured
            logger.warning(
                f"Could not delete MinIO object {minio_object_key}: {del_exc}"
            )

        # ===== Stage 2: Topic Extraction =====
        logger.info(f"[2/4] Extracting topics...")
        topic_svc = TopicExtractionService()
        extraction_result = topic_svc.extract_topics(
            transcript=transcript_text,
            session_id=session_id,
            top_k=15,
        )
        logger.info(f"✓ Topics extracted: {len(extraction_result.candidates)}")

        # ===== Stage 3: Syllabus Matching (Embeddings) =====
        logger.info(f"[3/4] Matching topics to curriculum...")
        embeddings_svc = LocalEmbeddingsService()
        matcher = SyllabusMatchingAgent(
            db=db,
            embeddings_service=embeddings_svc,
            confidence_threshold=0.6,  # δ
        )
        async_to_sync(matcher.initialize)()

        mapping_result = async_to_sync(matcher.match_topics_to_nodes)(
            session_id=session_id,
            course_id=course_id,
            topics=extraction_result.candidates,
            top_k_matches=3,
        )
        logger.info(f"✓ Mappings: {mapping_result.total_matches}, Below threshold: {mapping_result.below_threshold_count}")

        # ===== Stage 4: Create Verification Tasks =====
        logger.info(f"[4/4] Creating verification tasks...")
        above_threshold, below_threshold = matcher.filter_by_confidence(mapping_result)

        verif_agent = VerificationAgent(db)
        async_to_sync(verif_agent.initialize)()

        if below_threshold:
            verif_tasks = async_to_sync(verif_agent.create_verification_tasks)(
                session_id=session_id,
                course_id=course_id,
                below_threshold_matches=below_threshold,
            )
            logger.info(f"✓ Created {len(verif_tasks)} verification tasks")
        else:
            verif_tasks = []

        result = {
            "session_id": session_id,
            "course_id": course_id,
            "stage": "verification_needed" if verif_tasks else "completed",
            "transcript_length": len(transcript_text),
            "topics_extracted": len(extraction_result.candidates),
            "mapped_topics": mapping_result.mapped_topics_count,
            "total_matches": mapping_result.total_matches,
            "below_threshold": len(below_threshold),
            "verification_tasks_created": len(verif_tasks),
            "inference_time_seconds": transcript_result.inference_time_seconds,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"✓ Curriculum pipeline completed for {session_id}")
        return result

    except Exception as exc:
        logger.error(f"Curriculum pipeline failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@celery_app.task(
    name='tasks.unlock_resources_for_session',
    max_retries=2,
    default_retry_delay=30,
)
def unlock_resources_for_session(
    session_id: str,
    course_id: str,
    verified_curriculum_node_ids: list,
) -> Dict[str, Any]:
    """
    Progressively unlock resources for all students with A_t = True.
    
    Called after attendance verification completes.
    
    Args:
        session_id: Classroom session
        course_id: Course ID
        verified_curriculum_node_ids: Nodes with verified mappings
    
    Returns:
        {
            "session_id": str,
            "students_with_attendance": int,
            "resources_unlocked": int,
            "total_unlock_events": int,
        }
    """
    try:
        from app.services.resource_unlock import ResourceUnlockService
        from app.database import db
        from motor.motor_asyncio import AsyncIOMotorClient
        
        logger.info(f"Unlocking resources for session {session_id}")
        
        unlock_svc = ResourceUnlockService(db)
        async_to_sync(unlock_svc.initialize)()
        
        # Query attendance decisions with A_t = True for this session
        attendance_col = db["attendance_decisions"]
        cursor = attendance_col.find({
            "session_id": session_id,
            "attendance_marked": True,  # A_t = True
        })
        
        attendees = async_to_sync(cursor.to_list)(length=1000)
        
        total_unlocks = 0
        total_resources = 0
        
        for attendance in attendees:
            user_id = attendance["user_id"]
            decision_id = attendance["decision_id"]
            
            # Unlock resources for this student
            unlock_result = async_to_sync(unlock_svc.unlock_resources_for_student)(
                user_id=user_id,
                session_id=session_id,
                course_id=course_id,
                attendance_verified=True,  # A_t = True
                attendance_decision_id=decision_id,
                curriculum_node_ids=verified_curriculum_node_ids,
            )
            
            total_unlocks += 1
            total_resources += unlock_result.unlock_count
        
        result = {
            "session_id": session_id,
            "course_id": course_id,
            "students_with_attendance": len(attendees),
            "total_unlock_events": total_unlocks,
            "resources_unlocked": total_resources,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        
        logger.info(
            f"✓ Unlocked {total_resources} resources for {len(attendees)} students",
            extra={"session_id": session_id}
        )
        return result
        
    except Exception as exc:
        logger.error(f"Resource unlock failed: {exc}", exc_info=True)
        raise


# ============================================================================
# TASK STATUS TRACKING
# ============================================================================

def get_task_status(task_id: str) -> Dict[str, Any]:
    """Query task status and result."""
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "state": result.state,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "result": result.result if result.ready() else None,
    }


def revoke_task(task_id: str, terminate: bool = False):
    """Cancel a running task."""
    celery_app.control.revoke(task_id, terminate=terminate)
    logger.info(f"Revoked task {task_id}")


# ============================================================================
# CELERY BEAT SCHEDULE (Periodic tasks)
# ============================================================================

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'batch-risk-computation': {
        'task': 'tasks.batch_compute_risk',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM UTC
        'args': ('all-courses',),
    },
    'archive-audit-logs': {
        'task': 'tasks.archive_audit_logs',
        'schedule': crontab(day_of_week=0, hour=3, minute=0),  # Weekly Sunday 3 AM
        'kwargs': {'days_old': 90},
    },
}


# ============================================================================
# HELPER: FETCH STUDENT FEATURES (placeholder)
# ============================================================================

async def fetch_student_features(
    user_id: str,
    course_id: str,
    lookback_days: int,
) -> list:
    """
    Fetch feature vector for risk model.
    
    Returns: [absence_rate, engagement, anomaly, curriculum_gap, participation]
    """
    # Implementation: query attendance_events, curriculum_events, etc.
    return [0.3, 0.6, 0.1, 0.4, 0.7]
