from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.database import users_collection, settings
from app.schemas import (UserCreate, Token, UserResponse, RoleEnum, LoginRequest,
                         WebAuthnOptionsRequest, WebAuthnRegistrationVerify, WebAuthnAuthVerify)
from app.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from datetime import timedelta
from typing import Dict, Any
from jose import jwt, JWTError
import logging

# WebAuthn Imports
from webauthn import (
    generate_registration_options, verify_registration_response,
    generate_authentication_options, verify_authentication_response,
    options_to_json, base64url_to_bytes
)
from webauthn.helpers.structs import RegistrationCredential, AuthenticationCredential

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

# --- WebAuthn Configuration ---
RP_ID = "localhost" # Update to your production domain later
RP_NAME = "ScholarLab Verification"
ORIGIN = "http://localhost:5173" # Vite default port

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest):
    """
    Login with email and password using JSON request body.
    """
    logger.info(f"Login attempt for email: {credentials.email}")
    
    # Find user by email
    user = await users_collection.find_one({"email": credentials.email})
    
    if not user:
        logger.warning(f"User not found: {credentials.email}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Verify password
    password_valid = verify_password(credentials.password, user.get("hashed_password", ""))
    if not password_valid:
        logger.warning(f"Invalid password for user: {credentials.email}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    logger.info(f"Successful login for: {credentials.email}")
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": user["email"], "role": user["role"]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user["email"]},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    # Return token and user info
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserResponse(
            email=user["email"],
            full_name=user["full_name"],
            role=RoleEnum(user["role"])
        )
    }

@router.post("/register", response_model=Token)
async def register(user: UserCreate):
    """
    Register a new user.
    Returns access token, refresh token, and user info.
    """
    # Check if email already exists
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    user_dict = user.model_dump()
    user_dict.pop("password", None)
    user_dict["hashed_password"] = hashed_password
    user_dict["webauthn_credentials"] = []
    
    await users_collection.insert_one(user_dict)
    
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserResponse(email=user.email, full_name=user.full_name, role=user.role)
    }

@router.post("/token/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    """
    Verify the refresh token and issue a fresh access token.
    """
    try:
        # Decode the refresh token
        payload = jwt.decode(request.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
            
        # Verify user still exists
        user = await users_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
            
        # Generate new tokens
        access_token = create_access_token(
            data={"sub": user["email"], "role": user["role"]},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        new_refresh_token = create_refresh_token(
            data={"sub": user["email"]},
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": UserResponse(
                email=user["email"],
                full_name=user["full_name"],
                role=RoleEnum(user["role"])
            )
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

@router.post("/webauthn/register/options")
async def generate_webauthn_registration_options(request: WebAuthnOptionsRequest):
    """Generate cryptographic challenge for new authenticator registration."""
    user = await users_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_credentials = user.get("webauthn_credentials", [])
    
    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=str(user["_id"]).encode(),
        user_name=user["email"],
        exclude_credentials=[cred["credential_id"] for cred in existing_credentials]
    )
    
    # Store challenge temporarily for verification
    await users_collection.update_one(
        {"_id": user["_id"]}, 
        {"$set": {"current_challenge": options.challenge}}
    )
    
    return options_to_json(options)

@router.post("/webauthn/register/verify")
async def verify_webauthn_registration(request: WebAuthnRegistrationVerify):
    """Verify the authenticator's response and save the public key."""
    user = await users_collection.find_one({"email": request.email})
    if not user or "current_challenge" not in user:
        raise HTTPException(status_code=400, detail="Challenge not found")

    try:
        verification = verify_registration_response(
            credential=request.credential,
            expected_challenge=user["current_challenge"],
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID
        )
        
        # Store the credential
        new_credential = {
            "credential_id": verification.credential_id,
            "public_key": verification.credential_public_key,
            "sign_count": verification.sign_count,
            "transports": request.credential.get("response", {}).get("transports", [])
        }
        
        await users_collection.update_one(
            {"_id": user["_id"]},
            {
                "$push": {"webauthn_credentials": new_credential},
                "$unset": {"current_challenge": ""}
            }
        )
        return {"status": "success", "message": "Authenticator registered"}
    except Exception as e:
        logger.error(f"WebAuthn verification failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Registration verification failed")

@router.post("/webauthn/authenticate/options")
async def generate_webauthn_auth_options(request: WebAuthnOptionsRequest):
    """Generate challenge for verifying presence during attendance."""
    user = await users_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    options = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=[cred["credential_id"] for cred in user.get("webauthn_credentials", [])]
    )
    
    await users_collection.update_one(
        {"_id": user["_id"]}, 
        {"$set": {"current_challenge": options.challenge}}
    )
    
    return options_to_json(options)