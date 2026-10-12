"""Create biomedical knowledge graph schema."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261011_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def upgrade() -> None:
    source = sa.Enum("open_targets", "europe_pmc", name="sourcename", native_enum=False)
    entity_type = sa.Enum(
        "gene", "protein", "pathway", "disease", name="entitytype", native_enum=False
    )
    relationship_type = sa.Enum(
        "gene_associated_with_disease", name="relationshiptype", native_enum=False
    )
    evidence_type = sa.Enum(
        "association_datasource_score",
        "association_overall_score",
        "literature_context",
        name="evidencetype",
        native_enum=False,
    )
    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("canonical_id", sa.String(128), nullable=False),
        sa.Column("entity_type", entity_type, nullable=False),
        sa.Column("label", sa.String(512), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("source", source, nullable=False),
        sa.Column("source_identifier", sa.String(255), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        *timestamp_columns(),
        sa.UniqueConstraint("canonical_id", name="uq_entities_canonical_id"),
        sa.UniqueConstraint("source", "source_identifier", name="source_identifier"),
    )
    op.create_index("ix_entities_type_label", "entities", ["entity_type", "label"])

    op.create_table(
        "publications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source", source, nullable=False),
        sa.Column("source_identifier", sa.String(255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("author_string", sa.Text()),
        sa.Column("journal", sa.String(512)),
        sa.Column("publication_year", sa.Integer()),
        sa.Column("abstract", sa.Text()),
        sa.Column("doi", sa.String(255)),
        sa.Column("pmid", sa.String(64)),
        sa.Column("pmcid", sa.String(64)),
        sa.Column("is_open_access", sa.Boolean()),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        *timestamp_columns(),
        sa.UniqueConstraint("source", "source_identifier", name="source_publication"),
    )
    op.create_index("ix_publications_pmid", "publications", ["pmid"])
    op.create_index("ix_publications_doi", "publications", ["doi"])

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("domain_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("statistics", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "relationships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("canonical_key", sa.String(768), nullable=False),
        sa.Column(
            "source_entity_id",
            sa.Uuid(),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_entity_id",
            sa.Uuid(),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", relationship_type, nullable=False),
        sa.Column("source", source, nullable=False),
        sa.Column("source_identifier", sa.String(512), nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("score_interpretation", sa.Text()),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        *timestamp_columns(),
        sa.UniqueConstraint("canonical_key", name="uq_relationships_canonical_key"),
        sa.UniqueConstraint(
            "source", "source_identifier", "relationship_type", name="source_relationship"
        ),
    )
    op.create_index(
        "ix_relationships_source_target",
        "relationships",
        ["source_entity_id", "target_entity_id"],
    )

    op.create_table(
        "evidence_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "relationship_id",
            sa.Uuid(),
            sa.ForeignKey("relationships.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", source, nullable=False),
        sa.Column("source_record_id", sa.String(512), nullable=False),
        sa.Column("evidence_type", evidence_type, nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("summary", sa.Text()),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        *timestamp_columns(),
        sa.UniqueConstraint(
            "relationship_id", "source", "source_record_id", name="relationship_source_record"
        ),
    )
    op.create_index(
        "ix_evidence_relationship_type",
        "evidence_records",
        ["relationship_id", "evidence_type"],
    )

    op.create_table(
        "evidence_publications",
        sa.Column(
            "evidence_id",
            sa.Uuid(),
            sa.ForeignKey("evidence_records.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "publication_id",
            sa.Uuid(),
            sa.ForeignKey("publications.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("evidence_publications")
    op.drop_index("ix_evidence_relationship_type", table_name="evidence_records")
    op.drop_table("evidence_records")
    op.drop_index("ix_relationships_source_target", table_name="relationships")
    op.drop_table("relationships")
    op.drop_table("ingestion_runs")
    op.drop_index("ix_publications_doi", table_name="publications")
    op.drop_index("ix_publications_pmid", table_name="publications")
    op.drop_table("publications")
    op.drop_index("ix_entities_type_label", table_name="entities")
    op.drop_table("entities")
