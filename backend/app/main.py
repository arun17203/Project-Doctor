from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback
import sys

from backend.app.core.config import settings
from backend.app.api.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Doctor for Software: Comprehensive static code analysis, security auditing, dependency analysis, architecture visualization, and AI codebase assistant.",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print(f"UNHANDLED EXCEPTION on {request.method} {request.url.path}:\n{tb}", file=sys.stderr)
    return JSONResponse(
        status_code=500,
        content={
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            "traceback": tb,
            "path": str(request.url.path),
        },
    )

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Router
app.include_router(api_router, prefix="/api")



@app.get("/")
def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs",
    }


@app.get("/api/test", tags=["Diagnostic"])
def api_test():
    from backend.app.core.database import check_db_connection
    return {
        "status": "ok",
        "database": "connected" if check_db_connection() else "disconnected",
        "message": "Project Doctor backend is running cleanly on Vercel!",
    }



@app.get("/health", tags=["Health"])
def liveness_health():
    """Lightweight liveness probe for Docker, Kubernetes, and reverse proxies."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"])
def readiness_health():
    """Readiness probe checking database connectivity."""
    from backend.app.core.database import check_db_connection
    from fastapi import HTTPException, status

    db_ok = check_db_connection()
    if not db_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connectivity unavailable",
        )
    return {
        "status": "ready",
        "database": "connected",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
