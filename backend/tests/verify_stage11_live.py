import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import io
import time
import zipfile
import httpx
from unittest.mock import patch

BASE_URL = "http://127.0.0.1:8000"


def create_test_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        auth_code = """
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "super-secret-token-key-do-not-leak"
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
"""
        z.writestr("auth/jwt.py", auth_code)

        db_code = """
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
"""
        z.writestr("database/models.py", db_code)

        env_code = "DATABASE_URL=postgres://user:password@localhost:5432/db\nAPI_KEY=live_secret_123456\n"
        z.writestr(".env", env_code)

        req_code = "pyjwt==2.8.0\nsqlalchemy==2.0.25\n"
        z.writestr("requirements.txt", req_code)

    buf.seek(0)
    return buf.getvalue()


def run_live_verification():
    print("=" * 60)
    print("STAGE 11 LIVE VERIFICATION: ASK MY CODEBASE Q&A")
    print("=" * 60)

    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[PASS] Backend API is healthy.")

    # 2. Register & login test user
    ts = int(time.time())
    email = f"qa_tester_{ts}@example.com"
    password = "Password123!"

    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "name": "QA Codebase Tester"},
    )
    assert reg_res.status_code in (200, 201), f"Registration failed: {reg_res.text}"

    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[PASS] User registered and authenticated: {email}")

    # 3. Create project
    proj_res = client.post(
        "/api/projects",
        json={
            "name": f"QA Diagnostic Target {ts}",
            "description": "Stage 11 Q&A verification project",
            "source_type": "zip",
        },
        headers=headers,
    )
    assert proj_res.status_code == 201, f"Create project failed: {proj_res.text}"
    project_id = proj_res.json()["id"]
    print(f"[PASS] Project created: {project_id}")

    # 4. Upload zip
    zip_bytes = create_test_zip()
    upload_res = client.post(
        f"/api/projects/{project_id}/upload",
        files={"file": ("code.zip", zip_bytes, "application/zip")},
        headers=headers,
    )
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    print("[PASS] ZIP codebase uploaded and extracted.")

    # 5. Scan repository
    scan_res = client.post(f"/api/projects/{project_id}/scan", headers=headers)
    assert scan_res.status_code == 200, f"Scan failed: {scan_res.text}"
    print(f"[PASS] Repository scanned: {scan_res.json()['total_files']} files discovered.")

    # 6. Run deterministic quality & security audits
    qual_res = client.post(f"/api/projects/{project_id}/analyze/quality", headers=headers)
    assert qual_res.status_code == 200
    sec_res = client.post(f"/api/projects/{project_id}/analyze/security", headers=headers)
    assert sec_res.status_code == 200
    print("[PASS] Deterministic quality and security analyzers executed.")

    # 7. Validation test: Empty question -> 422 Unprocessable Entity
    empty_res = client.post(
        f"/api/projects/{project_id}/ask",
        json={"question": ""},
        headers=headers,
    )
    assert empty_res.status_code == 422, f"Expected 422 for empty question, got {empty_res.status_code}"
    print("[PASS] Empty question validation rejected with HTTP 422.")

    # 8. Unauthenticated access test -> 401 Unauthorized
    unauth_res = client.post(
        f"/api/projects/{project_id}/ask",
        json={"question": "Where is auth?"},
    )
    assert unauth_res.status_code == 401, f"Expected 401, got {unauth_res.status_code}"
    print("[PASS] Unauthenticated access rejected with HTTP 401.")

    # 9. Non-owner / unauthorized project access test -> 404 Not Found
    other_email = f"other_user_{ts}@example.com"
    client.post("/api/auth/register", json={"email": other_email, "password": password, "name": "Other User"})
    other_login = client.post("/api/auth/login", json={"email": other_email, "password": password})
    other_token = other_login.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    forbidden_res = client.post(
        f"/api/projects/{project_id}/ask",
        json={"question": "How is authentication handled?"},
        headers=other_headers,
    )
    assert forbidden_res.status_code == 404, f"Expected 404 for non-owner, got {forbidden_res.status_code}"
    print("[PASS] Project access control verified: Non-owner gets 404.")

    # 10. Live Q&A endpoint invocation
    ask_payload = {
        "question": "Where is user authentication and token creation implemented?",
        "conversation": [],
    }
    ask_res = client.post(
        f"/api/projects/{project_id}/ask",
        json=ask_payload,
        headers=headers,
    )
    print(f"Ask API Status Code: {ask_res.status_code}")

    if ask_res.status_code == 200:
        qa_data = ask_res.json()
        print("[PASS] Real Gemini Q&A answer returned successfully:")
        print(f"  Answer: {qa_data['answer'][:120]}...")
        print(f"  Sources count: {len(qa_data['sources'])}")
        for src in qa_data["sources"]:
            print(f"    - {src['file_path']} (L{src.get('line_start')}-L{src.get('line_end')}): {src.get('reason')}")
    elif ask_res.status_code == 503:
        detail = ask_res.json().get("detail", "")
        print(f"[PASS] Graceful degradation verified (HTTP 503): {detail}")
    else:
        raise AssertionError(f"Unexpected status code {ask_res.status_code}: {ask_res.text}")

    # 11. Direct service citation verification and zero-hallucination test
    print("\nVerifying direct CodebaseQAService citation filtering & zero-hallucination engine...")
    from backend.app.core.database import SessionLocal
    from backend.app.models.user import User
    from backend.app.models.project import Project
    from backend.app.ai.qa_service import CodebaseQAService
    from backend.app.ai.schemas import CodebaseQAOutput, SourceCitation
    from backend.app.ai.retrieval import CodebaseRetriever

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None

        project = db.query(Project).filter(Project.id == project_id).first()
        assert project is not None

        # Test CodebaseRetriever disallows .env and masks secrets
        retriever = CodebaseRetriever(project, db)
        ctx = retriever.retrieve("authentication jwt secret password")
        
        # Verify .env is strictly excluded from snippets
        for s in ctx.code_snippets:
            assert ".env" not in s.file_path, f".env was not blocked from snippet retrieval: {s.file_path}"
        print("[PASS] Sensitive .env file strictly blocked from retrieval context.")

        # Test secret masking
        for snip in ctx.code_snippets:
            assert "super-secret-token-key" not in snip.content, "Raw secret leaked in code snippet!"
        print("[PASS] Secret masking verified: Raw secrets properly redacted before sending to LLM.")

        # Test Citation Pruning (Zero Hallucination Filter)
        qa_service = CodebaseQAService(db)
        mock_output = CodebaseQAOutput(
            answer="Authentication is implemented using PyJWT in auth/jwt.py.",
            sources=[
                SourceCitation(
                    file_path="auth/jwt.py",
                    line_start=1,
                    line_end=20,
                    reason="JWT creation and token decoding logic",
                ),
                SourceCitation(
                    file_path="fake_directory/hallucinated_auth.py",
                    line_start=10,
                    line_end=30,
                    reason="Hallucinated file that does not exist in repo",
                ),
            ],
        )

        with patch("backend.app.ai.qa_service.GeminiClient.generate_qa_answer", return_value=mock_output):
            result = qa_service.answer_question(
                project_id=project_id,
                user_id=user.id,
                question="How is authentication handled?",
            )
            assert result.available is True
            # The real file should be kept
            file_paths = [s.file_path for s in result.sources]
            assert "auth/jwt.py" in file_paths, "Real source file should be preserved in citations"
            # The hallucinated file MUST be pruned
            assert "fake_directory/hallucinated_auth.py" not in file_paths, "Hallucinated file was NOT pruned!"
            print("[PASS] Strict citation filtering verified: Real source file preserved, hallucinated file pruned.")

    finally:
        db.close()

    print("\n" + "=" * 60)
    print("ALL STAGE 11 LIVE VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_live_verification()
