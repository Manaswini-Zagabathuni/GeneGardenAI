from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean

from pydantic import BaseModel, ConfigDict, Field

from genegarden_api.graph.discovery import BiomedicalDiscoveryEngine
from genegarden_api.models import (
    BiologicalEntity,
    BiomedicalRelationship,
    CandidatePath,
    DiscoveryOptions,
    EntityType,
    EvidenceRecord,
    EvidenceType,
    KnowledgeGraphSnapshot,
    RelationshipType,
    SourceName,
)
from genegarden_api.services.normalization import relationship_key


class BenchmarkModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BenchmarkSource(BenchmarkModel):
    name: str
    url: str
    data_release: str
    retrieved_at: str
    construction: str


class BenchmarkEntity(BenchmarkModel):
    canonical_id: str
    entity_type: EntityType
    label: str
    source_identifier: str


class BenchmarkRelationship(BenchmarkModel):
    source_entity_id: str
    target_entity_id: str
    score: float = Field(ge=0, le=1)
    datasource_ids: tuple[str, ...]


class BenchmarkCase(BenchmarkModel):
    case_id: str
    source_id: str
    expected_target_id: str
    max_path_length: int = Field(default=3, ge=2, le=4)


class DiscoveryBenchmark(BenchmarkModel):
    name: str
    version: str
    source: BenchmarkSource
    entities: tuple[BenchmarkEntity, ...]
    relationships: tuple[BenchmarkRelationship, ...]
    cases: tuple[BenchmarkCase, ...]
    limitations: tuple[str, ...]

    def snapshot(self) -> KnowledgeGraphSnapshot:
        retrieved_at = datetime.fromisoformat(self.source.retrieved_at).replace(tzinfo=UTC)
        entities = tuple(
            BiologicalEntity(
                canonical_id=item.canonical_id,
                entity_type=item.entity_type,
                label=item.label,
                source=SourceName.OPEN_TARGETS,
                source_identifier=item.source_identifier,
                retrieved_at=retrieved_at,
            )
            for item in self.entities
        )
        relationships = []
        for item in self.relationships:
            source_identifier = (
                f"{item.source_entity_id.split(':', 1)[1]}:{item.target_entity_id.split(':', 1)[1]}"
            )
            evidence = tuple(
                EvidenceRecord(
                    source=SourceName.OPEN_TARGETS,
                    source_record_id=f"{source_identifier}:datasource:{datasource_id}",
                    evidence_type=EvidenceType.ASSOCIATION_DATASOURCE_SCORE,
                    attributes={"datasource_id": datasource_id},
                    retrieved_at=retrieved_at,
                )
                for datasource_id in item.datasource_ids
            )
            relationships.append(
                BiomedicalRelationship(
                    canonical_key=relationship_key(
                        SourceName.OPEN_TARGETS,
                        RelationshipType.GENE_ASSOCIATED_WITH_DISEASE,
                        item.source_entity_id,
                        item.target_entity_id,
                    ),
                    source_entity_id=item.source_entity_id,
                    target_entity_id=item.target_entity_id,
                    relationship_type=RelationshipType.GENE_ASSOCIATED_WITH_DISEASE,
                    source=SourceName.OPEN_TARGETS,
                    source_identifier=source_identifier,
                    score=item.score,
                    score_interpretation=(
                        "Open Targets heuristic association ranking score; not confidence."
                    ),
                    evidence=evidence,
                    retrieved_at=retrieved_at,
                )
            )
        return KnowledgeGraphSnapshot(entities=entities, relationships=tuple(relationships))


class MethodMetrics(BenchmarkModel):
    method: str
    precision_at_k: float
    recall_at_k: float
    mean_reciprocal_rank: float


class BenchmarkReport(BenchmarkModel):
    benchmark_name: str
    benchmark_version: str
    case_count: int
    k: int
    methods: tuple[MethodMetrics, ...]
    limitations: tuple[str, ...]


def load_benchmark(path: Path) -> DiscoveryBenchmark:
    return DiscoveryBenchmark.model_validate_json(path.read_text(encoding="utf-8"))


def evaluate_benchmark(benchmark: DiscoveryBenchmark, *, k: int = 5) -> BenchmarkReport:
    if not 1 <= k <= 25:
        raise ValueError("k must be between 1 and 25")
    snapshot = benchmark.snapshot()
    method_ranks: dict[str, list[int | None]] = {
        "transparent_baseline_v1": [],
        "shortest_path": [],
        "unweighted_path_count": [],
    }
    engine = BiomedicalDiscoveryEngine()

    for case in benchmark.cases:
        masked = snapshot.model_copy(
            update={
                "relationships": tuple(
                    relationship
                    for relationship in snapshot.relationships
                    if {
                        relationship.source_entity_id,
                        relationship.target_entity_id,
                    }
                    != {case.source_id, case.expected_target_id}
                )
            }
        )
        result = engine.search(
            masked,
            DiscoveryOptions(
                source_id=case.source_id,
                target_entity_types=frozenset({EntityType.DISEASE}),
                max_path_length=case.max_path_length,
                result_count=5000,
            ),
        )
        ranked = {
            "transparent_baseline_v1": _best_endpoint_order(result.paths),
            "shortest_path": _shortest_path_order(result.paths),
            "unweighted_path_count": _path_count_order(result.paths),
        }
        for method, endpoints in ranked.items():
            try:
                rank: int | None = endpoints.index(case.expected_target_id) + 1
            except ValueError:
                rank = None
            method_ranks[method].append(rank)

    metrics = tuple(_metrics(method, ranks, k) for method, ranks in method_ranks.items())
    return BenchmarkReport(
        benchmark_name=benchmark.name,
        benchmark_version=benchmark.version,
        case_count=len(benchmark.cases),
        k=k,
        methods=metrics,
        limitations=benchmark.limitations,
    )


def _best_endpoint_order(paths: tuple[CandidatePath, ...]) -> list[str]:
    return list(dict.fromkeys(path.nodes[-1].canonical_id for path in paths))


def _shortest_path_order(paths: tuple[CandidatePath, ...]) -> list[str]:
    ordered = sorted(
        paths,
        key=lambda path: (
            len(path.edges),
            path.nodes[-1].canonical_id,
            tuple(node.canonical_id for node in path.nodes),
        ),
    )
    return _best_endpoint_order(tuple(ordered))


def _path_count_order(paths: tuple[CandidatePath, ...]) -> list[str]:
    counts = Counter(path.nodes[-1].canonical_id for path in paths)
    return [item for item, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _metrics(method: str, ranks: list[int | None], k: int) -> MethodMetrics:
    hits = [rank is not None and rank <= k for rank in ranks]
    return MethodMetrics(
        method=method,
        precision_at_k=round(fmean((1 / k) if hit else 0 for hit in hits), 6),
        recall_at_k=round(fmean(1.0 if hit else 0.0 for hit in hits), 6),
        mean_reciprocal_rank=round(
            fmean((1 / rank) if rank is not None else 0.0 for rank in ranks), 6
        ),
    )
