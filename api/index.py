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

from backend.app.main import app as backend_app

# Top-level ASGI / WSGI entrypoints required by Vercel Function runtime
app = backend_app
application = backend_app
handler = backend_app

# Automatically initialize database tables on cold start
try:
    from backend.app.core.database import init_db
    init_db()
except Exception as err:
    print(f"Serverless init_db notice: {err}", file=sys.stderr)

