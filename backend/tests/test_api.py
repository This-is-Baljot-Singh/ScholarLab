import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_auth_and_rbac():
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Register a Faculty Member (Notice the /api/ prefix)
        response = await ac.post("/api/auth/register", json={
            "email": "dr.smith@university.edu",
            "password": "SecurePassword123!",
            "full_name": "Dr. John Smith",
            "role": "faculty"
        })
        assert response.status_code == 200
        assert "access_token" in response.json()
        
        faculty_token = response.json()["access_token"]
        
        # 2. Register a Student
        student_resp = await ac.post("/api/auth/register", json={
            "email": "student@university.edu",
            "password": "SecurePassword123!",
            "full_name": "Alice Johnson",
            "role": "student"
        })
        student_token = student_resp.json()["access_token"]

        # 3. Test RBAC: Student attempting to access Faculty dashboard
        unauthorized_req = await ac.get("/faculty/dashboard", headers={
            "Authorization": f"Bearer {student_token}"
        })
        assert unauthorized_req.status_code == 403 # Forbidden
        
        # 4. Test RBAC: Faculty accessing Faculty dashboard
        authorized_req = await ac.get("/faculty/dashboard", headers={
            "Authorization": f"Bearer {faculty_token}"
        })
        assert authorized_req.status_code == 200