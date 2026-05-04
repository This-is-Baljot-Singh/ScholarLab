import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["scholarlab"]
    users = await db.users.find({}, {"email": 1, "role": 1}).to_list(100)
    for u in users:
        print(f"Email: {u.get('email')}, Role: {u.get('role')}")

if __name__ == "__main__":
    asyncio.run(check())
