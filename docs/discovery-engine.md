# Biomedical discovery engine

## Scope and semantics

The discovery engine enumerates bounded, cycle-free paths from one normalized entity. It is a hypothesis-generation tool: a returned path does not establish causality, clinical validity, or diagnostic relevance.

The current persisted graph has one supported relationship type, `gene_associated_with_disease`, sourced from Open Targets. The engine can traverse this relationship in either direction to support gene-to-disease and disease-to-gene exploration, but every response preserves the stored source/target direction and labels reverse traversal. Relationship types may only be combined after adding an explicit compatibility mapping. Unknown combinations fail rather than being treated as semantically interchangeable.

Europe PMC search results remain `literature_context`. They are returned with edge provenance but do not contribute numeric support to ranking because a title/abstract match has not been independently validated as supporting the relationship.

## Search algorithm and limits

`BiomedicalDiscoveryEngine` builds a NetworkX `MultiGraph` from a bounded database snapshot. Parallel database relationships with the same endpoints and type become one logical traversal edge containing every distinct relationship record. Evidence records are deduplicated by `(source, source_record_id)`.

The engine performs deterministic depth-first enumeration of simple paths. A node already present in the current path cannot be revisited, preventing cycles. A path signature containing its ordered node IDs and relationship types prevents duplicate results.

Public API limits are deliberately small:

- maximum path length: 4 edges;
- maximum returned paths: 25;
- maximum enumerated paths: 5,000;
- maximum path expansions: 20,000;
- maximum loaded entities: 500;
- maximum loaded relationships: 2,000.

The repository expands the persisted neighborhood one depth at a time and places a SQL limit on each relationship query. Exceeding a graph or enumeration budget returns `discovery_query_limit` instead of silently returning a partial result.

## Transparent baseline ranking

`transparent_baseline_v1` is an ordering utility in `[0, 1]`; it is not a probability or confidence value.

| Component | Weight | Normalization |
| --- | ---: | --- |
| Path length | 0.40 | `1 - ((edge_count - 1) / configured_max_length)` |
| Comparable evidence strength | 0.40 | Arithmetic mean of per-edge Open Targets overall association scores |
| Datasource breadth | 0.20 | Per-edge unique Open Targets datasource count, capped at 3, divided by 3, then averaged |
| Relationship reliability | 0.00 | Unavailable; returned as `null` and excluded |

The final utility is the weighted sum. Inputs are already bounded to `[0, 1]`. For parallel duplicate relationships, only the maximum comparable relationship score is used for that logical edge, preventing duplicate records from increasing the score. If any edge lacks a comparable Open Targets overall score, the complete strength component is set to zero and the limitation is returned.

Datasource breadth is only a bounded breadth indicator. Datasources may share publications, cohorts, methods, or upstream records, so the value is not interpreted as independent confirmation. No reliability value is invented because the current data model has no independently calibrated relationship reliability measure.

Every candidate includes the raw value, normalized value, weight, contribution, formula explanation, original relationships, evidence records, source identifiers, retrieval timestamps, and uncertainty limitations.

## API

```http
POST /api/v1/discovery/paths
Content-Type: application/json

{
  "source_id": "ensembl:ENSG00000141510",
  "target_entity_types": ["disease"],
  "relationship_types": ["gene_associated_with_disease"],
  "max_path_length": 3,
  "result_count": 10
}
```

`target_id` can restrict discovery to one entity. `intermediate_entity_types` restricts traversal nodes, while `target_entity_types` restricts returned endpoints. Identifiers must already be canonical namespaced IDs.

## Complexity

Let `V` and `E` be the bounded snapshot sizes, `L` the maximum path length, `b` the effective branching factor, and `P` the enumerated path count.

- Database expansion: at most `L` bounded relationship queries; application processing is `O(V + E)` within the returned snapshot.
- NetworkX graph construction: `O(V + E)` time and space.
- Simple-path enumeration: worst-case `O(b^L)` time because simple-path enumeration is inherently exponential. The hard `L <= 4` and `P <= 5,000` limits bound application work.
- Per-path scoring: linear in path length and retained evidence, `O(L × evidence_per_edge)`.
- Ranking: `O(P log P)` time.
- Search memory: `O(V + E + P × L)` because bounded candidate paths are retained for deterministic sorting.

Increasing path length improves recall of indirect routes but rapidly increases runtime, memory, and the risk of biologically weak chains. The default length of 3 is intentionally conservative.

## Reproducible benchmark

`apps/api/resources/benchmarks/oncology_open_targets_26_09.json` is a frozen, transformed subset of Open Targets Platform release 26.09 retrieved on 2026-10-11. It contains four genes, six diseases, fourteen association records, original overall scores, and datasource identifiers. Three known direct relationships are evaluated by masking the direct edge and asking whether the remaining graph recovers the expected disease through an indirect path.

All three ranking methods receive the same complete candidate set, bounded at 5,000 enumerated
paths. The 25-result public API cap is not used to preselect benchmark candidates, avoiding a
comparison in which the transparent method's top 25 silently constrain the other baselines.

Run:

```bash
cd apps/api
python -m genegarden_api.cli.benchmark \
  --benchmark resources/benchmarks/oncology_open_targets_26_09.json \
  --k 5
```

Verified output from the committed benchmark:

| Method | Precision@5 | Recall@5 | MRR |
| --- | ---: | ---: | ---: |
| `transparent_baseline_v1` | 0.133333 | 0.666667 | 0.233333 |
| `shortest_path` | 0.133333 | 0.666667 | 0.233333 |
| `unweighted_path_count` | 0.133333 | 0.666667 | 0.205556 |

These three cases do not support a superiority claim. Expected labels and traversal edges come from the same Open Targets release, causing source and aggregation leakage. The benchmark is an engineering regression check, not an estimate of biological discovery performance. A defensible future evaluation should use preregistered temporal splits or an independent curated source, larger disease-area coverage, endpoint-level negative sampling, and confidence intervals.

Open Targets documents the [GraphQL API and single-entity access pattern](https://platform-docs.opentargets.org/data-access/graphql-api), the [association scoring method and interpretation](https://platform-docs.opentargets.org/associations), and its [citation expectations](https://platform-docs.opentargets.org/citation).
