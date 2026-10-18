"""
CodeGraph AI - Graph Ingestion Engine
Transforms AST static analysis results into a queryable graph in FalkorDB.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.database import get_falkordb_client, get_graph
from app.parser.ast_analyzer import (
    ASTAnalyzer,
    AnalysisResult,
    ClassNode,
    FileNode,
    FunctionNode,
)

logger = logging.getLogger(__name__)


def sanitize_graph_name(repo_identifier: str) -> str:
    """
    Generate a safe, isolated, alphanumeric FalkorDB graph identifier from a repository path.
    Example: 'demo_repo' -> 'codegraph_demo_repo'
    """
    norm = Path(repo_identifier).name.strip().lower()
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", norm)
    clean = clean.strip("_")
    return f"codegraph_{clean}" if clean else settings.falkordb_graph_name


@dataclass
class IngestionStats:
    """Summary metrics of the graph ingestion operation."""
    graph_name: str
    repo_path: str
    files_count: int = 0
    classes_count: int = 0
    functions_count: int = 0
    calls_count: int = 0
    imports_count: int = 0
    inheritances_count: int = 0
    total_nodes_in_db: int = 0
    total_relationships_in_db: int = 0
    parse_errors: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_ms: float = 0.0


class GraphIngestionService:
    """Orchestrates AST parsing and atomic graph population in FalkorDB."""

    def __init__(self, analyzer: Optional[ASTAnalyzer] = None):
        self.analyzer = analyzer or ASTAnalyzer()

    def ensure_indexes(self, graph) -> None:
        """Create indexes on primary node IDs to optimize traversal and lookups."""
        index_queries = [
            "CREATE INDEX FOR (f:File) ON (f.id)",
            "CREATE INDEX FOR (c:Class) ON (c.id)",
            "CREATE INDEX FOR (fn:Function) ON (fn.id)",
        ]
        for q in index_queries:
            try:
                graph.query(q)
            except Exception:
                # Index may already exist or engine handles idempotency
                pass

    def ingest_repository(
        self,
        repo_path: str,
        graph_name: Optional[str] = None,
        clean_existing: bool = True,
    ) -> IngestionStats:
        """
        Parses the repository with ASTAnalyzer and merges all entities and relations
        into FalkorDB.
        """
        start_time = time.perf_counter()

        target_graph_name = graph_name or sanitize_graph_name(repo_path)
        graph = get_graph(target_graph_name)

        # 1. Run zero-execution AST static analysis
        analysis: AnalysisResult = self.analyzer.analyze_repository(repo_path)

        # 2. Optionally purge previous graph state for this isolated repository
        if clean_existing:
            try:
                graph.query("MATCH (n) DETACH DELETE n")
            except Exception as exc:
                logger.warning(f"Could not clear graph before ingestion: {exc}")

        # 3. Ensure performance indexes exist
        self.ensure_indexes(graph)

        # 4. Ingest File Nodes
        for f in analysis.files:
            graph.query(
                "MERGE (node:File {id: $id}) "
                "ON CREATE SET node.path = $path, node.name = $name, node.line_count = $lines "
                "ON MATCH SET node.path = $path, node.name = $name, node.line_count = $lines",
                {
                    "id": f.id,
                    "path": f.path,
                    "name": f.name,
                    "lines": f.line_count,
                },
            )

        # 5. Ingest Class Nodes and File-CONTAINS-Class relationships
        for c in analysis.classes:
            graph.query(
                "MERGE (node:Class {id: $id}) "
                "ON CREATE SET node.name = $name, node.file_path = $file_path, "
                "node.start_line = $start_line, node.end_line = $end_line "
                "ON MATCH SET node.name = $name, node.file_path = $file_path, "
                "node.start_line = $start_line, node.end_line = $end_line",
                {
                    "id": c.id,
                    "name": c.name,
                    "file_path": c.file_path,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                },
            )
            file_id = f"file:{c.file_path}"
            graph.query(
                "MATCH (f:File {id: $file_id}), (c:Class {id: $class_id}) "
                "MERGE (f)-[:CONTAINS]->(c)",
                {"file_id": file_id, "class_id": c.id},
            )

        # 6. Ingest Function Nodes and CONTAINS relationships
        for fn in analysis.functions:
            graph.query(
                "MERGE (node:Function {id: $id}) "
                "ON CREATE SET node.name = $name, node.file_path = $file_path, "
                "node.scope = $scope, node.start_line = $start_line, "
                "node.end_line = $end_line, node.is_method = $is_method "
                "ON MATCH SET node.name = $name, node.file_path = $file_path, "
                "node.scope = $scope, node.start_line = $start_line, "
                "node.end_line = $end_line, node.is_method = $is_method",
                {
                    "id": fn.id,
                    "name": fn.name,
                    "file_path": fn.file_path,
                    "scope": fn.scope,
                    "start_line": fn.start_line,
                    "end_line": fn.end_line,
                    "is_method": fn.is_method,
                },
            )

            if fn.is_method:
                # Class CONTAINS Function (method)
                class_id = f"class:{fn.file_path}:{fn.scope}"
                graph.query(
                    "MATCH (c:Class {id: $class_id}), (f:Function {id: $func_id}) "
                    "MERGE (c)-[:CONTAINS]->(f)",
                    {"class_id": class_id, "func_id": fn.id},
                )
            else:
                # File CONTAINS Function (standalone)
                file_id = f"file:{fn.file_path}"
                graph.query(
                    "MATCH (f:File {id: $file_id}), (fn:Function {id: $func_id}) "
                    "MERGE (f)-[:CONTAINS]->(fn)",
                    {"file_id": file_id, "func_id": fn.id},
                )

        # 7. Ingest Class Inheritance Relationships
        for inh in analysis.inheritances:
            if inh.resolved_superclass_id:
                graph.query(
                    "MATCH (sub:Class {id: $sub_id}), (sup:Class {id: $sup_id}) "
                    "MERGE (sub)-[:INHERITS_FROM]->(sup)",
                    {"sub_id": inh.subclass_id, "sup_id": inh.resolved_superclass_id},
                )

        # 8. Ingest File IMPORTS File Relationships
        for imp in analysis.imports:
            if imp.resolved_file and imp.resolved_file != imp.source_file:
                src_file_id = f"file:{imp.source_file}"
                dst_file_id = f"file:{imp.resolved_file}"
                graph.query(
                    "MATCH (src:File {id: $src_id}), (dst:File {id: $dst_id}) "
                    "MERGE (src)-[r:IMPORTS]->(dst) "
                    "ON CREATE SET r.line_number = $line "
                    "ON MATCH SET r.line_number = $line",
                    {
                        "src_id": src_file_id,
                        "dst_id": dst_file_id,
                        "line": imp.line_number,
                    },
                )

        # 9. Ingest Function CALLS Function Relationships (Resolved Calls)
        calls_landed = 0
        for call in analysis.calls:
            if call.is_resolved and call.resolved_callee_id:
                # If caller is a Function
                if call.caller_id.startswith("func:"):
                    graph.query(
                        "MATCH (caller:Function {id: $caller_id}), (callee:Function {id: $callee_id}) "
                        "MERGE (caller)-[r:CALLS]->(callee) "
                        "SET r.line_number = $line",
                        {
                            "caller_id": call.caller_id,
                            "callee_id": call.resolved_callee_id,
                            "line": call.line_number,
                        },
                    )
                    calls_landed += 1
                elif call.caller_id.startswith("file:"):
                    # Top-level module execution calling a function
                    graph.query(
                        "MATCH (caller:File {id: $caller_id}), (callee:Function {id: $callee_id}) "
                        "MERGE (caller)-[r:CALLS]->(callee) "
                        "SET r.line_number = $line",
                        {
                            "caller_id": call.caller_id,
                            "callee_id": call.resolved_callee_id,
                            "line": call.line_number,
                        },
                    )
                    calls_landed += 1

        # 10. Verify Real Counts directly from FalkorDB
        total_nodes = 0
        total_relationships = 0

        try:
            node_res = graph.query("MATCH (n) RETURN count(n) AS cnt")
            if node_res.result_set and len(node_res.result_set) > 0:
                total_nodes = int(node_res.result_set[0][0])

            rel_res = graph.query("MATCH ()-[r]->() RETURN count(r) AS cnt")
            if rel_res.result_set and len(rel_res.result_set) > 0:
                total_relationships = int(rel_res.result_set[0][0])
        except Exception as exc:
            logger.error(f"Failed to query verification counts: {exc}")

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return IngestionStats(
            graph_name=target_graph_name,
            repo_path=str(Path(repo_path).resolve()),
            files_count=len(analysis.files),
            classes_count=len(analysis.classes),
            functions_count=len(analysis.functions),
            calls_count=calls_landed,
            imports_count=len([i for i in analysis.imports if i.resolved_file]),
            inheritances_count=len([h for h in analysis.inheritances if h.resolved_superclass_id]),
            total_nodes_in_db=total_nodes,
            total_relationships_in_db=total_relationships,
            parse_errors=analysis.errors,
            execution_time_ms=round(elapsed_ms, 2),
        )
