# Deployment guide

This guide describes a deployment design; it is not a claim that the repository has been deployed
to a public environment. The only deployment artifact verified in the local review was the frontend
production build. Docker image construction could not be executed because Docker was unavailable in
the review environment; CI is configured to validate and build both images.

## Local Compose deployment

Requirements: Docker Engine with Compose v2.

```bash
cp .env.example .env
docker compose config --quiet
docker compose up --build
```

The database health check gates the API. The API then runs `alembic upgrade head`, starts Uvicorn,
and gates the Nginx frontend through `/api/v1/health`. Container CPU and memory caps have conservative
development defaults and can be overridden with environment variables.

Initialize the bounded starter dataset only after the API is healthy:

```bash
docker compose exec api python -m genegarden_api.cli.ingest \
  --manifest resources/starter_domain.json
```

The ingestion command calls public external APIs. Core browsing of an already-ingested graph and
the deterministic research assistant do not require a paid service.

## Environment variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | API | SQLAlchemy async PostgreSQL URL. Treat as a secret outside local development. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Compose database | Local database initialization. Replace the example password in shared environments. |
| `API_CORS_ORIGINS` | API | JSON array of allowed frontend origins; use the exact HTTPS production origin. |
| `OPEN_TARGETS_GRAPHQL_URL` | API | Open Targets public GraphQL endpoint. |
| `EUROPE_PMC_API_URL` | API | Europe PMC public REST base URL. |
| `EUROPE_PMC_EMAIL` | Optional | Contact metadata for upstream requests; not a credential. |
| `EXTERNAL_REQUEST_TIMEOUT_SECONDS` | Optional | Per-request timeout, constrained to 60 seconds or less. |
| `EXTERNAL_REQUEST_MAX_ATTEMPTS` | Optional | Bounded retry count, constrained to 1–5. |
| `EXTERNAL_REQUEST_BACKOFF_SECONDS` | Optional | Initial bounded exponential backoff. |
| `EXTERNAL_CACHE_TTL_SECONDS` | Optional | In-process metadata cache TTL. |
| `ASSISTANT_LLM_PROVIDER` | Optional | Currently only `none`; deterministic summaries require no key. |
| `VITE_API_BASE_URL` | Frontend build | Public API URL embedded into browser assets; never put a secret here. |
| `API_HOST_PORT`, `WEB_HOST_PORT`, `POSTGRES_HOST_PORT` | Compose | Host port mappings. |
| `*_MEMORY_LIMIT`, `*_CPU_LIMIT` | Compose | Local container resource ceilings. |

`.env` is ignored by Git. Production credentials should come from the target platform's encrypted
secret store, not a committed environment file, Docker build argument, frontend variable, or image
layer.

## Production topology

Use three independently managed components:

```text
Browser ──HTTPS──> static frontend / CDN
                      │
                      └──HTTPS──> FastAPI container ──TLS──> managed PostgreSQL
                                      │
                                      ├──HTTPS──> Open Targets
                                      └──HTTPS──> Europe PMC
```

Recommended production changes:

1. Push the API and web images to a private or trusted registry using immutable tags.
2. Use managed PostgreSQL with encryption, automated backups, point-in-time recovery, and restricted
   network access. Run Alembic as a one-off release task before shifting traffic.
3. Terminate TLS at the platform load balancer and set one exact HTTPS `API_CORS_ORIGINS` value.
4. Give the API its own least-privilege database user. Do not expose PostgreSQL publicly.
5. Retain the existing non-root API runtime user and `no-new-privileges` setting. Add a read-only
   filesystem only after verifying runtime temporary-directory requirements on the target platform.
6. Send application logs to centralized storage. Request logging includes method, path, status, and
   duration but intentionally excludes request bodies and credentials.
7. Alert separately on process health, database reachability, upstream failures, and ingestion-run
   failures. `/health` currently confirms process availability only.
8. Schedule ingestion deliberately instead of on application startup. Review upstream attribution,
   licensing, rate limits, and source-specific redistribution constraints before increasing scope.

## Database initialization and recovery

The first migration creates entities, relationships, evidence records, publications, join records,
and ingestion-run audit records:

```bash
cd apps/api
alembic upgrade head
alembic current
```

Back up PostgreSQL before migrations or large ingestion runs. In local Compose, the named
`postgres_data` volume survives `docker compose down`; `docker compose down -v` intentionally deletes
it. The repository does not currently provide automated restore scripts, so production recovery must
be tested using the chosen database provider.

## Release verification

```bash
make check
cp .env.example .env
docker compose config --quiet
docker compose build api web
docker compose up -d
curl --fail http://localhost:8000/api/v1/health
curl --fail http://localhost:5173/healthz
```

Do not label a release successful until migrations, both health checks, a bounded discovery request,
and an evidence request have been exercised against the intended environment. The GitHub Actions
workflow runs source checks, PostgreSQL migrations, unit/integration tests, the frozen benchmark,
frontend build, Compose validation, and container builds without external biomedical API calls.
