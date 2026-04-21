# ScholarLab/backend/app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.database import db, init_db_indexes
from app.schemas import RoleEnum
from app.security import require_role
import logging
from contextlib import asynccontextmanager

# Import all routers
from app.routers import auth, geofences, attendance, student, websockets, analytics # <-- Added analytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Connecting to MongoDB...")
    try:
        await db.command("ping")
        logger.info("Successfully connected to MongoDB!")
        await init_db_indexes()
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
    yield

app = FastAPI(
    title="Scholarlab API",
    description="Backend for Anti-Spoofed Attendance & Curriculum Sync",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include standard API routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(geofences.router, prefix="/api/geofences")
app.include_router(attendance.router, prefix="/api/attendance")
app.include_router(student.router, prefix="/api/student")
app.include_router(analytics.router, prefix="/api/analytics")
app.include_router(websockets.router, prefix="/api/ws")

@app.get("/api/faculty/dashboard")
async def faculty_only_route(current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin]))):
    return {"message": f"Welcome Faculty {current_user['full_name']}"}

@app.get("/")
async def root():
    return {"message": "Scholarlab API is operational"}