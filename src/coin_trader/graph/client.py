"""FalkorDB connection management."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog
from falkordb import FalkorDB, Graph

logger = structlog.get_logger()

GRAPH_NAME = "coin_trader"


class GraphClient:
    """FalkorDB client wrapper."""

    def __init__(self, host: str = "localhost", port: int = 6380) -> None:
        self.host = host
        self.port = port
        self._db: Optional[FalkorDB] = None
        self._graph: Optional[Graph] = None

    def connect(self) -> None:
        self._db = FalkorDB(host=self.host, port=self.port)
        self._graph = self._db.select_graph(GRAPH_NAME)
        logger.info("graph.connected", host=self.host, port=self.port)

    def close(self) -> None:
        # FalkorDB uses Redis connection underneath
        if self._db:
            logger.info("graph.closed")

    @property
    def graph(self) -> Graph:
        if self._graph is None:
            raise RuntimeError("Graph not connected")
        return self._graph

    def query(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a Cypher query."""
        if params:
            return self.graph.query(cypher, params)
        return self.graph.query(cypher)

    def query_result(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Execute query and return result rows."""
        result = self.query(cypher, params)
        return result.result_set if result.result_set else []
