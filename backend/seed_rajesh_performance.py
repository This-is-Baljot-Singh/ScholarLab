import asyncio
import os
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient

async def seed_performance():
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "scholarlab")
    
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]
    attendance_collection = db["attendance"]
    
    student_email = "rajesh.kumar1@scholarlab.edu"
    
    # Clear existing attendance for Rajesh
    await attendance_collection.delete_many({"email": student_email})
    
    # Generate 28 days of verified attendance (out of 30)
    attendance_records = []
    now = datetime.now(timezone.utc)
    
    for i in range(30):
        # 9:00 AM (zero delay)
        timestamp = (now - timedelta(days=i)).replace(hour=9, minute=0, second=0, microsecond=0)
        
        attendance_records.append({
            "email": student_email,
            "session_id": f"sess-{i}",
            "timestamp": timestamp,
            "status": "verified",
            "is_spoofed": False,
            "verification_confidence": 0.98,
            "device_fingerprint": "dev-12345",
            "validated_coordinates": {"lat": 28.5355, "lng": 77.3910}
        })
    
    if attendance_records:
        await attendance_collection.insert_many(attendance_records)
        print(f"✓ Seeded {len(attendance_records)} verified attendance records for {student_email}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_performance())
