import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from genegarden_api.core.config import get_settings
from genegarden_api.db.session import close_database, get_db_session
from genegarden_api.repositories import KnowledgeRepository
from genegarden_api.services.cache import TTLMemoryCache
from genegarden_api.services.clients import EuropePmcClient, OpenTargetsClient
from genegarden_api.services.ingestion import BiomedicalIngestionService, IngestionManifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest a bounded biomedical research domain into GeneGarden AI."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def load_manifest(path: Path) -> IngestionManifest:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
        return IngestionManifest.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise SystemExit(f"Invalid ingestion manifest {path}: {exc}") from exc


async def run(manifest: IngestionManifest) -> None:
    settings = get_settings()
    cache: TTLMemoryCache[dict[str, Any]] = TTLMemoryCache(
        ttl_seconds=settings.external_cache_ttl_seconds
    )
    async with httpx.AsyncClient() as http_client:
        common = {
            "timeout_seconds": settings.external_request_timeout_seconds,
            "max_attempts": settings.external_request_max_attempts,
            "backoff_seconds": settings.external_request_backoff_seconds,
            "user_agent": settings.external_user_agent,
            "cache": cache,
            "client": http_client,
        }
        open_targets = OpenTargetsClient(base_url=str(settings.open_targets_graphql_url), **common)
        europe_pmc = EuropePmcClient(
            base_url=str(settings.europe_pmc_api_url),
            email=settings.europe_pmc_email,
            **common,
        )
        session_iterator = get_db_session()
        session = await anext(session_iterator)
        try:
            service = BiomedicalIngestionService(
                open_targets, europe_pmc, KnowledgeRepository(session)
            )
            statistics = await service.ingest(manifest)
            print(statistics.model_dump_json(indent=2))
        finally:
            await session_iterator.aclose()
    await close_database()


def main() -> None:
    asyncio.run(run(load_manifest(parse_args().manifest)))


if __name__ == "__main__":
    main()
