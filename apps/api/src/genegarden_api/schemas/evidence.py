from pydantic import BaseModel, ConfigDict, Field, model_validator

from genegarden_api.schemas.discovery import DiscoveryRequest
from genegarden_api.services.normalization import validate_canonical_entity_id


class PathEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discovery: DiscoveryRequest
    path_id: str = Field(min_length=8, max_length=128)


class AssistantQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=1000)
    entity_id: str | None = None
    path: PathEvidenceRequest | None = None
    use_llm: bool = True

    @model_validator(mode="after")
    def require_exactly_one_scope(self) -> "AssistantQuestionRequest":
        if (self.entity_id is None) == (self.path is None):
            raise ValueError("Provide exactly one of entity_id or path")
        if self.entity_id is not None:
            self.entity_id = validate_canonical_entity_id(self.entity_id)
        return self
