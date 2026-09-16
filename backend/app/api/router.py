from datetime import datetime, timezone
from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.core.database import check_db_connection
from backend.app.schemas.common import HealthResponse
from backend.app.api.auth import auth_router
from backend.app.api.projects import projects_router
from backend.app.api.scans import scans_router
from backend.app.api.quality import quality_router
from backend.app.api.security import security_router
from backend.app.api.dependencies import dependencies_router
from backend.app.api.architecture import architecture_router
from backend.app.api.health_analyzer import health_router
from backend.app.api.ai_explainer import router as ai_explainer_router
from backend.app.api.codebase_qa import qa_router
from backend.app.api.history import history_router
from backend.app.api.remediation import remediation_router

api_router = APIRouter()

# Register sub-routers
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(scans_router)
api_router.include_router(quality_router)
api_router.include_router(security_router)
api_router.include_router(dependencies_router)
api_router.include_router(architecture_router)
api_router.include_router(health_router)
api_router.include_router(ai_explainer_router)
api_router.include_router(qa_router)
api_router.include_router(history_router)
api_router.include_router(remediation_router)


@api_router.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Health check endpoint to verify backend service and database connectivity."""
    db_ok = check_db_connection()
    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        database="connected" if db_ok else "disconnected",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
