import os
import sys

# Silence GitPython binary check on serverless import
os.environ["GIT_PYTHON_REFRESH"] = "0"

# Mark execution environment as Vercel serverless
os.environ.setdefault("VERCEL", "1")

# Ensure all possible serverless directory structures are in sys.path
_curr = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.abspath(os.path.join(_curr, ".."))
_cwd = os.getcwd()
_lambda_root = os.environ.get("LAMBDA_TASK_ROOT", "/var/task")

for _p in [_parent, _curr, _cwd, _lambda_root]:
    if os.path.exists(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

# Ensure temporary storage directory and writable SQLite database for serverless environment
if not os.environ.get("STORAGE_DIR"):
    os.environ["STORAGE_DIR"] = "/tmp/storage"

if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite:////tmp/project_doctor.db"

try:
    os.makedirs("/tmp/storage", exist_ok=True)
except Exception:
    pass

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Top-level ASGI entrypoint required by Vercel Function runtime for FastAPI
app = FastAPI(title="Project Doctor")

init_error = None
try:
    from backend.app.main import app as backend_app
    app = backend_app


    # Automatically initialize database tables on cold start
    try:
        from backend.app.core.database import init_db
        init_db()
    except Exception as db_err:
        print(f"Serverless init_db notice: {db_err}", file=sys.stderr)

except Exception as err:
    import traceback
    init_error = traceback.format_exc()
    print(f"CRITICAL BACKEND STARTUP ERROR:\n{init_error}", file=sys.stderr)

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    async def fallback_route(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Backend initialization failed",
                "details": str(err),
                "traceback": init_error,
                "cwd": os.getcwd(),
                "sys_path": sys.path,
                "dir_contents": os.listdir(os.getcwd()) if os.path.exists(os.getcwd()) else []
            }
        )


