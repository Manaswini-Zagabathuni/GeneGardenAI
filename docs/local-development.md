# Local development without Docker

This workflow runs Vite and FastAPI directly on macOS and stores application data in hosted
PostgreSQL. It does not install or invoke Docker, and it does not substitute SQLite. The repository
still uses the same SQLAlchemy models, Alembic migration, asyncpg driver, and PostgreSQL schema as
the Compose workflow.

## 1. Create a hosted PostgreSQL database

Neon is one supported option; another hosted PostgreSQL provider works when it supplies a standard
TLS connection URL.

1. In the [Neon console](https://console.neon.tech), create a project and a development database.
   A separate development branch is recommended so experiments cannot affect another environment.
2. Open **Connect**, select the database and role, and copy its connection string. A direct
   connection is simplest for this long-running local API and Alembic. Keep the value private.
3. Neon currently supplies a URL shaped like
   `postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require&channel_binding=require`.
   GeneGarden accepts that provider form and converts it in memory to SQLAlchemy's asyncpg dialect.
   `sslmode=require` remains an enforced TLS setting; the unsupported libpq-only
   `channel_binding` query option is not passed to asyncpg.

Do not paste the connection string into chat, source code, a frontend variable, or a committed
file. If a URL is accidentally disclosed, rotate the database role password in the provider console.

## 2. Configure the repository

From the repository root:

```bash
python3.12 -m venv work/venv  # skip this when the existing environment is present
work/venv/bin/python -m pip install -e './apps/api[dev]'
npm ci
cp .env.example .env
chmod 600 .env
```

Python virtual environments are not portable between checkout locations. If the repository is moved
or copied, recreate `work/venv` and reinstall the editable package instead of reusing the old
environment. This prevents imports from resolving to a previous checkout.

Open `.env` in a local editor and replace only `DATABASE_URL` with the copied hosted connection
string. The required and relevant settings are:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require
DATABASE_READINESS_TIMEOUT_SECONDS=5
API_CORS_ORIGINS=["http://localhost:5173"]
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

`.env` is excluded by `.gitignore`. `DATABASE_URL` is backend-only; every `VITE_` value is embedded
in browser assets and therefore must never contain a secret. `OPEN_TARGETS_GRAPHQL_URL` and
`EUROPE_PMC_API_URL` in `.env.example` are public endpoints, not credentials. `EUROPE_PMC_EMAIL` is
optional contact metadata.

For Neon hosts, startup validation rejects a URL that does not request `require`, `verify-ca`, or
`verify-full` TLS. PostgreSQL URLs for other providers should also include the TLS mode that provider
requires. The application never logs the connection URL, and the readiness error deliberately omits
driver error text.

## 3. Migrate and verify PostgreSQL

The following uses the existing environment without activation, so separate terminals behave
consistently:

```bash
make local-migrate
cd apps/api && ../../work/venv/bin/python -m alembic current && cd ../..
```

Start the API from the repository root:

```bash
make dev-api-local
```

In another terminal, distinguish process health from database readiness:

```bash
curl --fail http://localhost:8000/api/v1/health
curl --fail http://localhost:8000/api/v1/ready
```

The first can succeed while PostgreSQL is unavailable. The second runs a bounded `SELECT 1`; it
returns HTTP 503 with code `database_unavailable` if the configured database cannot serve a query.

## 4. Run bounded live biomedical ingestion

With migrations applied and outbound HTTPS available:

```bash
make local-ingest-starter
```

This invokes the existing reviewed manifest at `apps/api/resources/starter_domain.json`. It resolves
two Ensembl target identifiers through the public Open Targets GraphQL API, retains at most five
associations per target, and requests at most three Europe PMC records for each association. The
command validates upstream responses and prints record counts, not database credentials. Upstream
failure is an error; it never falls back to fixtures.

After a successful run, verify that records are served from PostgreSQL:

```bash
curl --fail 'http://localhost:8000/api/v1/knowledge/entities/ensembl:ENSG00000141510'
curl --fail 'http://localhost:8000/api/v1/knowledge/graph/ensembl:ENSG00000141510'
```

The response should contain source identifiers and retrieval timestamps created by the live
ingestion. Do not describe these records as live until the command and API requests have succeeded
against your configured database.

## 5. Start the frontend

Keep the API running and use a third terminal:

```bash
make dev-web-local
```

The local target invokes Vite with Node directly after `npm ci` has installed the dependencies. It
resolves `node` from `PATH` and has no dependency on Codex or a machine-specific runtime location.
Override the executable explicitly when needed:

```bash
make dev-web-local NODE=/absolute/path/to/node
```

Open <http://localhost:5173>. Search using an identifier actually returned by ingestion, inspect a
returned path, select graph elements, and compare its evidence with the knowledge response. The Vite
frontend calls `http://localhost:8000/api/v1`; no database credential is exposed to it.

## Troubleshooting

- `GET /health` succeeds but `/ready` returns 503: check the provider endpoint status, database name,
  role, password, network access rules, and required TLS query parameter in the private `.env` file.
- Migration cannot import `genegarden_api`: reinstall the editable backend package with the exact
  `work/venv/bin/python -m pip install -e './apps/api[dev]'` command above.
- The API returns no discovery paths after readiness succeeds: run the ingestion command and inspect
  its explicit upstream or validation error. An empty database is not an API connectivity failure.
- A hosted provider URL uses another SQLAlchemy driver: use a standard `postgresql://` URL or the
  documented `postgresql+asyncpg://` form. Other drivers are rejected rather than silently changing
  database behavior.
