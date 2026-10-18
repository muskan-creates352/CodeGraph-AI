"""
Automated tests for FalkorDB Graph Ingestion & Cypher Verification
Verifies entity storage, relationships, idempotency, isolation, and API endpoints.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.database import get_graph, get_falkordb_client
from app.graph.ingestion import GraphIngestionService, sanitize_graph_name
from app.main import app

DEMO_REPO_PATH = str(Path(__file__).resolve().parent.parent.parent / "demo_repo")
TEST_GRAPH_NAME = "codegraph_test"
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_test_graph():
    """Ensure clean test graph before and after the test suite."""
    g = get_graph(TEST_GRAPH_NAME)
    try:
        g.query("MATCH (n) DETACH DELETE n")
    except Exception:
        pass

    yield g

    try:
        g.delete()
    except Exception:
        pass


def test_1_ingest_demo_repo_into_falkordb():
    """Verify demo_repo can be ingested and returns accurate entity counts."""
    service = GraphIngestionService()
    stats = service.ingest_repository(
        repo_path=DEMO_REPO_PATH,
        graph_name=TEST_GRAPH_NAME,
        clean_existing=True,
    )

    assert stats.files_count >= 6
    assert stats.classes_count >= 2
    assert stats.functions_count >= 10
    assert stats.calls_count >= 5
    assert stats.total_nodes_in_db > 0
    assert stats.total_relationships_in_db > 0
    assert stats.execution_time_ms > 0
    assert len(stats.parse_errors) == 0


def test_2_verify_file_nodes_stored_and_retrieved():
    """Verify :File nodes have expected properties in FalkorDB."""
    g = get_graph(TEST_GRAPH_NAME)
    res = g.query("MATCH (f:File {name: 'logger.py'}) RETURN f.id, f.path, f.line_count")

    assert res.result_set is not None
    assert len(res.result_set) == 1
    row = res.result_set[0]
    assert row[0] == "file:utils/logger.py"
    assert row[1] == "utils/logger.py"
    assert int(row[2]) > 0


def test_3_verify_class_and_function_nodes():
    """Verify :Class and :Function nodes can be queried via Cypher."""
    g = get_graph(TEST_GRAPH_NAME)

    # Verify Class
    class_res = g.query("MATCH (c:Class {name: 'OrderService'}) RETURN c.id, c.file_path")
    assert len(class_res.result_set) == 1
    assert class_res.result_set[0][1] == "services/order_service.py"

    # Verify Function
    func_res = g.query("MATCH (fn:Function {name: 'calculate_discount'}) RETURN fn.scope, fn.is_method")
    assert len(func_res.result_set) == 1
    assert func_res.result_set[0][0] == "global"
    assert func_res.result_set[0][1] is False


def test_4_verify_contains_relationships():
    """Verify File-CONTAINS-Class, Class-CONTAINS-Function, and File-CONTAINS-Function."""
    g = get_graph(TEST_GRAPH_NAME)

    # File CONTAINS Class
    f_c_res = g.query(
        "MATCH (f:File {name: 'order_service.py'})-[:CONTAINS]->(c:Class {name: 'OrderService'}) "
        "RETURN c.name"
    )
    assert len(f_c_res.result_set) == 1

    # Class CONTAINS Method
    c_fn_res = g.query(
        "MATCH (c:Class {name: 'OrderService'})-[:CONTAINS]->(m:Function {name: 'checkout_order'}) "
        "RETURN m.name"
    )
    assert len(c_fn_res.result_set) == 1

    # File CONTAINS Standalone Function
    f_fn_res = g.query(
        "MATCH (f:File {name: 'logger.py'})-[:CONTAINS]->(fn:Function {name: 'log_info'}) "
        "RETURN fn.name"
    )
    assert len(f_fn_res.result_set) == 1


def test_5_verify_calls_relationships():
    """Verify resolved CALLS edges match actual invocation in the code."""
    g = get_graph(TEST_GRAPH_NAME)

    # process_order_payment CALLS charge_credit_card
    res = g.query(
        "MATCH (caller:Function {name: 'process_order_payment'})-[r:CALLS]->(callee:Function {name: 'charge_credit_card'}) "
        "RETURN r.line_number"
    )
    assert len(res.result_set) >= 1
    assert int(res.result_set[0][0]) > 0


def test_6_verify_imports_relationships():
    """Verify File IMPORTS File edges exist."""
    g = get_graph(TEST_GRAPH_NAME)
    res = g.query(
        "MATCH (src:File {name: 'order_service.py'})-[r:IMPORTS]->(dst:File {name: 'discount_service.py'}) "
        "RETURN r.line_number"
    )
    assert len(res.result_set) == 1
    assert int(res.result_set[0][0]) > 0


def test_7_verify_inherits_from_relationships():
    """Verify Class INHERITS_FROM Class relationships exist."""
    g = get_graph(TEST_GRAPH_NAME)
    res = g.query(
        "MATCH (sub:Class {name: 'PercentageDiscountRule'})-[:INHERITS_FROM]->(sup:Class {name: 'BaseDiscountRule'}) "
        "RETURN sup.name"
    )
    assert len(res.result_set) == 1
    assert res.result_set[0][0] == "BaseDiscountRule"


def test_8_verify_idempotency_no_duplicate_nodes():
    """Verify that re-ingesting the repository does not duplicate nodes or edges."""
    g = get_graph(TEST_GRAPH_NAME)
    initial_nodes = int(g.query("MATCH (n) RETURN count(n)").result_set[0][0])
    initial_rels = int(g.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0])

    # Ingest again without clean_existing
    service = GraphIngestionService()
    service.ingest_repository(
        repo_path=DEMO_REPO_PATH,
        graph_name=TEST_GRAPH_NAME,
        clean_existing=False,
    )

    reingested_nodes = int(g.query("MATCH (n) RETURN count(n)").result_set[0][0])
    reingested_rels = int(g.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0])

    assert reingested_nodes == initial_nodes, "Re-ingestion created duplicate nodes!"
    assert reingested_rels == initial_rels, "Re-ingestion created duplicate relationships!"


def test_9_verify_graph_isolation():
    """Verify that separate graph names maintain independent state."""
    graph_a_name = "codegraph_test_iso_a"
    graph_b_name = "codegraph_test_iso_b"

    ga = get_graph(graph_a_name)
    gb = get_graph(graph_b_name)

    try:
        ga.query("CREATE (:File {id: 'file:only_in_a.py', name: 'only_in_a.py'})")
        gb.query("CREATE (:File {id: 'file:only_in_b.py', name: 'only_in_b.py'})")

        res_a = ga.query("MATCH (f:File) RETURN f.name")
        res_b = gb.query("MATCH (f:File) RETURN f.name")

        names_a = [r[0] for r in res_a.result_set]
        names_b = [r[0] for r in res_b.result_set]

        assert "only_in_a.py" in names_a
        assert "only_in_b.py" not in names_a

        assert "only_in_b.py" in names_b
        assert "only_in_a.py" not in names_b
    finally:
        try:
            ga.delete()
        except Exception:
            pass
        try:
            gb.delete()
        except Exception:
            pass


def test_10_api_analyze_endpoint():
    """Verify POST /api/analyze can trigger demo ingestion via HTTP."""
    response = client.post("/api/analyze", json={"is_demo": True, "graph_name": "codegraph_api_test"})
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["graph_name"] == "codegraph_api_test"
    assert data["files_ingested"] >= 6
    assert data["total_nodes_in_db"] > 0
    assert data["total_relationships_in_db"] > 0

    # Clean up test api graph
    try:
        get_graph("codegraph_api_test").delete()
    except Exception:
        pass
