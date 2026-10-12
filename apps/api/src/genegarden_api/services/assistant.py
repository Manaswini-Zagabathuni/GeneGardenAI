from dataclasses import dataclass
from typing import Protocol

from genegarden_api.models import (
    AssistantAnswer,
    AssistantClaim,
    AssistantClaimCategory,
    AssistantEvidenceBundle,
)


@dataclass(frozen=True)
class GroundedGenerationRequest:
    question: str
    evidence: AssistantEvidenceBundle
    allowed_citation_ids: frozenset[str]
    instructions: str = (
        "Use only the supplied evidence. Every reported finding must cite one or more allowed "
        "citation IDs. Label hypotheses and model interpretations. Do not infer a new graph edge."
    )


@dataclass(frozen=True)
class GroundedGenerationResult:
    claims: tuple[AssistantClaim, ...]


class LlmProvider(Protocol):
    """Provider-neutral boundary; implementations return structured, cited claims only."""

    async def generate(self, request: GroundedGenerationRequest) -> GroundedGenerationResult: ...


class ResearchAssistantService:
    def __init__(self, provider: LlmProvider | None = None) -> None:
        self._provider = provider

    async def answer(
        self, *, question: str, evidence: AssistantEvidenceBundle, use_llm: bool
    ) -> AssistantAnswer:
        allowed_ids = {reference.citation_id for reference in evidence.publications}
        allowed_ids.update(
            item.evidence_id
            for relationship in evidence.relationships
            for item in relationship.evidence_items
        )
        claims = self._deterministic_claims(evidence)
        unsupported: list[str] = []
        mode = "evidence_summary"
        if use_llm and self._provider is not None:
            result = await self._provider.generate(
                GroundedGenerationRequest(
                    question=question,
                    evidence=evidence,
                    allowed_citation_ids=frozenset(allowed_ids),
                )
            )
            accepted: list[AssistantClaim] = []
            for claim in result.claims:
                if _claim_is_grounded(claim, allowed_ids):
                    accepted.append(claim)
                else:
                    unsupported.append(claim.text)
            if accepted:
                claims = tuple(accepted)
                mode = "llm_grounded"

        limitations = list(evidence.limitations)
        if use_llm and self._provider is None:
            limitations.append(
                "No LLM provider is configured; this response is a deterministic evidence summary."
            )
        if unsupported:
            limitations.append(
                "One or more model claims were withheld because their citations were missing or "
                "not present in the retrieved evidence bundle."
            )
        return AssistantAnswer(
            question=question,
            mode=mode,
            provider_available=self._provider is not None,
            claims=claims,
            references=evidence.publications,
            unsupported_claims=tuple(unsupported),
            limitations=tuple(dict.fromkeys(limitations)),
            evidence_bundle=evidence,
        )

    @staticmethod
    def _deterministic_claims(evidence: AssistantEvidenceBundle) -> tuple[AssistantClaim, ...]:
        if evidence.path is not None:
            path = evidence.path
            category = (
                AssistantClaimCategory.REPORTED_FINDING
                if path.claim_scope == "direct_relationship"
                else AssistantClaimCategory.HYPOTHESIS
            )
            route = " → ".join(f"{node.label} ({node.canonical_id})" for node in path.path.nodes)
            citation_ids = tuple(
                dict.fromkeys(
                    [reference.citation_id for reference in path.publications]
                    + [
                        item.evidence_id
                        for relationship in path.relationships
                        for item in relationship.evidence_items
                    ]
                )
            )
            wording = (
                "The stored graph directly contains the relationship"
                if category == AssistantClaimCategory.REPORTED_FINDING
                else "The discovery engine found an inferred multi-step path"
            )
            return (
                AssistantClaim(
                    text=f"{wording}: {route}.",
                    category=category,
                    citation_ids=citation_ids,
                ),
            )
        if evidence.scope_entity is not None and evidence.relationships:
            entity = evidence.scope_entity
            citation_ids = tuple(
                dict.fromkeys(
                    item.evidence_id
                    for relationship in evidence.relationships
                    for item in relationship.evidence_items
                )
            )
            return (
                AssistantClaim(
                    text=(
                        "The stored graph contains "
                        f"{len(evidence.relationships)} directly adjacent "
                        f"relationship record(s) for {entity.label} ({entity.canonical_id})."
                    ),
                    category=AssistantClaimCategory.REPORTED_FINDING,
                    citation_ids=citation_ids,
                ),
            )
        return (
            AssistantClaim(
                text="The retrieved records are insufficient to answer this question.",
                category=AssistantClaimCategory.INSUFFICIENT_EVIDENCE,
            ),
        )


def _claim_is_grounded(claim: AssistantClaim, allowed_ids: set[str]) -> bool:
    if claim.category == AssistantClaimCategory.REPORTED_FINDING:
        return bool(claim.citation_ids) and set(claim.citation_ids).issubset(allowed_ids)
    return set(claim.citation_ids).issubset(allowed_ids)


def get_research_assistant_service() -> ResearchAssistantService:
    """Default no-credential service; deployments may override this FastAPI dependency."""
    return ResearchAssistantService(provider=None)
