import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings with safe local defaults."""
    falkordb_host: str = os.getenv("FALKORDB_HOST", "localhost")
    falkordb_port: int = int(os.getenv("FALKORDB_PORT", "6379"))
    falkordb_password: str | None = os.getenv("FALKORDB_PASSWORD", None)
    falkordb_graph_name: str = os.getenv("FALKORDB_GRAPH_NAME", "codegraph")
    api_title: str = "CodeGraph AI Backend"
    api_version: str = "0.1.0"


settings = Settings()
