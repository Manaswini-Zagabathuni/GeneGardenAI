from dataclasses import dataclass
from math import isfinite
from numbers import Real

import networkx as nx


@dataclass(frozen=True, slots=True)
class PathResult:
    node_ids: tuple[str, ...]
    total_cost: float


class GraphService:
    """Pure graph operations, independent of HTTP and persistence.

    Edge `cost` should be derived from a documented evidence-scoring policy before
    calling this service. Lower cost represents a stronger traversable connection.
    """

    def __init__(self, graph: nx.Graph) -> None:
        self._validate_edge_costs(graph)
        self._graph = graph.copy()

    @staticmethod
    def _validate_edge_costs(graph: nx.Graph) -> None:
        for source, target, attributes in graph.edges(data=True):
            cost = attributes.get("cost")
            if (
                isinstance(cost, bool)
                or not isinstance(cost, Real)
                or not isfinite(float(cost))
                or cost < 0
            ):
                raise ValueError(
                    f"Edge {source!r} -> {target!r} must have a finite, non-negative cost."
                )

    def shortest_evidence_path(self, source: str, target: str) -> PathResult | None:
        if source not in self._graph or target not in self._graph:
            return None

        try:
            nodes = nx.shortest_path(self._graph, source, target, weight="cost")
        except nx.NetworkXNoPath:
            return None

        cost = nx.path_weight(self._graph, nodes, weight="cost") if len(nodes) > 1 else 0.0
        return PathResult(node_ids=tuple(nodes), total_cost=float(cost))
