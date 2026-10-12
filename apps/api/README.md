# GeneGarden API

FastAPI service for GeneGarden AI. See the repository root README for complete setup and architecture.

## External contracts

- [Open Targets GraphQL](https://platform-docs.opentargets.org/data-access/graphql-api): `POST https://api.platform.opentargets.org/api/v4/graphql`. Gene identifiers are Ensembl IDs and disease identifiers follow the ontology identifiers returned by the Platform. The implemented query requests one target plus a capped page of `associatedDiseases`, including overall, datatype, and datasource scores. The selected fields are checked against the Platform's [published GraphQL schema](https://api.platform.opentargets.org/api/v4/graphql/schema).
- [Europe PMC REST](https://europepmc.org/RestfulWebService): `GET https://www.ebi.ac.uk/europepmc/webservices/rest/search` with `format=json`, `resultType=core`, and a capped `pageSize`. Results are publication metadata attached as literature context.

`services/clients/` owns transport resilience and source-response validation. `services/ingestion.py` owns documented mappings. `services/normalization.py` owns canonical identifiers and duplicate merging. `repositories/knowledge.py` is the only layer translating domain records to SQLAlchemy rows.

No Europe PMC search result creates a biological relationship. A title/abstract term match is not treated as evidence that a publication supports an association.

The discovery endpoint is `POST /api/v1/discovery/paths`. It loads a depth-bounded database neighborhood, creates a NetworkX multigraph, enumerates cycle-free paths, deduplicates parallel logical paths, and returns complete relationship/evidence provenance with score explanations. See the repository's `docs/discovery-engine.md` for formulas and complexity.

## Commands

From this directory with the development environment installed:

```bash
alembic upgrade head
python -m genegarden_api.cli.ingest --manifest resources/starter_domain.json
python -m genegarden_api.cli.benchmark --benchmark resources/benchmarks/oncology_open_targets_26_09.json --k 5
pytest
ruff check .
ruff format --check .
```

The command records a row in `ingestion_runs`, validates all upstream JSON before mapping, upserts normalized records, and prints deterministic record counts. It exits with a clear error if an upstream is unavailable or changes its response shape.
