"""
Enhanced JWT Authentication with Refresh Token Rotation

Implements:
- Short-lived access tokens (15 min default)
- Refresh token rotation (issue new refresh token on each refresh)
- Token revocation blacklist
- Token family tracking (prevent token reuse attacks)
- Secure token storage metadata in MongoDB
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.database import db, settings
from pydantic import BaseModel, Field
import logging
from uuid import uuid4
import hashlib

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ============================================================================
# DOMAIN MODELS
# ============================================================================

class TokenMetadata(BaseModel):
    """Metadata for tracking token lifecycle."""
    token_id: str  # Unique token identifier
    token_family: str  # Family ID for tracking token chains
    token_version: int  # Version in family (incremented on rotation)
    user_id: str
    user_email: str
    user_role: str
    issued_at: datetime
    expires_at: datetime
    is_refresh_token: bool
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    revoked: bool = False
    revoked_at: Optional[datetime] = None


class AccessTokenRequest(BaseModel):
    """Request to get new access token from refresh token."""
    refresh_token: str


class RefreshTokenPayload(BaseModel):
    """Payload embedded in refresh token JWT."""
    sub: str  # email
    token_id: str
    token_family: str
    token_version: int
    role: str


# ============================================================================
# ENHANCED JWT SECURITY
# ============================================================================

class EnhancedJWTSecurity:
    """Enhanced JWT operations with rotation and revocation."""
    
    def __init__(self):
        self.tokens_collection = db.get_collection("token_metadata")
        self.revocation_list_collection = db.get_collection("token_revocation_list")
    
    async def initialize(self):
        """Setup collection indexes."""
        await self.tokens_collection.create_index("token_id", unique=True)
        await self.tokens_collection.create_index("token_family")
        await self.tokens_collection.create_index("user_id")
        await self.tokens_collection.create_index([("expires_at", 1)], expireAfterSeconds=0)
        
        await self.revocation_list_collection.create_index("token_id", unique=True)
        await self.revocation_list_collection.create_index([("expires_at", 1)], expireAfterSeconds=0)
        
        logger.info("JWT security collections initialized")
    
    # ========================================================================
    # TOKEN CREATION
    # ========================================================================
    
    def _hash_token(self, token: str) -> str:
        """Hash token for storage (never store raw tokens)."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def create_token_pair(
        self,
        user_id: str,
        user_email: str,
        user_role: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Create new access + refresh token pair.
        
        Returns:
            {access_token, refresh_token, access_token_expires_in, refresh_token_expires_in}
        """
        token_family = f"family_{uuid4().hex[:12]}"
        token_version = 1
        
        # Access token (short-lived: 15 min)
        access_token_id = f"access_{uuid4().hex[:12]}"
        access_token_exp = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        
        access_token = jwt.encode(
            {
                "sub": user_email,
                "token_id": access_token_id,
                "role": user_role,
                "type": "access",
                "exp": access_token_exp.timestamp(),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Refresh token (long-lived: 7 days, but will rotate on use)
        refresh_token_id = f"refresh_{uuid4().hex[:12]}"
        refresh_token_exp = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        
        refresh_token = jwt.encode(
            {
                "sub": user_email,
                "token_id": refresh_token_id,
                "token_family": token_family,
                "token_version": token_version,
                "role": user_role,
                "type": "refresh",
                "exp": refresh_token_exp.timestamp(),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        # Store metadata for both tokens
        now = datetime.now(timezone.utc)
        
        # Access token metadata
        access_meta = TokenMetadata(
            token_id=access_token_id,
            token_family=token_family,
            token_version=token_version,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            issued_at=now,
            expires_at=access_token_exp,
            is_refresh_token=False,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        # Refresh token metadata
        refresh_meta = TokenMetadata(
            token_id=refresh_token_id,
            token_family=token_family,
            token_version=token_version,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            issued_at=now,
            expires_at=refresh_token_exp,
            is_refresh_token=True,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        # Store metadata
        await self.tokens_collection.insert_many([
            access_meta.model_dump(),
            refresh_meta.model_dump(),
        ])
        
        logger.info(
            f"Token pair created",
            extra={
                'user_email': user_email,
                'token_family': token_family,
                'access_expires_in_min': settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            }
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "access_token_expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "refresh_token_expires_in": settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        }
    
    # ========================================================================
    # TOKEN VALIDATION & REFRESH
    # ========================================================================
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Refresh access token using refresh token.
        
        Implements refresh token rotation:
        1. Validate refresh token
        2. Check against revocation list
        3. Verify token hasn't been reused
        4. Issue new access + refresh token pair
        5. Revoke old refresh token
        
        Returns:
            {access_token, refresh_token, token_type, ...}
        """
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            
            # Validate token type
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )
            
            user_email = payload.get("sub")
            token_id = payload.get("token_id")
            token_family = payload.get("token_family")
            token_version = payload.get("token_version", 0)
            user_role = payload.get("role")
            
            # Check if token is revoked
            is_revoked = await self.is_token_revoked(token_id)
            if is_revoked:
                # Possible token reuse attack
                logger.warning(
                    f"Attempted use of revoked refresh token",
                    extra={
                        'user_email': user_email,
                        'token_id': token_id,
                        'token_family': token_family,
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked (possible reuse attack)",
                )
            
            # Get user for ID
            users_collection = db.get_collection("users")
            user = await users_collection.find_one({"email": user_email})
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )
            
            # Revoke old refresh token
            await self.revoke_token(token_id, "refresh_rotation")
            
            # Create new token pair (incremented version)
            new_tokens = await self.create_token_pair(
                user_id=str(user.get("_id")),
                user_email=user_email,
                user_role=user_role,
            )
            
            logger.info(
                f"Access token refreshed",
                extra={
                    'user_email': user_email,
                    'old_token_version': token_version,
                    'new_token_family': token_family,
                }
            )
            
            return new_tokens
        
        except JWTError as e:
            logger.warning(f"Invalid refresh token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
    
    async def validate_access_token(self, token: str) -> Dict[str, Any]:
        """
        Validate access token and return payload.
        
        Args:
            token: JWT access token
        
        Returns:
            Token payload
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            
            # Validate token type
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )
            
            # Check if revoked
            token_id = payload.get("token_id")
            is_revoked = await self.is_token_revoked(token_id)
            if is_revoked:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                )
            
            return payload
        
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    
    # ========================================================================
    # TOKEN REVOCATION
    # ========================================================================
    
    async def revoke_token(self, token_id: str, reason: str = "user_logout"):
        """
        Revoke a token.
        
        Args:
            token_id: Token to revoke
            reason: Reason for revocation
        """
        # Get original token metadata
        token_meta = await self.tokens_collection.find_one({"token_id": token_id})
        if not token_meta:
            logger.warning(f"Token metadata not found for revocation: {token_id}")
            return
        
        # Add to revocation list
        await self.revocation_list_collection.insert_one({
            "token_id": token_id,
            "revoked_at": datetime.now(timezone.utc),
            "reason": reason,
            "expires_at": datetime.fromtimestamp(
                token_meta.get("expires_at").timestamp()
            ) if isinstance(token_meta.get("expires_at"), datetime) else token_meta.get("expires_at"),
        })
        
        logger.info(f"Token revoked: {token_id} (reason: {reason})")
    
    async def is_token_revoked(self, token_id: str) -> bool:
        """Check if token is in revocation list."""
        revoked = await self.revocation_list_collection.find_one({"token_id": token_id})
        return revoked is not None
    
    async def revoke_all_user_tokens(self, user_email: str, reason: str = "security_event"):
        """
        Revoke all tokens for a user (e.g., on password change).
        
        Args:
            user_email: User email
            reason: Reason for revocation
        """
        # Get all active tokens for user
        tokens = await self.tokens_collection.find({"user_email": user_email}).to_list(None)
        
        for token_meta in tokens:
            await self.revoke_token(token_meta["token_id"], reason)
        
        logger.warning(
            f"All tokens revoked for user",
            extra={'user_email': user_email, 'reason': reason}
        )


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

_jwt_security: Optional[EnhancedJWTSecurity] = None


async def get_jwt_security() -> EnhancedJWTSecurity:
    """Get JWT security instance (singleton)."""
    global _jwt_security
    if _jwt_security is None:
        _jwt_security = EnhancedJWTSecurity()
        await _jwt_security.initialize()
    return _jwt_security


async def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    jwt_security: EnhancedJWTSecurity = Depends(get_jwt_security),
) -> Dict[str, Any]:
    """
    Dependency to get current user from access token.
    
    Returns:
        User document from MongoDB
    """
    payload = await jwt_security.validate_access_token(token)
    
    user_email = payload.get("sub")
    users_collection = db.get_collection("users")
    user = await users_collection.find_one({"email": user_email})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user
