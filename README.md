# GeneGarden AI

GeneGarden AI is an evidence-grounded biomedical discovery platform for exploring possible relationships among genes, proteins, pathways, and diseases. It is a research and educational tool—not a diagnostic or clinical decision-making system.

This repository contains a botanical research dashboard, a typed FastAPI service, a provenance-aware PostgreSQL knowledge graph, bounded clients for Open Targets and Europe PMC, NetworkX graph construction, Docker development infrastructure, and deterministic tests. It deliberately contains no fabricated biomedical citations or evaluation claims.

## Motivation

Biomedical discovery tools often make an indirect connection look more certain than its sources
justify. GeneGarden focuses on the engineering boundary between exploration and evidence: every graph
edge keeps its provenance, inferred paths are labeled as hypotheses, missing or unassessed evidence
stays visible, and ranking inputs are inspectable. The project demonstrates full-stack product work,
defensive external-API integration, graph algorithms, reproducible evaluation, and a constrained
retrieval-grounded assistant.

## Technology stack

| Layer        | Technology                                                                             |
| ------------ | -------------------------------------------------------------------------------------- |
| Web          | React 19, TypeScript, Vite, Tailwind CSS, Cytoscape.js                                 |
| API          | Python 3.12, FastAPI, Pydantic, HTTPX                                                  |
| Graph        | NetworkX bounded multigraph traversal and transparent ranking                          |
| Persistence  | PostgreSQL 17, SQLAlchemy asyncio, Alembic                                             |
| Data sources | Open Targets Platform GraphQL and Europe PMC REST                                      |
| Quality      | Pytest, Vitest, Testing Library, Playwright, Ruff, ESLint, Prettier, strict TypeScript |
| Delivery     | Multi-stage Dockerfiles, Docker Compose, Nginx, GitHub Actions                         |

## Architecture

```text
apps/
├── api/                         FastAPI service
│   ├── src/genegarden_api/
│   │   ├── api/                 HTTP routing only
│   │   ├── core/                configuration and cross-cutting errors
│   │   ├── db/                  SQLAlchemy schema and database sessions
│   │   ├── graph/               NetworkX construction and algorithms
│   │   ├── models/              source-independent biomedical domain models
│   │   ├── repositories/        persistence and ORM/domain mapping
│   │   ├── schemas/             API contracts
│   │   └── services/            ingestion, normalization, cache, source clients
│   ├── migrations/              Alembic database revision history
│   ├── resources/               bounded ingestion manifests
│   └── tests/
└── web/                         React/Vite client
    └── src/
        ├── components/          reusable UI and graph view
        ├── lib/                 typed API client
        └── test/                test setup
```

The runtime flow is `external client -> validated source model -> normalization -> domain model -> repository -> PostgreSQL`. Read APIs follow `route -> repository -> domain response`; NetworkX construction remains separate from transport and persistence so algorithms can be evaluated reproducibly.

```text
Open Targets ─┐
              ├─> validated clients ─> normalization ─> PostgreSQL
Europe PMC ───┘                                      │
                                                     v
React UI <─> FastAPI routes <─> services <─> bounded snapshot
    │                                      │
    └─ Cytoscape visualization             └─ NetworkX search/ranking
                                                   │
                                                   └─ evidence bundle ─> optional LLM adapter
```

The discovery flow is `validated query -> bounded database neighborhood -> NetworkX multigraph -> simple-path enumeration -> transparent ranking`. See `docs/discovery-engine.md` for scoring assumptions, limits, complexity, benchmark results, and scientific limitations.

Evidence retrieval follows `replayed discovery query -> verified path ID -> edge provenance -> exact evidence/publication joins`. The optional assistant consumes that immutable bundle through a provider-neutral interface and returns a deterministic summary when no LLM is configured. See `docs/evidence-assistant.md` for the contracts, grounding checks, examples, and limitations.

Only an Open Targets target–disease association creates a `gene_associated_with_disease` edge. Europe PMC title/abstract search results are stored as `literature_context`, never promoted into proof that an association is true. Every edge and evidence item carries its source identifier and retrieval time. Open Targets scores are retained for ranking and explicitly described as heuristic scores rather than probabilities or confidence values.

## Persisted schema

| Table                   | Purpose                         | Important uniqueness/provenance                 |
| ----------------------- | ------------------------------- | ----------------------------------------------- |
| `entities`              | Normalized genes and diseases   | `canonical_id`; `(source, source_identifier)`   |
| `relationships`         | Typed directed edges            | `canonical_key`; source pair/type               |
| `evidence_records`      | Per-source evidence and scores  | relationship/source/source-record               |
| `publications`          | Europe PMC publication metadata | source/source-identifier; DOI/PMID indexed      |
| `evidence_publications` | Evidence-to-publication links   | composite primary key                           |
| `ingestion_runs`        | Reproducibility audit           | manifest parameters, status, counts, timestamps |

Identifiers are normalized as namespaced values such as `ensembl:ENSG00000141510` and `efo:EFO_0000001`. Duplicate inputs upsert the same records instead of creating parallel nodes.

## Frontend experience

The hash-routed React workspace includes:

- A home dashboard that submits canonical Ensembl gene identifiers to the validated discovery API
  and carries the returned session into the workspace.
- A discovery workspace with bounded query controls, accessible entity/edge lists, and an
  interactive Cytoscape.js network built only from returned paths.
- An evidence inspector that keeps provenance, uncertainty, and publication availability visible.
- A verified-source evidence explorer with direct-versus-inferred labeling, exact Europe PMC links,
  unresolved-reference warnings, and an optional grounded path assistant.
- A candidate-path comparison view populated from the same backend response and its path-evidence
  endpoints, plus evaluation and methodology screens.
- Loading, empty, offline, success, and graph-rendering error states.

Successful API payloads are checked at runtime with Zod before they enter application state. The
legacy layout fixture remains isolated in `apps/web/src/data/demoDataset.ts` for development
reference and is not imported by the home, discovery, graph, evidence, or comparison workflow.

## Screenshots

Screenshots are intentionally not committed as evidence of a live biomedical deployment. To capture
portfolio images from the reproducible local interface:

1. Run the Docker setup and starter ingestion below.
2. Open <http://localhost:5173> at a 1440 × 900 browser viewport.
3. Capture `#home`, `#discover`, `#compare`, `#evaluation`, and `#methodology`.
4. For the evidence explorer, use an identifier returned by the ingestion command; keep the visible
   stable IDs, provenance, and uncertainty panel in frame.
5. If the API is offline or ingestion has not run, capture the explicit unavailable or empty state;
   do not describe a mocked test fixture as scientific data.

Before publishing screenshots, verify that they contain no local credentials, private hostnames, or
unreviewed copyrighted full text.

## Run with Docker (recommended)

Requirements: Docker with Compose support.

```bash
cp .env.example .env
docker compose up --build
```

The API container applies the Alembic migration before starting. To ingest the bounded starter domain after the services are healthy:

```bash
docker compose exec api python -m genegarden_api.cli.ingest \
  --manifest resources/starter_domain.json
```

Open the web app at <http://localhost:5173>, API documentation at <http://localhost:8000/docs>, and health endpoint at <http://localhost:8000/api/v1/health>. Stop with `docker compose down`. Add `-v` only if you intentionally want to delete the local PostgreSQL volume.

## Run without Docker

Use Python 3.12+ and Node.js 22.12+.

```bash
cp .env.example .env
cd apps/api
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
alembic upgrade head
uvicorn genegarden_api.main:app --reload
```

In another terminal, from the repository root:

```bash
npm ci
npm run dev:web
```

For local PostgreSQL outside Docker, ensure the database described by `DATABASE_URL` exists. The current health endpoint checks the API process only and does not imply database or upstream-source availability.

Run the reproducible starter ingestion from `apps/api`:

```bash
python -m genegarden_api.cli.ingest --manifest resources/starter_domain.json
```

The starter manifest resolves two Ensembl target IDs live, retains at most five Open Targets associations per target, and retrieves at most three Europe PMC results per association. It therefore makes at most two Open Targets requests and ten Europe PMC searches. Names, associations, scores, and publications are not hard-coded. Expand the domain by creating another reviewed manifest; keep API requests small, or use the sources' documented bulk-access routes for systematic analysis.

## Knowledge API

After ingestion:

```bash
curl http://localhost:8000/api/v1/knowledge/entities/ensembl:ENSG00000141510
curl http://localhost:8000/api/v1/knowledge/graph/ensembl:ENSG00000141510
```

The graph response contains `entities`, `relationships`, `publications`, and `generated_at`. This abbreviated shape uses **development-fixture values only**, not verified biomedical data:

```json
{
  "entities": [
    {
      "canonical_id": "ensembl:ENSG00000141510",
      "entity_type": "gene",
      "label": "FIXTURE_GENE",
      "source": "open_targets"
    }
  ],
  "relationships": [
    {
      "relationship_type": "gene_associated_with_disease",
      "source": "open_targets",
      "score": 0.73,
      "evidence": [
        { "evidence_type": "literature_context", "source": "europe_pmc" }
      ]
    }
  ],
  "publications": [
    {
      "source_identifier": "MED:FIXTURE-1",
      "title": "Fixture publication for API contract testing"
    }
  ]
}
```

Full response contracts are available from `/docs` and are mirrored as TypeScript interfaces in `apps/web/src/lib/api.ts`.

After discovery, submit the original query and returned `path_id` to
`POST /api/v1/evidence/paths`. Ask a scoped question through `POST /api/v1/assistant/answer`.
The default `ASSISTANT_LLM_PROVIDER=none` setting requires no AI credentials and returns a
deterministic evidence summary. Provider output cannot mutate the graph, and uncited reported claims
are withheld.

Discover bounded candidate paths:

```bash
curl -X POST http://localhost:8000/api/v1/discovery/paths \
  -H 'Content-Type: application/json' \
  -d '{"source_id":"ensembl:ENSG00000141510","target_entity_types":["disease"],"max_path_length":3,"result_count":10}'
```

Run the frozen Open Targets edge-masking benchmark:

```bash
cd apps/api
python -m genegarden_api.cli.benchmark \
  --benchmark resources/benchmarks/oncology_open_targets_26_09.json --k 5
```

The benchmark is a frozen experiment configuration: Open Targets release 26.09, retrieved
2026-10-11, four genes, six diseases, 14 association records, and three direct edges masked as
labels. At `k=5`, the verified run produced:

| Method                    | Precision@5 | Recall@5 |      MRR |
| ------------------------- | ----------: | -------: | -------: |
| `transparent_baseline_v1` |    0.133333 | 0.666667 | 0.233333 |
| `shortest_path`           |    0.133333 | 0.666667 | 0.233333 |
| `unweighted_path_count`   |    0.133333 | 0.666667 | 0.205556 |

The transparent method did not outperform shortest path on these three cases. Labels and traversal
edges come from the same release, so the benchmark has source and aggregation leakage and is only an
engineering regression check. See `docs/discovery-engine.md` for construction, formulas, complexity,
and limitations.

## Quality checks

```bash
make api-lint
make api-test
make web-lint
make web-format
make web-test
npm run build:web
```

Or run the complete local gate, including the frozen benchmark and production frontend build:

```bash
make check
```

Run the deterministic browser suite with `npm run test:e2e`. It mocks the HTTP contracts and is
separate from the PostgreSQL/live-source procedure in `docs/end-to-end-testing.md`.

The initial 2026-10-11 portfolio-readiness run completed 40 backend tests with 87.58% statement
coverage. The subsequent verified-frontend integration run completed 24 frontend tests across eight
files. It also completed Ruff lint/format checks, ESLint, Prettier,
strict TypeScript compilation, the Vite production build, and the benchmark command. Docker itself
was unavailable in that review environment, so container construction was not claimed as locally
verified; `.github/workflows/ci.yml` performs Compose validation and image builds on GitHub runners.
The backend package was also installed into a fresh temporary virtual environment, while an isolated
frontend copy completed `npm ci` and the full frontend gate. This verifies clean dependency installs,
but not a live PostgreSQL/Docker startup on that machine.

Backend dependencies and tools are declared in `apps/api/pyproject.toml`; frontend dependencies and scripts are declared in the root workspace and `apps/web/package.json`. The committed `package-lock.json` locks the complete frontend dependency tree; use `npm ci` in clean and CI environments.

## Configuration

Settings use environment variables, with `.env` ignored by Git. `API_CORS_ORIGINS` is a JSON array. `VITE_API_BASE_URL` is embedded into the frontend build and is therefore public configuration, never a place for secrets.

When `APP_ENV=production`, startup rejects the documented development database password and any
non-HTTPS CORS origin. Operators still need to supply secrets through their deployment platform and
terminate TLS at a trusted ingress or proxy.

External calls use a descriptive user agent, explicit timeouts, at most five configurable attempts, bounded exponential backoff for transient status codes, response validation, request-size caps, and a TTL cache. `EUROPE_PMC_EMAIL` is optional contact metadata and must not contain a secret.

Errors use a stable JSON envelope with `code`, `message`, and optional `details`. Unexpected exceptions are logged server-side while clients receive a non-sensitive message.

## Source and fixture policy

- Live records are retrieved from the configured public APIs and stamped with retrieval times.
- `apps/api/tests/fixtures/`, `apps/web/src/test/verifiedFixtures.ts`, and
  `apps/web/src/data/demoDataset.ts` are synthetic development fixtures. The TypeScript fixtures
  exercise verified-response shapes but contain no scientific assertions. None are runtime fallback
  data, and none may be described as verified scientific records.
- Open Targets and upstream datasets have their own attribution and licensing expectations. Follow the Platform's [licence guidance](https://platform-docs.opentargets.org/licence), [terms of use](https://platform-docs.opentargets.org/licence/terms-of-use), and [citation guidance](https://platform-docs.opentargets.org/citation), then inspect each underlying data source's terms before redistribution.
- Europe PMC metadata and open-access content have different reuse conditions; this application stores metadata only and preserves source identifiers. Review the [developer access guidance](https://europepmc.org/developers) and respect the license attached to each article before using full text.
- Upstream errors remain explicit errors. The ingestion workflow never silently substitutes fixtures for live data.

See `apps/api/README.md` for source endpoints, documented mappings, and operational notes.

## Algorithm complexity and operational limits

Graph construction is `O(V + E)` for the bounded snapshot. Simple-path enumeration is exponential in
the worst case, approximately `O(b^L)` for branching factor `b` and maximum length `L`; ranking `P`
candidates costs `O(P log P)`. The public contract therefore caps path length at four, returned paths
at 25, enumerated paths at 5,000, expansions at 20,000, loaded nodes at 500, and loaded relationships
at 2,000. Exceeding a limit returns a structured error instead of a silent partial answer.

## Known limitations

- The knowledge graph currently supports one explicit relationship type: Open Targets
  gene–disease association.
- The starter ingestion domain is intentionally small and requires live public upstream access.
- Europe PMC title/abstract context is not manually adjudicated as supporting or refuting a claim.
- The ranking utility is transparent but uncalibrated and not a probability.
- The benchmark has only three source-leaky cases and cannot establish biological performance.
- NetworkX traversal materializes a bounded neighborhood in one API process; it is not designed for a
  global graph or unrestricted path length.
- The health endpoint checks process availability, not database or upstream readiness.
- No hosted LLM adapter is included. The default assistant is deterministic and provider-free.
- The project has not been claimed as publicly deployed, load-tested, clinically validated, or
  security-audited.

## Future improvements

- Add versioned raw-source snapshots and field-level lineage.
- Move ingestion to resumable background jobs with source-specific rate limiting.
- Evaluate temporal or independently curated benchmarks with confidence intervals and leakage audits.
- Add database readiness, OpenTelemetry traces, metrics, dependency scanning, and container scanning.
- Benchmark PostgreSQL recursive queries or a graph database when graph scale warrants it.
- Add a reviewed LLM adapter with structured outputs, entailment checks, and human feedback.
- Add user accounts and saved explorations only after defining privacy and retention requirements.

See `docs/deployment.md` for local and production deployment guidance and
`docs/interview-preparation.md` for project-specific interview questions and model answers.

## License and safety

Choose a repository license before public release. GeneGarden AI is for research and education only; it must not be presented as medical advice or used for clinical decisions.
