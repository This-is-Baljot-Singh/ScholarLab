from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# --- Enums ---
class RoleEnum(str, Enum):
    student = "student"
    faculty = "faculty"
    admin = "admin"

# --- User Schema ---
# Handles Identity and Access Management [cite: 99]
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: RoleEnum

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: str = Field(alias="_id")
    hashed_password: str
    webauthn_credentials: List[Dict[str, Any]] = [] # Stores public key credentials [cite: 99]

# --- Geofence Schema ---
# Spatial Boundary Definitions [cite: 99]
class GeoJSONPolygon(BaseModel):
    type: str = "Polygon"
    coordinates: List[List[List[float]]] # [[[lng, lat], [lng, lat], ...]]

class GeofenceModel(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    name: str
    boundary: GeoJSONPolygon

# --- Curriculum Knowledge Graph Schema ---
# Ontological Syllabus Mapping [cite: 99]
class CurriculumNode(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    course_id: str
    title: str
    node_type: str # e.g., "module", "topic"
    prerequisites: List[str] = [] # List of parent node IDs
    resource_uris: List[str] = [] # Links to PDF slides, quizzes, etc.

# --- Attendance Log Schema ---
# Time-Series Event Data [cite: 99]
class AttendanceLog(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    user_id: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    validated_coordinates: Dict[str, float] # {"lat": float, "lng": float}
    device_fingerprint: str # E.g., BSSID or hardware signature [cite: 99]
    is_spoofed: bool = False

# --- Authentication & Token Schemas ---
class UserResponse(BaseModel):
    email: str
    full_name: str
    role: RoleEnum

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[RoleEnum] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class WebAuthnOptionsRequest(BaseModel):
    email: EmailStr

class WebAuthnRegistrationVerify(BaseModel):
    email: EmailStr
    credential: Dict[str, Any]

class WebAuthnAuthVerify(BaseModel):
    email: EmailStr
    credential: Dict[str, Any]