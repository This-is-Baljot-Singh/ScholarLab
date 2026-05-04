#!/usr/bin/env python3
"""
Comprehensive database seeding script for ScholarLab.
Populates MongoDB with realistic data for students, faculty, geofences, curriculum, and attendance logs.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================================================
# REALISTIC DATA SETS
# ============================================================================

FACULTY_DATA = [
    {
        "name": "Dr. Sarah Chen",
        "email": "sarah.chen@scholarlab.edu",
        "department": "Computer Science",
        "expertise": "Machine Learning & AI",
        "password": "faculty123"
    },
    {
        "name": "Prof. James Wilson",
        "email": "james.wilson@scholarlab.edu",
        "department": "Computer Science",
        "expertise": "Software Engineering",
        "password": "faculty123"
    },
    {
        "name": "Dr. Priya Sharma",
        "email": "priya.sharma@scholarlab.edu",
        "department": "Mathematics",
        "expertise": "Linear Algebra & Statistics",
        "password": "faculty123"
    },
    {
        "name": "Prof. Michael O'Brien",
        "email": "michael.obrien@scholarlab.edu",
        "department": "Computer Science",
        "expertise": "Database Systems",
        "password": "faculty123"
    },
    {
        "name": "Dr. Yuki Tanaka",
        "email": "yuki.tanaka@scholarlab.edu",
        "department": "Electrical Engineering",
        "expertise": "Digital Signal Processing",
        "password": "faculty123"
    },
]

STUDENT_FIRST_NAMES = [
    "Rajesh", "Priya", "Arjun", "Neha", "Vikram",
    "Anjali", "Rohan", "Deepika", "Amit", "Sneha",
    "Akshay", "Pooja", "Sanjay", "Kavya", "Nikhil",
    "Sara", "Aditya", "Isha", "Rahul", "Maya",
    "Sameer", "Divya", "Varun", "Riya", "Harsh",
    "Ananya", "Suresh", "Nisha", "Karan", "Meera",
]

STUDENT_LAST_NAMES = [
    "Kumar", "Sharma", "Singh", "Patel", "Gupta",
    "Reddy", "Nair", "Iyer", "Desai", "Kapoor",
    "Verma", "Bhat", "Misra", "Joshi", "Rao",
    "Dubey", "Chopra", "Bansal", "Saxena", "Bhatt",
]

DEPARTMENTS = ["Computer Science", "Mathematics", "Physics", "Electrical Engineering"]

# Geofence coordinates for a realistic campus
# These represent actual campus building locations (approximate)
GEOFENCE_LOCATIONS = [
    {
        "name": "Computer Science Building",
        "building_code": "CS-101",
        "type": "polygon",
        "coords": [
            [-73.9352, 40.8059],  # NW corner
            [-73.9350, 40.8059],  # NE corner
            [-73.9350, 40.8057],  # SE corner
            [-73.9352, 40.8057],  # SW corner
        ]
    },
    {
        "name": "Mathematics & Physics Building",
        "building_code": "MP-201",
        "type": "polygon",
        "coords": [
            [-73.9360, 40.8070],
            [-73.9358, 40.8070],
            [-73.9358, 40.8068],
            [-73.9360, 40.8068],
        ]
    },
    {
        "name": "Engineering Labs",
        "building_code": "ENG-301",
        "type": "polygon",
        "coords": [
            [-73.9340, 40.8065],
            [-73.9338, 40.8065],
            [-73.9338, 40.8063],
            [-73.9340, 40.8063],
        ]
    },
    {
        "name": "Library & Study Center",
        "building_code": "LIB-401",
        "type": "radial",
        "center": [-73.9345, 40.8062],
        "radius": 100  # meters
    },
    {
        "name": "Main Auditorium",
        "building_code": "AUD-501",
        "type": "radial",
        "center": [-73.9355, 40.8075],
        "radius": 150
    },
]

CURRICULUM_DATA = [
    {
        "course_id": "CS101",
        "title": "Introduction to Computer Science",
        "modules": [
            {"title": "Getting Started with Python", "module_num": 1},
            {"title": "Data Types and Variables", "module_num": 2},
            {"title": "Control Flow: Loops and Conditionals", "module_num": 3},
            {"title": "Functions and Modular Programming", "module_num": 4},
            {"title": "Object-Oriented Programming", "module_num": 5},
            {"title": "File I/O and Exception Handling", "module_num": 6},
        ]
    },
    {
        "course_id": "CS201",
        "title": "Data Structures & Algorithms",
        "modules": [
            {"title": "Arrays and Lists", "module_num": 1},
            {"title": "Stacks and Queues", "module_num": 2},
            {"title": "Linked Lists", "module_num": 3},
            {"title": "Trees and Binary Search Trees", "module_num": 4},
            {"title": "Graphs and Graph Traversal", "module_num": 5},
            {"title": "Sorting and Searching Algorithms", "module_num": 6},
        ]
    },
    {
        "course_id": "MATH101",
        "title": "Linear Algebra Fundamentals",
        "modules": [
            {"title": "Vectors and Vector Spaces", "module_num": 1},
            {"title": "Matrices and Matrix Operations", "module_num": 2},
            {"title": "Determinants and Inverses", "module_num": 3},
            {"title": "Eigenvalues and Eigenvectors", "module_num": 4},
            {"title": "Applications in Computer Science", "module_num": 5},
        ]
    },
    {
        "course_id": "ENG301",
        "title": "Digital Signal Processing",
        "modules": [
            {"title": "Signal Representation", "module_num": 1},
            {"title": "Fourier Analysis", "module_num": 2},
            {"title": "Filtering Techniques", "module_num": 3},
            {"title": "Time-Frequency Analysis", "module_num": 4},
            {"title": "Applications in Real Systems", "module_num": 5},
        ]
    },
]

# ============================================================================
# SEED FUNCTIONS
# ============================================================================

async def seed_faculty(db):
    """Seed faculty members into the database."""
    users_collection = db["users"]
    
    logger.info("Seeding faculty members...")
    faculty_count = 0
    
    for faculty in FACULTY_DATA:
        existing = await users_collection.find_one({"email": faculty["email"]})
        if not existing:
            user_doc = {
                "email": faculty["email"],
                "full_name": faculty["name"],
                "role": "faculty",
                "department": faculty["department"],
                "expertise": faculty["expertise"],
                "hashed_password": pwd_context.hash(faculty["password"]),
                "webauthn_credentials": [],
                "created_at": datetime.now(timezone.utc)
            }
            await users_collection.insert_one(user_doc)
            faculty_count += 1
            logger.info(f"  ✓ Created faculty: {faculty['name']}")
    
    return faculty_count


async def seed_students(db, num_students=50):
    """Seed realistic student data into the database."""
    users_collection = db["users"]
    
    logger.info(f"Seeding {num_students} students...")
    student_count = 0
    
    for i in range(num_students):
        first_name = random.choice(STUDENT_FIRST_NAMES)
        last_name = random.choice(STUDENT_LAST_NAMES)
        full_name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}{i}@scholarlab.edu"
        
        existing = await users_collection.find_one({"email": email})
        if not existing:
            student_doc = {
                "email": email,
                "full_name": full_name,
                "role": "student",
                "department": random.choice(DEPARTMENTS),
                "student_id": f"STU{1000 + i}",
                "enrollment_year": random.choice([2022, 2023, 2024, 2025]),
                "hashed_password": pwd_context.hash("student123"),
                "webauthn_credentials": [],
                "created_at": datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365))
            }
            await users_collection.insert_one(student_doc)
            student_count += 1
            
            if student_count % 10 == 0:
                logger.info(f"  ✓ Created {student_count} students...")
    
    logger.info(f"  ✓ Total students created: {student_count}")
    return student_count


async def seed_geofences(db):
    """Seed geofence data (campus buildings/locations)."""
    geofences_collection = db["geofences"]
    
    logger.info("Seeding geofences...")
    geofence_count = 0
    
    for geofence in GEOFENCE_LOCATIONS:
        existing = await geofences_collection.find_one({"building_code": geofence["building_code"]})
        if not existing:
            if geofence["type"] == "polygon":
                boundary = {
                    "type": "Polygon",
                    "coordinates": [geofence["coords"] + [geofence["coords"][0]]]  # Close the loop
                }
            else:  # radial
                boundary = {
                    "type": "Point",
                    "coordinates": geofence["center"]
                }
            
            geofence_doc = {
                "name": geofence["name"],
                "building_code": geofence["building_code"],
                "type": geofence["type"],
                "boundary": boundary,
                "radius": geofence.get("radius", 50),
                "capacity": random.randint(30, 200),
                "available_equipment": random.choice(["projector", "whiteboard", "computer lab", "testing equipment"]),
                "expected_bssids": [f"BSSID-{geofence['building_code'].replace('-', '')}", "00:11:22:33:44:55"],
                "created_at": datetime.now(timezone.utc)
            }
            await geofences_collection.insert_one(geofence_doc)
            geofence_count += 1
            logger.info(f"  ✓ Created geofence: {geofence['name']}")
    
    return geofence_count


async def seed_curriculum(db):
    """Seed curriculum modules and learning paths."""
    curriculum_collection = db["curriculum"]
    
    logger.info("Seeding curriculum data...")
    curriculum_count = 0
    
    for course in CURRICULUM_DATA:
        for i, module in enumerate(course["modules"]):
            existing = await curriculum_collection.find_one({
                "course_id": course["course_id"],
                "module_num": module["module_num"]
            })
            
            if not existing:
                # Build prerequisites (previous modules)
                prerequisites = []
                if module["module_num"] > 1:
                    prev_module = await curriculum_collection.find_one({
                        "course_id": course["course_id"],
                        "module_num": module["module_num"] - 1
                    })
                    if prev_module:
                        prerequisites = [str(prev_module["_id"])]
                
                curriculum_doc = {
                    "course_id": course["course_id"],
                    "course_title": course["title"],
                    "title": module["title"],
                    "module_num": module["module_num"],
                    "node_type": "module",
                    "prerequisites": prerequisites,
                    "resource_uris": [
                        f"/resources/{course['course_id']}/module_{module['module_num']}_slides.pdf",
                        f"/resources/{course['course_id']}/module_{module['module_num']}_quiz.pdf",
                        f"/resources/{course['course_id']}/module_{module['module_num']}_lab.pdf",
                    ],
                    "difficulty": ["beginner", "intermediate", "advanced"][min(module["module_num"] - 1, 2)],
                    "estimated_hours": random.randint(3, 10),
                    "created_at": datetime.now(timezone.utc)
                }
                await curriculum_collection.insert_one(curriculum_doc)
                curriculum_count += 1
    
    logger.info(f"  ✓ Created {curriculum_count} curriculum modules")
    return curriculum_count


async def seed_attendance_logs(db):
    """Seed realistic attendance logs for pattern analysis."""
    attendance_collection = db["attendance"]
    users_collection = db["users"]
    geofences_collection = db["geofences"]
    
    logger.info("Seeding attendance logs...")
    
    # Get all students and geofences
    students = await users_collection.find({"role": "student"}).to_list(100)
    geofences = await geofences_collection.find({}).to_list(10)
    
    if not students or not geofences:
        logger.warning("  ! No students or geofences found. Skipping attendance logs.")
        return 0
    
    attendance_count = 0
    base_date = datetime.now(timezone.utc) - timedelta(days=30)
    
    # Create attendance patterns for the last 30 days
    for day_offset in range(30):
        current_date = base_date + timedelta(days=day_offset)
        
        # Only weekdays (Monday-Friday)
        if current_date.weekday() >= 5:
            continue
        
        for student in students:
            # 80% attendance rate (realistic)
            if random.random() > 0.8:
                continue
            
            geofence = random.choice(geofences)
            
            # Vary time of attendance (8 AM to 6 PM)
            hour = random.randint(8, 18)
            minute = random.randint(0, 59)
            attendance_time = current_date.replace(hour=hour, minute=minute, second=0)
            
            # Add some GPS variation within geofence bounds
            if geofence["type"] == "radial":
                base_lon, base_lat = geofence["boundary"]["coordinates"]
                lat = base_lat + random.uniform(-0.001, 0.001)
                lon = base_lon + random.uniform(-0.001, 0.001)
            else:
                coords = geofence["boundary"]["coordinates"][0]
                lat = coords[1][1] + random.uniform(-0.0001, 0.0001)
                lon = coords[0][0] + random.uniform(-0.0001, 0.0001)
            
            building_code = geofence.get('building_code', geofence.get('name', 'UNKNOWN'))
            attendance_doc = {
                "user_id": str(student["_id"]),
                "user_email": student["email"],
                "session_id": f"SESSION-{current_date.strftime('%Y%m%d')}-{building_code}",
                "geofence_id": str(geofence["_id"]),
                "geofence_name": geofence["name"],
                "timestamp": attendance_time,
                "validated_coordinates": {
                    "lat": lat,
                    "lng": lon
                },
                "device_fingerprint": f"DEVICE-{random.randint(100000, 999999)}",
                "is_spoofed": False,
                "verification_method": random.choice(["webauthn", "biometric", "proximity"])
            }
            await attendance_collection.insert_one(attendance_doc)
            attendance_count += 1
    
    logger.info(f"  ✓ Created {attendance_count} attendance logs")
    return attendance_count


async def seed_admin_user(db):
    """Seed an admin user for system management."""
    users_collection = db["users"]
    
    logger.info("Seeding admin user...")
    
    existing = await users_collection.find_one({"email": "admin@scholarlab.edu"})
    if not existing:
        admin_doc = {
            "email": "admin@scholarlab.edu",
            "full_name": "System Administrator",
            "role": "admin",
            "hashed_password": pwd_context.hash("admin123"),
            "webauthn_credentials": [],
            "created_at": datetime.now(timezone.utc)
        }
        await users_collection.insert_one(admin_doc)
        logger.info("  ✓ Created admin user: admin@scholarlab.edu")
        return 1
    
    return 0


async def main():
    """Main seeding orchestration function."""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = client["scholarlab"]
        
        logger.info("=" * 70)
        logger.info("ScholarLab Database Seeding")
        logger.info("=" * 70)
        
        # Check if database is already populated
        users_count = await db["users"].count_documents({})
        if users_count > 10:
            logger.info(f"\n⚠️  Database already contains {users_count} users")
            logger.info("Clearing and re-seeding with fresh data...")
            await db["users"].delete_many({})
            await db["geofences"].delete_many({})
            await db["curriculum"].delete_many({})
            await db["attendance"].delete_many({})
            logger.info("✓ Collections cleared\n")
        
        # Execute seeding
        stats = {
            "faculty": await seed_faculty(db),
            "students": await seed_students(db, num_students=50),
            "admin": await seed_admin_user(db),
            "geofences": await seed_geofences(db),
            "curriculum": await seed_curriculum(db),
            "attendance": await seed_attendance_logs(db),
        }
        
        # Display summary
        logger.info("\n" + "=" * 70)
        logger.info("SEEDING SUMMARY")
        logger.info("=" * 70)
        logger.info(f"✓ Faculty Members:     {stats['faculty']}")
        logger.info(f"✓ Students:            {stats['students']}")
        logger.info(f"✓ Admin Users:         {stats['admin']}")
        logger.info(f"✓ Geofences:           {stats['geofences']}")
        logger.info(f"✓ Curriculum Modules:  {stats['curriculum']}")
        logger.info(f"✓ Attendance Logs:     {stats['attendance']}")
        logger.info("=" * 70)
        
        # Display test credentials
        logger.info("\n📝 TEST CREDENTIALS:")
        logger.info("=" * 70)
        logger.info("Admin:")
        logger.info("  Email:    admin@scholarlab.edu")
        logger.info("  Password: admin123")
        logger.info("\nFaculty:")
        logger.info("  Email:    sarah.chen@scholarlab.edu")
        logger.info("  Password: faculty123")
        logger.info("\nStudent:")
        logger.info("  Email:    rajesh.kumar0@scholarlab.edu")
        logger.info("  Password: student123")
        logger.info("=" * 70 + "\n")
        
        client.close()
        
    except Exception as e:
        logger.error(f"Seeding failed: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
