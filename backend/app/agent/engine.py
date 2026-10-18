"""
CodeGraph AI - Investigation Agent Engine
Executes Cypher graph traversals in FalkorDB to conduct evidence-backed codebase investigations.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.agent.models import (
    AffectedEntity,
    CandidateDeadFunction,
    DeadCodeResult,
    ImpactAnalysisResult,
    InvestigationResponse,
    PathTraceResult,
)
from app.config import settings
from app.database import get_graph

logger = logging.getLogger(__name__)


class CodeGraphAgent:
    """
    Intelligent agent that acts directly on connected code graph data in FalkorDB.
    Specializes in blast radius impact, call path tracing, and dead code detection.
    """

    def __init__(self, graph_name: Optional[str] = None):
        self.graph_name = graph_name or settings.falkordb_graph_name

    def _get_graph(self):
        return get_graph(self.graph_name)

    def analyze_impact(self, target_name: str, max_depth: int = 5) -> InvestigationResponse:
        """
        Assess blast radius: find all functions and files that depend on the target.
        Traverses incoming CALLS and IMPORTS relationships.
        """
        start_time = time.perf_counter()
        graph = self._get_graph()
        cypher_queries: List[str] = []

        # 1. Locate Target Node(s)
        find_target_q = (
            "MATCH (n) WHERE (n:Function OR n:Class) AND n.name = $name "
            "RETURN n.id, labels(n)[0] AS label, n.name, coalesce(n.file_path, '') AS file_path, "
            "coalesce(n.scope, '') AS scope"
        )
        cypher_queries.append(find_target_q)
        target_res = graph.query(find_target_q, {"name": target_name})

        if not target_res.result_set or len(target_res.result_set) == 0:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return InvestigationResponse(
                investigation_type="impact_analysis",
                target=target_name,
                status="not_found",
                summary=f"Entity '{target_name}' was not found in the codebase graph '{self.graph_name}'.",
                details={},
                cypher_queries=cypher_queries,
                execution_time_ms=round(elapsed_ms, 2),
                limitations=["Entity name must match an ingested function or class."],
            )

        target_row = target_res.result_set[0]
        target_id = target_row[0]
        target_type = target_row[1]
        target_file = target_row[3]

        # 2. Traverse Incoming CALLS (Upstream Callers)
        traverse_q = (
            f"MATCH path = (caller:Function)-[:CALLS*1..{max_depth}]->(target:Function {{name: $name}}) "
            "RETURN caller.id, caller.name, caller.file_path, caller.scope, length(path) AS depth, "
            "[n in nodes(path) | n.name] AS call_chain "
            "ORDER BY depth ASC"
        )
        cypher_queries.append(traverse_q)
        call_res = graph.query(traverse_q, {"name": target_name})

        # Also check top-level module callers (File -CALLS-> Function)
        mod_call_q = (
            "MATCH path = (caller:File)-[:CALLS]->(target:Function {name: $name}) "
            "RETURN caller.id, caller.name, caller.path, 'file', 1 AS depth, "
            "[caller.name, target.name] AS call_chain"
        )
        cypher_queries.append(mod_call_q)
        mod_call_res = graph.query(mod_call_q, {"name": target_name})

        # Also check File IMPORTS File dependencies
        import_q = (
            "MATCH (importer:File)-[r:IMPORTS]->(target_file:File {path: $target_file}) "
            "RETURN importer.name, importer.path, r.line_number"
        )
        cypher_queries.append(import_q)
        import_res = graph.query(import_q, {"target_file": target_file})

        # 3. Process & Categorize Affected Entities
        seen_caller_ids: Set[str] = set()
        direct_impacts: List[AffectedEntity] = []
        indirect_impacts: List[AffectedEntity] = []
        impacted_files: Set[str] = set()
        evidence_paths: List[Dict[str, Any]] = []

        # Process function callers
        combined_rows = (call_res.result_set or []) + (mod_call_res.result_set or [])
        step_num = 1

        for row in combined_rows:
            c_id = str(row[0])
            c_name = str(row[1])
            c_file = str(row[2])
            c_scope = str(row[3])
            depth = int(row[4])
            raw_chain = row[5]
            chain = [str(item) for item in raw_chain] if isinstance(raw_chain, list) else [c_name, target_name]

            if c_id not in seen_caller_ids:
                seen_caller_ids.add(c_id)
                impacted_files.add(c_file)

                is_direct = (depth == 1)
                entity = AffectedEntity(
                    id=c_id,
                    name=c_name,
                    file_path=c_file,
                    scope=c_scope,
                    depth=depth,
                    is_direct=is_direct,
                    call_chain=chain,
                )

                if is_direct:
                    direct_impacts.append(entity)
                else:
                    indirect_impacts.append(entity)

                evidence_paths.append({
                    "step": step_num,
                    "type": "CALLS_UPSTREAM",
                    "from_node": c_name,
                    "to_node": target_name,
                    "depth": depth,
                    "file": c_file,
                    "chain": " -> ".join(chain),
                    "impact": "Direct caller" if is_direct else f"Indirect caller ({depth} hops away)",
                })
                step_num += 1

        # Process importing files
        imported_by_files: List[str] = []
        if import_res.result_set:
            for i_row in import_res.result_set:
                imp_name = str(i_row[0])
                imp_path = str(i_row[1])
                line = int(i_row[2]) if i_row[2] is not None else 1
                imported_by_files.append(imp_path)
                evidence_paths.append({
                    "step": step_num,
                    "type": "IMPORTS_FILE",
                    "from_node": imp_name,
                    "to_node": target_file,
                    "file": imp_path,
                    "line": line,
                    "impact": "Source file import dependency",
                })
                step_num += 1

        # 4. Generate Human-Readable Summary
        total_affected_callers = len(direct_impacts) + len(indirect_impacts)
        impact_score = (len(direct_impacts) * 2) + len(indirect_impacts)

        if total_affected_callers == 0 and len(imported_by_files) == 0:
            severity = "ISOLATED"
            summary = (
                f"Modifying '{target_name}' in `{target_file}` has ZERO detected upstream callers. "
                f"It appears to be an isolated or standalone function."
            )
        else:
            severity = "HIGH" if impact_score >= 4 else "MODERATE" if impact_score >= 2 else "LOW"
            direct_names = ", ".join(f"`{d.name}`" for d in direct_impacts) if direct_impacts else "none"
            indirect_names = ", ".join(f"`{i.name}`" for i in indirect_impacts) if indirect_impacts else "none"

            summary = (
                f"**Impact Severity: {severity} (Score: {impact_score})**\n\n"
                f"Modifying `{target_name}` ({target_type} in `{target_file}`) directly affects "
                f"{len(direct_impacts)} caller(s): {direct_names}.\n"
                f"It indirectly affects {len(indirect_impacts)} transitive caller(s): {indirect_names}.\n"
                f"Total affected files: {len(impacted_files)} file(s)."
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        details = {
            "target_name": target_name,
            "target_type": target_type,
            "target_file": target_file,
            "impact_score": impact_score,
            "direct_impact_count": len(direct_impacts),
            "indirect_impact_count": len(indirect_impacts),
            "direct_impacts": [e.__dict__ for e in direct_impacts],
            "indirect_impacts": [e.__dict__ for e in indirect_impacts],
            "impacted_files": sorted(list(impacted_files)),
            "imported_by_files": imported_by_files,
        }

        return InvestigationResponse(
            investigation_type="impact_analysis",
            target=target_name,
            status="success",
            summary=summary,
            details=details,
            evidence_paths=evidence_paths,
            cypher_queries=cypher_queries,
            nodes_examined=total_affected_callers + 1,
            relationships_examined=len(evidence_paths),
            execution_time_ms=round(elapsed_ms, 2),
            limitations=[
                "Dynamic dispatches via getattr(), kwargs, or callbacks cannot be traced statically.",
                "External consumers importing this repository from outside are not tracked.",
            ],
        )

    def trace_call_path(self, source_name: str, destination_name: str) -> InvestigationResponse:
        """
        Find shortest execution/call path between two functions in the graph.
        Returns ordered nodes and relationships as proof.
        """
        start_time = time.perf_counter()
        graph = self._get_graph()
        cypher_queries: List[str] = []

        # 1. Verify existence of source and destination
        check_q = (
            "MATCH (fn) WHERE (fn:Function OR fn:File) AND fn.name = $name "
            "RETURN fn.id, labels(fn)[0] AS type, fn.name, coalesce(fn.file_path, fn.path, '') AS path"
        )
        cypher_queries.append(check_q)

        src_res = graph.query(check_q, {"name": source_name})
        dst_res = graph.query(check_q, {"name": destination_name})

        src_exists = src_res.result_set and len(src_res.result_set) > 0
        dst_exists = dst_res.result_set and len(dst_res.result_set) > 0

        if not src_exists or not dst_exists:
            missing = []
            if not src_exists:
                missing.append(f"Source '{source_name}'")
            if not dst_exists:
                missing.append(f"Destination '{destination_name}'")

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return InvestigationResponse(
                investigation_type="call_path_tracing",
                target=f"{source_name} -> {destination_name}",
                status="not_found",
                summary=f"Cannot trace call path: {', '.join(missing)} not found in codebase graph.",
                details={"source_found": src_exists, "destination_found": dst_exists},
                cypher_queries=cypher_queries,
                execution_time_ms=round(elapsed_ms, 2),
                limitations=["Both functions must be indexed in the codebase graph."],
            )

        # 2. Shortest Path Cypher Query
        path_q = (
            "MATCH path = (src)-[:CALLS*1..10]->(dst) "
            "WHERE (src:Function OR src:File) AND (dst:Function OR dst:File) "
            "AND src.name = $src AND dst.name = $dst "
            "RETURN [n in nodes(path) | {id: n.id, name: n.name, file: coalesce(n.file_path, n.path, '')}] AS path_nodes, "
            "length(path) AS hops "
            "ORDER BY hops ASC "
            "LIMIT 1"
        )
        cypher_queries.append(path_q)
        path_res = graph.query(path_q, {"src": source_name, "dst": destination_name})

        if not path_res.result_set or len(path_res.result_set) == 0:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return InvestigationResponse(
                investigation_type="call_path_tracing",
                target=f"{source_name} -> {destination_name}",
                status="no_path",
                summary=(
                    f"No call path exists between `{source_name}` and `{destination_name}`. "
                    f"Based on static analysis, `{source_name}` does not directly or transitively invoke `{destination_name}`."
                ),
                details={"hops": -1, "path_nodes": []},
                evidence_paths=[],
                cypher_queries=cypher_queries,
                execution_time_ms=round(elapsed_ms, 2),
                limitations=[
                    "Dynamic invocations or message queues connecting these functions cannot be verified statically."
                ],
            )

        row = path_res.result_set[0]
        raw_nodes = row[0]
        hops = int(row[1])

        # Parse node chain
        path_nodes: List[Dict[str, Any]] = []
        if isinstance(raw_nodes, list):
            for n in raw_nodes:
                if isinstance(n, dict):
                    path_nodes.append(n)
                else:
                    path_nodes.append({"name": str(n)})

        # Build evidence steps
        evidence_paths: List[Dict[str, Any]] = []
        for idx in range(len(path_nodes) - 1):
            curr = path_nodes[idx]
            nxt = path_nodes[idx + 1]
            evidence_paths.append({
                "step": idx + 1,
                "relationship": "CALLS",
                "from_node": curr.get("name", "unknown"),
                "from_file": curr.get("file", ""),
                "to_node": nxt.get("name", "unknown"),
                "to_file": nxt.get("file", ""),
            })

        chain_str = " ➔ ".join(n.get("name", "") for n in path_nodes)
        summary = (
            f"**Verified Execution Path Found ({hops} hops):**\n\n"
            f"`{chain_str}`\n\n"
            f"Function `{source_name}` invokes `{destination_name}` through {hops} verified static call step(s)."
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return InvestigationResponse(
            investigation_type="call_path_tracing",
            target=f"{source_name} -> {destination_name}",
            status="success",
            summary=summary,
            details={"hops": hops, "path_nodes": path_nodes},
            evidence_paths=evidence_paths,
            cypher_queries=cypher_queries,
            nodes_examined=len(path_nodes),
            relationships_examined=hops,
            execution_time_ms=round(elapsed_ms, 2),
            limitations=[
                "Path is based on statically verifiable direct and imported function calls.",
            ],
        )

    def investigate_dead_code(self) -> InvestigationResponse:
        """
        Identify candidate unreferenced functions with zero incoming CALLS edges.
        Provides confidence scoring and limitations (entry points, frameworks).
        """
        start_time = time.perf_counter()
        graph = self._get_graph()
        cypher_queries: List[str] = []

        dead_q = (
            "MATCH (fn:Function) "
            "WHERE NOT ()-[:CALLS]->(fn) "
            "RETURN fn.id, fn.name, fn.file_path, fn.scope, "
            "fn.start_line, fn.end_line, fn.is_method "
            "ORDER BY fn.file_path, fn.start_line"
        )
        cypher_queries.append(dead_q)
        res = graph.query(dead_q)

        candidates: List[CandidateDeadFunction] = []
        evidence_paths: List[Dict[str, Any]] = []

        entry_point_prefixes = ("test_", "post_", "get_", "put_", "delete_", "handle_", "run_", "cli_")

        for row in (res.result_set or []):
            f_id = str(row[0])
            f_name = str(row[1])
            f_file = str(row[2])
            f_scope = str(row[3])
            start_line = int(row[4])
            is_method = bool(row[6])

            # Filter dunders
            if f_name.startswith("__") and f_name.endswith("__"):
                continue

            # Evaluate confidence
            if f_name.startswith("test_"):
                continue
            elif f_name == "main" or f_name.startswith(entry_point_prefixes):
                confidence = "low"
                reason = "Zero internal callers, but matches standard entry point or API endpoint prefix."
                caveat = "Likely invoked externally by an HTTP client, framework router, or CLI script."
            elif "unused" in f_file or "legacy" in f_name or "deprecated" in f_name:
                confidence = "high"
                reason = "Explicitly unreferenced helper function with zero callers in the entire repository."
                caveat = "Strong candidate for removal if not part of a planned public interface."
            elif not is_method and ("utils" in f_file or "helpers" in f_file):
                confidence = "high"
                reason = "Internal utility function with zero incoming references across all files."
                caveat = "Verify it is not dynamically imported or used by external modules."
            else:
                confidence = "medium"
                reason = "No callers found in static call graph."
                caveat = "Could be part of a public class interface or invoked dynamically."

            candidate = CandidateDeadFunction(
                id=f_id,
                name=f_name,
                file_path=f_file,
                line_number=start_line,
                scope=f_scope,
                is_method=is_method,
                confidence=confidence,
                reason=reason,
                caveat=caveat,
            )
            candidates.append(candidate)

            evidence_paths.append({
                "function": f_name,
                "file": f_file,
                "line": start_line,
                "confidence": confidence,
                "incoming_calls": 0,
                "reason": reason,
            })

        high_conf = [c for c in candidates if c.confidence == "high"]
        med_conf = [c for c in candidates if c.confidence == "medium"]
        low_conf = [c for c in candidates if c.confidence == "low"]

        summary = (
            f"**Dead Code Investigation:** Found **{len(candidates)}** unreferenced function candidate(s).\n\n"
            f"* **High Confidence (Likely Dead):** {len(high_conf)} function(s)\n"
            f"* **Medium Confidence (Unreferenced Internally):** {len(med_conf)} function(s)\n"
            f"* **Low Confidence (Probable API/Entry Points):** {len(low_conf)} function(s)\n\n"
            "Every candidate has zero verified incoming static call edges in FalkorDB."
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        details = {
            "total_candidates": len(candidates),
            "high_confidence_count": len(high_conf),
            "medium_confidence_count": len(med_conf),
            "low_confidence_count": len(low_conf),
            "candidates": [c.__dict__ for c in candidates],
        }

        return InvestigationResponse(
            investigation_type="dead_code",
            target="codebase_orphans",
            status="success",
            summary=summary,
            details=details,
            evidence_paths=evidence_paths,
            cypher_queries=cypher_queries,
            nodes_examined=len(candidates),
            relationships_examined=0,
            execution_time_ms=round(elapsed_ms, 2),
            limitations=[
                "Functions called exclusively via runtime reflection, getattr(), or decorators may appear uncalled.",
                "API endpoint handlers called by external HTTP requests have 0 internal graph callers.",
            ],
        )

    def get_graph_snapshot(self, limit: int = 150) -> Dict[str, Any]:
        """
        Produce a bounded graph summary (nodes and links) suitable for 2D/3D force-directed
        visualization on the frontend.
        """
        graph = self._get_graph()
        safe_limit = min(max(10, limit), 300)

        nodes_q = (
            "MATCH (n) "
            "RETURN n.id AS id, labels(n)[0] AS type, n.name AS name, "
            "coalesce(n.file_path, n.path, '') AS file, coalesce(n.scope, '') AS scope "
            f"LIMIT {safe_limit}"
        )
        links_q = (
            "MATCH (s)-[r]->(t) "
            "RETURN s.id AS source, type(r) AS type, t.id AS target, "
            "coalesce(r.line_number, 0) AS line "
            f"LIMIT {safe_limit}"
        )

        node_res = graph.query(nodes_q)
        link_res = graph.query(links_q)

        nodes = []
        links = []
        node_ids: Set[str] = set()

        for row in (node_res.result_set or []):
            n_id = str(row[0])
            node_ids.add(n_id)
            nodes.append({
                "id": n_id,
                "type": str(row[1]),
                "name": str(row[2]),
                "file": str(row[3]),
                "scope": str(row[4]),
            })

        for row in (link_res.result_set or []):
            src = str(row[0])
            rel_type = str(row[1])
            dst = str(row[2])
            line = int(row[3]) if row[3] is not None else 0

            # Only include link if both nodes exist in the returned node list (or add stub)
            if src in node_ids and dst in node_ids:
                links.append({
                    "source": src,
                    "target": dst,
                    "type": rel_type,
                    "line": line,
                })

        # Total counts in FalkorDB
        total_nodes = 0
        total_edges = 0
        try:
            total_nodes = int(graph.query("MATCH (n) RETURN count(n)").result_set[0][0])
            total_edges = int(graph.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0])
        except Exception:
            pass

        return {
            "graph_name": self.graph_name,
            "total_nodes_in_db": total_nodes,
            "total_edges_in_db": total_edges,
            "returned_nodes": len(nodes),
            "returned_links": len(links),
            "nodes": nodes,
            "links": links,
        }
