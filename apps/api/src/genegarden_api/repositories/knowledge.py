from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from genegarden_api.db.models import (
    EntityRow,
    EvidenceRow,
    IngestionRunRow,
    PublicationRow,
    RelationshipRow,
)
from genegarden_api.models import (
    BiologicalEntity,
    BiomedicalRelationship,
    EvidenceRecord,
    KnowledgeGraphSnapshot,
    Publication,
)


class GraphSnapshotLimitError(RuntimeError):
    """The persisted neighborhood exceeded a safe in-memory graph boundary."""


class KnowledgeRepository:
    """Persists normalized domain records without exposing ORM rows to services."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist_snapshot(self, snapshot: KnowledgeGraphSnapshot) -> None:
        entity_rows: dict[str, EntityRow] = {}
        for entity in snapshot.entities:
            entity_rows[entity.canonical_id] = await self._upsert_entity(entity)

        publication_rows: dict[str, PublicationRow] = {}
        for publication in snapshot.publications:
            publication_rows[publication.source_identifier] = await self._upsert_publication(
                publication
            )

        await self._session.flush()
        for relationship in snapshot.relationships:
            source = entity_rows.get(relationship.source_entity_id)
            target = entity_rows.get(relationship.target_entity_id)
            if source is None or target is None:
                raise ValueError(
                    f"Relationship {relationship.canonical_key!r} references a missing entity"
                )
            row = await self._upsert_relationship(relationship, source.id, target.id)
            await self._session.flush()
            for evidence in relationship.evidence:
                await self._upsert_evidence(row.id, evidence, publication_rows)
        await self._session.commit()

    async def start_ingestion_run(
        self, domain_name: str, parameters: dict[str, object], started_at: datetime
    ) -> UUID:
        row = IngestionRunRow(
            domain_name=domain_name,
            status="running",
            parameters=parameters,
            statistics={},
            started_at=started_at,
        )
        self._session.add(row)
        await self._session.commit()
        return row.id

    async def finish_ingestion_run(
        self,
        run_id: UUID,
        *,
        status: str,
        completed_at: datetime,
        statistics: dict[str, object] | None = None,
        error_message: str | None = None,
    ) -> None:
        await self._session.rollback()
        row = await self._session.get(IngestionRunRow, run_id)
        if row is None:
            raise ValueError(f"Unknown ingestion run {run_id}")
        row.status = status
        row.completed_at = completed_at
        row.statistics = statistics or {}
        row.error_message = error_message
        await self._session.commit()

    async def get_entity(self, canonical_id: str) -> BiologicalEntity | None:
        row = await self._session.scalar(
            select(EntityRow).where(EntityRow.canonical_id == canonical_id)
        )
        return self._entity_to_domain(row) if row else None

    async def get_neighborhood(self, canonical_id: str) -> KnowledgeGraphSnapshot | None:
        center = await self._session.scalar(
            select(EntityRow).where(EntityRow.canonical_id == canonical_id)
        )
        if center is None:
            return None

        query: Select[tuple[RelationshipRow]] = (
            select(RelationshipRow)
            .where(
                or_(
                    RelationshipRow.source_entity_id == center.id,
                    RelationshipRow.target_entity_id == center.id,
                )
            )
            .options(
                selectinload(RelationshipRow.source_entity),
                selectinload(RelationshipRow.target_entity),
                selectinload(RelationshipRow.evidence_records).selectinload(
                    EvidenceRow.publications
                ),
            )
        )
        rows = tuple((await self._session.scalars(query)).unique().all())
        entity_rows = {center.canonical_id: center}
        publication_rows: dict[str, PublicationRow] = {}
        for relationship in rows:
            entity_rows[relationship.source_entity.canonical_id] = relationship.source_entity
            entity_rows[relationship.target_entity.canonical_id] = relationship.target_entity
            for evidence in relationship.evidence_records:
                for publication in evidence.publications:
                    publication_rows[publication.source_identifier] = publication

        return KnowledgeGraphSnapshot(
            entities=tuple(self._entity_to_domain(row) for row in entity_rows.values()),
            relationships=tuple(self._relationship_to_domain(row) for row in rows),
            publications=tuple(
                self._publication_to_domain(row) for row in publication_rows.values()
            ),
        )

    async def get_bounded_subgraph(
        self,
        canonical_id: str,
        *,
        max_depth: int,
        max_nodes: int = 500,
        max_relationships: int = 2000,
    ) -> KnowledgeGraphSnapshot | None:
        """Load an undirected traversal neighborhood with hard SQL/result limits."""
        if not 1 <= max_depth <= 4:
            raise ValueError("max_depth must be between 1 and 4")
        center = await self._session.scalar(
            select(EntityRow).where(EntityRow.canonical_id == canonical_id)
        )
        if center is None:
            return None

        entity_rows: dict[UUID, EntityRow] = {center.id: center}
        relationship_rows: dict[UUID, RelationshipRow] = {}
        publication_rows: dict[str, PublicationRow] = {}
        visited_entities = {center.id}
        frontier = {center.id}

        for _ in range(max_depth):
            if not frontier:
                break
            remaining = max_relationships - len(relationship_rows)
            if remaining <= 0:
                raise GraphSnapshotLimitError(
                    f"The graph exceeded the {max_relationships}-relationship limit."
                )
            query = (
                select(RelationshipRow)
                .where(
                    or_(
                        RelationshipRow.source_entity_id.in_(frontier),
                        RelationshipRow.target_entity_id.in_(frontier),
                    )
                )
                .options(
                    selectinload(RelationshipRow.source_entity),
                    selectinload(RelationshipRow.target_entity),
                    selectinload(RelationshipRow.evidence_records).selectinload(
                        EvidenceRow.publications
                    ),
                )
                .order_by(RelationshipRow.canonical_key)
                .limit(remaining + 1)
            )
            if relationship_rows:
                query = query.where(RelationshipRow.id.not_in(relationship_rows))
            rows = tuple((await self._session.scalars(query)).unique().all())
            if len(rows) > remaining:
                raise GraphSnapshotLimitError(
                    f"The graph exceeded the {max_relationships}-relationship limit."
                )

            next_frontier: set[UUID] = set()
            for relationship in rows:
                relationship_rows[relationship.id] = relationship
                for entity in (relationship.source_entity, relationship.target_entity):
                    entity_rows[entity.id] = entity
                    if entity.id not in visited_entities:
                        next_frontier.add(entity.id)
                for evidence in relationship.evidence_records:
                    for publication in evidence.publications:
                        publication_rows[publication.source_identifier] = publication

            if len(entity_rows) > max_nodes:
                raise GraphSnapshotLimitError(f"The graph exceeded the {max_nodes}-entity limit.")
            visited_entities.update(next_frontier)
            frontier = next_frontier

        return KnowledgeGraphSnapshot(
            entities=tuple(self._entity_to_domain(row) for row in entity_rows.values()),
            relationships=tuple(
                self._relationship_to_domain(row) for row in relationship_rows.values()
            ),
            publications=tuple(
                self._publication_to_domain(row) for row in publication_rows.values()
            ),
        )

    async def _upsert_entity(self, entity: BiologicalEntity) -> EntityRow:
        row = await self._session.scalar(
            select(EntityRow).where(EntityRow.canonical_id == entity.canonical_id)
        )
        values = {
            "entity_type": entity.entity_type,
            "label": entity.label,
            "description": entity.description,
            "source": entity.source,
            "source_identifier": entity.source_identifier,
            "aliases": list(entity.aliases),
            "attributes_json": entity.attributes,
            "retrieved_at": entity.retrieved_at,
        }
        if row is None:
            row = EntityRow(canonical_id=entity.canonical_id, **values)
            self._session.add(row)
        else:
            for name, value in values.items():
                setattr(row, name, value)
        return row

    async def _upsert_publication(self, publication: Publication) -> PublicationRow:
        row = await self._session.scalar(
            select(PublicationRow).where(
                PublicationRow.source == publication.source,
                PublicationRow.source_identifier == publication.source_identifier,
            )
        )
        values = {
            "title": publication.title,
            "author_string": publication.author_string,
            "journal": publication.journal,
            "publication_year": publication.publication_year,
            "abstract": publication.abstract,
            "doi": publication.doi,
            "pmid": publication.pmid,
            "pmcid": publication.pmcid,
            "is_open_access": publication.is_open_access,
            "attributes_json": publication.attributes,
            "retrieved_at": publication.retrieved_at,
        }
        if row is None:
            row = PublicationRow(
                source=publication.source,
                source_identifier=publication.source_identifier,
                **values,
            )
            self._session.add(row)
        else:
            for name, value in values.items():
                setattr(row, name, value)
        return row

    async def _upsert_relationship(
        self, relationship: BiomedicalRelationship, source_id: UUID, target_id: UUID
    ) -> RelationshipRow:
        row = await self._session.scalar(
            select(RelationshipRow).where(
                RelationshipRow.canonical_key == relationship.canonical_key
            )
        )
        values = {
            "source_entity_id": source_id,
            "target_entity_id": target_id,
            "relationship_type": relationship.relationship_type,
            "source": relationship.source,
            "source_identifier": relationship.source_identifier,
            "score": relationship.score,
            "score_interpretation": relationship.score_interpretation,
            "attributes_json": relationship.attributes,
            "retrieved_at": relationship.retrieved_at,
        }
        if row is None:
            row = RelationshipRow(canonical_key=relationship.canonical_key, **values)
            self._session.add(row)
        else:
            for name, value in values.items():
                setattr(row, name, value)
        return row

    async def _upsert_evidence(
        self,
        relationship_id: UUID,
        evidence: EvidenceRecord,
        publications: dict[str, PublicationRow],
    ) -> EvidenceRow:
        row = await self._session.scalar(
            select(EvidenceRow)
            .where(
                EvidenceRow.relationship_id == relationship_id,
                EvidenceRow.source == evidence.source,
                EvidenceRow.source_record_id == evidence.source_record_id,
            )
            .options(selectinload(EvidenceRow.publications))
        )
        values = {
            "evidence_type": evidence.evidence_type,
            "score": evidence.score,
            "summary": evidence.summary,
            "attributes_json": evidence.attributes,
            "retrieved_at": evidence.retrieved_at,
        }
        if row is None:
            row = EvidenceRow(
                relationship_id=relationship_id,
                source=evidence.source,
                source_record_id=evidence.source_record_id,
                **values,
            )
            self._session.add(row)
        else:
            for name, value in values.items():
                setattr(row, name, value)
        linked = [publications[item] for item in evidence.publication_ids if item in publications]
        row.publications = linked
        return row

    @staticmethod
    def _entity_to_domain(row: EntityRow) -> BiologicalEntity:
        return BiologicalEntity(
            canonical_id=row.canonical_id,
            entity_type=row.entity_type,
            label=row.label,
            description=row.description,
            source=row.source,
            source_identifier=row.source_identifier,
            aliases=tuple(row.aliases),
            attributes=row.attributes_json,
            retrieved_at=_as_utc(row.retrieved_at),
        )

    @staticmethod
    def _publication_to_domain(row: PublicationRow) -> Publication:
        return Publication(
            source=row.source,
            source_identifier=row.source_identifier,
            title=row.title,
            author_string=row.author_string,
            journal=row.journal,
            publication_year=row.publication_year,
            abstract=row.abstract,
            doi=row.doi,
            pmid=row.pmid,
            pmcid=row.pmcid,
            is_open_access=row.is_open_access,
            attributes=row.attributes_json,
            retrieved_at=_as_utc(row.retrieved_at),
        )

    @classmethod
    def _relationship_to_domain(cls, row: RelationshipRow) -> BiomedicalRelationship:
        return BiomedicalRelationship(
            canonical_key=row.canonical_key,
            source_entity_id=row.source_entity.canonical_id,
            target_entity_id=row.target_entity.canonical_id,
            relationship_type=row.relationship_type,
            source=row.source,
            source_identifier=row.source_identifier,
            score=row.score,
            score_interpretation=row.score_interpretation,
            attributes=row.attributes_json,
            retrieved_at=_as_utc(row.retrieved_at),
            evidence=tuple(
                EvidenceRecord(
                    source=evidence.source,
                    source_record_id=evidence.source_record_id,
                    evidence_type=evidence.evidence_type,
                    score=evidence.score,
                    summary=evidence.summary,
                    publication_ids=tuple(
                        publication.source_identifier for publication in evidence.publications
                    ),
                    attributes=evidence.attributes_json,
                    retrieved_at=_as_utc(evidence.retrieved_at),
                )
                for evidence in row.evidence_records
            ),
        )


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
