from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime, timezone
from app.database import geofences_collection
from app.security import get_current_user, require_role
from app.schemas import RoleEnum

router = APIRouter(tags=["Geofences"])

class GeofenceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # "radial" or "polygon"
    coordinates: List[Any] # Radial: [lon, lat] | Polygon: [[lon, lat], [lon, lat], ...]
    radius: Optional[float] = None
    expected_bssids: Optional[List[str]] = []

# FIX: Use "" instead of "/" to prevent strict slash 404 errors
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_geofence(geofence: GeofenceCreate, current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin]))):
    # MongoDB 2dsphere indexing requires strict GeoJSON formatting
    if geofence.type == "polygon":
        if geofence.coordinates[0] != geofence.coordinates[-1]:
            geofence.coordinates.append(geofence.coordinates[0]) # Close the loop
        geo_json = {"type": "Polygon", "coordinates": [geofence.coordinates]}
    elif geofence.type == "radial":
        geo_json = {"type": "Point", "coordinates": geofence.coordinates}
    else:
        raise HTTPException(status_code=400, detail="Type must be radial or polygon")

    doc = {
        "name": geofence.name,
        "description": geofence.description,
        "type": geofence.type,
        "boundary": geo_json,
        "radius": geofence.radius,
        "expected_bssids": geofence.expected_bssids,
        "created_by": str(current_user["_id"]),
        "created_at": datetime.now(timezone.utc)
    }
    
    result = await geofences_collection.insert_one(doc)
    return {"message": "Geofence established", "geofence_id": str(result.inserted_id)}

@router.get("")
async def list_geofences(current_user: dict = Depends(get_current_user)):
    cursor = geofences_collection.find({})
    geofences = await cursor.to_list(length=100)
    for g in geofences:
        g["_id"] = str(g["_id"])
    return geofences