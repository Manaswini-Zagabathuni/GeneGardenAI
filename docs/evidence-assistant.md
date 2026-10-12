# Evidence explorer and research assistant

GeneGarden's evidence layer is a read-only projection over the persisted knowledge graph. It does
not create relationships, reinterpret a literature search result as causal evidence, or write an
LLM response back to PostgreSQL.

## Retrieval flow

1. The client submits the same validated discovery query plus a returned `path_id`.
2. The API reloads the bounded graph neighborhood and repeats the deterministic path search. A path
   ID is accepted only if it occurs in that result, preventing a client from supplying an invented
   path.
3. Every traversed edge is expanded into its original directed relationship, stable entity IDs,
   source identifier, retrieval timestamp, and evidence records.
4. An evidence record's exact `publication_ids` are joined to persisted Europe PMC records. A
   publication is never attached by title similarity at display time. Safe `SOURCE:ID` pairs link to
   `https://europepmc.org/article/{SOURCE}/{ID}`; malformed or unresolved identifiers are shown as
   missing rather than turned into links.
5. Stored abstracts are those returned by the Europe PMC `core` response during ingestion. The
   bounded `EuropePmcClient.fetch_publication()` method supports an exact `EXT_ID` + `SRC` refresh,
   validates the response, and uses the existing timeout, retry, and TTL-cache policy.

Europe PMC documents that `core` includes full publication metadata and abstracts, and that source
plus external ID identifies an exact record. See the official [REST API](https://europepmc.org/RestfulWebService)
and [search help](https://europepmc.org/help).

## Semantics

- A one-edge result is labeled `direct_relationship`: the edge itself is present in the persisted
  source graph. This does not mean the relationship is causal.
- A multi-edge result is labeled `inferred_path`: each component edge is stored, but the combined
  path is a GeneGarden hypothesis for exploration rather than a directly reported finding.
- Open Targets overall and datasource scores retain their documented, source-specific meanings.
  They are not probabilities.
- `literature_context` means the paper was retrieved in the entity-pair context. Its presence alone
  is not proof that the paper supports the relationship.
- Conflict is reported only when normalized `stance=support` and `stance=refute` metadata are both
  present. Current Open Targets aggregate and Europe PMC records normally lack that mapping, so the
  honest default is `not_assessed`, not `none`.

## API

Resolve evidence for a path returned by `/api/v1/discovery/paths`:

```bash
curl -X POST http://localhost:8000/api/v1/evidence/paths \
  -H 'Content-Type: application/json' \
  -d '{
    "discovery": {
      "source_id": "ensembl:ENSG00000141510",
      "target_entity_types": ["disease"],
      "max_path_length": 3,
      "result_count": 5
    },
    "path_id": "PATH_ID_FROM_DISCOVERY"
  }'
```

Ask about that path:

```bash
curl -X POST http://localhost:8000/api/v1/assistant/answer \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "What does the retrieved evidence support?",
    "path": {
      "discovery": {
        "source_id": "ensembl:ENSG00000141510",
        "target_entity_types": ["disease"],
        "max_path_length": 3,
        "result_count": 5
      },
      "path_id": "PATH_ID_FROM_DISCOVERY"
    },
    "use_llm": true
  }'
```

An entity-scoped question uses `{"question":"…","entity_id":"ensembl:…"}`. Exactly one of
`entity_id` and `path` is required. Queries are capped by the discovery and repository limits.

## Optional provider interface

`ResearchAssistantService` accepts an implementation of the `LlmProvider` protocol. The default
API passes no provider and therefore returns a deterministic evidence summary; no credentials or
paid service are required. A future adapter must accept a `GroundedGenerationRequest` and return
structured `AssistantClaim` objects. It must not receive a graph-write capability.

Before model claims are returned, the service checks that every `reported_finding` has at least one
citation and that all citations occur in the retrieved bundle. Uncited or unknown-citation claims
are withheld and surfaced in `unsupported_claims`. Hypotheses and model interpretations are
separate enum values, not prose conventions.

Citation membership is a necessary safeguard, not proof that generated prose is entailed by a
paper. A production LLM adapter should add sentence-level entailment evaluation and human review;
the application must continue to expose abstracts and source records so researchers can inspect the
underlying material.

## Known limitations

- Europe PMC metadata and abstracts do not replace reading the full paper. Full text is not fetched.
- A paper retrieved using an entity pair can be background or contradictory; GeneGarden does not
  assign a support/refute stance unless a trusted mapping explicitly provides one.
- Missing publication links do not mean no literature exists; they mean no exact linked record is
  available in this graph snapshot.
- Conflicts may be absent because they have not been normalized, not because the literature agrees.
- Graph adjacency and path ranking are discovery aids. They do not establish mechanism, direction
  of effect, causality, clinical validity, or diagnostic relevance.
- The default assistant summarizes stored records and may be less fluent than an LLM, but it remains
  available offline from AI providers and does not invent biomedical explanations.
