#!/usr/bin/env python3
"""Quick script to populate MongoDB with test users."""
import asyncio
import sys
import os
from datetime import datetime, timezone
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed():
    try:
        # Get MongoDB URL - supports both Docker and local
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        database_name = os.getenv("DATABASE_NAME", "scholarlab")
        
        print(f"📡 Connecting to MongoDB: {mongodb_url.split('@')[-1] if '@' in mongodb_url else mongodb_url}")
        
        # Connect to MongoDB
        client = AsyncIOMotorClient(mongodb_url)
        db = client[database_name]
        users_collection = db["users"]
        
        # Check if users already exist
        count = await users_collection.count_documents({})
        if count > 0:
            print(f"✓ Database already has {count} users. Skipping seeding.")
            client.close()
            return
        
        # Test users
        test_users = [
            {
                "email": "prof.sharma@scholarlab.edu",
                "full_name": "Dr. Sharma",
                "role": "faculty",
                "hashed_password": pwd_context.hash("faculty123"),
                "webauthn_credentials": [],
                "created_at": datetime.now(timezone.utc),
            },
            {
                "email": "prof.singh@scholarlab.edu",
                "full_name": "Prof. Singh",
                "role": "faculty",
                "hashed_password": pwd_context.hash("faculty123"),
                "webauthn_credentials": [],
                "created_at": datetime.now(timezone.utc),
            },
            {
                "email": "admin@scholarlab.edu",
                "full_name": "System Administrator",
                "role": "admin",
                "hashed_password": pwd_context.hash("admin123"),
                "webauthn_credentials": [],
                "created_at": datetime.now(timezone.utc),
            },
            {
                "email": "rajesh.kumar1@scholarlab.edu",
                "full_name": "Rajesh Kumar",
                "role": "student",
                "hashed_password": pwd_context.hash("student123"),
                "webauthn_credentials": [],
                "created_at": datetime.now(timezone.utc),
            },
            {
                "email": "priya.sharma2@scholarlab.edu",
                "full_name": "Priya Sharma",
                "role": "student",
                "hashed_password": pwd_context.hash("student123"),
                "webauthn_credentials": [],
                "created_at": datetime.now(timezone.utc),
            },
        ]
        
        # Insert users
        result = await users_collection.insert_many(test_users)
        print(f"✓ Seeded {len(result.inserted_ids)} users")
        print("\n📝 Test Credentials:")
        print("  Faculty: prof.sharma@scholarlab.edu / faculty123")
        print("  Faculty: prof.singh@scholarlab.edu / faculty123")
        print("  Admin:   admin@scholarlab.edu / admin123")
        print("  Student: rajesh.kumar1@scholarlab.edu / student123")
        print("  Student: priya.sharma2@scholarlab.edu / student123\n")
        
        client.close()
    except Exception as e:
        print(f"❌ Error seeding database: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(seed())
