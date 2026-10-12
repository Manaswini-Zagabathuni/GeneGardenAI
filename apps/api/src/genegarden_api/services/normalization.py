import re
from collections.abc import Iterable

from genegarden_api.models import BiologicalEntity, BiomedicalRelationship, EvidenceRecord

_ENSEMBL_GENE_PATTERN = re.compile(r"^ENSG\d{11}$")
_ONTOLOGY_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*_[A-Z0-9]+$")
_CANONICAL_GENE_PATTERN = re.compile(r"^ensembl:ENSG\d{11}$")
_CANONICAL_ONTOLOGY_PATTERN = re.compile(r"^[a-z][a-z0-9]*:[A-Z][A-Z0-9]*_[A-Z0-9]+$")


class IdentifierNormalizationError(ValueError):
    """Raised when a source identifier cannot be normalized safely."""


def validate_canonical_entity_id(value: str) -> str:
    normalized = value.strip()
    if not (
        _CANONICAL_GENE_PATTERN.fullmatch(normalized)
        or _CANONICAL_ONTOLOGY_PATTERN.fullmatch(normalized)
    ):
        raise IdentifierNormalizationError(
            "Expected a canonical identifier such as "
            "'ensembl:ENSG00000141510' or 'mondo:MONDO_0007254'."
        )
    return normalized


def normalize_ensembl_gene_id(value: str) -> str:
    normalized = value.strip().upper().split(".", maxsplit=1)[0]
    if not _ENSEMBL_GENE_PATTERN.fullmatch(normalized):
        raise IdentifierNormalizationError(f"Invalid Ensembl gene identifier: {value!r}")
    return f"ensembl:{normalized}"


def normalize_disease_id(value: str) -> str:
    normalized = value.strip().upper().replace(":", "_")
    if not _ONTOLOGY_PATTERN.fullmatch(normalized):
        raise IdentifierNormalizationError(f"Invalid disease or phenotype identifier: {value!r}")
    namespace = normalized.split("_", maxsplit=1)[0].lower()
    return f"{namespace}:{normalized}"


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized.removeprefix(prefix)
    return normalized or None


def relationship_key(
    source_name: str, relationship_type: str, source_entity_id: str, target_entity_id: str
) -> str:
    return "|".join(
        (
            source_name.strip().lower(),
            relationship_type.strip().lower(),
            source_entity_id,
            target_entity_id,
        )
    )


def deduplicate_entities(entities: Iterable[BiologicalEntity]) -> tuple[BiologicalEntity, ...]:
    unique: dict[str, BiologicalEntity] = {}
    for entity in entities:
        existing = unique.get(entity.canonical_id)
        if existing is None:
            unique[entity.canonical_id] = entity
            continue
        if existing.entity_type != entity.entity_type:
            raise IdentifierNormalizationError(
                f"Conflicting entity types for {entity.canonical_id!r}"
            )
        unique[entity.canonical_id] = existing.model_copy(
            update={
                "aliases": tuple(sorted(set(existing.aliases) | set(entity.aliases))),
                "attributes": {**existing.attributes, **entity.attributes},
                "retrieved_at": max(existing.retrieved_at, entity.retrieved_at),
            }
        )
    return tuple(unique.values())


def deduplicate_relationships(
    relationships: Iterable[BiomedicalRelationship],
) -> tuple[BiomedicalRelationship, ...]:
    unique: dict[str, BiomedicalRelationship] = {}
    for relationship in relationships:
        existing = unique.get(relationship.canonical_key)
        if existing is None:
            unique[relationship.canonical_key] = relationship
            continue
        evidence_by_key: dict[tuple[str, str], EvidenceRecord] = {
            (item.source, item.source_record_id): item for item in existing.evidence
        }
        evidence_by_key.update(
            {(item.source, item.source_record_id): item for item in relationship.evidence}
        )
        scores = [score for score in (existing.score, relationship.score) if score is not None]
        unique[relationship.canonical_key] = existing.model_copy(
            update={
                "score": max(scores) if scores else None,
                "evidence": tuple(evidence_by_key.values()),
                "attributes": {**existing.attributes, **relationship.attributes},
                "retrieved_at": max(existing.retrieved_at, relationship.retrieved_at),
            }
        )
    return tuple(unique.values())
