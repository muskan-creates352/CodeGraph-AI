"""
API routes for Codebase Investigation Agent and Graph Visualization snapshot.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.agent.engine import CodeGraphAgent
from app.config import settings

router = APIRouter(prefix="/api", tags=["Investigation Agent"])


class InvestigateRequest(BaseModel):
    """Payload for triggering an evidence-backed codebase investigation."""
    mode: str = Field(
        ...,
        description="Investigation type: 'impact' (blast radius), 'path' (call trace), or 'dead_code'",
    )
    target: Optional[str] = Field(None, description="Function or Class name to investigate for impact")
    source: Optional[str] = Field(None, description="Starting function name for call path tracing")
    destination: Optional[str] = Field(None, description="Target destination function name for call path tracing")
    graph_name: Optional[str] = Field(None, description="Optional custom FalkorDB graph identifier")
    max_depth: int = Field(5, ge=1, le=10, description="Maximum traversal depth for impact analysis")


@router.post("/investigate", status_code=status.HTTP_200_OK)
def run_investigation(req: InvestigateRequest) -> Dict[str, Any]:
    """
    Run a connected-data investigation query using FalkorDB Cypher traversals.
    Returns verifiable graph paths and structured evidence.
    """
    agent = CodeGraphAgent(graph_name=req.graph_name or settings.falkordb_graph_name)

    mode = req.mode.strip().lower()

    if mode in ("impact", "blast_radius"):
        if not req.target or not req.target.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A 'target' function or class name is required for impact analysis.",
            )
        res = agent.analyze_impact(target_name=req.target.strip(), max_depth=req.max_depth)
        return res.to_dict()

    elif mode in ("path", "trace", "call_path"):
        if not req.source or not req.destination:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both 'source' and 'destination' function names are required for call path tracing.",
            )
        res = agent.trace_call_path(source_name=req.source.strip(), destination_name=req.destination.strip())
        return res.to_dict()

    elif mode in ("dead_code", "orphans", "unused"):
        res = agent.investigate_dead_code()
        return res.to_dict()

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported investigation mode '{req.mode}'. Choose from 'impact', 'path', or 'dead_code'.",
        )


@router.get("/graph", status_code=status.HTTP_200_OK)
def get_graph_summary(
    graph_name: Optional[str] = Query(None, description="Specific FalkorDB graph identifier"),
    limit: int = Query(150, ge=10, le=300, description="Max node and edge threshold"),
) -> Dict[str, Any]:
    """
    Return a bounded graph snapshot formatted for 2D/3D force-directed frontend visualization.
    """
    agent = CodeGraphAgent(graph_name=graph_name or settings.falkordb_graph_name)
    return agent.get_graph_snapshot(limit=limit)
