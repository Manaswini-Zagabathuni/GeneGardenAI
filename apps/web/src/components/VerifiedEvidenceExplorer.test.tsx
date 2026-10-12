import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { ApiPathEvidenceView } from '../lib/api'
import { VerifiedEvidenceExplorer } from './VerifiedEvidenceExplorer'

const evidence = {
  path_id: 'fixture-path',
  claim_scope: 'inferred_path',
  missing_evidence: false,
  conflict_status: 'not_assessed',
  uncertainty: ['Conflict was not assessed by the stored sources.'],
  publications: [
    {
      citation_id: 'publication:MED:12345',
      source_identifier: 'MED:12345',
      title: 'Verified fixture publication',
      web_url: 'https://europepmc.org/article/MED/12345',
      author_string: 'Example A',
      journal: 'Fixture Journal',
      publication_year: 2024,
      abstract: 'Synthetic test abstract with no scientific assertion.',
      doi: null,
      pmid: '12345',
      pmcid: null,
      is_open_access: true,
      verified_from: 'persisted_europe_pmc',
    },
  ],
  relationships: [
    {
      claim_id: 'relationship:fixture',
      claim_scope: 'direct_relationship',
      source_entity: {
        canonical_id: 'ensembl:ENSG00000000001',
        entity_type: 'gene',
        label: 'Fixture gene',
        description: null,
        source: 'open_targets',
        source_identifier: 'ENSG00000000001',
        aliases: [],
        attributes: {},
        retrieved_at: '2026-10-11T00:00:00Z',
      },
      target_entity: {
        canonical_id: 'efo:EFO_0000001',
        entity_type: 'disease',
        label: 'Fixture disease',
        description: null,
        source: 'open_targets',
        source_identifier: 'EFO_0000001',
        aliases: [],
        attributes: {},
        retrieved_at: '2026-10-11T00:00:00Z',
      },
      traversed_from: 'ensembl:ENSG00000000001',
      traversed_to: 'efo:EFO_0000001',
      direction: 'forward',
      relationship: {
        canonical_key: 'fixture',
        source_entity_id: 'ensembl:ENSG00000000001',
        target_entity_id: 'efo:EFO_0000001',
        relationship_type: 'gene_associated_with_disease',
        source: 'open_targets',
        source_identifier: 'fixture-source',
        score: 0.5,
        score_interpretation: 'Fixture score; not confidence.',
        evidence: [],
        attributes: {},
        retrieved_at: '2026-10-11T00:00:00Z',
      },
      evidence_items: [
        {
          evidence_id: 'evidence:fixture',
          record: {
            source: 'europe_pmc',
            source_record_id: 'fixture-literature-search',
            evidence_type: 'literature_context',
            score: null,
            summary: 'Fixture context only.',
            publication_ids: ['MED:12345'],
            attributes: {},
            retrieved_at: '2026-10-11T00:00:00Z',
          },
          publications: [],
          missing_publication_ids: [],
          interpretation: 'Literature context is not causal evidence.',
        },
      ],
      conflict_status: 'not_assessed',
      uncertainty: ['Conflict not assessed.'],
    },
  ],
  path: {
    path_id: 'fixture-path',
    nodes: [],
    edges: [],
    score: {
      ranking_utility: 0.5,
      method: 'fixture',
      components: [],
      interpretation: 'Not a probability.',
    },
    limitations: [],
  },
} satisfies ApiPathEvidenceView

describe('VerifiedEvidenceExplorer', () => {
  it('renders identifiers, inference warning, evidence source, and verified publication link', () => {
    render(<VerifiedEvidenceExplorer evidence={evidence} />)

    expect(screen.getAllByText('Inferred path').length).toBeGreaterThan(0)
    expect(screen.getByText('ensembl:ENSG00000000001', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('open_targets')).toBeInTheDocument()
    expect(screen.getByText(/not a reported causal chain/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Verified fixture publication' })).toHaveAttribute(
      'href',
      'https://europepmc.org/article/MED/12345',
    )
    expect(screen.getByText(/Available abstract/i)).toBeInTheDocument()
  })
})
