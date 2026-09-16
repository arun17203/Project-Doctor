import os
import sys

# Silence GitPython binary check on serverless import
os.environ["GIT_PYTHON_REFRESH"] = "0"

# Mark execution environment as Vercel serverless
os.environ.setdefault("VERCEL", "1")

# Ensure root repository directory is in sys.path so 'backend.app...' imports resolve
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Ensure temporary storage directory and writable SQLite database for serverless environment
if not os.environ.get("STORAGE_DIR"):
    os.environ["STORAGE_DIR"] = "/tmp/storage"

if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite:////tmp/project_doctor.db"

try:
    os.makedirs("/tmp/storage", exist_ok=True)
except Exception:
    pass

try:
    from backend.app.core.database import init_db
    from backend.app.main import app

    # Automatically initialize database tables on cold start
    try:
        init_db()
    except Exception as err:
        print(f"Serverless init_db notice: {err}", file=sys.stderr)

except Exception as exc:
    import traceback
    err_tb = traceback.format_exc()
    print(f"Serverless app startup error:\n{err_tb}", file=sys.stderr)

    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="Project Doctor Error Fallback")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def fallback_error_handler(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Backend initialization failed",
                "details": str(exc),
                "path": path,
            },
        )

