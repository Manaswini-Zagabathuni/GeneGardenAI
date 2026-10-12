from fastapi import APIRouter

from genegarden_api.api.routes.discovery import router as discovery_router
from genegarden_api.api.routes.evidence import router as evidence_router
from genegarden_api.api.routes.health import router as health_router
from genegarden_api.api.routes.knowledge import router as knowledge_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(knowledge_router, tags=["knowledge graph"])
api_router.include_router(discovery_router, tags=["discovery"])
api_router.include_router(evidence_router, tags=["evidence and research assistant"])
