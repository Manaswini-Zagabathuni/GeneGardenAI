export type NodeKind = 'gene' | 'protein' | 'pathway' | 'disease'

export interface KnowledgeNode {
  id: string
  label: string
  kind: NodeKind
  description: string
}

export interface EvidenceRecord {
  sourceLabel: string
  sourceType: 'demo-fixture' | 'open-targets' | 'europe-pmc'
  externalId?: string
  summary: string
  uncertainty: 'not-assessed' | 'low' | 'medium' | 'high'
  publications: readonly string[]
}

export interface KnowledgeEdge {
  id: string
  source: string
  target: string
  label: string
  evidence: EvidenceRecord
}

export interface CandidatePath {
  id: string
  rank: number
  nodeIds: readonly string[]
  illustrativeScore: number
  rationale: string
}

export interface DemoDataset {
  label: string
  description: string
  nodes: readonly KnowledgeNode[]
  edges: readonly KnowledgeEdge[]
  paths: readonly CandidatePath[]
}
