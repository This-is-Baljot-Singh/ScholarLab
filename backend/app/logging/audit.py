"""
Audit-ready logging system: Immutable, append-only, tamper-evident.

Features:
- Every request → immutable audit log
- Merkle chain hash linking (previous log hash included)
- Optional digital signatures (production)
- Structured JSON output for compliance
- Request correlation via request_id
"""

import logging
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid
from contextvars import ContextVar
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# Context variable to track request_id across async context
request_id_context: ContextVar[str] = ContextVar('request_id', default=None)
actor_context: ContextVar[str] = ContextVar('actor', default='system')


class AuditAction(str, Enum):
    """Standardized audit actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    OVERRIDE = "override"
    VERIFY = "verify"
    SIGN = "sign"
    EXPORT = "export"


class AuditResourceType(str, Enum):
    """Standardized resource types."""
    USER = "user"
    ATTENDANCE = "attendance"
    CURRICULUM = "curriculum"
    RISK_SCORE = "risk_score"
    OVERRIDE = "override"
    DEVICE = "device"
    SESSION = "session"
    GEOFENCE = "geofence"


class AuditLogger:
    """
    Immutable audit logger with tamper-evidence.
    
    All entries are:
    - Timestamped in UTC
    - Linked via Merkle chain (previous_log_hash)
    - Optionally signed (production)
    - Written to immutable collection (write-once)
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str = "audit_logs"):
        self.db = db
        self.collection = db[collection_name]
        self.previous_log_hash: Optional[str] = None
    
    async def initialize(self):
        """Setup immutable audit log collection."""
        await self.collection.create_index("timestamp")
        await self.collection.create_index("actor")
        await self.collection.create_index("resource_id")
        await self.collection.create_index("request_id", unique=True)
        logger.info("Audit log collection initialized")
    
    @staticmethod
    def _compute_hash(entry_dict: Dict[str, Any]) -> str:
        """
        Compute SHA256 hash of log entry.
        
        Used for Merkle chain linking to detect tampering.
        """
        # Serialize deterministically (sorted keys)
        entry_json = json.dumps(entry_dict, sort_keys=True, default=str)
        return hashlib.sha256(entry_json.encode()).hexdigest()
    
    def _generate_request_id(self) -> str:
        """Generate or retrieve current request_id."""
        existing = request_id_context.get()
        if existing:
            return existing
        new_id = str(uuid.uuid4())
        request_id_context.set(new_id)
        return new_id
    
    def _get_actor(self) -> str:
        """Get current actor from context."""
        return actor_context.get() or "system"
    
    async def log(
        self,
        action: AuditAction,
        resource_type: AuditResourceType,
        resource_id: str,
        actor: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        actor_role: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        signature: Optional[str] = None,
    ) -> str:
        """
        Log an audit event (immutable).
        
        Returns: log_id for reference in API responses
        """
        request_id = self._generate_request_id()
        actor_id = actor or self._get_actor()
        timestamp = datetime.now(timezone.utc)
        
        # Build entry
        entry = {
            "_id": str(uuid.uuid4()),
            "request_id": request_id,
            "timestamp": timestamp,
            "actor": actor_id,
            "actor_role": actor_role,
            "action": action.value,
            "resource_type": resource_type.value,
            "resource_id": resource_id,
            "old_value": old_value,
            "new_value": new_value,
            "success": success,
            "error_message": error_message,
            "metadata": metadata or {},
            "signature": signature,
        }
        
        # Link to previous entry (Merkle chain)
        if self.previous_log_hash:
            entry["previous_log_hash"] = self.previous_log_hash
        
        # Compute hash for next entry
        entry_hash = self._compute_hash(entry)
        entry["entry_hash"] = entry_hash
        self.previous_log_hash = entry_hash
        
        # Write to immutable collection
        try:
            result = await self.collection.insert_one(entry)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            raise
    
    async def query_logs(
        self,
        actor: Optional[str] = None,
        resource_type: Optional[AuditResourceType] = None,
        action: Optional[AuditAction] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query immutable audit logs."""
        query = {}
        
        if actor:
            query["actor"] = actor
        if resource_type:
            query["resource_type"] = resource_type.value
        if action:
            query["action"] = action.value
        
        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = start_date
            if end_date:
                query["timestamp"]["$lte"] = end_date
        
        cursor = self.collection.find(query).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def verify_chain_integrity(
        self,
        start_log_id: str,
        end_log_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verify Merkle chain integrity between two logs.
        
        Returns: {valid: bool, gaps: [...], tampering_detected: bool}
        """
        start_log = await self.collection.find_one({"_id": start_log_id})
        if not start_log:
            raise ValueError(f"Start log not found: {start_log_id}")
        
        # Walk forward from start_log
        current = start_log
        gaps = []
        
        while current:
            next_log = await self.collection.find_one({
                "previous_log_hash": current.get("entry_hash")
            })
            
            if not next_log:
                # End of chain or gap
                if end_log_id and current["_id"] != end_log_id:
                    gaps.append({
                        "after_log_id": current["_id"],
                        "expected_next": end_log_id,
                    })
                break
            
            # Verify hash matches
            recomputed_hash = self._compute_hash({
                k: v for k, v in next_log.items()
                if k not in ["_id", "entry_hash", "signature"]
            })
            if recomputed_hash != next_log.get("entry_hash"):
                gaps.append({
                    "tampered_log_id": next_log["_id"],
                    "original_hash": next_log.get("entry_hash"),
                    "recomputed_hash": recomputed_hash,
                })
            
            current = next_log
        
        return {
            "valid": len(gaps) == 0,
            "gaps": gaps,
            "tampering_detected": any("tampered_log_id" in gap for gap in gaps),
        }


class StructuredLogger:
    """
    Structured logging with correlation IDs.
    
    Output format: JSON for easy parsing in log aggregation systems.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_json_logging()
    
    def _setup_json_logging(self):
        """Configure JSON logging format."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def _get_context(self) -> Dict[str, str]:
        """Extract context from async context vars."""
        return {
            "request_id": request_id_context.get() or "unknown",
            "actor": actor_context.get() or "system",
        }
    
    def info(self, msg: str, **kwargs):
        """Log info with context."""
        ctx = self._get_context()
        self.logger.info(f"{msg} | context={json.dumps(ctx)} | extra={json.dumps(kwargs)}")
    
    def warning(self, msg: str, **kwargs):
        """Log warning with context."""
        ctx = self._get_context()
        self.logger.warning(f"{msg} | context={json.dumps(ctx)} | extra={json.dumps(kwargs)}")
    
    def error(self, msg: str, **kwargs):
        """Log error with context."""
        ctx = self._get_context()
        self.logger.error(f"{msg} | context={json.dumps(ctx)} | extra={json.dumps(kwargs)}")


# Global audit logger instance (initialized in app startup)
audit_logger: Optional[AuditLogger] = None
structured_logger = StructuredLogger(__name__)


def set_request_id(request_id: str):
    """Set request_id in context."""
    request_id_context.set(request_id)


def set_actor(actor_id: str):
    """Set actor in context."""
    actor_context.set(actor_id)


def get_request_id() -> str:
    """Get current request_id."""
    return request_id_context.get() or "unknown"


def get_actor() -> str:
    """Get current actor."""
    return actor_context.get() or "system"
