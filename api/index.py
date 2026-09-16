import os
import sys

# Ensure root repository directory is in sys.path so 'backend.app...' imports resolve
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Ensure temporary storage directory for serverless environment
if not os.environ.get("STORAGE_DIR"):
    os.environ["STORAGE_DIR"] = "/tmp/storage"

if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite:////tmp/project_doctor.db"

from backend.app.core.database import init_db
from backend.app.main import app

# Automatically initialize database tables on cold start if needed
try:
    init_db()
except Exception as err:
    print(f"Serverless init_db notice: {err}")
