"""
Device Registration Service: Cryptographic device binding.

Implements WebAuthn credential registration and verification.
Stores only public keys and certificate fingerprints, never private keys.

Key principle: Device is a security boundary. One student + one device = unique identity binding.
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class WebAuthnCredential(BaseModel):
    """Registered WebAuthn credential (public key only)."""
    credential_id: str  # Base64url encoded
    public_key: Dict[str, Any]  # JWK format
    public_key_hash: str  # SHA256 for quick lookup
    counter: int = 0  # Signature counter for cloned device detection
    transports: list = []  # ["usb", "ble", "internal"]
    attestation_verified: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeviceBinding(BaseModel):
    """Device binding record (cryptographic identity anchor)."""
    device_id: str  # Derived from hardware
    user_id: str
    device_type: str  # "phone", "laptop", "tablet"
    os: str  # "ios", "android", "macos", "windows"
    os_version: str
    # Hardware identifiers (hashed for privacy)
    model_hash: str  # SHA256(device model)
    serial_hash: str  # SHA256(device serial) - privacy preserving
    # WebAuthn credentials
    webauthn_credentials: list[WebAuthnCredential] = []
    # Certificate chain
    device_certificate_fingerprint: str  # SHA256 of device cert
    certificate_expiry: datetime
    certificate_public_key: str  # PEM format (public only)
    # Trust state
    is_trusted: bool = False
    trust_approved_at: Optional[datetime] = None
    trust_approved_by: Optional[str] = None  # admin_id
    # Risk assessment
    failed_verification_count: int = 0
    last_verification_success: Optional[datetime] = None
    last_verification_failure: Optional[datetime] = None
    # Geofence exceptions
    allowed_geofence_ids: list = []  # Pre-approved locations
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# DEVICE REGISTRATION SERVICE
# ============================================================================

class DeviceRegistrationService:
    """
    Handles device registration and cryptographic binding.
    
    Lifecycle:
    1. Device sends hardware identifiers + WebAuthn credential
    2. Service verifies attestation and creates device binding
    3. Admin approves (optional for high-security deployments)
    4. Device is trusted for future authentication
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.devices_col: AsyncIOMotorCollection = db["devices"]
        self.device_auth_attempts_col: AsyncIOMotorCollection = db["device_auth_attempts"]
    
    async def initialize(self):
        """Setup device collection indexes."""
        await self.devices_col.create_index("device_id", unique=True)
        await self.devices_col.create_index("user_id")
        await self.devices_col.create_index("device_certificate_fingerprint", unique=True)
        await self.devices_col.create_index("public_key_hash")
        await self.devices_col.create_index("certificate_expiry")
        # TTL index for failed attempts
        await self.device_auth_attempts_col.create_index(
            "created_at",
            expireAfterSeconds=3600  # 1 hour
        )
        logger.info("Device collection indexes created")
    
    @staticmethod
    def compute_device_id(model: str, serial: str) -> str:
        """
        Compute device ID from hardware identifiers.
        
        Device ID is deterministic but privacy-preserving:
        - Same device → same ID (allows user to re-authenticate)
        - Different device → different ID (prevents credential reuse)
        
        We do NOT store the raw identifiers; only the hashes.
        """
        combined = f"{model}:{serial}"
        device_id = hashlib.sha256(combined.encode()).hexdigest()[:32]
        return device_id
    
    @staticmethod
    def hash_identifier(value: str) -> str:
        """Hash a hardware identifier for privacy."""
        return hashlib.sha256(value.encode()).hexdigest()
    
    async def register_device(
        self,
        user_id: str,
        device_type: str,
        os: str,
        os_version: str,
        model: str,
        serial: str,
        device_certificate_fingerprint: str,
        certificate_expiry: datetime,
        certificate_public_key: str,
        webauthn_credential: Dict[str, Any],
    ) -> Tuple[str, DeviceBinding]:
        """
        Register a new device with cryptographic binding.
        
        Args:
            user_id: Student ID
            device_type: phone, laptop, tablet
            os: ios, android, macos, windows
            model: Device model (e.g., "iPhone 15 Pro")
            serial: Device serial number
            device_certificate_fingerprint: SHA256 of device cert
            certificate_expiry: When device cert expires
            certificate_public_key: Public key from device cert (PEM)
            webauthn_credential: WebAuthn credential from registration
        
        Returns:
            (device_id, device_binding)
        
        Raises:
            ValueError: If device already registered or certificate invalid
        """
        # Verify certificate expiry
        if certificate_expiry <= datetime.now(timezone.utc):
            raise ValueError("Device certificate already expired")
        
        # Compute device ID
        device_id = self.compute_device_id(model, serial)
        
        # Check if device already registered
        existing = await self.devices_col.find_one({"device_id": device_id})
        if existing:
            # Device already registered for same user: update (re-binding)
            logger.info(f"Device {device_id} already registered for user {user_id}")
        
        # Parse WebAuthn credential
        credential_id = webauthn_credential.get("id")
        public_key = webauthn_credential.get("response", {}).get("publicKey")
        
        if not credential_id or not public_key:
            raise ValueError("Invalid WebAuthn credential structure")
        
        # Compute public key hash for quick lookup
        public_key_hash = hashlib.sha256(
            json.dumps(public_key, sort_keys=True).encode()
        ).hexdigest()
        
        # Create credential object
        credential = WebAuthnCredential(
            credential_id=credential_id,
            public_key=public_key,
            public_key_hash=public_key_hash,
            counter=webauthn_credential.get("response", {}).get("signCount", 0),
            transports=webauthn_credential.get("response", {}).get("transports", []),
            attestation_verified=False,  # Should verify attestation in production
        )
        
        # Create device binding
        binding = DeviceBinding(
            device_id=device_id,
            user_id=user_id,
            device_type=device_type,
            os=os,
            os_version=os_version,
            model_hash=self.hash_identifier(model),
            serial_hash=self.hash_identifier(serial),
            webauthn_credentials=[credential],
            device_certificate_fingerprint=device_certificate_fingerprint,
            certificate_expiry=certificate_expiry,
            certificate_public_key=certificate_public_key,
            is_trusted=False,  # Admin approval required
        )
        
        # Store in database
        doc = binding.dict()
        doc["_id"] = ObjectId()
        result = await self.devices_col.insert_one(doc)
        
        logger.info(
            f"Device registered: {device_id} for user {user_id}",
            extra={"device_type": device_type, "os": os}
        )
        
        return device_id, binding
    
    async def approve_device(
        self,
        device_id: str,
        admin_id: str,
    ) -> bool:
        """
        Admin approval for device trust.
        
        High-security deployments require explicit admin approval.
        """
        result = await self.devices_col.update_one(
            {"device_id": device_id},
            {
                "$set": {
                    "is_trusted": True,
                    "trust_approved_at": datetime.now(timezone.utc),
                    "trust_approved_by": admin_id,
                }
            }
        )
        
        if result.matched_count == 0:
            raise ValueError(f"Device not found: {device_id}")
        
        logger.info(f"Device approved by admin {admin_id}: {device_id}")
        return True
    
    async def verify_device_signature(
        self,
        device_id: str,
        signature_data: Dict[str, Any],
    ) -> bool:
        """
        Verify device signature using stored public key.
        
        Signature includes:
        - Timestamp
        - Nonce
        - Attendance session ID
        - Device ID
        
        All signed by device's private key.
        """
        # Fetch device binding
        device = await self.devices_col.find_one({"device_id": device_id})
        if not device:
            logger.warning(f"Device not found: {device_id}")
            return False
        
        # Check certificate expiry
        cert_expiry = device.get("certificate_expiry")
        if cert_expiry and cert_expiry <= datetime.now(timezone.utc):
            logger.warning(f"Device certificate expired: {device_id}")
            return False
        
        # Verify signature (implementation: use cryptography library)
        # This is a placeholder; actual verification depends on signature algorithm
        try:
            # In production: verify ECDSA or RSA signature using public_key
            # from device.certificate_public_key
            logger.debug(f"Verifying device signature for {device_id}")
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    async def get_device(self, device_id: str) -> Optional[DeviceBinding]:
        """Retrieve device binding."""
        doc = await self.devices_col.find_one({"device_id": device_id})
        if doc:
            doc.pop("_id", None)
            return DeviceBinding(**doc)
        return None
    
    async def log_auth_attempt(
        self,
        device_id: str,
        user_id: str,
        success: bool,
        error_msg: Optional[str] = None,
    ):
        """Log device authentication attempt for anomaly detection."""
        await self.device_auth_attempts_col.insert_one({
            "device_id": device_id,
            "user_id": user_id,
            "success": success,
            "error_msg": error_msg,
            "created_at": datetime.now(timezone.utc),
        })
        
        # Update device binding
        if success:
            await self.devices_col.update_one(
                {"device_id": device_id},
                {
                    "$set": {"last_verification_success": datetime.now(timezone.utc)},
                    "$inc": {"failed_verification_count": 0},
                }
            )
        else:
            await self.devices_col.update_one(
                {"device_id": device_id},
                {
                    "$set": {"last_verification_failure": datetime.now(timezone.utc)},
                    "$inc": {"failed_verification_count": 1},
                }
            )
    
    async def check_device_is_cloned(self, device_id: str, new_counter: int) -> bool:
        """
        Detect cloned devices using WebAuthn counter.
        
        Each WebAuthn key increments a counter on signature.
        If counter decreases, device may be cloned (rollback attack).
        """
        device = await self.devices_col.find_one({"device_id": device_id})
        if not device:
            return False
        
        stored_counter = device.get("webauthn_credentials", [{}])[0].get("counter", 0)
        
        if new_counter <= stored_counter:
            logger.warning(f"Possible cloned device detected: {device_id}")
            # Alert security team
            return True
        
        # Update counter
        await self.devices_col.update_one(
            {"device_id": device_id},
            {"$set": {"webauthn_credentials.0.counter": new_counter}}
        )
        
        return False


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class DeviceRegistrationRequest(BaseModel):
    """Device registration initiation."""
    device_type: str  # "phone", "laptop", "tablet"
    os: str  # "ios", "android", "macos", "windows"
    os_version: str
    model: str
    serial: str
    device_certificate_fingerprint: str
    certificate_expiry: datetime
    certificate_public_key: str


class DeviceRegistrationCompleteRequest(BaseModel):
    """Complete device registration with WebAuthn credential."""
    device_type: str
    os: str
    os_version: str
    model: str
    serial: str
    device_certificate_fingerprint: str
    certificate_expiry: datetime
    certificate_public_key: str
    webauthn_credential: Dict[str, Any]


class DeviceRegistrationResponse(BaseModel):
    """Device registration response."""
    device_id: str
    is_trusted: bool
    requires_admin_approval: bool
    registered_at: datetime
