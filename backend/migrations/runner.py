"""
MongoDB migration script: Manages indexes, schema validation, and versioning.

Migrations are idempotent: safe to run multiple times.
Each migration is timestamped and tracked in `schema_migrations` collection.

Run: python -m app.migrations.runner --env production
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any
import pymongo
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class MigrationType(str, Enum):
    """Types of migrations."""
    INDEX_CREATE = "index_create"
    SCHEMA_VALIDATION = "schema_validation"
    DATA_TRANSFORM = "data_transform"
    COLLECTION_CREATE = "collection_create"


class Migration:
    """Base migration class."""
    
    version: str  # e.g., "001_initial_schema"
    description: str
    migration_type: MigrationType
    
    async def up(self, db: AsyncIOMotorDatabase):
        """Apply migration."""
        raise NotImplementedError
    
    async def down(self, db: AsyncIOMotorDatabase):
        """Rollback migration."""
        raise NotImplementedError


# ============================================================================
# MIGRATIONS
# ============================================================================

class Migration001InitialSchema(Migration):
    """001: Create immutable event collections with indexes."""
    
    version = "001_initial_schema"
    description = "Create core collections with indexes for zero-trust architecture"
    migration_type = MigrationType.INDEX_CREATE
    
    async def up(self, db: AsyncIOMotorDatabase):
        """Apply migration."""
        logger.info(f"Applying {self.version}...")
        
        # Users collection - mutable profile state
        await db.create_collection("users", check_exists=True)
        users_col = db["users"]
        await users_col.create_index("email", unique=True, sparse=True)
        await users_col.create_index("role")
        await users_col.create_index("created_at")
        logger.info("✓ Created users collection with indexes")
        
        # Devices collection - device registry
        await db.create_collection("devices", check_exists=True)
        devices_col = db["devices"]
        await devices_col.create_index("device_id", unique=True)
        await devices_col.create_index("user_id")
        await devices_col.create_index("certificate_expiry")
        logger.info("✓ Created devices collection with indexes")
        
        # Sessions collection - active sessions
        await db.create_collection("sessions", check_exists=True)
        sessions_col = db["sessions"]
        await sessions_col.create_index("session_id", unique=True)
        await sessions_col.create_index("user_id")
        await sessions_col.create_index("expires_at", expireAfterSeconds=0)
        logger.info("✓ Created sessions collection with TTL index")
        
        # Rooms/Geofences - mutable venue metadata
        await db.create_collection("geofences", check_exists=True)
        geofences_col = db["geofences"]
        await geofences_col.create_index([("boundary", pymongo.GEOSPHERE)])
        await geofences_col.create_index("geofence_id", unique=True)
        logger.info("✓ Created geofences collection with 2dsphere index")
        
        # Courses - mutable curriculum structure
        await db.create_collection("courses", check_exists=True)
        courses_col = db["courses"]
        await courses_col.create_index("course_id", unique=True)
        await courses_col.create_index("faculty_id")
        await courses_col.create_index("course_code", unique=True)
        logger.info("✓ Created courses collection with indexes")
        
        # Curriculum nodes - mutable
        await db.create_collection("curriculum_nodes", check_exists=True)
        curr_col = db["curriculum_nodes"]
        await curr_col.create_index("node_id", unique=True)
        await curr_col.create_index("course_id")
        await curr_col.create_index("prerequisites")
        logger.info("✓ Created curriculum_nodes collection")
        
        # ============ IMMUTABLE EVENT COLLECTIONS ============
        
        # Attendance events - IMMUTABLE append-only
        await db.create_collection("attendance_events", check_exists=True)
        att_col = db["attendance_events"]
        await att_col.create_index("timestamp")
        await att_col.create_index("user_id")
        await att_col.create_index("course_id")
        await att_col.create_index("session_id", unique=True)
        await att_col.create_index([("timestamp", pymongo.ASCENDING)], expireAfterSeconds=7776000)  # 90 days
        logger.info("✓ Created attendance_events (immutable) with TTL")
        
        # Curriculum events - IMMUTABLE append-only
        await db.create_collection("curriculum_events", check_exists=True)
        curr_events_col = db["curriculum_events"]
        await curr_events_col.create_index("timestamp")
        await curr_events_col.create_index("session_id")
        await curr_events_col.create_index("course_id")
        logger.info("✓ Created curriculum_events (immutable)")
        
        # Risk events - IMMUTABLE append-only
        await db.create_collection("risk_events", check_exists=True)
        risk_col = db["risk_events"]
        await risk_col.create_index("timestamp")
        await risk_col.create_index("user_id")
        await risk_col.create_index("course_id")
        await risk_col.create_index([("timestamp", pymongo.ASCENDING)], expireAfterSeconds=7776000)  # 90 days
        logger.info("✓ Created risk_events (immutable) with TTL")
        
        # Override events - IMMUTABLE append-only
        await db.create_collection("override_events", check_exists=True)
        override_col = db["override_events"]
        await override_col.create_index("timestamp")
        await override_col.create_index("actor")
        await override_col.create_index("entity_id")
        logger.info("✓ Created override_events (immutable)")
        
        # ============ AUDIT LOG COLLECTION ============
        
        # Audit logs - IMMUTABLE, tamper-evident
        await db.create_collection("audit_logs", check_exists=True)
        audit_col = db["audit_logs"]
        await audit_col.create_index("timestamp")
        await audit_col.create_index("request_id", unique=True)
        await audit_col.create_index("actor")
        await audit_col.create_index("resource_id")
        await audit_col.create_index("entry_hash", unique=True)
        # Merkle chain linking
        await audit_col.create_index("previous_log_hash", sparse=True)
        logger.info("✓ Created audit_logs (immutable, tamper-evident)")
        
        # Schema migrations tracking
        await db.create_collection("schema_migrations", check_exists=True)
        await db["schema_migrations"].create_index("version", unique=True)
        logger.info("✓ Created schema_migrations tracking collection")
    
    async def down(self, db: AsyncIOMotorDatabase):
        """Rollback migration."""
        logger.info(f"Rolling back {self.version}...")
        collections = [
            "users", "devices", "sessions", "geofences", "courses",
            "curriculum_nodes", "attendance_events", "curriculum_events",
            "risk_events", "override_events", "audit_logs"
        ]
        for col in collections:
            try:
                await db.drop_collection(col)
                logger.info(f"✓ Dropped {col}")
            except Exception as e:
                logger.warning(f"Could not drop {col}: {e}")


class Migration002AddRoleBasedIndexes(Migration):
    """002: Add indexes for role-based queries."""
    
    version = "002_add_role_indexes"
    description = "Add indexes for faculty/admin audit queries"
    migration_type = MigrationType.INDEX_CREATE
    
    async def up(self, db: AsyncIOMotorDatabase):
        """Apply migration."""
        logger.info(f"Applying {self.version}...")
        
        # Compound index for audit queries: (actor, action, timestamp)
        audit_col = db["audit_logs"]
        await audit_col.create_index([
            ("actor", pymongo.ASCENDING),
            ("action", pymongo.ASCENDING),
            ("timestamp", pymongo.DESCENDING),
        ])
        logger.info("✓ Created compound index on audit_logs (actor, action, timestamp)")
        
        # Index for override queries: (actor, timestamp)
        override_col = db["override_events"]
        await override_col.create_index([
            ("actor", pymongo.ASCENDING),
            ("timestamp", pymongo.DESCENDING),
        ])
        logger.info("✓ Created compound index on override_events (actor, timestamp)")
    
    async def down(self, db: AsyncIOMotorDatabase):
        """Rollback migration."""
        logger.info(f"Rolling back {self.version}...")
        # Manual index deletion would go here if needed


class Migration003CurriculumPipeline(Migration):
    """003: Create curriculum pipeline collections (audio→topics→mappings→unlock)."""
    
    version = "003_curriculum_pipeline"
    description = "Create collections for privacy-preserving curriculum processing"
    migration_type = MigrationType.COLLECTION_CREATE
    
    async def up(self, db: AsyncIOMotorDatabase):
        """Apply migration."""
        logger.info(f"Applying {self.version}...")
        
        # Topic mappings: extracted topics matched to curriculum nodes
        await db.create_collection("curriculum_topic_mappings", check_exists=True)
        mappings_col = db["curriculum_topic_mappings"]
        await mappings_col.create_index("session_id")
        await mappings_col.create_index("course_id")
        await mappings_col.create_index("topic")
        await mappings_col.create_index("created_at")
        logger.info("✓ Created curriculum_topic_mappings (topic extraction→syllabi matching results)")
        
        # Embeddings cache: precomputed node embeddings for cosine similarity
        await db.create_collection("curriculum_node_embeddings_cache", check_exists=True)
        cache_col = db["curriculum_node_embeddings_cache"]
        await cache_col.create_index("node_id", unique=True)
        await cache_col.create_index("course_id")
        logger.info("✓ Created curriculum_node_embeddings_cache (precomputed embeddings)")
        
        # Verification tasks: below-threshold mappings for faculty review
        await db.create_collection("curriculum_verification_tasks", check_exists=True)
        tasks_col = db["curriculum_verification_tasks"]
        await tasks_col.create_index("task_id", unique=True)
        await tasks_col.create_index("session_id")
        await tasks_col.create_index("course_id")
        await tasks_col.create_index("status")
        await tasks_col.create_index("faculty_id")
        await tasks_col.create_index("created_at")
        logger.info("✓ Created curriculum_verification_tasks (manual review workflows)")
        
        # Verified mappings: faculty-verified curriculum matches
        await db.create_collection("curriculum_verified_mappings", check_exists=True)
        verified_col = db["curriculum_verified_mappings"]
        await verified_col.create_index("session_id")
        await verified_col.create_index("course_id")
        await verified_col.create_index("task_id")
        logger.info("✓ Created curriculum_verified_mappings (faculty decisions)")
        
        # Curriculum resources: lecture notes, slides, recordings, etc.
        await db.create_collection("curriculum_resources", check_exists=True)
        resources_col = db["curriculum_resources"]
        await resources_col.create_index("curriculum_node_id")
        await resources_col.create_index("resource_type")
        await resources_col.create_index("requires_attendance")
        logger.info("✓ Created curriculum_resources (lecture materials)")
        
        # Resource accesses: audit trail of student downloads
        await db.create_collection("curriculum_resource_accesses", check_exists=True)
        accesses_col = db["curriculum_resource_accesses"]
        await accesses_col.create_index("user_id")
        await accesses_col.create_index("resource_id")
        await accesses_col.create_index("session_id")
        await accesses_col.create_index("accessed_at")
        # TTL index: auto-cleanup after 90 days
        await accesses_col.create_index(
            "accessed_at",
            expireAfterSeconds=7776000  # 90 days
        )
        logger.info("✓ Created curriculum_resource_accesses (audit trail, 90-day TTL)")
        
        # Progressive unlocks: when resources are unlocked for students (attendance-gated)
        await db.create_collection("curriculum_progressive_unlocks", check_exists=True)
        unlocks_col = db["curriculum_progressive_unlocks"]
        await unlocks_col.create_index("user_id")
        await unlocks_col.create_index("session_id")
        await unlocks_col.create_index("unlocked_at")
        logger.info("✓ Created curriculum_progressive_unlocks (attendance-gated unlock events)")
    
    async def down(self, db: AsyncIOMotorDatabase):
        """Rollback migration."""
        logger.info(f"Rolling back {self.version}...")
        collections = [
            "curriculum_topic_mappings",
            "curriculum_node_embeddings_cache",
            "curriculum_verification_tasks",
            "curriculum_verified_mappings",
            "curriculum_resources",
            "curriculum_resource_accesses",
            "curriculum_progressive_unlocks",
        ]
        for col in collections:
            try:
                await db.drop_collection(col)
                logger.info(f"✓ Dropped {col}")
            except Exception as e:
                logger.warning(f"Could not drop {col}: {e}")


# ============================================================================
# MIGRATION RUNNER
# ============================================================================

class MigrationRunner:
    """Manages migration execution and tracking."""
    
    MIGRATIONS: List[Migration] = [
        Migration001InitialSchema(),
        Migration002AddRoleBasedIndexes(),
        Migration003CurriculumPipeline(),
    ]
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.migrations_col = db["schema_migrations"]
    
    async def initialize(self):
        """Ensure migrations tracking collection exists."""
        await self.db.create_collection("schema_migrations", check_exists=True)
        await self.migrations_col.create_index("version", unique=True)
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of already-applied migration versions."""
        docs = await self.migrations_col.find().to_list(length=None)
        return [doc["version"] for doc in docs]
    
    async def run_pending_migrations(self) -> Dict[str, Any]:
        """
        Run all pending migrations.
        
        Returns: {applied: [...], skipped: [...], errors: [...]}
        """
        await self.initialize()
        applied = await self.get_applied_migrations()
        
        result = {"applied": [], "skipped": [], "errors": []}
        
        for migration in self.MIGRATIONS:
            if migration.version in applied:
                logger.info(f"Skipping {migration.version} (already applied)")
                result["skipped"].append(migration.version)
                continue
            
            try:
                logger.info(f"Running migration {migration.version}: {migration.description}")
                await migration.up(self.db)
                
                # Record in tracking collection
                await self.migrations_col.insert_one({
                    "version": migration.version,
                    "description": migration.description,
                    "applied_at": datetime.now(timezone.utc),
                    "migration_type": migration.migration_type.value,
                })
                logger.info(f"✓ Completed {migration.version}")
                result["applied"].append(migration.version)
                
            except Exception as e:
                logger.error(f"✗ Failed to apply {migration.version}: {e}", exc_info=True)
                result["errors"].append({
                    "version": migration.version,
                    "error": str(e),
                })
        
        return result
    
    async def rollback_migration(self, version: str):
        """Rollback a specific migration."""
        migration = next((m for m in self.MIGRATIONS if m.version == version), None)
        if not migration:
            raise ValueError(f"Migration not found: {version}")
        
        logger.info(f"Rolling back {version}...")
        await migration.down(self.db)
        await self.migrations_col.delete_one({"version": version})
        logger.info(f"✓ Rolled back {version}")


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

async def main(env: str = "dev"):
    """Run migrations for specified environment."""
    from app.config.environment import get_settings_for_env, EnvironmentEnum
    from motor.motor_asyncio import AsyncIOMotorClient
    
    settings = get_settings_for_env(EnvironmentEnum(env))
    
    client = AsyncIOMotorClient(settings.mongodb.url, tz_aware=True)
    db = client[settings.mongodb.database]
    
    try:
        runner = MigrationRunner(db)
        result = await runner.run_pending_migrations()
        
        logger.info("\n" + "="*60)
        logger.info(f"Migration Report ({env}):")
        logger.info(f"  Applied: {len(result['applied'])}")
        logger.info(f"  Skipped: {len(result['skipped'])}")
        logger.info(f"  Errors:  {len(result['errors'])}")
        logger.info("="*60)
        
        if result["errors"]:
            logger.error("Errors encountered:")
            for err in result["errors"]:
                logger.error(f"  {err['version']}: {err['error']}")
            return 1
        
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    import sys
    env = sys.argv[1] if len(sys.argv) > 1 else "dev"
    exit_code = asyncio.run(main(env))
    sys.exit(exit_code)
