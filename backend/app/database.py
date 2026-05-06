from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings
import pymongo
import logging
import os

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # MongoDB URL - supports both Docker and local connections
    MONGODB_URL: str = os.getenv(
        "MONGODB_URL",
        "mongodb://localhost:27017"  # Local default
    )
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "scholarlab")
    SECRET_KEY: str = "your-super-secret-jwt-key" # Rotate in production!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Log MongoDB connection info (mask password)
_masked_url = settings.MONGODB_URL.replace(settings.MONGODB_URL.split("@")[0].split("://")[1] if "@" in settings.MONGODB_URL else "", "***") if "@" in settings.MONGODB_URL else settings.MONGODB_URL
logger.info(f"MongoDB URL: {_masked_url}")

client = AsyncIOMotorClient(settings.MONGODB_URL, tz_aware=True)
db = client[settings.DATABASE_NAME]

users_collection = db.get_collection("users")
geofences_collection = db.get_collection("geofences")
curriculum_collection = db.get_collection("curriculum")
attendance_collection = db.get_collection("attendance")
sessions_collection = db.get_collection("sessions")


async def get_db():
    """FastAPI dependency to get the database instance."""
    return db

async def init_db_indexes():
    """Establish required indexes for performance and spatial querying."""
    logger.info("Initializing database indexes...")
    # Unique email index for users
    await users_collection.create_index("email", unique=True)
    
    # 2dsphere index for GeoJSON spatial boundaries
    await geofences_collection.create_index([("boundary", pymongo.GEOSPHERE)])
    logger.info("Database indexes configured successfully.")

async def seed_test_users():
    """Create test users if they don't exist."""
    from passlib.context import CryptContext
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    logger.info("Checking for test users...")
    
    test_users = [
        {
            "email": "student@example.com",
            "full_name": "Demo Student",
            "role": "student",
            "password": "password",
        },
        {
            "email": "faculty@example.com",
            "full_name": "Demo Faculty",
            "role": "faculty",
            "password": "password",
        },
        {
            "email": "admin@example.com",
            "full_name": "Demo Admin",
            "role": "admin",
            "password": "password",
        }
    ]
    
    for test_user in test_users:
        existing = await users_collection.find_one({"email": test_user["email"]})
        
        if not existing:
            user_data = {
                "email": test_user["email"],
                "full_name": test_user["full_name"],
                "role": test_user["role"],
                "hashed_password": pwd_context.hash(test_user["password"]),
                "webauthn_credentials": []
            }
            await users_collection.insert_one(user_data)
            logger.info(f"Created test user: {test_user['email']}")
        else:
            logger.info(f"Test user already exists: {test_user['email']}")