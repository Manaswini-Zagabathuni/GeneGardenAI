# End-to-end testing

GeneGarden has two separate end-to-end procedures. The automated browser suite is deterministic and
uses route-level API fixtures. The live-data procedure uses PostgreSQL plus records retrieved by the
documented ingestion command. Passing the mocked suite is not evidence that live ingestion works.

## Deterministic browser suite

Requirements: Node.js 22.12+ and either Google Chrome or a Playwright-managed Chromium install.
The checked-in configuration uses the locally installed Google Chrome channel and does not download
a browser automatically.

```bash
npm ci
npm run test:e2e
```

The tests intercept only `/api/v1` requests. They cover successful discovery and Cytoscape event
handling, exact evidence identifiers and publication links, empty results, unsupported identifiers,
an API failure followed by retry, keyboard controls, and a 390 × 844 viewport. All response values
come from `apps/web/src/test/verifiedFixtures.ts` and are test-only records.

## Live PostgreSQL and external-source demonstration

For the verified Docker-free workflow, use Python 3.12+, Node.js 22.12+, a hosted PostgreSQL database
such as Neon, and outbound HTTPS access to the documented Open Targets and Europe PMC endpoints.
Follow `docs/local-development.md` to configure the private `.env` file, then run:

```bash
make local-migrate
make local-ingest-starter
# Terminal 1:
make dev-api-local
# Terminal 2:
make dev-web-local
curl --fail http://localhost:8000/api/v1/health
curl --fail http://localhost:8000/api/v1/ready
```

Run the ingestion command once for a new or intentionally refreshed database; do not repeat it as a
routine application-startup step. A Docker Compose alternative remains available:

```bash
cp .env.example .env
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose exec api alembic current
docker compose exec api python -m genegarden_api.cli.ingest \
  --manifest resources/starter_domain.json
curl --fail http://localhost:8000/api/v1/health
curl --fail http://localhost:8000/api/v1/ready
curl --fail http://localhost:5173/healthz
```

Open <http://localhost:5173>, enter one identifier from `resources/starter_domain.json` using the
frontend's namespaced form, and verify all of the following:

1. The home search sends a request and opens the discovery workspace.
2. At least one returned path is present; an empty result is valid and must not be replaced.
3. Cytoscape renders the returned nodes and directed edges.
4. Selecting the path loads claim-level evidence, source-record identifiers, and any verified
   publication metadata returned by the API.
5. Database inspection shows the same canonical entity IDs, relationship source identifiers,
   evidence source-record IDs, and retrieval timestamps.
6. No displayed relationship comes from `apps/web/src/data/demoDataset.ts` or
   `apps/web/src/test/verifiedFixtures.ts`.

Record the Open Targets and Europe PMC request date, API responses or ingestion-run identifier, image
digests, migration revision, and the exact Git commit. Do not report a successful live demonstration
when Docker, PostgreSQL, outbound APIs, or returned paths were not actually exercised.
