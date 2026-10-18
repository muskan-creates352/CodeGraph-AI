from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import check_falkordb_health
from app.routers.analyze import router as analyze_router
from app.routers.investigate import router as investigate_router

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Backend API for CodeGraph AI - AI-powered codebase investigation agent",
)

# Enable CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(investigate_router)


@app.get("/health", tags=["System"])
def get_system_health():
    """Report that the FastAPI backend server is alive and operational."""
    return {
        "status": "healthy",
        "service": settings.api_title,
        "version": settings.api_version,
    }


@app.get("/api/db-health", tags=["Database"])
def get_database_health():
    """
    Test real connectivity to FalkorDB and verify Cypher query execution.
    Returns safe connection telemetry without exposing credentials.
    """
    health = check_falkordb_health()
    if health.get("status") == "connected":
        return JSONResponse(status_code=status.HTTP_200_OK, content=health)
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health,
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
