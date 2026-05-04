import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Configure a specific logger for performance metrics
metrics_logger = logging.getLogger("performance_metrics")
metrics_logger.setLevel(logging.INFO)

class PerformanceMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track API latency for IEEE manuscript evaluation metrics.
    Captures processing time for Authentication, Attendance, and ML Analytics.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        # Process the request
        response = await call_next(request)
        
        process_time_ms = (time.perf_counter() - start_time) * 1000
        
        path = request.url.path
        
        # Selectively log specific critical pathways for the research paper
        if "/api/attendance/verify" in path:
            metrics_logger.info(f"[METRIC] Attendance Pipeline (Auth+Geo): {process_time_ms:.2f}ms")
        elif "/api/analytics/predict/risk" in path:
            metrics_logger.info(f"[METRIC] ML Inference (XGBoost+SHAP): {process_time_ms:.2f}ms")
        elif "/api/auth/webauthn" in path:
            metrics_logger.info(f"[METRIC] Cryptographic WebAuthn Validation: {process_time_ms:.2f}ms")
            
        # Optional: Add a custom header to the response for frontend debugging
        response.headers["X-Process-Time-Ms"] = str(round(process_time_ms, 2))
        
        return response