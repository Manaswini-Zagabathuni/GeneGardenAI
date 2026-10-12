# GeneGarden AI interview preparation

These answers describe the committed implementation. They avoid claiming production deployment,
biological validation, or model quality beyond the recorded tests and three-case regression
benchmark.

## 1. Why did you use PostgreSQL plus NetworkX instead of a graph database?

PostgreSQL provides mature constraints, migrations, transactions, JSON metadata, and straightforward
deployment for the current bounded dataset. The repository loads a depth-limited neighborhood and
converts it into a NetworkX `MultiGraph` for algorithm work. This keeps persistence independent from
search experiments and makes tests deterministic. The trade-off is that every query materializes a
subgraph in application memory. If the graph or concurrency grew substantially, I would evaluate a
graph database or PostgreSQL recursive queries, while preserving the source-independent domain
models and provenance contracts.

## 2. How do you stop indirect path search from exhausting the service?

There are limits at several layers: four edges per path, 25 returned paths, 5,000 enumerated paths,
20,000 expansions, 500 loaded entities, and 2,000 loaded relationships. The repository expands one
depth at a time with SQL limits, and the algorithm raises a stable `discovery_query_limit` error
instead of returning an undocumented partial result. The assistant uses an even smaller one-hop,
100-node, 100-relationship budget for entity questions.

## 3. How does the ranking algorithm work, and what does the score mean?

`transparent_baseline_v1` is an ordering utility, not a probability. It weights normalized path
length at 0.40, comparable Open Targets association strength at 0.40, and capped datasource breadth
at 0.20. Relationship reliability has weight zero because there is no independently calibrated
value. Each response exposes raw values, normalization, weights, contributions, and limitations.
Missing comparable strength contributes zero rather than receiving an invented default.

## 4. How do you prevent duplicate or circular paths?

Depth-first enumeration carries the current ordered node tuple and refuses to revisit a node, so each
candidate is a simple path. A second signature over ordered node IDs and relationship types prevents
duplicate logical paths. Parallel relationship records are grouped into one logical traversal edge,
but every distinct underlying relationship and evidence record remains attached. Tests cover cycles,
self-loops, duplicate edges, dangling endpoints, disconnected targets, and work-budget exhaustion.

## 5. How is biomedical provenance preserved?

Entities, relationships, evidence records, and publications retain their original source identifier
and retrieval timestamp. Evidence-to-publication links are persisted in a join table. Evidence
exploration resolves only exact linked Europe PMC `SOURCE:ID` records; it does not attach papers by
fuzzy title matching. Reverse graph traversal is labeled `reverse` while retaining the original edge
direction. Europe PMC search results remain `literature_context` and never create graph edges.

## 6. How does the AI assistant avoid hallucinated citations?

The core assistant is deterministic and needs no LLM. A provider adapter receives an immutable
retrieved evidence bundle and returns structured claims. Every model `reported_finding` must cite an
allowed evidence or publication ID. Unknown or missing citations cause the claim to be withheld and
reported in `unsupported_claims`. The provider has no repository or graph-write capability. This is
necessary but not sufficient for semantic faithfulness; a production adapter still needs entailment
evaluation and human review.

## 7. What was difficult about integrating Open Targets and Europe PMC?

The sources have different semantics. Open Targets supplies target–disease association aggregations;
Europe PMC supplies publication metadata and search context. Treating a literature search hit as
proof would be incorrect. The ingestion layer validates source-specific Pydantic models, normalizes
identifiers, persists the association only from Open Targets, and attaches Europe PMC results with an
explicit warning that they were not independently validated as support.

## 8. What bugs and edge cases did the test strategy catch?

The release-readiness pass caught backend files that passed lint but failed the formatter and a
frontend test harness that did not explicitly clean the DOM between tests. The suite now verifies
invalid canonical IDs, error-envelope stability, timezone-aware timestamps, unknown schema fields,
bounded retries, malformed upstream responses, missing evidence, invalid publication IDs, graph
self-loops, reverse traversal, frontend loading/empty states, keyboard-accessible graph selection,
and verified evidence rendering.

## 9. How is the benchmark reproducible, and what can it actually show?

The JSON fixture records its Open Targets release (`26.09`), retrieval date, four genes, six diseases,
14 association edges, source scores, datasource labels, three masked expected edges, and limitations.
The command reconstructs the graph, masks each direct label, and compares the transparent method with
shortest-path and unweighted path-count orderings. At `k=5`, all methods recorded Precision@5
0.133333 and Recall@5 0.666667; MRR was 0.233333 for the transparent and shortest-path methods and
0.205556 for path count. Three source-leaky cases are only a regression check and do not establish
biological validity or superiority.

## 10. How would you extend the system for larger-scale or production use?

I would separate ingestion into an idempotent job queue, store immutable source snapshots, add
temporal dataset versions, and introduce request-level caching keyed by graph version. For search, I
would benchmark database-native traversal or a graph store before changing architecture. For
evaluation, I would use preregistered temporal splits or an independent curated source, more disease
areas, confidence intervals, and leakage checks. Operationally, I would add database readiness,
metrics and tracing, SLOs, automated backups, dependency scanning, image scanning, and a staged
migration/release process.

## Architecture trade-offs to emphasize

- **Typed source adapters vs. flexible dictionaries:** stricter and noisier, but upstream schema drift
  fails visibly instead of corrupting the graph.
- **Bounded in-memory traversal vs. unrestricted exploration:** predictable for a portfolio-scale
  service, but may miss longer hypotheses and does not scale to a global graph.
- **Transparent heuristic vs. learned ranking:** explainable with little labeled data, but not
  calibrated and not proven better than shortest path.
- **Deterministic default assistant vs. mandatory LLM:** less fluent, but free, reproducible, and
  usable without credentials.
- **Exact publication joins vs. fuzzy retrieval:** higher provenance precision, but unresolved or
  incomplete literature remains explicitly missing.

## System-design extensions worth discussing

1. Versioned raw-source storage and lineage from raw responses to normalized records.
2. Background ingestion with per-source rate limiting, dead-letter handling, and resumable manifests.
3. Redis or database-backed cache shared across API replicas.
4. Hybrid keyword/vector literature retrieval with claim-level entailment checks.
5. Graph snapshots partitioned by data release and research domain.
6. User-saved explorations with immutable query and algorithm-version metadata.
7. OpenTelemetry traces, Prometheus metrics, database readiness, and upstream health dashboards.
8. Independent evaluation datasets, temporal holdouts, uncertainty intervals, and automated leakage
   audits.
