from typing import Literal

from pydantic import Field

from genegarden_api.models.domain import (
    BiologicalEntity,
    BiomedicalRelationship,
    DomainModel,
    EntityType,
    RelationshipType,
)


class DiscoveryOptions(DomainModel):
    source_id: str
    target_id: str | None = None
    target_entity_types: frozenset[EntityType] = frozenset()
    intermediate_entity_types: frozenset[EntityType] = frozenset()
    relationship_types: frozenset[RelationshipType] = frozenset(
        {RelationshipType.GENE_ASSOCIATED_WITH_DISEASE}
    )
    max_path_length: int = Field(default=3, ge=1, le=4)
    # The HTTP schema imposes the public limit of 25. Evaluation may retain the full bounded set
    # so baseline methods are not compared only after another method has truncated candidates.
    result_count: int = Field(default=10, ge=1, le=5000)
    max_enumerated_paths: int = Field(default=5000, ge=1, le=5000)
    max_path_expansions: int = Field(default=20000, ge=1, le=20000)


class TraversedEdge(DomainModel):
    traversed_from: str
    traversed_to: str
    direction: Literal["forward", "reverse"]
    relationship_type: RelationshipType
    relationships: tuple[BiomedicalRelationship, ...]


class ScoreComponent(DomainModel):
    name: str
    raw_value: float | int | None
    normalized_value: float | None = Field(default=None, ge=0, le=1)
    weight: float = Field(ge=0, le=1)
    contribution: float = Field(ge=0, le=1)
    explanation: str


class PathScore(DomainModel):
    ranking_utility: float = Field(ge=0, le=1)
    method: str
    components: tuple[ScoreComponent, ...]
    interpretation: str


class CandidatePath(DomainModel):
    path_id: str
    nodes: tuple[BiologicalEntity, ...]
    edges: tuple[TraversedEdge, ...]
    score: PathScore
    limitations: tuple[str, ...]


class DiscoveryResult(DomainModel):
    query: DiscoveryOptions
    paths: tuple[CandidatePath, ...]
    graph_node_count: int
    graph_relationship_count: int
    enumerated_path_count: int
    path_expansion_count: int
    warnings: tuple[str, ...]
