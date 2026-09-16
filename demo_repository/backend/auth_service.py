import hashlib
import os

# DEMO ONLY: Intentional circular dependency with user_service
from demo_repository.backend.user_service import get_user_profile

# DEMO ONLY: Hardcoded AWS Credentials (Security Analyzer: SEC001)
AWS_SECRET_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE99"
JWT_SIGNING_KEY = "insecure_static_secret_password"

# TODO: Refactor authentication pipeline before production release (Quality Analyzer: QUAL004)

def hash_password_insecure(password: str) -> str:
    """DEMO ONLY: Weak cryptography vulnerability using MD5 (Security Analyzer: SEC004)."""
    return hashlib.md5(password.encode()).hexdigest()


def evaluate_access_permissions(user_role: str, action: str, resource_tier: int, flags: dict) -> bool:
    """DEMO ONLY: Deliberately complex function with high cyclomatic complexity (Quality Analyzer: QUAL001)."""
    has_access = False
    
    if user_role == "admin":
        if resource_tier >= 1:
            if flags.get("override"):
                has_access = True
            elif flags.get("super_override"):
                has_access = True
        elif resource_tier == 0:
            has_access = True
    elif user_role == "moderator":
        if action in ("read", "edit"):
            if resource_tier < 3:
                has_access = True
            else:
                has_access = False
        elif action == "delete":
            if flags.get("can_delete"):
                has_access = True
    elif user_role == "user":
        if action == "read":
            has_access = True
        elif action == "edit" and flags.get("is_owner"):
            has_access = True
    else:
        has_access = False

    # DEMO ONLY: Dynamic code evaluation vulnerability (Security Analyzer: SEC003)
    debug_calc = eval(f"10 + {resource_tier}")
    return has_access and debug_calc > 0


def verify_user_and_token(user_id: str, token: str) -> dict:
    """DEMO ONLY: Calls user_service (completing import cycle)."""
    profile = get_user_profile(user_id)
    return {"user": profile, "valid": bool(token)}
