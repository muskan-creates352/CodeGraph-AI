"""
API routes for triggering codebase analysis and FalkorDB graph ingestion.
"""

from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.graph.ingestion import GraphIngestionService, sanitize_graph_name

router = APIRouter(prefix="/api", tags=["Analysis"])

# Compute workspace root and demo_repo path reliably
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEMO_REPO_PATH = WORKSPACE_ROOT / "demo_repo"


class AnalyzeRequest(BaseModel):
    """Payload for triggering repository analysis."""
    repo_path: Optional[str] = Field(None, description="Absolute or relative path to a local repository")
    is_demo: bool = Field(False, description="If True, analyzes the bundled demo_repo")
    clean_existing: bool = Field(True, description="If True, purges previously ingested graph state")
    graph_name: Optional[str] = Field(None, description="Optional custom FalkorDB graph identifier")


@router.get("/demo-repo")
def get_demo_repo_info() -> Dict[str, Any]:
    """Return availability and metadata about the pre-bundled demonstration repository."""
    exists = DEMO_REPO_PATH.exists() and DEMO_REPO_PATH.is_dir()
    return {
        "available": exists,
        "name": "E-Commerce Microservice Demo",
        "path": str(DEMO_REPO_PATH.resolve()) if exists else None,
        "description": "Pre-bundled Python codebase with orders, payments, discount rules, and dead helpers",
    }


@router.post("/analyze", status_code=status.HTTP_200_OK)
def analyze_repository(req: AnalyzeRequest) -> Dict[str, Any]:
    """
    Safely parse a Python repository with AST and ingest its entities into FalkorDB.
    """
    if req.is_demo:
        target_path = DEMO_REPO_PATH
    elif req.repo_path:
        target_path = Path(req.repo_path).resolve()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'is_demo' must be true or a valid 'repo_path' must be provided.",
        )

    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target repository path does not exist or is not a directory: {target_path}",
        )

    try:
        service = GraphIngestionService()
        stats = service.ingest_repository(
            repo_path=str(target_path),
            graph_name=req.graph_name or settings.falkordb_graph_name,
            clean_existing=req.clean_existing,
        )

        return {
            "status": "success",
            "graph_name": stats.graph_name,
            "repo_path": stats.repo_path,
            "files_ingested": stats.files_count,
            "classes_ingested": stats.classes_count,
            "functions_ingested": stats.functions_count,
            "calls_ingested": stats.calls_count,
            "imports_ingested": stats.imports_count,
            "inheritances_ingested": stats.inheritances_count,
            "total_nodes_in_db": stats.total_nodes_in_db,
            "total_relationships_in_db": stats.total_relationships_in_db,
            "execution_time_ms": stats.execution_time_ms,
            "errors": stats.parse_errors,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph ingestion failed: {str(exc)}",
        )
