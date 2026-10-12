from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from statistics import fmean

import networkx as nx

from genegarden_api.models import (
    BiologicalEntity,
    BiomedicalRelationship,
    CandidatePath,
    DiscoveryOptions,
    DiscoveryResult,
    EntityType,
    EvidenceRecord,
    PathScore,
    RelationshipType,
    ScoreComponent,
    SourceName,
    TraversedEdge,
)
from genegarden_api.models.domain import KnowledgeGraphSnapshot

CAUSALITY_WARNING = (
    "Graph paths are hypotheses for exploration. They do not establish causality, "
    "clinical validity, or diagnostic relevance."
)
SCORE_WARNING = (
    "ranking_utility is a transparent ordering score, not a probability or confidence value."
)
_DIVERSITY_CAP_PER_EDGE = 3
_SUPPORTED_COMBINATIONS = {
    frozenset({RelationshipType.GENE_ASSOCIATED_WITH_DISEASE}),
}


class DiscoveryLimitError(RuntimeError):
    """Raised when a bounded query exceeds its explicit work budget."""


class IncompatibleRelationshipError(ValueError):
    """Raised when no explicit semantic mapping permits mixing relationship types."""


@dataclass(frozen=True, slots=True)
class _LogicalEdge:
    node_a: str
    node_b: str
    relationship_type: RelationshipType
    relationships: tuple[BiomedicalRelationship, ...]

    def other(self, node_id: str) -> str:
        return self.node_b if node_id == self.node_a else self.node_a

    def traverse(self, from_id: str) -> TraversedEdge:
        to_id = self.other(from_id)
        first = self.relationships[0]
        direction = "forward" if first.source_entity_id == from_id else "reverse"
        return TraversedEdge(
            traversed_from=from_id,
            traversed_to=to_id,
            direction=direction,
            relationship_type=self.relationship_type,
            relationships=self.relationships,
        )


class BiomedicalDiscoveryEngine:
    """Enumerates bounded simple paths and ranks them with an auditable baseline."""

    def search(
        self, snapshot: KnowledgeGraphSnapshot, options: DiscoveryOptions
    ) -> DiscoveryResult:
        if options.relationship_types not in _SUPPORTED_COMBINATIONS:
            raise IncompatibleRelationshipError(
                "The requested relationship types do not have an explicit compatibility mapping."
            )

        entities = {entity.canonical_id: entity for entity in snapshot.entities}
        if options.source_id not in entities:
            return self._empty_result(snapshot, options)
        if options.target_id is not None and options.target_id not in entities:
            return self._empty_result(snapshot, options)

        graph = self._build_graph(snapshot, options.relationship_types)
        candidates: list[CandidatePath] = []
        seen_paths: set[tuple[tuple[str, ...], tuple[RelationshipType, ...]]] = set()
        enumerated_count = 0
        expansion_count = 0
        stack: list[tuple[str, tuple[str, ...], tuple[TraversedEdge, ...]]] = [
            (options.source_id, (options.source_id,), ())
        ]

        while stack:
            current, node_ids, edges = stack.pop()
            if edges and self._is_candidate(current, entities[current], options):
                signature = (node_ids, tuple(edge.relationship_type for edge in edges))
                if signature not in seen_paths:
                    seen_paths.add(signature)
                    enumerated_count += 1
                    if enumerated_count > options.max_enumerated_paths:
                        raise DiscoveryLimitError(
                            "Path enumeration exceeded the configured work budget."
                        )
                    candidates.append(
                        self._make_candidate(node_ids, edges, entities, options.max_path_length)
                    )
                if options.target_id is not None:
                    continue

            if len(edges) >= options.max_path_length:
                continue

            for logical_edge in reversed(self._incident_edges(graph, current)):
                next_id = logical_edge.other(current)
                if next_id in node_ids:
                    continue
                next_entity = entities[next_id]
                if not self._can_traverse_intermediate(next_id, next_entity, options):
                    continue
                expansion_count += 1
                if expansion_count > options.max_path_expansions:
                    raise DiscoveryLimitError("Path expansion exceeded the configured work budget.")
                stack.append(
                    (
                        next_id,
                        (*node_ids, next_id),
                        (*edges, logical_edge.traverse(current)),
                    )
                )

        candidates.sort(
            key=lambda path: (
                -path.score.ranking_utility,
                len(path.edges),
                tuple(node.canonical_id for node in path.nodes),
            )
        )
        return DiscoveryResult(
            query=options,
            paths=tuple(candidates[: options.result_count]),
            graph_node_count=len(snapshot.entities),
            graph_relationship_count=len(snapshot.relationships),
            enumerated_path_count=enumerated_count,
            path_expansion_count=expansion_count,
            warnings=(CAUSALITY_WARNING, SCORE_WARNING),
        )

    @staticmethod
    def _build_graph(
        snapshot: KnowledgeGraphSnapshot,
        allowed_types: frozenset[RelationshipType],
    ) -> nx.MultiGraph:
        groups: dict[tuple[str, str, RelationshipType], dict[str, BiomedicalRelationship]] = (
            defaultdict(dict)
        )
        entities = {entity.canonical_id: entity for entity in snapshot.entities}
        for relationship in snapshot.relationships:
            if relationship.relationship_type not in allowed_types:
                continue
            if (
                relationship.source_entity_id not in entities
                or relationship.target_entity_id not in entities
            ):
                continue
            if relationship.source_entity_id == relationship.target_entity_id:
                continue
            if relationship.relationship_type == RelationshipType.GENE_ASSOCIATED_WITH_DISEASE:
                source_type = entities[relationship.source_entity_id].entity_type
                target_type = entities[relationship.target_entity_id].entity_type
                if source_type != EntityType.GENE or target_type != EntityType.DISEASE:
                    raise IncompatibleRelationshipError(
                        "gene_associated_with_disease must be stored in gene-to-disease direction."
                    )
            node_a, node_b = sorted((relationship.source_entity_id, relationship.target_entity_id))
            cleaned = relationship.model_copy(
                update={"evidence": _deduplicate_evidence(relationship.evidence)}
            )
            groups[(node_a, node_b, relationship.relationship_type)][relationship.canonical_key] = (
                cleaned
            )

        graph = nx.MultiGraph()
        graph.add_nodes_from(entity.canonical_id for entity in snapshot.entities)
        for (node_a, node_b, relationship_type), relationship_map in groups.items():
            logical_edge = _LogicalEdge(
                node_a=node_a,
                node_b=node_b,
                relationship_type=relationship_type,
                relationships=tuple(relationship_map[key] for key in sorted(relationship_map)),
            )
            graph.add_edge(
                node_a,
                node_b,
                key=relationship_type.value,
                logical_edge=logical_edge,
            )
        return graph

    @staticmethod
    def _incident_edges(graph: nx.MultiGraph, node_id: str) -> tuple[_LogicalEdge, ...]:
        edges = (
            attributes["logical_edge"]
            for _, _, _, attributes in graph.edges(node_id, keys=True, data=True)
        )
        return tuple(
            sorted(
                edges,
                key=lambda edge: (edge.other(node_id), edge.relationship_type.value),
            )
        )

    @staticmethod
    def _is_candidate(node_id: str, entity: BiologicalEntity, options: DiscoveryOptions) -> bool:
        if options.target_id is not None and node_id != options.target_id:
            return False
        return not options.target_entity_types or entity.entity_type in options.target_entity_types

    @staticmethod
    def _can_traverse_intermediate(
        node_id: str, entity: BiologicalEntity, options: DiscoveryOptions
    ) -> bool:
        is_requested_target = options.target_id is not None and node_id == options.target_id
        is_target_type = (
            bool(options.target_entity_types) and entity.entity_type in options.target_entity_types
        )
        if is_requested_target or is_target_type:
            return True
        return (
            not options.intermediate_entity_types
            or entity.entity_type in options.intermediate_entity_types
        )

    def _make_candidate(
        self,
        node_ids: tuple[str, ...],
        edges: tuple[TraversedEdge, ...],
        entities: dict[str, BiologicalEntity],
        max_path_length: int,
    ) -> CandidatePath:
        score, limitations = self._score(edges, max_path_length)
        signature = (
            "|".join(node_ids) + "|" + "|".join(edge.relationship_type.value for edge in edges)
        )
        if any(edge.direction == "reverse" for edge in edges):
            limitations.append(
                "At least one directed relationship was traversed in reverse for discovery; "
                "the stored biological direction is preserved on the returned edge."
            )
        return CandidatePath(
            path_id=sha256(signature.encode()).hexdigest()[:16],
            nodes=tuple(entities[node_id] for node_id in node_ids),
            edges=edges,
            score=score,
            limitations=tuple(dict.fromkeys(limitations)),
        )

    @staticmethod
    def _score(
        edges: tuple[TraversedEdge, ...], max_path_length: int
    ) -> tuple[PathScore, list[str]]:
        path_length = len(edges)
        length_normalized = 1.0 - ((path_length - 1) / max_path_length)

        comparable_edge_scores: list[float] = []
        missing_score = False
        diversity_values: list[float] = []
        for edge in edges:
            scores = [
                relationship.score
                for relationship in edge.relationships
                if relationship.source == SourceName.OPEN_TARGETS
                and relationship.relationship_type == RelationshipType.GENE_ASSOCIATED_WITH_DISEASE
                and relationship.score is not None
            ]
            if scores:
                comparable_edge_scores.append(max(scores))
            else:
                missing_score = True
            datasource_ids = {
                str(evidence.attributes["datasource_id"])
                for relationship in edge.relationships
                for evidence in relationship.evidence
                if evidence.source == SourceName.OPEN_TARGETS
                and "datasource_id" in evidence.attributes
            }
            diversity_values.append(
                min(len(datasource_ids), _DIVERSITY_CAP_PER_EDGE) / _DIVERSITY_CAP_PER_EDGE
            )

        strength = (
            fmean(comparable_edge_scores) if len(comparable_edge_scores) == len(edges) else None
        )
        diversity = fmean(diversity_values) if diversity_values else 0.0
        strength_normalized = strength if strength is not None else 0.0
        length_contribution = 0.4 * length_normalized
        strength_contribution = 0.4 * strength_normalized
        diversity_contribution = 0.2 * diversity
        ranking_utility = length_contribution + strength_contribution + diversity_contribution

        limitations = [
            "Open Targets association scores are heuristic ranking values, not probabilities.",
            "Datasource breadth is capped and does not imply statistical independence; "
            "correlated evidence may remain.",
            "No independently calibrated relationship-reliability value is available, "
            "so reliability is reported but contributes zero weight.",
            "Europe PMC literature-context records are retained but are not scored as support.",
        ]
        if missing_score:
            limitations.append(
                "At least one edge lacked a comparable Open Targets association score; "
                "the evidence-strength component was set to zero."
            )

        components = (
            ScoreComponent(
                name="path_length",
                raw_value=path_length,
                normalized_value=round(length_normalized, 6),
                weight=0.4,
                contribution=round(length_contribution, 6),
                explanation=(
                    "Fewer edges rank higher: 1 - ((path_length - 1) / configured_max_length)."
                ),
            ),
            ScoreComponent(
                name="comparable_evidence_strength",
                raw_value=round(strength, 6) if strength is not None else None,
                normalized_value=round(strength_normalized, 6),
                weight=0.4,
                contribution=round(strength_contribution, 6),
                explanation=(
                    "Arithmetic mean of per-edge Open Targets overall association scores. "
                    "Parallel duplicate records contribute only their maximum score."
                ),
            ),
            ScoreComponent(
                name="evidence_datasource_breadth",
                raw_value=round(diversity, 6),
                normalized_value=round(diversity, 6),
                weight=0.2,
                contribution=round(diversity_contribution, 6),
                explanation=(
                    "Mean per-edge count of unique Open Targets datasource identifiers, "
                    f"capped at {_DIVERSITY_CAP_PER_EDGE} and divided by that cap."
                ),
            ),
            ScoreComponent(
                name="relationship_reliability",
                raw_value=None,
                normalized_value=None,
                weight=0.0,
                contribution=0.0,
                explanation=(
                    "Not included because this graph has no independently calibrated "
                    "relationship-reliability measure."
                ),
            ),
        )
        return (
            PathScore(
                ranking_utility=round(ranking_utility, 6),
                method="transparent_baseline_v1",
                components=components,
                interpretation=SCORE_WARNING,
            ),
            limitations,
        )

    @staticmethod
    def _empty_result(
        snapshot: KnowledgeGraphSnapshot, options: DiscoveryOptions
    ) -> DiscoveryResult:
        return DiscoveryResult(
            query=options,
            paths=(),
            graph_node_count=len(snapshot.entities),
            graph_relationship_count=len(snapshot.relationships),
            enumerated_path_count=0,
            path_expansion_count=0,
            warnings=(CAUSALITY_WARNING, SCORE_WARNING),
        )


def _deduplicate_evidence(evidence: tuple[EvidenceRecord, ...]) -> tuple[EvidenceRecord, ...]:
    unique: dict[tuple[SourceName, str], EvidenceRecord] = {}
    for record in evidence:
        unique[(record.source, record.source_record_id)] = record
    return tuple(unique[key] for key in sorted(unique, key=lambda item: (item[0].value, item[1])))
