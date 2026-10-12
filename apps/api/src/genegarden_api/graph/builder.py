import networkx as nx

from genegarden_api.models import KnowledgeGraphSnapshot


class KnowledgeGraphBuilder:
    """Converts persisted domain records into an algorithm-ready NetworkX graph."""

    def build(self, snapshot: KnowledgeGraphSnapshot) -> nx.MultiDiGraph:
        graph = nx.MultiDiGraph(generated_at=snapshot.generated_at.isoformat())
        for entity in snapshot.entities:
            node_attributes = {
                **entity.attributes,
                "entity_type": entity.entity_type.value,
                "label": entity.label,
                "description": entity.description,
                "source": entity.source.value,
                "source_identifier": entity.source_identifier,
                "retrieved_at": entity.retrieved_at.isoformat(),
            }
            graph.add_node(entity.canonical_id, **node_attributes)
        for relationship in snapshot.relationships:
            if relationship.source_entity_id not in graph:
                raise ValueError(
                    f"Relationship {relationship.canonical_key!r} has an unknown source entity"
                )
            if relationship.target_entity_id not in graph:
                raise ValueError(
                    f"Relationship {relationship.canonical_key!r} has an unknown target entity"
                )
            edge_attributes = {
                **relationship.attributes,
                "relationship_type": relationship.relationship_type.value,
                "source": relationship.source.value,
                "source_identifier": relationship.source_identifier,
                "score": relationship.score,
                "score_interpretation": relationship.score_interpretation,
                "evidence_count": len(relationship.evidence),
                "evidence_records": relationship.evidence,
                "weight": 1.0 - relationship.score if relationship.score is not None else 1.0,
                "retrieved_at": relationship.retrieved_at.isoformat(),
            }
            graph.add_edge(
                relationship.source_entity_id,
                relationship.target_entity_id,
                key=relationship.canonical_key,
                **edge_attributes,
            )
        return graph
