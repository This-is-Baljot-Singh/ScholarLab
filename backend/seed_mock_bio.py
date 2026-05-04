import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MOCK_CREDENTIAL_ID = "bW9jay1jcmVkZW50aWFsLTEyMzQ" # 24 chars, valid base64url
MOCK_PUBLIC_KEY = b'\xa5\x01\x02\x03& \x01!X \x1b\x0c\xed\x81\x11\x97\x8b\x13\x89\xab\xbd\x9e\x98\xca\x99\x81\x0c\xaf\x8f\x86\x11\xbc\x08\x0e\x1a\x11\x8d\x1f\xab\x11\x99\x8b"X \x13\x0b\xab\x11\xab\x81\x1b\x13\x11\x99\x1b\x13\x11\x1b\x11\x1b\x11\x1b\x11\x1b\x11\x1b\x11\x1b\x11\x1b\x11\x1b\x11\x1b'

async def seed():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["scholarlab"]
    
    # Give deepika.chopra0@scholarlab.edu the mock credential
    await db.users.update_one({"email": "deepika.chopra0@scholarlab.edu"}, {
        "$set": {
            "webauthn_credentials": [
                {
                    "credential_id": MOCK_CREDENTIAL_ID,
                    "public_key": MOCK_PUBLIC_KEY,
                    "sign_count": 0,
                    "transports": ["internal"]
                }
            ]
        }
    })
    print(f"Seeded deepika.chopra0@scholarlab.edu with mock ID: {MOCK_CREDENTIAL_ID}")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
