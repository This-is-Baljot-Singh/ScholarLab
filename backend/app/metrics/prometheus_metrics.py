"""
Prometheus Metrics Collection for ScholarLab

Collects metrics for key operational and security indicators:
- API latency (by endpoint)
- Spoof rejection rate
- False rejection rate
- Model inference time
- Token refresh events
- Risk predictions
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from typing import Optional, Dict
import time
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# PROMETHEUS METRICS REGISTRY
# ============================================================================

# Create custom registry for ScholarLab metrics
scholarlab_registry = CollectorRegistry()

# ============================================================================
# LATENCY METRICS
# ============================================================================

api_request_duration = Histogram(
    name='scholarlab_api_request_duration_ms',
    documentation='API request latency in milliseconds',
    labelnames=['method', 'endpoint', 'status_code'],
    buckets=(10, 25, 50, 100, 250, 500, 1000, 2500, 5000),
    registry=scholarlab_registry,
)

attendance_verification_duration = Histogram(
    name='scholarlab_attendance_verification_duration_ms',
    documentation='Attendance verification pipeline latency',
    labelnames=['verification_type', 'status'],
    buckets=(50, 100, 200, 500, 1000, 2000),
    registry=scholarlab_registry,
)

model_inference_duration = Histogram(
    name='scholarlab_model_inference_duration_ms',
    documentation='ML model inference time (XGBoost, SHAP)',
    labelnames=['model_name', 'inference_type'],
    buckets=(10, 25, 50, 100, 250, 500),
    registry=scholarlab_registry,
)

curriculum_sync_duration = Histogram(
    name='scholarlab_curriculum_sync_duration_ms',
    documentation='Curriculum sync operation latency',
    labelnames=['operation', 'status'],
    buckets=(100, 500, 1000, 2500, 5000),
    registry=scholarlab_registry,
)

# ============================================================================
# SECURITY METRICS
# ============================================================================

spoof_rejection_counter = Counter(
    name='scholarlab_spoof_rejections_total',
    documentation='Total spoof detection rejections',
    labelnames=['spoof_type', 'detection_method'],
    registry=scholarlab_registry,
)

false_rejection_counter = Counter(
    name='scholarlab_false_rejections_total',
    documentation='Total legitimate attendance rejections (false positives)',
    labelnames=['rejection_reason', 'reversal_status'],
    registry=scholarlab_registry,
)

biometric_verification_counter = Counter(
    name='scholarlab_biometric_verifications_total',
    documentation='Total biometric verification attempts',
    labelnames=['result'],  # pass, fail, timeout
    registry=scholarlab_registry,
)

device_clone_detection_counter = Counter(
    name='scholarlab_device_clone_detections_total',
    documentation='Total device cloning attempts detected',
    labelnames=['clone_type'],  # counter_mismatch, signature_mismatch, etc.
    registry=scholarlab_registry,
)

# ============================================================================
# ANOMALY & RISK METRICS
# ============================================================================

risk_predictions_counter = Counter(
    name='scholarlab_risk_predictions_total',
    documentation='Total risk predictions generated',
    labelnames=['risk_level'],  # low, medium, high, critical
    registry=scholarlab_registry,
)

collusion_detections_counter = Counter(
    name='scholarlab_collusion_detections_total',
    documentation='Total suspicious collusion pairs detected',
    labelnames=['confidence_level'],
    registry=scholarlab_registry,
)

anomaly_alerts_gauge = Gauge(
    name='scholarlab_active_anomaly_alerts',
    documentation='Current number of active anomaly alerts',
    labelnames=['alert_type'],
    registry=scholarlab_registry,
)

# ============================================================================
# AUTHENTICATION METRICS
# ============================================================================

login_attempts_counter = Counter(
    name='scholarlab_login_attempts_total',
    documentation='Total login attempts',
    labelnames=['result'],  # success, failure
    registry=scholarlab_registry,
)

token_refresh_counter = Counter(
    name='scholarlab_token_refreshes_total',
    documentation='Total token refreshes (rotation events)',
    labelnames=['status'],  # success, failure
    registry=scholarlab_registry,
)

token_revocation_counter = Counter(
    name='scholarlab_token_revocations_total',
    documentation='Total token revocations',
    labelnames=['reason'],
    registry=scholarlab_registry,
)

rbac_denial_counter = Counter(
    name='scholarlab_rbac_denials_total',
    documentation='Total RBAC permission denials',
    labelnames=['role', 'permission'],
    registry=scholarlab_registry,
)

# ============================================================================
# DATABASE METRICS
# ============================================================================

database_operation_duration = Histogram(
    name='scholarlab_database_operation_duration_ms',
    documentation='Database operation latency',
    labelnames=['operation', 'collection'],
    buckets=(5, 10, 25, 50, 100, 250, 500),
    registry=scholarlab_registry,
)

# ============================================================================
# SYSTEM METRICS
# ============================================================================

active_websocket_connections = Gauge(
    name='scholarlab_active_websocket_connections',
    documentation='Current number of active WebSocket connections',
    labelnames=['connection_type'],  # student, faculty
    registry=scholarlab_registry,
)

background_job_duration = Histogram(
    name='scholarlab_background_job_duration_ms',
    documentation='Celery background job duration',
    labelnames=['job_name', 'status'],
    buckets=(100, 500, 1000, 5000, 10000),
    registry=scholarlab_registry,
)


# ============================================================================
# METRICS HELPERS
# ============================================================================

class MetricsCollector:
    """Helper class for recording metrics."""
    
    @staticmethod
    def record_api_request(
        method: str,
        endpoint: str,
        status_code: int,
        duration_ms: float,
    ):
        """Record API request metrics."""
        api_request_duration.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
        ).observe(duration_ms)
    
    @staticmethod
    def record_attendance_verification(
        verification_type: str,
        status: str,
        duration_ms: float,
    ):
        """Record attendance verification metrics."""
        attendance_verification_duration.labels(
            verification_type=verification_type,
            status=status,
        ).observe(duration_ms)
    
    @staticmethod
    def record_model_inference(
        model_name: str,
        inference_type: str,
        duration_ms: float,
    ):
        """Record ML model inference time."""
        model_inference_duration.labels(
            model_name=model_name,
            inference_type=inference_type,
        ).observe(duration_ms)
    
    @staticmethod
    def record_spoof_rejection(
        spoof_type: str,
        detection_method: str,
    ):
        """Record spoof detection."""
        spoof_rejection_counter.labels(
            spoof_type=spoof_type,
            detection_method=detection_method,
        ).inc()
    
    @staticmethod
    def record_false_rejection(
        rejection_reason: str,
        reversal_status: str = "pending",
    ):
        """Record false rejection (false positive)."""
        false_rejection_counter.labels(
            rejection_reason=rejection_reason,
            reversal_status=reversal_status,
        ).inc()
    
    @staticmethod
    def record_risk_prediction(risk_level: str):
        """Record risk prediction."""
        risk_predictions_counter.labels(risk_level=risk_level).inc()
    
    @staticmethod
    def record_collusion_detection(confidence_level: str):
        """Record collusion detection."""
        collusion_detections_counter.labels(confidence_level=confidence_level).inc()
    
    @staticmethod
    def record_login_attempt(success: bool):
        """Record login attempt."""
        login_attempts_counter.labels(result="success" if success else "failure").inc()
    
    @staticmethod
    def record_token_refresh(success: bool):
        """Record token refresh."""
        token_refresh_counter.labels(status="success" if success else "failure").inc()
    
    @staticmethod
    def record_rbac_denial(role: str, permission: str):
        """Record RBAC denial."""
        rbac_denial_counter.labels(role=role, permission=permission).inc()


class MetricsMiddleware:
    """FastAPI middleware for recording metrics."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware callable."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.perf_counter()
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        
        status_code = 500  # Default to error
        
        async def send_with_metrics(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)
        
        try:
            await self.app(scope, receive, send_with_metrics)
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            MetricsCollector.record_api_request(method, path, status_code, duration_ms)
