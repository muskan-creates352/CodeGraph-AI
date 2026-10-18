"""
Data schemas and response models for CodeGraph AI Investigation Agent.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AffectedEntity:
    """Represents a function or file affected by a proposed code modification."""
    id: str
    name: str
    file_path: str
    scope: str
    depth: int
    is_direct: bool
    call_chain: List[str]


@dataclass
class ImpactAnalysisResult:
    """Details of blast-radius and upstream dependency analysis."""
    target_name: str
    target_type: str  # "Function" or "Class"
    target_file: Optional[str]
    direct_impacts: List[AffectedEntity] = field(default_factory=list)
    indirect_impacts: List[AffectedEntity] = field(default_factory=list)
    impacted_files: List[str] = field(default_factory=list)
    imported_by_files: List[str] = field(default_factory=list)
    impact_score: int = 0


@dataclass
class PathTraceResult:
    """Details of shortest execution/call path between two functions."""
    source_name: str
    destination_name: str
    path_found: bool
    hops: int = 0
    path_nodes: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""


@dataclass
class CandidateDeadFunction:
    """An orphan function with zero incoming CALLS edges."""
    id: str
    name: str
    file_path: str
    line_number: int
    scope: str
    is_method: bool
    confidence: str  # "high", "medium", "low"
    reason: str
    caveat: str


@dataclass
class DeadCodeResult:
    """Summary of orphan function detection."""
    candidates: List[CandidateDeadFunction] = field(default_factory=list)
    total_candidates: int = 0
    high_confidence_count: int = 0


@dataclass
class InvestigationResponse:
    """Universal evidence-backed response from the CodeGraph AI agent."""
    investigation_type: str  # "impact_analysis", "path_trace", "dead_code"
    target: str
    status: str  # "success", "not_found", "no_path", "error"
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    evidence_paths: List[Dict[str, Any]] = field(default_factory=list)
    cypher_queries: List[str] = field(default_factory=list)
    nodes_examined: int = 0
    relationships_examined: int = 0
    execution_time_ms: float = 0.0
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the response to a clean JSON-serializable dictionary."""
        return {
            "investigation_type": self.investigation_type,
            "target": self.target,
            "status": self.status,
            "summary": self.summary,
            "details": self.details,
            "evidence_paths": self.evidence_paths,
            "cypher_queries": self.cypher_queries,
            "telemetry": {
                "nodes_examined": self.nodes_examined,
                "relationships_examined": self.relationships_examined,
                "execution_time_ms": self.execution_time_ms,
            },
            "limitations": self.limitations,
        }
