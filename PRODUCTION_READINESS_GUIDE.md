"""
ScholarLab Production Readiness Guide

Comprehensive documentation for deploying and maintaining ScholarLab in production.
"""

# ============================================================================
# PRODUCTION READINESS CHECKLIST
# ============================================================================

PRODUCTION_CHECKLIST = """
## 1. STRUCTURED LOGGING & DISTRIBUTED TRACING ✅

### What's Implemented:
- Centralized JSON logging (app/logging/structured_logging.py)
  - Automatic context propagation (trace_id, span_id, user_id, request_id)
  - Boundary-specific loggers: API, Auth, Validation, Sync, Analytics
  - Performance monitoring with automatic duration tracking
  
- Distributed tracing (app/logging/tracing.py)
  - OpenTelemetry-compatible span creation and management
  - Async/sync decorator support for automatic tracing
  - Boundary-specific tracing helpers (APITracer, ValidationTracer, SyncTracer, AnalyticsTracer)
  - FastAPI middleware for request tracing

### Configuration:
- Default log level: INFO
- Log output: Console + file (/tmp/scholarlab.log)
- Trace context automatically set/cleared per request

### Usage Example:
```python
from app.logging.structured_logging import get_logger, PerformanceMonitor
from app.logging.tracing import get_tracer

logger = get_logger(__name__)
tracer = get_tracer()

# Automatic performance tracking
with PerformanceMonitor(logger, "my_operation", threshold_ms=1000):
    # Your code here
    pass

# Automatic distributed tracing
@tracer.trace_async("my_async_operation")
async def my_async_function():
    # Traced automatically
    pass
```

---

## 2. ENHANCED JWT & REFRESH TOKEN ROTATION ✅

### What's Implemented:
- Short-lived access tokens (15 min default)
- Refresh token rotation (new tokens on each refresh)
- Token revocation blacklist with MongoDB TTL
- Token family tracking (prevents token reuse attacks)
- Device binding to tokens (future)

### Key Files:
- app/security/auth_enhanced.py (EnhancedJWTSecurity)
- app/database.py (Token metadata collections)

### Collections:
- token_metadata: Stores token lifecycle info + indexes
- token_revocation_list: Revoked tokens (TTL auto-cleanup)

### Configuration (app/database.py):
```python
ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access
REFRESH_TOKEN_EXPIRE_DAYS: int = 7      # Longer-lived refresh
```

### Usage Example:
```python
from app.security.auth_enhanced import get_jwt_security

jwt_security = await get_jwt_security()

# Create token pair on login
tokens = await jwt_security.create_token_pair(
    user_id=user_id,
    user_email=user_email,
    user_role=user_role,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
)

# Refresh access token
new_tokens = await jwt_security.refresh_access_token(refresh_token)

# Revoke token (on logout)
await jwt_security.revoke_token(token_id, reason="user_logout")

# Revoke all user tokens (on password change)
await jwt_security.revoke_all_user_tokens(user_email, reason="password_change")
```

---

## 3. ENHANCED RBAC (Role-Based Access Control) ✅

### What's Implemented:
- Three roles: STUDENT, FACULTY, ADMIN
- Granular permission model (30+ permissions)
- Resource-level and operation-level access control
- RBAC denial audit logging

### Key Files:
- app/security/rbac.py (RBACEnforcer, permission definitions)

### Permissions by Role:

**STUDENT:**
- student:view_own_attendance
- student:view_own_curriculum
- student:view_own_risk_score
- student:submit_override_request

**FACULTY:**
- faculty:create_curriculum
- faculty:update_curriculum
- faculty:view_course_attendance
- faculty:view_course_analytics
- faculty:review_verification_tasks
- faculty:approve_override_requests
- faculty:view_risk_predictions
- faculty:access_faculty_portal
- faculty:manage_geofences

**ADMIN:**
- All permissions (admin:manage_users, admin:manage_roles, admin:view_audit_logs, etc.)

### Usage Example:
```python
from app.security.rbac import require_permission, require_role, Permission, Role

# Protect endpoint by permission
@app.get("/api/admin/users")
async def admin_users(
    current_user = Depends(require_permission(Permission.ADMIN_MANAGE_USERS))
):
    return {"users": [...]}

# Protect endpoint by role
@app.get("/api/faculty/dashboard")
async def faculty_dashboard(
    current_user = Depends(require_role(Role.FACULTY, Role.ADMIN))
):
    return {"dashboard": {...}}

# Check permission in code
from app.security.rbac import RBACEnforcer
if RBACEnforcer.user_has_permission(user, Permission.ADMIN_VIEW_AUDIT_LOGS):
    # Show audit logs
    pass
```

---

## 4. ADVERSARIAL INTEGRATION TESTS ✅

### What's Implemented:
- 8 test classes with 20+ test cases
- Real attack scenario simulations
- Located in: backend/tests/test_adversarial_integration.py

### Attack Vectors Tested:
1. **GPS Spoofing**
   - Distant GPS spoofing (NYC → London)
   - Nearby spoofing near geofence boundary
   - Impossible speed detection

2. **Network/Wi-Fi Mismatches**
   - SSID mismatch detection
   - BSSID spoofing detection
   - Signal strength anomalies

3. **Replay Attacks**
   - Nonce-based prevention
   - Counter-based device clone detection
   - Request signature binding

4. **Transcript Hallucination**
   - Hallucinated topic detection
   - Coherence score validation

5. **Biometric Spoofing**
   - Liveness detection
   - Match score thresholds

6. **Device Cloning**
   - Counter mismatch detection
   - Public key change detection

7. **Privilege Escalation**
   - JWT role tamperproofing

### Running Tests:
```bash
cd backend
pytest tests/test_adversarial_integration.py -v --tb=short
```

### Test Results Expected:
- All attacks should be detected/prevented
- No false negatives
- Minimal false positives on legitimate operations

---

## 5. PROMETHEUS METRICS & GRAFANA DASHBOARDS ✅

### What's Implemented:
- Prometheus metrics collection (app/metrics/prometheus_metrics.py)
- Metrics endpoint at /metrics
- 4 Grafana dashboards (app/monitoring/grafana_dashboards.py)

### Key Metrics Collected:

**Latency:**
- scholarlab_api_request_duration_ms (by endpoint, status)
- scholarlab_attendance_verification_duration_ms
- scholarlab_model_inference_duration_ms
- scholarlab_curriculum_sync_duration_ms

**Security:**
- scholarlab_spoof_rejections_total (by type, method)
- scholarlab_false_rejections_total (FRR)
- scholarlab_biometric_verifications_total
- scholarlab_device_clone_detections_total
- scholarlab_token_revocations_total
- scholarlab_rbac_denials_total

**Analytics:**
- scholarlab_risk_predictions_total (by risk level)
- scholarlab_collusion_detections_total
- scholarlab_active_anomaly_alerts

**System:**
- scholarlab_database_operation_duration_ms
- scholarlab_active_websocket_connections
- scholarlab_background_job_duration_ms
- scholarlab_login_attempts_total

### Grafana Dashboards:
1. **API Latency** - Request latency, endpoint performance
2. **Security Metrics** - Spoof rejection rate, FRR, device clones
3. **Analytics & ML** - Model inference time, risk predictions, collusion
4. **System Health** - DB latency, WebSocket connections, background jobs

### Accessing Metrics:
- Prometheus endpoint: http://localhost:8000/metrics
- Grafana: http://localhost:3000 (after setup)

### Docker Compose Setup:
```yaml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## 6. MIDDLEWARE INTEGRATION ✅

### Applied (in order):
1. **TracingMiddleware** - Request-level tracing
2. **MetricsMiddleware** - Latency recording
3. **CORSMiddleware** - Cross-origin requests

### Initialization:
```python
# In main.py
from app.logging.tracing import TracingMiddleware, initialize_tracer
from app.metrics.prometheus_metrics import MetricsMiddleware

tracer = initialize_tracer(service_name="scholarlab-api")
app.add_middleware(TracingMiddleware, tracer=tracer)
app.add_middleware(MetricsMiddleware)
```

---

## 7. DATABASE SETUP REQUIREMENTS ✅

### New Collections:
- token_metadata (JWT token lifecycle tracking)
- token_revocation_list (Revoked token blacklist)
- behavior_profiles (Student behavior for collusion detection)
- collusion_pairs (Flagged suspicious pairs)
- anomaly_reports (Anomaly detection reports)
- access_control_audit_logs (RBAC denial audit trail)

### Indexes (auto-created):
```
token_metadata:
  - token_id (unique)
  - token_family
  - user_id
  - expires_at (TTL, auto-delete after expiry)

token_revocation_list:
  - token_id (unique)
  - expires_at (TTL, auto-delete after expiry)

collusion_pairs:
  - student_pair_id (unique)
  - course_id
  - structural_similarity
  - is_suspicious

anomaly_reports:
  - course_id
  - analysis_date (descending)
```

---

## 8. CONFIGURATION REQUIREMENTS ✅

### Environment Variables:
```bash
# JWT Configuration
SECRET_KEY=your-super-secret-jwt-key-256-bits-minimum
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/scholarlab/api.log

# Database
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=scholarlab

# Feature Flags
ENABLE_BIOMETRIC=true
ENABLE_GEOFENCE=true
ENABLE_CURRICULUM_SYNC=true
ENABLE_ANALYTICS=true
```

### Security Best Practices:
1. **NEVER** commit secrets to repository
2. Use .env files (add to .gitignore)
3. Rotate SECRET_KEY in production regularly
4. Enable HTTPS only in production
5. Set CORS origins to specific domains
6. Enable MongoDB authentication + encryption
7. Use short-lived tokens (15 min access, 7 day refresh)
8. Implement rate limiting on auth endpoints
9. Monitor auth logs for suspicious activity
10. Regular security audits of RBAC permissions

---

## 9. MONITORING & ALERTING

### Critical Metrics to Alert On:

```yaml
Latency Alerts:
  - API p95 latency > 500ms
  - Attendance verification > 2000ms
  - Model inference > 500ms

Security Alerts:
  - Spoof rejection rate > 10/min
  - False rejection rate > 5%
  - Device clone detections > 5/day
  - Token revocation spike > 100/hour

Analytics Alerts:
  - Critical risk predictions > threshold
  - Collusion detections > threshold
  - Model inference errors

System Alerts:
  - DB operation latency > 1000ms
  - WebSocket disconnections > threshold
  - Background job failures
```

### Logging Standards:
- Always log with structured JSON format
- Include trace_id for request tracking
- Include user_id for user activity tracking
- Include timestamps in UTC ISO format
- Log security events to separate audit log

---

## 10. DEPLOYMENT CHECKLIST

### Before Production Deploy:

- [ ] All tests passing (including adversarial tests)
- [ ] JWT SECRET_KEY rotated and secure
- [ ] MongoDB indexes created and verified
- [ ] CORS origins configured for production domain
- [ ] Logging configured to persistent storage
- [ ] Prometheus + Grafana deployed and configured
- [ ] Alerting rules configured
- [ ] Backup/restore procedure tested
- [ ] Rate limiting configured on auth endpoints
- [ ] HTTPS/TLS enabled
- [ ] Security headers configured
- [ ] API documentation accessible (/api/docs)

### Production Operations:

- Monitor metrics dashboards 24/7
- Review audit logs daily
- Rotate tokens/credentials monthly
- Test disaster recovery monthly
- Keep dependencies updated
- Monitor error logs for anomalies

---

## 11. TROUBLESHOOTING

### JWT Issues:
```python
# Token validation failing?
# Check: 1) Token expiry, 2) Signature, 3) Revocation status

# Token refresh failing?
# Check: 1) Refresh token in revocation list, 2) Token version mismatch
```

### RBAC Issues:
```python
# Permission denied?
# Check: 1) User role in database, 2) Permission list for role
# Use: RBACEnforcer.get_user_permissions(user) to debug
```

### Metrics Issues:
```python
# Metrics not appearing?
# Check: 1) MetricsMiddleware added, 2) /metrics endpoint accessible
# Check: 3) Prometheus scrape config, 4) Grafana data source
```

### Tracing Issues:
```python
# Traces not appearing?
# Check: 1) TracingMiddleware added, 2) Trace context initialization
# Check: 3) Log file permissions, 4) Structured logging configured
```

---

## 12. PERFORMANCE TARGETS

### Latency (p95):
- API requests: < 500ms
- Attendance verification: < 2000ms
- Model inference: < 500ms
- Database operations: < 250ms

### Availability:
- API uptime: 99.9%
- Database uptime: 99.99%

### Security:
- False rejection rate (FRR): < 5%
- Spoof detection rate: > 95%
- Device clone detection: 100%

### Risk Model:
- Inference latency: < 500ms per student
- Batch prediction (1000 students): < 30s

---
"""

if __name__ == "__main__":
    print(PRODUCTION_CHECKLIST)
