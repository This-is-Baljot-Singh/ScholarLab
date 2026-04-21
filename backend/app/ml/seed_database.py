#!/usr/bin/env python3
"""
Production-grade database seeding script for ScholarLab.
Populates MongoDB with realistic test data including students, faculty, attendance records, and curriculum.
Run once to initialize the database with non-mocked data.
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import logging
from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Configuration
MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "scholarlab"

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
    },
    {
        "name": "Library Building",
        "boundary": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-122.41, 37.775],
                    [-122.409, 37.775],
                    [-122.409, 37.776],
                    [-122.41, 37.776],
                    [-122.41, 37.775]
                ]
            ]
        }
    },
    {
        "name": "Engineering Lab",
        "boundary": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-122.415, 37.774],
                    [-122.414, 37.774],
                    [-122.414, 37.775],
                    [-122.415, 37.775],
                    [-122.415, 37.774]
                ]
            ]
        }
    }
]

# Curriculum modules (knowledge graph nodes)
CURRICULUM_DATA = [
    {"course_id": "CS101", "title": "Introduction to Programming", "node_type": "module", "prerequisites": []},
    {"course_id": "CS102", "title": "Data Structures", "node_type": "module", "prerequisites": ["CS101"]},
    {"course_id": "CS103", "title": "Algorithms", "node_type": "module", "prerequisites": ["CS102"]},
    {"course_id": "CS201", "title": "Web Development", "node_type": "module", "prerequisites": ["CS101"]},
    {"course_id": "CS202", "title": "Database Design", "node_type": "module", "prerequisites": ["CS102"]},
    {"course_id": "CS203", "title": "Machine Learning", "node_type": "module", "prerequisites": ["CS103"]},
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
        collections = ["users", "attendance_logs", "curriculum_nodes", "geofences"]
        for collection_name in collections:
            collection = self.db.get_collection(collection_name)
            result = await collection.delete_many({})
            logger.info(f"✓ Cleared {collection_name}: {result.deleted_count} documents deleted")
            
    async def seed_users(self):
        """Populate users collection with students, faculty, and admin."""
        users_collection = self.db.get_collection("users")
        
        users = []
        
        # Create faculty users
        faculty_users = [
            {"email": "prof.sharma@scholarlab.edu", "full_name": "Dr. Sharma", "role": "faculty"},
            {"email": "prof.singh@scholarlab.edu", "full_name": "Prof. Singh", "role": "faculty"},
            {"email": "prof.gupta@scholarlab.edu", "full_name": "Dr. Gupta", "role": "faculty"},
        ]
        
        for faculty in faculty_users:
            users.append({
                "email": faculty["email"],
                "full_name": faculty["full_name"],
                "role": faculty["role"],
                "hashed_password": pwd_context.hash("faculty123"),
                "webauthn_credentials": [],
                "created_at": datetime.now(timezone.utc),
            })
        
        # Create admin user
        users.append({
            "email": "admin@scholarlab.edu",
            "full_name": "System Administrator",
            "role": "admin",
            "hashed_password": pwd_context.hash("admin123"),
            "webauthn_credentials": [],
            "created_at": datetime.now(timezone.utc),
        })
        
        # Create 60 realistic student users
        student_ids = []
        for i in range(60):
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            email = f"{first_name.lower()}.{last_name.lower()}{i}@scholarlab.edu"
            
            student = {
                "email": email,
                "full_name": f"{first_name} {last_name}",
                "role": "student",
                "hashed_password": pwd_context.hash("student123"),
                "webauthn_credentials": [],
                "created_at": datetime.now(timezone.utc),
            }
            users.append(student)
            student_ids.append(email)
        
        # Insert all users
        result = await users_collection.insert_many(users)
        logger.info(f"✓ Seeded {len(users)} users ({len(faculty_users)} faculty, 1 admin, {len(student_ids)} students)")
        
        return student_ids
        
    async def seed_attendance(self, student_emails: list):
        """Generate 30 days of realistic attendance records."""
        attendance_collection = self.db.get_collection("attendance")
        users_collection = self.db.get_collection("users")
        
        # Fetch actual student user IDs
        students = await users_collection.find({"role": "student"}).to_list(None)
        student_id_map = {student["email"]: str(student["_id"]) for student in students}
        
        attendance_records = []
        base_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Generate attendance for each student over 30 days
        for email in student_emails:
            user_id = student_id_map.get(email)
            if not user_id:
                continue
                
            # Each student attends approximately 80% of classes
            for day_offset in range(30):
                # Skip random days (20% absence rate)
                if random.random() > 0.8:
                    continue
                    
                timestamp = base_date + timedelta(days=day_offset, hours=random.randint(8, 16))
                
                record = {
                    "user_id": user_id,
                    "email": email,
                    "status": "verified",
                    "timestamp": timestamp,
                    "validated_coordinates": {
                        "lat": 37.7749 + random.uniform(-0.01, 0.01),
                        "lng": -122.4194 + random.uniform(-0.01, 0.01)
                    },
                    "device_fingerprint": f"device_{random.randint(1000, 9999)}",
                    "is_spoofed": random.random() < 0.05,  # 5% spoofed attempts
                }
                attendance_records.append(record)
        
        # Insert all attendance records
        result = await attendance_collection.insert_many(attendance_records)
        logger.info(f"✓ Seeded {len(attendance_records)} attendance records")
        
    async def seed_curriculum(self):
        """Populate curriculum knowledge graph."""
        curriculum_collection = self.db.get_collection("curriculum")
        
        curriculum = []
        for module in CURRICULUM_DATA:
            curriculum.append({
                "course_id": module["course_id"],
                "title": module["title"],
                "node_type": module["node_type"],
                "prerequisites": module["prerequisites"],
                "resource_uris": [
                    f"https://example.com/resources/{module['course_id']}/slides.pdf",
                    f"https://example.com/resources/{module['course_id']}/assignment.pdf"
                ],
                "created_at": datetime.now(timezone.utc),
            })
        
        result = await curriculum_collection.insert_many(curriculum)
        logger.info(f"✓ Seeded {len(curriculum)} curriculum modules")
        
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
        
        result = await geofences_collection.insert_many(geofences)
        logger.info(f"✓ Seeded {len(geofences)} geofences")
        
    async def create_indexes(self):
        """Create necessary database indexes."""
        users_collection = self.db.get_collection("users")
        attendance_collection = self.db.get_collection("attendance")
        geofences_collection = self.db.get_collection("geofences")
        
        # User indexes
        await users_collection.create_index("email", unique=True)
        
        # Attendance indexes
        await attendance_collection.create_index("user_id")
        await attendance_collection.create_index("email")
        await attendance_collection.create_index("timestamp")
        await attendance_collection.create_index([("timestamp", -1)])  # For sorting by recent
        
        # Geofence spatial index
        await geofences_collection.create_index([("boundary", "2dsphere")])
        
        logger.info("✓ Created database indexes")
        
    async def seed(self):
        """Run the complete seeding process."""
        try:
            await self.connect()
            logger.info("\n🌱 Starting database seeding process...\n")
            
            # Clear existing data
            await self.clear_collections()
            
            # Seed data
            student_emails = await self.seed_users()
            await self.seed_attendance(student_emails)
            await self.seed_curriculum()
            await self.seed_geofences()
            await self.create_indexes()
            
            logger.info("\n✅ Database seeding completed successfully!\n")
            logger.info("📝 Test Credentials:")
            logger.info("  Faculty: prof.sharma@scholarlab.edu / faculty123")
            logger.info("  Admin:   admin@scholarlab.edu / admin123")
            logger.info("  Student: (any student email) / student123\n")
            
        except Exception as e:
            logger.error(f"❌ Seeding failed: {str(e)}", exc_info=True)
        finally:
            await self.disconnect()

async def main():
    """Main entry point."""
    seeder = DatabaseSeeder()
    await seeder.seed()

if __name__ == "__main__":
    asyncio.run(main())
