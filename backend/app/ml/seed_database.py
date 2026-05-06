#!/usr/bin/env python3
"""
Production-grade database seeding script for ScholarLab.
Populates MongoDB with realistic test data including students, faculty, attendance records, and curriculum.
Run once to initialize the database with non-mocked data.
"""

import asyncio
import random
import uuid
import wave
import struct
import io
import os
import logging
from datetime import datetime, timedelta, timezone

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

# Import strict API contracts to validate seed data
from app.contexts.api_contracts import (
    UserCreateRequest,
    AttendanceRecord,
    CurriculumNodeCreateRequest
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Configuration
MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.environ.get("DATABASE_NAME", "scholarlab")

# MinIO Configuration
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET_NAME", "scholarlab-audio")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Sample data generators
FIRST_NAMES = [
    "Rajesh", "Priya", "Amit", "Neha", "Arjun", "Divya", "Ravi", "Ananya",
    "Karthik", "Shreya", "Aditya", "Pooja", "Vikram", "Sneha", "Rohan", "Anjali",
    "Akshay", "Sakshi", "Nikhil", "Isha", "Varun", "Ridhi", "Saurav", "Nisha",
    "Harsh", "Zara", "Aman", "Aarav", "Bhavna", "Chetan", "Swati", "Deepak",
    "Esha", "Faisal", "Gita", "Hemant", "Iris", "Javed", "Kavya", "Laxmi",
    "Mani", "Natalia", "Omkar", "Pradeep", "Quirine", "Rishi", "Sunita", "Tara"
]

LAST_NAMES = [
    "Kumar", "Singh", "Patel", "Sharma", "Gupta", "Verma", "Reddy", "Rao",
    "Nair", "Menon", "Chandra", "Sengupta", "Banerjee", "Roy", "Das", "Sinha",
    "Joshi", "Iyer", "Krishnan", "Murthy", "Bhat", "Yadav", "Mishra", "Trivedi"
]

# Sample geofence campuses (GeoJSON Polygon format)
GEOFENCES_DATA = [
    {
        "name": "Main Campus",
        "boundary": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-122.4194, 37.7749],   # San Francisco area (example)
                    [-122.4094, 37.7749],
                    [-122.4094, 37.7849],
                    [-122.4194, 37.7849],
                    [-122.4194, 37.7749]
                ]
            ]
        }
    }
]

# Curriculum Tree structure
# We'll generate dynamic IDs for these nodes as they are seeded.
CURRICULUM_TREE = [
    {
        "course_id": "CS101",
        "title": "Introduction to Programming",
        "node_type": "module",
        "learning_outcomes": ["Understand basic syntax", "Write simple scripts"],
        "prerequisites": [],
        "resource_uris": ["https://example.com/cs101/intro.pdf"],
        "children": [
            {
                "course_id": "CS101",
                "title": "Variables and Data Types",
                "node_type": "topic",
                "learning_outcomes": ["Declare variables", "Use integers and strings"],
                "prerequisites": [],
                "resource_uris": ["https://example.com/cs101/vars.pdf"]
            },
            {
                "course_id": "CS101",
                "title": "Control Structures",
                "node_type": "topic",
                "learning_outcomes": ["Write if statements", "Use loops"],
                "prerequisites": [],
                "resource_uris": ["https://example.com/cs101/loops.pdf"]
            }
        ]
    },
    {
        "course_id": "CS203",
        "title": "Machine Learning",
        "node_type": "module",
        "learning_outcomes": ["Understand ML basics", "Train models"],
        "prerequisites": ["CS101"],
        "resource_uris": ["https://example.com/cs203/ml_intro.pdf"],
        "children": [
            {
                "course_id": "CS203",
                "title": "Supervised Learning",
                "node_type": "topic",
                "learning_outcomes": ["Understand regression", "Classification tasks"],
                "prerequisites": [],
                "resource_uris": ["https://example.com/cs203/supervised.pdf"]
            },
            {
                "course_id": "CS203",
                "title": "Neural Networks",
                "node_type": "topic",
                "learning_outcomes": ["Build perceptrons", "Backpropagation"],
                "prerequisites": [],
                "resource_uris": ["https://example.com/cs203/nn.pdf"]
            }
        ]
    }
]


class DatabaseSeeder:
    def __init__(self):
        self.client = None
        self.db = None
        
    async def connect(self):
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client[DATABASE_NAME]
        logger.info(f"✓ Connected to MongoDB: {MONGODB_URL}")
        
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            
    async def clear_collections(self):
        """Clear existing data (use with caution!)."""
        # Ensure we use curriculum_nodes per recent migrations
        collections = ["users", "attendance", "curriculum_nodes", "geofences"]
        for collection_name in collections:
            collection = self.db.get_collection(collection_name)
            result = await collection.delete_many({})
            logger.info(f"✓ Cleared {collection_name}: {result.deleted_count} documents deleted")
            
    def generate_dummy_wav(self) -> io.BytesIO:
        """Generate a 1-second silent WAV file in memory."""
        buf = io.BytesIO()
        with wave.open(buf, 'w') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            # Write 1 second of silence
            for _ in range(16000):
                f.writeframesraw(struct.pack('<h', 0))
        buf.seek(0)
        return buf

    def seed_minio(self):
        """Initialize local MinIO bucket and upload a sample recording."""
        logger.info("Initializing MinIO...")
        client = boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        
        try:
            client.head_bucket(Bucket=MINIO_BUCKET)
            logger.info(f"✓ MinIO bucket '{MINIO_BUCKET}' already exists")
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchBucket"):
                client.create_bucket(Bucket=MINIO_BUCKET)
                logger.info(f"✓ Created MinIO bucket '{MINIO_BUCKET}'")
            else:
                logger.error(f"Error checking MinIO bucket: {exc}")
                raise
                
        wav_buf = self.generate_dummy_wav()
        object_key = "seed/dummy_lecture.wav"
        client.upload_fileobj(
            wav_buf,
            MINIO_BUCKET,
            object_key,
            ExtraArgs={"ContentType": "audio/wav"}
        )
        logger.info(f"✓ Uploaded dummy lecture to s3://{MINIO_BUCKET}/{object_key}")

    async def seed_users(self):
        """Populate users collection with realistic student performance profiles."""
        users_collection = self.db.get_collection("users")
        
        users = []
        valid_password = "Student123!"
        hashed_pwd = pwd_context.hash(valid_password)
        
        # Create faculty and admin (as before)
        faculty_templates = [
            {"email": "prof.sharma@scholarlab.edu", "full_name": "Dr Sharma", "role": "faculty"},
            {"email": "prof.singh@scholarlab.edu", "full_name": "Prof Singh", "role": "faculty"},
            {"email": "prof.gupta@scholarlab.edu", "full_name": "Dr Gupta", "role": "faculty"},
        ]
        
        for f in faculty_templates:
            users.append({
                "email": f["email"],
                "full_name": f["full_name"],
                "role": "faculty",
                "hashed_password": hashed_pwd,
                "webauthn_credentials": [],
                "created_at": datetime.now(timezone.utc),
            })
        
        users.append({
            "email": "admin@scholarlab.edu",
            "full_name": "System Administrator",
            "role": "admin",
            "hashed_password": hashed_pwd,
            "webauthn_credentials": [],
            "created_at": datetime.now(timezone.utc),
        })
        
        # Partition 60 students: 5 Critical, 15 Moderate, 40 Safe
        # The very first student is deterministic for the login demo (Safe/Star Student)
        student_emails = []
        student_profiles = {}
        
        # Create the Master Star Student first (Safe)
        master_email = "star.student@scholarlab.edu"
        users.append({
            "email": master_email,
            "full_name": "Star Student",
            "role": "student",
            "hashed_password": hashed_pwd,
            "webauthn_credentials": [],
            "created_at": datetime.now(timezone.utc),
        })
        student_emails.append(master_email)
        student_profiles[master_email] = "Safe"
        
        # Then create the rest
        profiles = (
            [("Critical", 5)] + 
            [("Moderate", 15)] + 
            [("Safe", 39)] # 40 - 1 master
        )
        
        count = 1
        for category, num in profiles:
            for i in range(num):
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
                email = f"{first_name.lower()}.{last_name.lower()}{count}@scholarlab.edu"
                
                users.append({
                    "email": email,
                    "full_name": f"{first_name} {last_name}",
                    "role": "student",
                    "hashed_password": hashed_pwd,
                    "webauthn_credentials": [],
                    "created_at": datetime.now(timezone.utc),
                })
                student_emails.append(email)
                student_profiles[email] = category
                count += 1
        
        await users_collection.insert_many(users)
        logger.info(f"✓ Seeded {len(users)} users (5 Critical, 15 Moderate, 40 Safe)")
        
        return student_emails, student_profiles
        
    async def seed_attendance(self, student_emails: list, student_profiles: dict):
        """Generate 30 days of jagged attendance trends with group-specific behaviors."""
        attendance_collection = self.db.get_collection("attendance")
        users_collection = self.db.get_collection("users")
        
        students = await users_collection.find({"role": "student"}).to_list(None)
        student_id_map = {student["email"]: str(student["_id"]) for student in students}
        
        attendance_records = []
        base_date = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0) - timedelta(days=30)
        
        # Attendance probabilities per profile
        probs = {
            "Safe": 0.94,
            "Moderate": 0.72,
            "Critical": 0.35
        }
        
        # Generate 30 days of data
        for day_offset in range(30):
            current_day = base_date + timedelta(days=day_offset)
            is_weekend = current_day.weekday() >= 5
            is_friday = current_day.weekday() == 4
            
            if is_weekend:
                continue # No classes on weekends
                
            # Global day factor for "jagged" trends
            day_factor = 1.0
            if is_friday:
                day_factor = 0.65 # Significant dip on Fridays
            
            # Random "dips" or "spikes" for certain days
            day_factor *= random.uniform(0.85, 1.15)
            
            for email in student_emails:
                user_id = student_id_map.get(email)
                category = student_profiles.get(email, "Safe")
                
                # Base probability modified by day factor
                p_attend = probs[category] * day_factor
                
                if random.random() > p_attend:
                    continue
                    
                # Deterministic arrival delay based on category
                if category == "Safe":
                    delay = random.randint(-5, 10) # Often early or slightly late
                elif category == "Moderate":
                    delay = random.randint(5, 30)
                else: # Critical
                    delay = random.randint(20, 120) # Frequently very late
                
                timestamp = current_day + timedelta(minutes=delay)
                
                # Critical students have higher spoofing rates
                spoof_rate = 0.02 if category == "Safe" else (0.15 if category == "Moderate" else 0.40)
                is_spoofed = random.random() < spoof_rate
                status = "denied" if is_spoofed else "verified"
                
                signals = {
                    "device_verified": not is_spoofed or random.random() > 0.3,
                    "crypto_verified": not is_spoofed or random.random() > 0.3,
                    "nonce_verified": not is_spoofed,
                    "biometric_verified": not is_spoofed,
                    "multi_modal_verified": not is_spoofed or random.random() > 0.4,
                    "spatial_verified": not is_spoofed or random.random() > 0.4
                }
                
                record = {
                    "event_id": f"evt_{uuid.uuid4().hex[:12]}",
                    "timestamp": timestamp,
                    "course_id": "CS203" if day_offset % 2 == 0 else "CS101",
                    "status": status,
                    "signals": signals,
                    "is_spoofed": is_spoofed,
                    "user_id": user_id,
                    "email": email
                }
                attendance_records.append(record)
        
        if attendance_records:
            # Sort by timestamp to ensure they appear in order
            attendance_records.sort(key=lambda x: x["timestamp"])
            await attendance_collection.insert_many(attendance_records)
        
        logger.info(f"✓ Seeded {len(attendance_records)} attendance logs across 30 days with jagged trends.")
        
    async def seed_curriculum(self):
        """Populate curriculum knowledge graph with full module->topic trees."""
        curriculum_collection = self.db.get_collection("curriculum_nodes")
        
        nodes_to_insert = []
        
        for parent_data in CURRICULUM_TREE:
            # Process parent
            parent_req = CurriculumNodeCreateRequest(
                course_id=parent_data["course_id"],
                title=parent_data["title"],
                node_type=parent_data["node_type"],
                learning_outcomes=parent_data["learning_outcomes"],
                prerequisites=parent_data["prerequisites"],
                resource_uris=parent_data["resource_uris"]
            )
            
            parent_doc = parent_req.model_dump()
            parent_doc["node_id"] = f"node_{uuid.uuid4().hex[:8]}"
            parent_doc["created_at"] = datetime.now(timezone.utc)
            nodes_to_insert.append(parent_doc)
            
            # Process children
            for child_data in parent_data.get("children", []):
                # Update child prerequisite to point to parent implicitly if needed
                child_req = CurriculumNodeCreateRequest(
                    course_id=child_data["course_id"],
                    title=child_data["title"],
                    node_type=child_data["node_type"],
                    learning_outcomes=child_data["learning_outcomes"],
                    prerequisites=[parent_doc["node_id"]] + child_data["prerequisites"],
                    resource_uris=child_data["resource_uris"]
                )
                child_doc = child_req.model_dump()
                child_doc["node_id"] = f"node_{uuid.uuid4().hex[:8]}"
                child_doc["created_at"] = datetime.now(timezone.utc)
                child_doc["parent_node_id"] = parent_doc["node_id"]
                nodes_to_insert.append(child_doc)
        
        await curriculum_collection.insert_many(nodes_to_insert)
        logger.info(f"✓ Seeded {len(nodes_to_insert)} curriculum nodes (courses, modules, topics)")
        
    async def seed_geofences(self):
        """Populate geofence boundaries."""
        geofences_collection = self.db.get_collection("geofences")
        
        geofences = [
            {
                "name": gf["name"],
                "boundary": gf["boundary"],
                "created_at": datetime.now(timezone.utc),
            }
            for gf in GEOFENCES_DATA
        ]
        
        await geofences_collection.insert_many(geofences)
        logger.info(f"✓ Seeded {len(geofences)} geofences")
        
    async def create_indexes(self):
        """Create necessary database indexes."""
        users_collection = self.db.get_collection("users")
        attendance_collection = self.db.get_collection("attendance")
        geofences_collection = self.db.get_collection("geofences")
        
        await users_collection.create_index("email", unique=True)
        await attendance_collection.create_index("user_id")
        await attendance_collection.create_index("email")
        await attendance_collection.create_index("timestamp")
        await attendance_collection.create_index([("timestamp", -1)])
        
        from pymongo import GEOSPHERE
        await geofences_collection.create_index([("boundary", GEOSPHERE)])
        
        logger.info("✓ Created database indexes")
        
    async def seed_verification_queues(self, student_emails: list):
        """Inject flagged items into Anti-Spoofing and Curriculum queues."""
        attendance_collection = self.db.get_collection("attendance")
        tasks_col = self.db.get_collection("curriculum_verification_tasks")
        users_collection = self.db.get_collection("users")
        
        # 1. Anti-Spoofing Audit Queue (status: 'moderate')
        students = await users_collection.find({"email": {"$in": student_emails[:5]}}).to_list(None)
        
        flagged_attendance = [
            {
                "user_id": str(students[0]["_id"]),
                "session_id": "session-audit-1",
                "geofence_id": "main-campus",
                "timestamp": datetime.now(timezone.utc),
                "status": "moderate",
                "metadata": {
                    "flag_reason": "GPS Anomaly: Location exceeds geofence by 150m.",
                    "distance_m": 150.5,
                    "confidence_score": 0.42
                }
            },
            {
                "user_id": str(students[1]["_id"]),
                "session_id": "session-audit-2",
                "geofence_id": "main-campus",
                "timestamp": datetime.now(timezone.utc),
                "status": "moderate",
                "metadata": {
                    "flag_reason": "Device Mismatch: Unknown hardware fingerprint.",
                    "device_id": "DEV-ERR-99",
                    "confidence_score": 0.15
                }
            },
            {
                "user_id": str(students[2]["_id"]),
                "session_id": "session-audit-3",
                "geofence_id": "main-campus",
                "timestamp": datetime.now(timezone.utc),
                "status": "moderate",
                "metadata": {
                    "flag_reason": "Biometric Warning: Liveness score below 0.80.",
                    "liveness_score": 0.74,
                    "confidence_score": 0.55
                }
            }
        ]
        await attendance_collection.insert_many(flagged_attendance)
        logger.info(f"✓ Injected {len(flagged_attendance)} items into Anti-Spoofing Audit Queue")

        # 2. Curriculum Verification Queue
        curriculum_tasks = [
            {
                "task_id": f"task-{uuid.uuid4().hex[:8]}",
                "session_id": "session-curric-1",
                "course_id": "CS203",
                "topic": "neural networks",
                "topic_confidence": 0.92,
                "original_node_id": "node-cs101-1",
                "original_node_title": "Module 1: Intro to Python",
                "similarity_score": 0.45,
                "status": "pending",
                "created_at": datetime.now(timezone.utc)
            },
            {
                "task_id": f"task-{uuid.uuid4().hex[:8]}",
                "session_id": "session-curric-2",
                "course_id": "CS101",
                "topic": "binary search trees",
                "topic_confidence": 0.88,
                "original_node_id": "node-cs101-5",
                "original_node_title": "Module 5: Advanced Data Structures",
                "similarity_score": 0.52,
                "status": "pending",
                "created_at": datetime.now(timezone.utc)
            }
        ]
        await tasks_col.insert_many(curriculum_tasks)
        logger.info(f"✓ Injected {len(curriculum_tasks)} items into Curriculum Verification Queue")
        
    async def seed(self):
        """Run the complete seeding process."""
        try:
            try:
                # First handle MinIO (synchronous)
                self.seed_minio()
            except Exception as e:
                logger.warning(f"⚠️ MinIO initialization skipped: {e}")
                
            await self.connect()
            logger.info("\n🌱 Starting database seeding process...\n")
            
            await self.clear_collections()
            
            student_emails, student_profiles = await self.seed_users()
            await self.seed_attendance(student_emails, student_profiles)
            await self.seed_curriculum()
            await self.seed_geofences()
            await self.seed_verification_queues(student_emails)
            await self.create_indexes()
            
            logger.info("\n✅ Database seeding completed successfully!\n")
            logger.info("📝 Test Credentials:")
            logger.info("  Faculty: prof.sharma@scholarlab.edu / Student123!")
            logger.info("  Admin:   admin@scholarlab.edu / Student123!")
            logger.info("  Student: (any student email) / Student123!\n")
            
        except Exception as e:
            logger.error(f"❌ Seeding failed: {str(e)}", exc_info=True)
        finally:
            await self.disconnect()

async def main():
    seeder = DatabaseSeeder()
    await seeder.seed()

if __name__ == "__main__":
    asyncio.run(main())
