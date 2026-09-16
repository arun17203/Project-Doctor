# DEMO ONLY: Intentional circular import back to auth_service
from demo_repository.backend.auth_service import hash_password_insecure
from demo_repository.backend.db import execute_raw_query


def get_user_profile(user_id: str) -> dict:
    """DEMO ONLY: Service function called by auth_service."""
    user = execute_raw_query(f"SELECT * FROM users WHERE id = '{user_id}'")
    return {"id": user_id, "data": user}


def create_user_account(username: str, plain_pass: str) -> dict:
    """DEMO ONLY: Creates user using insecure hash."""
    hashed = hash_password_insecure(plain_pass)
    execute_raw_query(f"INSERT INTO users (username, password) VALUES ('{username}', '{hashed}')")
    return {"status": "created", "username": username}
