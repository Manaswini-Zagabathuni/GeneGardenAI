import type { ApiPathEvidenceView, DiscoveryResponse, VerifiedDiscoverySession } from '../lib/api'

const retrievedAt = '2026-10-11T00:00:00Z'

export const verifiedDiscoveryResponse: DiscoveryResponse = {
  query: {
    source_id: 'ensembl:ENSG00000141510',
    target_id: null,
    target_entity_types: ['disease'],
    intermediate_entity_types: [],
    relationship_types: ['gene_associated_with_disease'],
    max_path_length: 3,
    result_count: 10,
    max_enumerated_paths: 5000,
    max_path_expansions: 20000,
  },
  paths: [
    {
      path_id: 'fixture-path-0001',
      nodes: [
        {
          canonical_id: 'ensembl:ENSG00000141510',
          entity_type: 'gene',
          label: 'Fixture source gene',
          description: 'Test-only entity, not a biomedical assertion.',
          source: 'open_targets',
          source_identifier: 'ENSG00000141510',
          aliases: [],
          attributes: {},
          retrieved_at: retrievedAt,
        },
        {
          canonical_id: 'mondo:MONDO_0000001',
          entity_type: 'disease',
          label: 'Fixture target disease',
          description: null,
          source: 'open_targets',
          source_identifier: 'MONDO_0000001',
          aliases: [],
          attributes: {},
          retrieved_at: retrievedAt,
        },
      ],
      edges: [
        {
          traversed_from: 'ensembl:ENSG00000141510',
          traversed_to: 'mondo:MONDO_0000001',
          direction: 'forward',
          relationship_type: 'gene_associated_with_disease',
          relationships: [
            {
              canonical_key: 'fixture-relationship-0001',
              source_entity_id: 'ensembl:ENSG00000141510',
              target_entity_id: 'mondo:MONDO_0000001',
              relationship_type: 'gene_associated_with_disease',
              source: 'open_targets',
              source_identifier: 'fixture-source-pair',
              score: 0.7,
              score_interpretation: 'Fixture source score; not a probability.',
              evidence: [
                {
                  source: 'open_targets',
                  source_record_id: 'fixture:datasource:eva',
                  evidence_type: 'association_datasource_score',
                  score: 0.7,
                  summary: 'Test-only evidence metadata.',
                  publication_ids: ['MED:12345'],
                  attributes: { datasource_id: 'eva' },
                  retrieved_at: retrievedAt,
                },
              ],
              attributes: {},
              retrieved_at: retrievedAt,
            },
          ],
        },
      ],
      score: {
        ranking_utility: 0.73,
        method: 'transparent_baseline_v1',
        components: [
          {
            name: 'path_length',
            raw_value: 1,
            normalized_value: 1,
            weight: 0.4,
            contribution: 0.4,
            explanation: 'Shorter paths receive higher utility within the configured bound.',
          },
          {
            name: 'evidence_strength',
            raw_value: 0.7,
            normalized_value: 0.7,
            weight: 0.3,
            contribution: 0.21,
            explanation: 'Uses comparable scores only where the backend mapping permits it.',
          },
        ],
        interpretation: 'Transparent ranking utility; not a probability or confidence value.',
      },
      limitations: ['A graph relationship does not establish causality.'],
    },
  ],
  graph_node_count: 2,
  graph_relationship_count: 1,
  enumerated_path_count: 1,
  path_expansion_count: 2,
  warnings: [],
}

export const verifiedDiscoverySession: VerifiedDiscoverySession = {
  request: {
    source_id: 'ensembl:ENSG00000141510',
    target_entity_types: ['disease'],
    relationship_types: ['gene_associated_with_disease'],
    max_path_length: 3,
    result_count: 10,
  },
  result: verifiedDiscoveryResponse,
}

export const verifiedPathEvidence: ApiPathEvidenceView = {
  path_id: 'fixture-path-0001',
  claim_scope: 'direct_relationship',
  path: verifiedDiscoveryResponse.paths[0],
  relationships: [
    {
      claim_id: 'relationship:fixture-relationship-0001',
      claim_scope: 'direct_relationship',
      source_entity: verifiedDiscoveryResponse.paths[0].nodes[0],
      target_entity: verifiedDiscoveryResponse.paths[0].nodes[1],
      traversed_from: 'ensembl:ENSG00000141510',
      traversed_to: 'mondo:MONDO_0000001',
      direction: 'forward',
      relationship: verifiedDiscoveryResponse.paths[0].edges[0].relationships[0],
      evidence_items: [
        {
          evidence_id: 'evidence:fixture',
          record: verifiedDiscoveryResponse.paths[0].edges[0].relationships[0].evidence[0],
          publications: [],
          missing_publication_ids: [],
          interpretation: 'The record preserves its source-specific meaning.',
        },
      ],
      conflict_status: 'not_assessed',
      uncertainty: ['Conflict was not assessed by the source.'],
    },
  ],
  publications: [
    {
      citation_id: 'publication:MED:12345',
      source_identifier: 'MED:12345',
      title: 'Verified fixture publication metadata',
      web_url: 'https://europepmc.org/article/MED/12345',
      author_string: 'Example A',
      journal: 'Fixture Journal',
      publication_year: 2024,
      abstract: 'Test-only abstract with no scientific assertion.',
      doi: null,
      pmid: '12345',
      pmcid: null,
      is_open_access: true,
      verified_from: 'persisted_europe_pmc',
    },
  ],
  missing_evidence: false,
  conflict_status: 'not_assessed',
  uncertainty: ['Conflict was not assessed by the stored source.'],
}

export const emptyDiscoveryResponse: DiscoveryResponse = {
  ...verifiedDiscoveryResponse,
  paths: [],
  enumerated_path_count: 0,
  path_expansion_count: 1,
}
