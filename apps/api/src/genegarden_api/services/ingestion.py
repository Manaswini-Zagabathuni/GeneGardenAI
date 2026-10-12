from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from genegarden_api.models import (
    BiologicalEntity,
    BiomedicalRelationship,
    EntityType,
    EvidenceRecord,
    EvidenceType,
    KnowledgeGraphSnapshot,
    Publication,
    RelationshipType,
    SourceName,
)
from genegarden_api.services.clients.europe_pmc import EuropePmcClient
from genegarden_api.services.clients.open_targets import OpenTargetsAssociation, OpenTargetsClient
from genegarden_api.services.normalization import (
    deduplicate_entities,
    deduplicate_relationships,
    normalize_disease_id,
    normalize_ensembl_gene_id,
    relationship_key,
)

SCORE_INTERPRETATION = (
    "Open Targets association score (0-1) used for heuristic ranking; "
    "it is not a statistical confidence or probability."
)


class IngestionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    domain_name: str = Field(min_length=1, max_length=255)
    target_ids: tuple[str, ...] = Field(min_length=1, max_length=10)
    max_associations_per_target: int = Field(default=5, ge=1, le=25)
    publications_per_association: int = Field(default=3, ge=0, le=25)

    @field_validator("target_ids")
    @classmethod
    def validate_target_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(normalize_ensembl_gene_id(value).split(":", 1)[1] for value in values)
        if len(normalized) != len(set(normalized)):
            raise ValueError("target_ids must be unique")
        return normalized


class IngestionStatistics(BaseModel):
    model_config = ConfigDict(frozen=True)

    entities: int
    relationships: int
    evidence_records: int
    publications: int
    targets_requested: int


class KnowledgeWriter(Protocol):
    async def start_ingestion_run(
        self, domain_name: str, parameters: dict[str, object], started_at: datetime
    ) -> UUID: ...

    async def persist_snapshot(self, snapshot: KnowledgeGraphSnapshot) -> None: ...

    async def finish_ingestion_run(
        self,
        run_id: UUID,
        *,
        status: str,
        completed_at: datetime,
        statistics: dict[str, object] | None = None,
        error_message: str | None = None,
    ) -> None: ...


class BiomedicalIngestionService:
    def __init__(
        self,
        open_targets: OpenTargetsClient,
        europe_pmc: EuropePmcClient,
        repository: KnowledgeWriter,
    ) -> None:
        self._open_targets = open_targets
        self._europe_pmc = europe_pmc
        self._repository = repository

    async def ingest(self, manifest: IngestionManifest) -> IngestionStatistics:
        started_at = datetime.now(UTC)
        parameters = manifest.model_dump(mode="json")
        run_id = await self._repository.start_ingestion_run(
            manifest.domain_name, parameters, started_at
        )
        try:
            snapshot = await self._build_snapshot(manifest)
            await self._repository.persist_snapshot(snapshot)
            statistics = IngestionStatistics(
                entities=len(snapshot.entities),
                relationships=len(snapshot.relationships),
                evidence_records=sum(len(item.evidence) for item in snapshot.relationships),
                publications=len(snapshot.publications),
                targets_requested=len(manifest.target_ids),
            )
            await self._repository.finish_ingestion_run(
                run_id,
                status="succeeded",
                completed_at=datetime.now(UTC),
                statistics=statistics.model_dump(),
            )
            return statistics
        except Exception as exc:
            await self._repository.finish_ingestion_run(
                run_id,
                status="failed",
                completed_at=datetime.now(UTC),
                error_message=str(exc)[:2000],
            )
            raise

    async def _build_snapshot(self, manifest: IngestionManifest) -> KnowledgeGraphSnapshot:
        entities: list[BiologicalEntity] = []
        relationships: list[BiomedicalRelationship] = []
        publications: dict[str, Publication] = {}

        for target_id in manifest.target_ids:
            retrieved_at = datetime.now(UTC)
            target = await self._open_targets.fetch_target_associations(
                target_id, page_size=manifest.max_associations_per_target
            )
            gene_id = normalize_ensembl_gene_id(target.id)
            entities.append(
                BiologicalEntity(
                    canonical_id=gene_id,
                    entity_type=EntityType.GENE,
                    label=target.approved_symbol,
                    description=target.approved_name,
                    source=SourceName.OPEN_TARGETS,
                    source_identifier=target.id,
                    aliases=(target.approved_name,),
                    attributes={"biotype": target.biotype or "unknown"},
                    retrieved_at=retrieved_at,
                )
            )
            for association in target.associated_diseases.rows:
                disease_id = normalize_disease_id(association.disease.id)
                entities.append(
                    BiologicalEntity(
                        canonical_id=disease_id,
                        entity_type=EntityType.DISEASE,
                        label=association.disease.name,
                        description=association.disease.description,
                        source=SourceName.OPEN_TARGETS,
                        source_identifier=association.disease.id,
                        retrieved_at=retrieved_at,
                    )
                )
                relationship, found_publications = await self._map_association(
                    target_id=target.id,
                    target_label=target.approved_symbol,
                    disease_id=disease_id,
                    disease_label=association.disease.name,
                    association=association,
                    publication_limit=manifest.publications_per_association,
                    retrieved_at=retrieved_at,
                )
                relationships.append(relationship)
                publications.update({item.source_identifier: item for item in found_publications})

        return KnowledgeGraphSnapshot(
            entities=deduplicate_entities(entities),
            relationships=deduplicate_relationships(relationships),
            publications=tuple(publications.values()),
        )

    async def _map_association(
        self,
        *,
        target_id: str,
        target_label: str,
        disease_id: str,
        disease_label: str,
        association: OpenTargetsAssociation,
        publication_limit: int,
        retrieved_at: datetime,
    ) -> tuple[BiomedicalRelationship, tuple[Publication, ...]]:
        gene_id = normalize_ensembl_gene_id(target_id)
        source_identifier = f"{target_id}:{association.disease.id}"
        evidence = [
            EvidenceRecord(
                source=SourceName.OPEN_TARGETS,
                source_record_id=f"{source_identifier}:datasource:{item.id}",
                evidence_type=EvidenceType.ASSOCIATION_DATASOURCE_SCORE,
                score=item.score,
                summary=f"Open Targets datasource score for {item.id}.",
                attributes={"datasource_id": item.id},
                retrieved_at=retrieved_at,
            )
            for item in association.datasource_scores
        ]
        if not evidence:
            evidence.append(
                EvidenceRecord(
                    source=SourceName.OPEN_TARGETS,
                    source_record_id=f"{source_identifier}:overall",
                    evidence_type=EvidenceType.ASSOCIATION_OVERALL_SCORE,
                    score=association.score,
                    summary="Open Targets overall association score.",
                    retrieved_at=retrieved_at,
                )
            )

        found_publications: tuple[Publication, ...] = ()
        if publication_limit:
            search_results = await self._europe_pmc.search_publications(
                target_label, disease_label, page_size=publication_limit
            )
            found_publications = tuple(
                result.to_domain(retrieved_at=retrieved_at) for result in search_results
            )
            if found_publications:
                evidence.append(
                    EvidenceRecord(
                        source=SourceName.EUROPE_PMC,
                        source_record_id=f"literature-search:{source_identifier}",
                        evidence_type=EvidenceType.LITERATURE_CONTEXT,
                        summary=(
                            "Europe PMC title/abstract search results for literature context; "
                            "these records were not independently validated as supporting "
                            "the association."
                        ),
                        publication_ids=tuple(
                            item.source_identifier for item in found_publications
                        ),
                        attributes={
                            "query_terms": [target_label, disease_label],
                            "result_count": len(found_publications),
                        },
                        retrieved_at=retrieved_at,
                    )
                )

        return (
            BiomedicalRelationship(
                canonical_key=relationship_key(
                    SourceName.OPEN_TARGETS,
                    RelationshipType.GENE_ASSOCIATED_WITH_DISEASE,
                    gene_id,
                    disease_id,
                ),
                source_entity_id=gene_id,
                target_entity_id=disease_id,
                relationship_type=RelationshipType.GENE_ASSOCIATED_WITH_DISEASE,
                source=SourceName.OPEN_TARGETS,
                source_identifier=source_identifier,
                score=association.score,
                score_interpretation=SCORE_INTERPRETATION,
                evidence=tuple(evidence),
                attributes={
                    "datatype_scores": {item.id: item.score for item in association.datatype_scores}
                },
                retrieved_at=retrieved_at,
            ),
            found_publications,
        )
