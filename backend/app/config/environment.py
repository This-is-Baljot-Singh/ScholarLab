"""
Environment profiles and configuration management for ScholarLab.

Supports: dev, staging, pilot, production
Each profile defines database strategy, validation strictness, and audit behavior.
"""

from enum import Enum
from pydantic_settings import BaseSettings
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)


class EnvironmentEnum(str, Enum):
    """Deployment environments."""
    dev = "dev"
    staging = "staging"
    pilot = "pilot"
    production = "production"


class MongoDBConfig(BaseSettings):
    """MongoDB configuration per environment."""
    url: str
    database: str
    # Connection pool settings
    max_pool_size: int = 10
    min_pool_size: int = 5
    # Indexes and validation
    auto_create_indexes: bool = True
    enforce_schemas: bool = False


class AuthConfig(BaseSettings):
    """Authentication configuration."""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    # WebAuthn settings
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "ScholarLab"
    webauthn_origin: str = "http://localhost:5173"


class AttendanceConfig(BaseSettings):
    """Attendance verification settings."""
    # Zero-trust requirements
    require_device_verification: bool = True
    require_biometric_verification: bool = True
    require_spatial_verification: bool = True
    # Confidence thresholds
    biometric_confidence_threshold: float = 0.95
    spatial_accuracy_threshold_meters: float = 10.0
    # Timeout settings
    challenge_expiry_seconds: int = 300
    session_validity_seconds: int = 3600


class AuditConfig(BaseSettings):
    """Audit logging configuration."""
    # Logging strategy
    log_all_requests: bool = True
    log_all_state_changes: bool = True
    log_sensitive_data_access: bool = True
    # Storage
    use_immutable_collection: bool = True
    audit_log_collection: str = "audit_logs"
    # Enforcement
    fail_on_audit_error: bool = False  # log but don't fail requests
    sign_audit_logs: bool = False  # set True in pilot/production


class JobQueueConfig(BaseSettings):
    """Background job queue configuration."""
    # Queue implementation
    provider: str = "celery"  # "celery" or "bull" (if Node.js integration)
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/1"
    # Task settings
    default_queue: str = "default"
    max_retries: int = 3
    task_timeout_seconds: int = 3600
    # Audio/LLM tasks
    enable_audio_transcription: bool = False  # requires Ollama
    enable_shap_inference: bool = False  # requires trained model


class FeatureFlags(BaseSettings):
    """Feature flags per environment."""
    # Privacy controls
    enforce_local_inference: bool = True
    disable_cloud_apis: bool = True
    # Validation strictness
    strict_input_validation: bool = True
    strict_output_validation: bool = True
    # Debug/dev features
    enable_debug_endpoints: bool = False
    enable_seed_data_endpoints: bool = False


class MinIOConfig(BaseSettings):
    """On-premises MinIO S3-compatible object store configuration."""
    endpoint: str = "http://localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket_name: str = "scholarlab-audio"
    # Derived: boto3 requires path-style access for MinIO
    use_path_style: bool = True


class ScholarLabSettings(BaseSettings):
    """Unified configuration for all environments."""

    environment: EnvironmentEnum = EnvironmentEnum.dev

    # Core configs
    mongodb: MongoDBConfig
    auth: AuthConfig
    attendance: AttendanceConfig
    audit: AuditConfig
    job_queue: JobQueueConfig
    features: FeatureFlags
    minio: MinIOConfig = MinIOConfig()

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"  # Support MONGODB__URL=... in .env


def get_settings_for_env(env: EnvironmentEnum) -> ScholarLabSettings:
    """
    Factory function to load settings for a specific environment.
    """
    if env == EnvironmentEnum.production:
        return ScholarLabSettings(
            environment=EnvironmentEnum.production,
            mongodb=MongoDBConfig(
                url="${MONGODB_URL}",  # Must be set via env var
                database="scholarlab_prod",
                max_pool_size=20,
                min_pool_size=10,
                auto_create_indexes=False,  # Migrations only
                enforce_schemas=True,
            ),
            auth=AuthConfig(
                secret_key="${SECRET_KEY}",  # Rotate quarterly
                webauthn_rp_id="${WEBAUTHN_RP_ID}",
                webauthn_origin="${WEBAUTHN_ORIGIN}",
            ),
            attendance=AttendanceConfig(
                require_device_verification=True,
                require_biometric_verification=True,
                require_spatial_verification=True,
                biometric_confidence_threshold=0.98,  # Stricter in prod
                spatial_accuracy_threshold_meters=5.0,
            ),
            audit=AuditConfig(
                log_all_requests=True,
                log_all_state_changes=True,
                log_sensitive_data_access=True,
                use_immutable_collection=True,
                fail_on_audit_error=True,  # Fail closed
                sign_audit_logs=True,
            ),
            job_queue=JobQueueConfig(
                broker_url="${REDIS_URL}",
                enable_audio_transcription=True,
                enable_shap_inference=True,
            ),
            features=FeatureFlags(
                enforce_local_inference=True,
                disable_cloud_apis=True,
                strict_input_validation=True,
                strict_output_validation=True,
                enable_debug_endpoints=False,
                enable_seed_data_endpoints=False,
            ),
        )
    
    elif env == EnvironmentEnum.pilot:
        return ScholarLabSettings(
            environment=EnvironmentEnum.pilot,
            mongodb=MongoDBConfig(
                url="${MONGODB_URL}",
                database="scholarlab_pilot",
                max_pool_size=15,
                min_pool_size=5,
                auto_create_indexes=True,
                enforce_schemas=True,
            ),
            auth=AuthConfig(
                secret_key="${SECRET_KEY}",
                webauthn_rp_id="${WEBAUTHN_RP_ID}",
                webauthn_origin="${WEBAUTHN_ORIGIN}",
            ),
            attendance=AttendanceConfig(
                require_device_verification=True,
                require_biometric_verification=True,
                require_spatial_verification=True,
                biometric_confidence_threshold=0.95,
                spatial_accuracy_threshold_meters=10.0,
            ),
            audit=AuditConfig(
                log_all_requests=True,
                log_all_state_changes=True,
                log_sensitive_data_access=True,
                use_immutable_collection=True,
                fail_on_audit_error=False,
                sign_audit_logs=True,
            ),
            job_queue=JobQueueConfig(
                broker_url="${REDIS_URL}",
                enable_audio_transcription=True,
                enable_shap_inference=True,
            ),
            features=FeatureFlags(
                enforce_local_inference=True,
                disable_cloud_apis=True,
                strict_input_validation=True,
                strict_output_validation=True,
                enable_debug_endpoints=False,
                enable_seed_data_endpoints=False,
            ),
        )
    
    elif env == EnvironmentEnum.staging:
        _mongo_url = os.environ.get("MONGODB_URL")
        if not _mongo_url:
            logger.warning(
                "MONGODB_URL not set; staging defaulting to unauthenticated "
                "localhost URI. Set MONGODB_URL for authenticated access."
            )
            _mongo_url = "mongodb://localhost:27017"
        return ScholarLabSettings(
            environment=EnvironmentEnum.staging,
            mongodb=MongoDBConfig(
                url=_mongo_url,
                database="scholarlab_staging",
                auto_create_indexes=True,
                enforce_schemas=False,
            ),
            auth=AuthConfig(
                secret_key="staging-test-key-rotate-in-production",
                webauthn_rp_id="staging.scholarlab.local",
                webauthn_origin="http://staging.scholarlab.local:5173",
            ),
            attendance=AttendanceConfig(
                require_device_verification=True,
                require_biometric_verification=True,
                require_spatial_verification=True,
                biometric_confidence_threshold=0.90,
                spatial_accuracy_threshold_meters=15.0,
            ),
            audit=AuditConfig(
                log_all_requests=True,
                log_all_state_changes=True,
                log_sensitive_data_access=True,
                use_immutable_collection=True,
                fail_on_audit_error=False,
                sign_audit_logs=False,
            ),
            job_queue=JobQueueConfig(
                broker_url="redis://localhost:6379/0",
                enable_audio_transcription=True,
                enable_shap_inference=True,
            ),
            features=FeatureFlags(
                enforce_local_inference=True,
                disable_cloud_apis=True,
                strict_input_validation=True,
                strict_output_validation=False,
                enable_debug_endpoints=False,
                enable_seed_data_endpoints=True,
            ),
        )
    
    else:  # dev
        _mongo_url = os.environ.get("MONGODB_URL")
        if not _mongo_url:
            logger.warning(
                "MONGODB_URL not set; dev defaulting to unauthenticated "
                "localhost URI. Set MONGODB_URL for authenticated access."
            )
            _mongo_url = "mongodb://localhost:27017"
        return ScholarLabSettings(
            environment=EnvironmentEnum.dev,
            mongodb=MongoDBConfig(
                url=_mongo_url,
                database="scholarlab_dev",
                auto_create_indexes=True,
                enforce_schemas=False,
            ),
            auth=AuthConfig(
                secret_key="dev-test-key-never-use-in-production",
                webauthn_rp_id="localhost",
                webauthn_origin="http://localhost:5173",
            ),
            attendance=AttendanceConfig(
                require_device_verification=True,
                require_biometric_verification=True,
                require_spatial_verification=True,
                biometric_confidence_threshold=0.85,
                spatial_accuracy_threshold_meters=20.0,
            ),
            audit=AuditConfig(
                log_all_requests=True,
                log_all_state_changes=True,
                log_sensitive_data_access=True,
                use_immutable_collection=True,
                fail_on_audit_error=False,
                sign_audit_logs=False,
            ),
            job_queue=JobQueueConfig(
                broker_url="redis://localhost:6379/0",
                enable_audio_transcription=False,
                enable_shap_inference=False,
            ),
            features=FeatureFlags(
                enforce_local_inference=True,
                disable_cloud_apis=True,
                strict_input_validation=True,
                strict_output_validation=False,
                enable_debug_endpoints=True,
                enable_seed_data_endpoints=True,
            ),
        )


# Load from environment variable
import os
ENVIRONMENT = os.getenv("SCHOLARLAB_ENV", "dev")
settings = get_settings_for_env(EnvironmentEnum(ENVIRONMENT))

logger.info(f"ScholarLab initialized with environment: {ENVIRONMENT}")
