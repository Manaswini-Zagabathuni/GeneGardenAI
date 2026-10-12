from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_relationship

from genegarden_api.db.base import Base
from genegarden_api.models import EntityType, EvidenceType, RelationshipType, SourceName


def enum_column(enum_type: type[StrEnum]) -> Enum:
    return Enum(
        enum_type,
        values_callable=lambda values: [item.value for item in values],
        native_enum=False,
        validate_strings=True,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EntityRow(TimestampMixin, Base):
    __tablename__ = "entities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    canonical_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(enum_column(EntityType), nullable=False)
    label: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[SourceName] = mapped_column(enum_column(SourceName), nullable=False)
    source_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    attributes_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    outgoing_relationships: Mapped[list["RelationshipRow"]] = orm_relationship(
        back_populates="source_entity",
        foreign_keys="RelationshipRow.source_entity_id",
    )
    incoming_relationships: Mapped[list["RelationshipRow"]] = orm_relationship(
        back_populates="target_entity",
        foreign_keys="RelationshipRow.target_entity_id",
    )

    __table_args__ = (
        UniqueConstraint("source", "source_identifier", name="source_identifier"),
        Index("ix_entities_type_label", "entity_type", "label"),
    )


class RelationshipRow(TimestampMixin, Base):
    __tablename__ = "relationships"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    canonical_key: Mapped[str] = mapped_column(String(768), unique=True, nullable=False)
    source_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    target_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[RelationshipType] = mapped_column(
        enum_column(RelationshipType), nullable=False
    )
    source: Mapped[SourceName] = mapped_column(enum_column(SourceName), nullable=False)
    source_identifier: Mapped[str] = mapped_column(String(512), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    score_interpretation: Mapped[str | None] = mapped_column(Text)
    attributes_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source_entity: Mapped[EntityRow] = orm_relationship(
        back_populates="outgoing_relationships", foreign_keys=[source_entity_id]
    )
    target_entity: Mapped[EntityRow] = orm_relationship(
        back_populates="incoming_relationships", foreign_keys=[target_entity_id]
    )
    evidence_records: Mapped[list["EvidenceRow"]] = orm_relationship(
        back_populates="relationship", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "source", "source_identifier", "relationship_type", name="source_relationship"
        ),
        Index("ix_relationships_source_target", "source_entity_id", "target_entity_id"),
    )


class EvidenceRow(TimestampMixin, Base):
    __tablename__ = "evidence_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    relationship_id: Mapped[UUID] = mapped_column(
        ForeignKey("relationships.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[SourceName] = mapped_column(enum_column(SourceName), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(512), nullable=False)
    evidence_type: Mapped[EvidenceType] = mapped_column(enum_column(EvidenceType), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[str | None] = mapped_column(Text)
    attributes_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    relationship: Mapped[RelationshipRow] = orm_relationship(back_populates="evidence_records")
    publications: Mapped[list["PublicationRow"]] = orm_relationship(
        secondary="evidence_publications", back_populates="evidence_records"
    )

    __table_args__ = (
        UniqueConstraint(
            "relationship_id", "source", "source_record_id", name="relationship_source_record"
        ),
        Index("ix_evidence_relationship_type", "relationship_id", "evidence_type"),
    )


class PublicationRow(TimestampMixin, Base):
    __tablename__ = "publications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source: Mapped[SourceName] = mapped_column(enum_column(SourceName), nullable=False)
    source_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    author_string: Mapped[str | None] = mapped_column(Text)
    journal: Mapped[str | None] = mapped_column(String(512))
    publication_year: Mapped[int | None] = mapped_column(Integer)
    abstract: Mapped[str | None] = mapped_column(Text)
    doi: Mapped[str | None] = mapped_column(String(255))
    pmid: Mapped[str | None] = mapped_column(String(64))
    pmcid: Mapped[str | None] = mapped_column(String(64))
    is_open_access: Mapped[bool | None] = mapped_column(Boolean)
    attributes_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    evidence_records: Mapped[list[EvidenceRow]] = orm_relationship(
        secondary="evidence_publications", back_populates="publications"
    )

    __table_args__ = (
        UniqueConstraint("source", "source_identifier", name="source_publication"),
        Index("ix_publications_pmid", "pmid"),
        Index("ix_publications_doi", "doi"),
    )


class EvidencePublicationRow(Base):
    __tablename__ = "evidence_publications"

    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_records.id", ondelete="CASCADE"), primary_key=True
    )
    publication_id: Mapped[UUID] = mapped_column(
        ForeignKey("publications.id", ondelete="CASCADE"), primary_key=True
    )


class IngestionRunRow(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    statistics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
