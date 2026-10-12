from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from genegarden_api.core.errors import ApplicationError
from genegarden_api.core.limits import KNOWLEDGE_MAX_NODES, KNOWLEDGE_MAX_RELATIONSHIPS
from genegarden_api.db.session import get_db_session
from genegarden_api.models import BiologicalEntity, KnowledgeGraphSnapshot
from genegarden_api.repositories import GraphSnapshotLimitError, KnowledgeRepository

router = APIRouter(prefix="/knowledge")
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
CanonicalEntityId = Annotated[
    str,
    Path(
        min_length=3,
        max_length=128,
        pattern=r"^(ensembl:ENSG\d{11}|[a-z][a-z0-9]*:[A-Z][A-Z0-9]*_[A-Z0-9]+)$",
    ),
]


def not_found(canonical_id: str) -> ApplicationError:
    return ApplicationError(
        code="entity_not_found",
        message=f"No ingested entity exists for canonical identifier {canonical_id!r}.",
        status_code=404,
    )


@router.get(
    "/entities/{canonical_id}",
    response_model=BiologicalEntity,
    summary="Get one normalized biological entity",
)
async def get_entity(canonical_id: CanonicalEntityId, session: DatabaseSession) -> BiologicalEntity:
    entity = await KnowledgeRepository(session).get_entity(canonical_id)
    if entity is None:
        raise not_found(canonical_id)
    return entity


@router.get(
    "/graph/{canonical_id}",
    response_model=KnowledgeGraphSnapshot,
    summary="Get the persisted one-hop neighborhood for an entity",
)
async def get_graph(
    canonical_id: CanonicalEntityId, session: DatabaseSession
) -> KnowledgeGraphSnapshot:
    try:
        snapshot = await KnowledgeRepository(session).get_bounded_subgraph(
            canonical_id,
            max_depth=1,
            max_nodes=KNOWLEDGE_MAX_NODES,
            max_relationships=KNOWLEDGE_MAX_RELATIONSHIPS,
        )
    except GraphSnapshotLimitError as exc:
        raise ApplicationError(
            code="knowledge_graph_limit",
            message=str(exc),
            status_code=422,
        ) from exc
    if snapshot is None:
        raise not_found(canonical_id)
    return snapshot
