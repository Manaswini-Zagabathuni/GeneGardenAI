import networkx as nx
import pytest

from genegarden_api.graph import GraphService


def test_shortest_evidence_path_uses_edge_cost() -> None:
    graph = nx.Graph()
    graph.add_edge("source", "weak", cost=4.0)
    graph.add_edge("weak", "target", cost=4.0)
    graph.add_edge("source", "strong", cost=1.0)
    graph.add_edge("strong", "target", cost=1.0)

    result = GraphService(graph).shortest_evidence_path("source", "target")

    assert result is not None
    assert result.node_ids == ("source", "strong", "target")
    assert result.total_cost == 2.0


def test_shortest_evidence_path_returns_none_for_unknown_node() -> None:
    result = GraphService(nx.Graph()).shortest_evidence_path("missing", "also-missing")

    assert result is None


def test_graph_service_rejects_edge_without_explicit_cost() -> None:
    graph = nx.Graph()
    graph.add_edge("source", "target")

    with pytest.raises(ValueError, match="finite, non-negative cost"):
        GraphService(graph)
