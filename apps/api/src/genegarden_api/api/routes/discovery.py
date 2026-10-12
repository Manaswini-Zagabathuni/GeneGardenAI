from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from genegarden_api.core.errors import ApplicationError
from genegarden_api.core.limits import DISCOVERY_MAX_NODES, DISCOVERY_MAX_RELATIONSHIPS
from genegarden_api.db.session import get_db_session
from genegarden_api.graph.discovery import (
    BiomedicalDiscoveryEngine,
    DiscoveryLimitError,
    IncompatibleRelationshipError,
)
from genegarden_api.models import DiscoveryResult
from genegarden_api.repositories import GraphSnapshotLimitError, KnowledgeRepository
from genegarden_api.schemas.discovery import DiscoveryRequest

router = APIRouter(prefix="/discovery")
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "/paths",
    response_model=DiscoveryResult,
    summary="Find and transparently rank bounded biomedical paths",
)
async def discover_paths(request: DiscoveryRequest, session: DatabaseSession) -> DiscoveryResult:
    repository = KnowledgeRepository(session)
    options = request.to_options()
    if await repository.get_entity(options.source_id) is None:
        raise _not_found(options.source_id)
    if options.target_id and await repository.get_entity(options.target_id) is None:
        raise _not_found(options.target_id)
    try:
        snapshot = await repository.get_bounded_subgraph(
            options.source_id,
            max_depth=options.max_path_length,
            max_nodes=DISCOVERY_MAX_NODES,
            max_relationships=DISCOVERY_MAX_RELATIONSHIPS,
        )
        if snapshot is None:  # Defensive: source existence was checked above.
            raise _not_found(options.source_id)
        return BiomedicalDiscoveryEngine().search(snapshot, options)
    except (DiscoveryLimitError, GraphSnapshotLimitError) as exc:
        raise ApplicationError(
            code="discovery_query_limit",
            message=str(exc),
            status_code=422,
        ) from exc
    except IncompatibleRelationshipError as exc:
        raise ApplicationError(
            code="incompatible_relationship_types",
            message=str(exc),
            status_code=422,
        ) from exc


def _not_found(canonical_id: str) -> ApplicationError:
    return ApplicationError(
        code="entity_not_found",
        message=f"No ingested entity exists for canonical identifier {canonical_id!r}.",
        status_code=404,
    )
