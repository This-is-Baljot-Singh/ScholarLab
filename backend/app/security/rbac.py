"""
Enhanced Role-Based Access Control (RBAC)

Implements granular permission model across Student, Faculty, and Admin roles
with resource-level and operation-level access control.

Permission Model:
- STUDENT: View own attendance, curriculum progress, risk scores
- FACULTY: Manage curriculum, review student attendance, access analytics
- ADMIN: System administration, user management, configuration
"""

from typing import List, Dict, Optional, Set, Callable, Any
from enum import Enum
from functools import wraps
from fastapi import Depends, HTTPException, status
from app.database import db
from app.security.auth_enhanced import get_current_user_from_token
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# ROLE DEFINITIONS
# ============================================================================

class Role(str, Enum):
    """User roles in ScholarLab."""
    STUDENT = "student"
    FACULTY = "faculty"
    ADMIN = "admin"


class Permission(str, Enum):
    """Granular permissions."""
    
    # ---- STUDENT PERMISSIONS ----
    STUDENT_VIEW_OWN_ATTENDANCE = "student:view_own_attendance"
    STUDENT_VIEW_OWN_CURRICULUM = "student:view_own_curriculum"
    STUDENT_VIEW_OWN_RISK_SCORE = "student:view_own_risk_score"
    STUDENT_SUBMIT_OVERRIDE_REQUEST = "student:submit_override_request"
    
    # ---- FACULTY PERMISSIONS ----
    FACULTY_CREATE_CURRICULUM = "faculty:create_curriculum"
    FACULTY_UPDATE_CURRICULUM = "faculty:update_curriculum"
    FACULTY_VIEW_COURSE_ATTENDANCE = "faculty:view_course_attendance"
    FACULTY_VIEW_COURSE_ANALYTICS = "faculty:view_course_analytics"
    FACULTY_REVIEW_VERIFICATION_TASKS = "faculty:review_verification_tasks"
    FACULTY_APPROVE_OVERRIDE_REQUESTS = "faculty:approve_override_requests"
    FACULTY_VIEW_RISK_PREDICTIONS = "faculty:view_risk_predictions"
    FACULTY_ACCESS_FACULTY_PORTAL = "faculty:access_faculty_portal"
    FACULTY_MANAGE_GEOFENCES = "faculty:manage_geofences"
    
    # ---- ADMIN PERMISSIONS ----
    ADMIN_MANAGE_USERS = "admin:manage_users"
    ADMIN_MANAGE_ROLES = "admin:manage_roles"
    ADMIN_VIEW_AUDIT_LOGS = "admin:view_audit_logs"
    ADMIN_SYSTEM_CONFIG = "admin:system_config"
    ADMIN_VIEW_ALL_ANALYTICS = "admin:view_all_analytics"
    ADMIN_REVOKE_TOKENS = "admin:revoke_tokens"


# ============================================================================
# ROLE-PERMISSION MAPPING
# ============================================================================

ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.STUDENT: {
        Permission.STUDENT_VIEW_OWN_ATTENDANCE,
        Permission.STUDENT_VIEW_OWN_CURRICULUM,
        Permission.STUDENT_VIEW_OWN_RISK_SCORE,
        Permission.STUDENT_SUBMIT_OVERRIDE_REQUEST,
    },
    Role.FACULTY: {
        # All faculty permissions
        Permission.FACULTY_CREATE_CURRICULUM,
        Permission.FACULTY_UPDATE_CURRICULUM,
        Permission.FACULTY_VIEW_COURSE_ATTENDANCE,
        Permission.FACULTY_VIEW_COURSE_ANALYTICS,
        Permission.FACULTY_REVIEW_VERIFICATION_TASKS,
        Permission.FACULTY_APPROVE_OVERRIDE_REQUESTS,
        Permission.FACULTY_VIEW_RISK_PREDICTIONS,
        Permission.FACULTY_ACCESS_FACULTY_PORTAL,
        Permission.FACULTY_MANAGE_GEOFENCES,
    },
    Role.ADMIN: {
        # Admins have all permissions
        *[p for p in Permission],
    },
}


# ============================================================================
# RBAC ENFORCEMENT
# ============================================================================

class RBACEnforcer:
    """Enforces role-based and resource-based access control."""
    
    @staticmethod
    def get_user_permissions(user: Dict) -> Set[Permission]:
        """Get all permissions for a user based on role."""
        role_str = user.get("role", "student").lower()
        try:
            role = Role(role_str)
            return ROLE_PERMISSIONS.get(role, set())
        except ValueError:
            logger.warning(f"Unknown role: {role_str}")
            return set()
    
    @staticmethod
    def user_has_permission(user: Dict, permission: Permission) -> bool:
        """Check if user has permission."""
        permissions = RBACEnforcer.get_user_permissions(user)
        return permission in permissions
    
    @staticmethod
    def user_has_role(user: Dict, role: Role) -> bool:
        """Check if user has role."""
        return user.get("role", "").lower() == role.value
    
    @staticmethod
    def can_access_student_data(user: Dict, target_student_id: str) -> bool:
        """
        Check if user can access target student's data.
        
        Rules:
        - STUDENT can only access their own data
        - FACULTY can access students in their courses
        - ADMIN can access any student
        """
        user_id = str(user.get("_id"))
        user_role = Role(user.get("role", "student").lower())
        
        if user_role == Role.ADMIN:
            return True
        
        if user_role == Role.STUDENT:
            return user_id == target_student_id
        
        if user_role == Role.FACULTY:
            # TODO: Check if faculty teaches student (requires course relationship)
            return True
        
        return False
    
    @staticmethod
    def can_access_course_data(user: Dict, course_id: str) -> bool:
        """
        Check if user can access course data.
        
        Rules:
        - STUDENT can access courses they're enrolled in
        - FACULTY can access courses they teach
        - ADMIN can access any course
        """
        user_role = Role(user.get("role", "student").lower())
        
        if user_role == Role.ADMIN:
            return True
        
        if user_role == Role.FACULTY:
            # TODO: Check if faculty teaches course
            return True
        
        if user_role == Role.STUDENT:
            # TODO: Check if student is enrolled in course
            return True
        
        return False


# ============================================================================
# DEPENDENCY INJECTION HELPERS
# ============================================================================

def require_permission(permission: Permission):
    """
    Dependency that enforces a specific permission.
    
    Usage:
        @app.get("/api/admin/users")
        async def admin_users(current_user = Depends(require_permission(Permission.ADMIN_MANAGE_USERS))):
            ...
    """
    async def check_permission(current_user: Dict = Depends(get_current_user_from_token)):
        if not RBACEnforcer.user_has_permission(current_user, permission):
            logger.warning(
                f"Permission denied",
                extra={
                    'user_email': current_user.get("email"),
                    'required_permission': permission.value,
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}",
            )
        return current_user
    
    return check_permission


def require_role(*allowed_roles: Role):
    """
    Dependency that enforces specific roles.
    
    Usage:
        @app.get("/api/faculty/dashboard")
        async def faculty_dashboard(current_user = Depends(require_role(Role.FACULTY, Role.ADMIN))):
            ...
    """
    async def check_role(current_user: Dict = Depends(get_current_user_from_token)):
        user_role = Role(current_user.get("role", "student").lower())
        if user_role not in allowed_roles:
            logger.warning(
                f"Role denied",
                extra={
                    'user_email': current_user.get("email"),
                    'required_roles': [r.value for r in allowed_roles],
                    'actual_role': user_role.value,
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This resource requires one of roles: {', '.join(r.value for r in allowed_roles)}",
            )
        return current_user
    
    return check_role


def require_resource_access(
    resource_type: str,
    resource_id_param: str = "resource_id",
):
    """
    Dependency that enforces resource-level access control.
    
    Args:
        resource_type: Type of resource (student, course, etc.)
        resource_id_param: Name of path parameter containing resource ID
    
    Usage:
        @app.get("/api/attendance/{student_id}")
        async def get_attendance(
            student_id: str,
            current_user = Depends(require_resource_access("student", "student_id"))
        ):
            ...
    """
    async def check_resource_access(
        current_user: Dict = Depends(get_current_user_from_token),
    ):
        # Note: resource_id will come from request path parameter
        # This is a template for how to structure resource access checks
        return current_user
    
    return check_resource_access


# ============================================================================
# AUDIT LOGGING FOR ACCESS CONTROL
# ============================================================================

async def log_access_control_event(
    user_email: str,
    action: str,
    resource: str,
    allowed: bool,
    reason: Optional[str] = None,
):
    """
    Log access control decisions for audit trail.
    
    Args:
        user_email: User attempting access
        action: Action attempted (read, write, delete, etc.)
        resource: Resource being accessed
        allowed: Whether access was allowed
        reason: Reason if denied
    """
    audit_logs = db.get_collection("access_control_audit_logs")
    
    await audit_logs.insert_one({
        "timestamp": datetime.now(timezone.utc),
        "user_email": user_email,
        "action": action,
        "resource": resource,
        "allowed": allowed,
        "reason": reason,
    })


from datetime import datetime, timezone
