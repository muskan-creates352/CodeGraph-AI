"""
Automated tests for CodeGraph AI Investigation Agent
Verifies Blast Radius Impact, Call Path Tracing, Dead Code Detection,
Evidence Formatting, and REST API Endpoints.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.agent.engine import CodeGraphAgent
from app.database import get_graph
from app.graph.ingestion import GraphIngestionService
from app.main import app

DEMO_REPO_PATH = str(Path(__file__).resolve().parent.parent.parent / "demo_repo")
AGENT_TEST_GRAPH = "codegraph_agent_test"
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_agent_test_graph():
    """Ingest demo repository into isolated test graph once for all agent tests."""
    service = GraphIngestionService()
    service.ingest_repository(
        repo_path=DEMO_REPO_PATH,
        graph_name=AGENT_TEST_GRAPH,
        clean_existing=True,
    )

    yield

    try:
        get_graph(AGENT_TEST_GRAPH).delete()
    except Exception:
        pass


@pytest.fixture
def agent() -> CodeGraphAgent:
    return CodeGraphAgent(graph_name=AGENT_TEST_GRAPH)


# ============================================================================
# 1. Blast Radius / Impact Analysis Tests
# ============================================================================

def test_1_impact_analysis_valid_function(agent: CodeGraphAgent):
    """Verify impact analysis discovers both direct and indirect upstream callers."""
    res = agent.analyze_impact(target_name="charge_credit_card", max_depth=5)

    assert res.status == "success"
    assert res.investigation_type == "impact_analysis"
    assert res.target == "charge_credit_card"
    assert res.details["impact_score"] > 0

    # process_order_payment directly calls charge_credit_card (depth 1)
    direct_names = [e["name"] for e in res.details["direct_impacts"]]
    assert "process_order_payment" in direct_names

    # checkout_order indirectly calls charge_credit_card via process_order_payment (depth > 1)
    all_affected = direct_names + [e["name"] for e in res.details["indirect_impacts"]]
    assert "checkout_order" in all_affected

    # Evidence paths are populated
    assert len(res.evidence_paths) > 0
    assert "process_order_payment" in res.evidence_paths[0]["from_node"]


def test_2_impact_analysis_missing_entity(agent: CodeGraphAgent):
    """Verify requesting impact for non-existent function returns not_found status."""
    res = agent.analyze_impact(target_name="non_existent_function_xyz")
    assert res.status == "not_found"
    assert "was not found" in res.summary


def test_3_impact_analysis_isolated_entity(agent: CodeGraphAgent):
    """Verify dead/uncalled function reports zero upstream impact."""
    res = agent.analyze_impact(target_name="legacy_format_currency")
    assert res.status == "success"
    assert res.details["direct_impact_count"] == 0
    assert res.details["indirect_impact_count"] == 0
    assert res.details["impact_score"] == 0


# ============================================================================
# 2. Call Path Tracing Tests
# ============================================================================

def test_4_call_path_tracing_valid_path(agent: CodeGraphAgent):
    """Verify shortest path successfully traces multi-hop call execution."""
    res = agent.trace_call_path(
        source_name="post_checkout_endpoint",
        destination_name="format_log_entry",
    )

    assert res.status == "success"
    assert res.investigation_type == "call_path_tracing"
    assert res.details["hops"] >= 2

    # The chain must start with post_checkout_endpoint and end with format_log_entry
    path_nodes = [n["name"] for n in res.details["path_nodes"]]
    assert path_nodes[0] == "post_checkout_endpoint"
    assert path_nodes[-1] == "format_log_entry"

    # Evidence steps show pairwise links
    assert len(res.evidence_paths) == res.details["hops"]
    assert res.evidence_paths[0]["from_node"] == "post_checkout_endpoint"


def test_5_call_path_tracing_missing_nodes(agent: CodeGraphAgent):
    """Verify path tracing handles unknown functions cleanly."""
    res = agent.trace_call_path(
        source_name="post_checkout_endpoint",
        destination_name="missing_callee_func",
    )
    assert res.status == "not_found"
    assert "Destination 'missing_callee_func'" in res.summary


def test_6_call_path_tracing_no_path_exists(agent: CodeGraphAgent):
    """Verify reverse or disconnected functions report no_path status."""
    # format_log_entry does NOT call post_checkout_endpoint
    res = agent.trace_call_path(
        source_name="format_log_entry",
        destination_name="post_checkout_endpoint",
    )
    assert res.status == "no_path"
    assert "No call path exists" in res.summary
    assert res.details["hops"] == -1


# ============================================================================
# 3. Dead Code Detection Tests
# ============================================================================

def test_7_dead_code_investigation_confidence_scoring(agent: CodeGraphAgent):
    """Verify orphan detection scores high confidence for helpers and low for endpoints."""
    res = agent.investigate_dead_code()

    assert res.status == "success"
    assert res.investigation_type == "dead_code"
    assert res.details["total_candidates"] > 0

    candidates = {c["name"]: c for c in res.details["candidates"]}

    # Intentional dead helpers should be high confidence
    assert "legacy_format_currency" in candidates
    assert candidates["legacy_format_currency"]["confidence"] == "high"

    assert "calculate_vat_deprecated" in candidates
    assert candidates["calculate_vat_deprecated"]["confidence"] == "high"

    # Public endpoint post_checkout_endpoint should be low confidence (entrypoint)
    if "post_checkout_endpoint" in candidates:
        assert candidates["post_checkout_endpoint"]["confidence"] == "low"

    # Heavily called functions should not be present
    assert "log_info" not in candidates
    assert "charge_credit_card" not in candidates


# ============================================================================
# 4. REST API Endpoint Tests
# ============================================================================

def test_8_api_investigate_impact():
    """Verify POST /api/investigate endpoint handles impact mode."""
    response = client.post(
        "/api/investigate",
        json={
            "mode": "impact",
            "target": "charge_credit_card",
            "graph_name": AGENT_TEST_GRAPH,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["investigation_type"] == "impact_analysis"
    assert len(data["evidence_paths"]) > 0


def test_9_api_investigate_call_path():
    """Verify POST /api/investigate endpoint handles path mode."""
    response = client.post(
        "/api/investigate",
        json={
            "mode": "path",
            "source": "post_checkout_endpoint",
            "destination": "log_info",
            "graph_name": AGENT_TEST_GRAPH,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["details"]["hops"] >= 1


def test_10_api_investigate_dead_code():
    """Verify POST /api/investigate endpoint handles dead_code mode."""
    response = client.post(
        "/api/investigate",
        json={"mode": "dead_code", "graph_name": AGENT_TEST_GRAPH},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["details"]["high_confidence_count"] >= 2


def test_11_api_investigate_validation_errors():
    """Verify bad requests are rejected with status 400."""
    # Missing target in impact mode
    res1 = client.post("/api/investigate", json={"mode": "impact"})
    assert res1.status_code == 400

    # Missing source/dest in path mode
    res2 = client.post("/api/investigate", json={"mode": "path", "source": "a"})
    assert res2.status_code == 400

    # Invalid mode
    res3 = client.post("/api/investigate", json={"mode": "unknown_mode"})
    assert res3.status_code == 400


def test_12_api_get_graph_snapshot():
    """Verify GET /api/graph returns bounded nodes and links for frontend visualizer."""
    response = client.get(f"/api/graph?graph_name={AGENT_TEST_GRAPH}&limit=50")
    assert response.status_code == 200
    data = response.json()

    assert data["graph_name"] == AGENT_TEST_GRAPH
    assert "nodes" in data
    assert "links" in data
    assert len(data["nodes"]) > 0
    assert len(data["links"]) > 0
    assert data["total_nodes_in_db"] > 0
    assert data["total_edges_in_db"] > 0
