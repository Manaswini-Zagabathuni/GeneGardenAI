from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from genegarden_api.core.errors import ApplicationError
from genegarden_api.core.limits import (
    ASSISTANT_MAX_NODES,
    ASSISTANT_MAX_RELATIONSHIPS,
    DISCOVERY_MAX_NODES,
    DISCOVERY_MAX_RELATIONSHIPS,
)
from genegarden_api.db.session import get_db_session
from genegarden_api.graph.discovery import (
    BiomedicalDiscoveryEngine,
    DiscoveryLimitError,
    IncompatibleRelationshipError,
)
from genegarden_api.models import (
    AssistantAnswer,
    AssistantEvidenceBundle,
    CandidatePath,
    DiscoveryOptions,
    KnowledgeGraphSnapshot,
    PathEvidenceView,
)
from genegarden_api.repositories import GraphSnapshotLimitError, KnowledgeRepository
from genegarden_api.schemas.evidence import AssistantQuestionRequest, PathEvidenceRequest
from genegarden_api.services.assistant import (
    ResearchAssistantService,
    get_research_assistant_service,
)
from genegarden_api.services.evidence import EvidenceExplorerService

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
AssistantService = Annotated[ResearchAssistantService, Depends(get_research_assistant_service)]


@router.post(
    "/evidence/paths",
    response_model=PathEvidenceView,
    summary="Resolve claim-level evidence and publications for a discovered path",
)
async def explore_path_evidence(
    request: PathEvidenceRequest, session: DatabaseSession
) -> PathEvidenceView:
    path, snapshot = await _resolve_path(request, KnowledgeRepository(session))
    return await EvidenceExplorerService().explore_path(path, snapshot)


@router.post(
    "/assistant/answer",
    response_model=AssistantAnswer,
    summary="Answer from retrieved evidence, with optional provider-neutral LLM generation",
)
async def answer_research_question(
    request: AssistantQuestionRequest,
    session: DatabaseSession,
    assistant: AssistantService,
) -> AssistantAnswer:
    repository = KnowledgeRepository(session)
    explorer = EvidenceExplorerService()
    if request.path is not None:
        path, snapshot = await _resolve_path(request.path, repository)
        path_view = await explorer.explore_path(path, snapshot)
        bundle = AssistantEvidenceBundle(
            path=path_view,
            relationships=path_view.relationships,
            publications=path_view.publications,
            limitations=path_view.uncertainty,
        )
    else:
        assert request.entity_id is not None
        try:
            snapshot = await repository.get_bounded_subgraph(
                request.entity_id,
                max_depth=1,
                max_nodes=ASSISTANT_MAX_NODES,
                max_relationships=ASSISTANT_MAX_RELATIONSHIPS,
            )
        except GraphSnapshotLimitError as exc:
            raise ApplicationError(
                code="assistant_query_limit",
                message=str(exc),
                status_code=422,
            ) from exc
        if snapshot is None:
            raise _entity_not_found(request.entity_id)
        options = DiscoveryOptions(
            source_id=request.entity_id,
            max_path_length=1,
            result_count=25,
        )
        try:
            result = BiomedicalDiscoveryEngine().search(snapshot, options)
        except IncompatibleRelationshipError as exc:
            raise ApplicationError(
                code="incompatible_relationship_types",
                message=str(exc),
                status_code=422,
            ) from exc
        relationship_views = []
        publications = {}
        limitations = [*result.warnings]
        for candidate in result.paths:
            view = await explorer.explore_path(candidate, snapshot)
            relationship_views.extend(view.relationships)
            publications.update({item.citation_id: item for item in view.publications})
            limitations.extend(view.uncertainty)
        bundle = AssistantEvidenceBundle(
            scope_entity=next(
                entity for entity in snapshot.entities if entity.canonical_id == request.entity_id
            ),
            relationships=tuple(relationship_views),
            publications=tuple(publications.values()),
            limitations=tuple(dict.fromkeys(limitations)),
        )
    return await assistant.answer(
        question=request.question,
        evidence=bundle,
        use_llm=request.use_llm,
    )


async def _resolve_path(
    request: PathEvidenceRequest, repository: KnowledgeRepository
) -> tuple[CandidatePath, KnowledgeGraphSnapshot]:
    options = request.discovery.to_options()
    if await repository.get_entity(options.source_id) is None:
        raise _entity_not_found(options.source_id)
    try:
        snapshot = await repository.get_bounded_subgraph(
            options.source_id,
            max_depth=options.max_path_length,
            max_nodes=DISCOVERY_MAX_NODES,
            max_relationships=DISCOVERY_MAX_RELATIONSHIPS,
        )
        if snapshot is None:
            raise _entity_not_found(options.source_id)
        result = BiomedicalDiscoveryEngine().search(snapshot, options)
    except (DiscoveryLimitError, GraphSnapshotLimitError) as exc:
        raise ApplicationError(
            code="discovery_query_limit", message=str(exc), status_code=422
        ) from exc
    except IncompatibleRelationshipError as exc:
        raise ApplicationError(
            code="incompatible_relationship_types", message=str(exc), status_code=422
        ) from exc
    path = next(
        (candidate for candidate in result.paths if candidate.path_id == request.path_id), None
    )
    if path is None:
        raise ApplicationError(
            code="path_not_found",
            message=(
                "The path ID is not present in the reproducible discovery result. Re-run discovery "
                "with the same query and select a returned path."
            ),
            status_code=404,
        )
    return path, snapshot


def _entity_not_found(canonical_id: str) -> ApplicationError:
    return ApplicationError(
        code="entity_not_found",
        message=f"No ingested entity exists for canonical identifier {canonical_id!r}.",
        status_code=404,
    )
