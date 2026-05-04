# ScholarLab/backend/app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.database import db, init_db_indexes
from app.schemas import RoleEnum
from contextlib import asynccontextmanager

# Production-ready: Structured logging & tracing
from app.logging.structured_logging import (
    configure_structured_logging,
    get_logger,
    set_trace_context,
    clear_trace_context,
)
from app.logging.tracing import initialize_tracer, TracingMiddleware, get_tracer

# Production-ready: Enhanced JWT & RBAC
from app.security.auth_enhanced import get_jwt_security
from app.security.rbac import RBACEnforcer

# Production-ready: Metrics
from app.metrics.prometheus_metrics import MetricsMiddleware

# Import all routers
from app.routers import auth, geofences, attendance, student, websockets, analytics, ws as ws_router, curriculum as curriculum_router, metrics as metrics_router
# from app.routers.attendance_verification import router as attendance_verification_router

# Initialize structured logging
configure_structured_logging(level="INFO", log_file="/tmp/scholarlab.log")
logger = get_logger(__name__)

# Initialize distributed tracing
tracer = initialize_tracer(service_name="scholarlab-api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("Starting ScholarLab API...", extra={"startup": True})
    
    try:
        # Initialize MongoDB connection
        logger.info("Connecting to MongoDB...")
        await db.command("ping")
        logger.info("MongoDB connection successful")
        
        # Initialize database indexes
        await init_db_indexes()
        logger.info("Database indexes initialized")
        
        # Initialize JWT security (token metadata collections)
        jwt_security = await get_jwt_security()
        logger.info("JWT security system initialized")
        
        logger.info("ScholarLab API startup complete", extra={"status": "ready"})
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}", extra={"error_type": type(e).__name__})
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down ScholarLab API...", extra={"shutdown": True})

app = FastAPI(
    title="Scholarlab API",
    description="Backend for Anti-Spoofed Attendance & Curriculum Sync",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# ============================================================================
# PRODUCTION MIDDLEWARE (in order of application)
# ============================================================================

# 1. Distributed Tracing Middleware (first to capture all requests)
app.add_middleware(TracingMiddleware, tracer=tracer)

# 2. Metrics Middleware (for latency recording)
app.add_middleware(MetricsMiddleware)

# 3. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:80",
        "http://127.0.0.1",
        "http://127.0.0.1:80",
        "http://localhost:5173", 
        "http://localhost:5174", 
        "http://localhost:3000", 
        "http://127.0.0.1:5173", 
        "http://127.0.0.1:5174"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# PRODUCTION ROUTERS
# ============================================================================

# Standard API routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(geofences.router, prefix="/api/geofences")
app.include_router(attendance.router, prefix="/api/attendance")
# app.include_router(attendance_verification_router, prefix="/api")
app.include_router(student.router, prefix="/api/student")
app.include_router(analytics.router, prefix="/api/analytics")
app.include_router(websockets.router, prefix="/api/ws")  # Student WebSocket
app.include_router(ws_router.router, prefix="/ws")       # Faculty WebSocket
app.include_router(curriculum_router.router, prefix="/api/curriculum")

# Production monitoring
app.include_router(metrics_router.router, prefix="", tags=["monitoring"])


@app.get("/api/faculty/dashboard")
async def faculty_only_route(current_user: dict = Depends(get_jwt_security)):
    """Faculty dashboard (accessible by faculty and admin only)."""
    from app.security.rbac import Role, require_role as check_require_role
    
    user_role = current_user.get("role", "student").lower()
    if user_role not in ["faculty", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faculty portal access denied",
        )
    
    return {"message": f"Welcome Faculty {current_user.get('full_name', 'User')}"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "ScholarLab API is operational", "version": "1.0.0"}