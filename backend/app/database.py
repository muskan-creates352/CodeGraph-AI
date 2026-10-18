import logging
from typing import Any, Dict
from falkordb import FalkorDB
from app.config import settings

logger = logging.getLogger(__name__)


def get_falkordb_client() -> FalkorDB:
    """Instantiate and return a FalkorDB client instance."""
    kwargs: Dict[str, Any] = {
        "host": settings.falkordb_host,
        "port": settings.falkordb_port,
    }
    if settings.falkordb_password:
        kwargs["password"] = settings.falkordb_password

    return FalkorDB(**kwargs)


def get_graph(graph_name: str | None = None):
    """Retrieve a specific graph handle from FalkorDB."""
    client = get_falkordb_client()
    target_graph = graph_name or settings.falkordb_graph_name
    return client.select_graph(target_graph)


def check_falkordb_health() -> Dict[str, Any]:
    """
    Test real connectivity to FalkorDB without exposing credentials.
    Returns a dictionary with status, host, port, and latency/error.
    """
    try:
        client = get_falkordb_client()
        # Verify underlying Redis connection
        if hasattr(client, "connection") and client.connection:
            client.connection.ping()

        # Run a minimal Cypher test query on a temporary ephemeral check
        test_graph = client.select_graph("health_check_ephemeral")
        result = test_graph.query("RETURN 1 AS alive")
        
        # Clean up ephemeral health check graph
        try:
            test_graph.delete()
        except Exception:
            pass

        return {
            "status": "connected",
            "database": "FalkorDB",
            "host": settings.falkordb_host,
            "port": settings.falkordb_port,
            "active_graph": settings.falkordb_graph_name,
            "query_verified": True,
        }
    except Exception as exc:
        logger.error(f"FalkorDB connection check failed: {exc}")
        return {
            "status": "error",
            "database": "FalkorDB",
            "host": settings.falkordb_host,
            "port": settings.falkordb_port,
            "query_verified": False,
            "error_message": str(exc),
        }
