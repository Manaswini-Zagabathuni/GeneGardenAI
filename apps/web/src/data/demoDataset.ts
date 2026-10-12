import type { DemoDataset } from '../types/domain'

const demoEvidence = {
  sourceLabel: 'GeneGarden interface fixture',
  sourceType: 'demo-fixture' as const,
  summary:
    'Synthetic relationship created only to demonstrate interaction and evidence-panel layout.',
  uncertainty: 'not-assessed' as const,
  publications: [],
}

export const demoDataset: DemoDataset = {
  label: 'Synthetic botanical demo',
  description:
    'A deliberately fictional network for interface development. It is not biomedical evidence.',
  nodes: [
    {
      id: 'demo-gene-a',
      label: 'Demo gene A',
      kind: 'gene',
      description: 'Synthetic gene-shaped entity used for layout testing.',
    },
    {
      id: 'demo-protein-a',
      label: 'Demo protein A',
      kind: 'protein',
      description: 'Synthetic protein-shaped entity used for layout testing.',
    },
    {
      id: 'demo-pathway-1',
      label: 'Demo pathway 1',
      kind: 'pathway',
      description: 'Synthetic pathway entity with no biological interpretation.',
    },
    {
      id: 'demo-disease-x',
      label: 'Demo disease X',
      kind: 'disease',
      description: 'Synthetic disease-shaped entity used for layout testing.',
    },
    {
      id: 'demo-gene-b',
      label: 'Demo gene B',
      kind: 'gene',
      description: 'Second synthetic gene-shaped entity for comparison views.',
    },
    {
      id: 'demo-pathway-2',
      label: 'Demo pathway 2',
      kind: 'pathway',
      description: 'Second synthetic pathway entity with no scientific meaning.',
    },
    {
      id: 'demo-protein-b',
      label: 'Demo protein B',
      kind: 'protein',
      description: 'Second synthetic protein-shaped entity for graph branching.',
    },
  ],
  edges: [
    {
      id: 'demo-edge-1',
      source: 'demo-gene-a',
      target: 'demo-protein-a',
      label: 'synthetic mapping',
      evidence: demoEvidence,
    },
    {
      id: 'demo-edge-2',
      source: 'demo-protein-a',
      target: 'demo-pathway-1',
      label: 'synthetic membership',
      evidence: demoEvidence,
    },
    {
      id: 'demo-edge-3',
      source: 'demo-pathway-1',
      target: 'demo-disease-x',
      label: 'synthetic association',
      evidence: demoEvidence,
    },
    {
      id: 'demo-edge-4',
      source: 'demo-gene-b',
      target: 'demo-pathway-1',
      label: 'synthetic membership',
      evidence: demoEvidence,
    },
    {
      id: 'demo-edge-5',
      source: 'demo-gene-a',
      target: 'demo-pathway-2',
      label: 'synthetic membership',
      evidence: demoEvidence,
    },
    {
      id: 'demo-edge-6',
      source: 'demo-pathway-2',
      target: 'demo-protein-b',
      label: 'synthetic regulation',
      evidence: demoEvidence,
    },
    {
      id: 'demo-edge-7',
      source: 'demo-protein-b',
      target: 'demo-disease-x',
      label: 'synthetic association',
      evidence: demoEvidence,
    },
  ],
  paths: [
    {
      id: 'demo-path-a',
      rank: 1,
      nodeIds: ['demo-gene-a', 'demo-protein-a', 'demo-pathway-1', 'demo-disease-x'],
      illustrativeScore: 0.82,
      rationale: 'Shortest synthetic route with three demonstration edges.',
    },
    {
      id: 'demo-path-b',
      rank: 2,
      nodeIds: ['demo-gene-a', 'demo-pathway-2', 'demo-protein-b', 'demo-disease-x'],
      illustrativeScore: 0.71,
      rationale: 'Alternative synthetic route used to demonstrate path comparison.',
    },
  ],
}

export const demoNodeById = new Map(demoDataset.nodes.map((node) => [node.id, node]))
