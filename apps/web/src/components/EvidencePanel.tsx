import type { KnowledgeEdge, KnowledgeNode } from '../types/domain'
import { Icon } from './Icon'
import { StatusNotice } from './StatusNotice'

interface EvidencePanelProps {
  edge?: KnowledgeEdge
  sourceNode?: KnowledgeNode
  targetNode?: KnowledgeNode
}

export function EvidencePanel({ edge, sourceNode, targetNode }: EvidencePanelProps) {
  if (!edge || !sourceNode || !targetNode) {
    return (
      <aside className="evidence-panel" aria-labelledby="evidence-heading">
        <span className="eyebrow">Evidence inspector</span>
        <h2 id="evidence-heading" className="section-title mt-2">
          Select a relationship
        </h2>
        <div className="evidence-empty">
          <span aria-hidden="true">❁</span>
          <p>
            Choose an edge in the graph or the accessible relationship list to inspect its
            provenance.
          </p>
        </div>
      </aside>
    )
  }

  const isDemo = edge.evidence.sourceType === 'demo-fixture'

  return (
    <aside className="evidence-panel" aria-labelledby="evidence-heading">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <span className="eyebrow">Evidence inspector</span>
          <h2 id="evidence-heading" className="section-title mt-2">
            Relationship details
          </h2>
        </div>
        {isDemo && <span className="demo-pill">Synthetic demo</span>}
      </div>
      <div className="relationship-route mt-6">
        <div>
          <span className={`node-dot node-${sourceNode.kind}`} />
          <strong>{sourceNode.label}</strong>
          <small>{sourceNode.kind}</small>
        </div>
        <span className="relationship-line">
          <span>{edge.label}</span>
        </span>
        <div>
          <span className={`node-dot node-${targetNode.kind}`} />
          <strong>{targetNode.label}</strong>
          <small>{targetNode.kind}</small>
        </div>
      </div>
      <dl className="evidence-list">
        <div>
          <dt>Source</dt>
          <dd>{edge.evidence.sourceLabel}</dd>
        </div>
        <div>
          <dt>Source type</dt>
          <dd>{edge.evidence.sourceType.replace('-', ' ')}</dd>
        </div>
        <div>
          <dt>Uncertainty</dt>
          <dd>{edge.evidence.uncertainty.replace('-', ' ')}</dd>
        </div>
        <div>
          <dt>Publications</dt>
          <dd>{edge.evidence.publications.length || 'None attached'}</dd>
        </div>
      </dl>
      <div className="rounded-2xl bg-cream-100 p-4 text-sm leading-6 text-ink-soft">
        <div className="mb-2 flex items-center gap-2 font-bold text-ink">
          <Icon name="about" className="h-4 w-4 text-lavender-700" /> Evidence summary
        </div>
        {edge.evidence.summary}
      </div>
      {isDemo && (
        <div className="mt-4">
          <StatusNotice tone="warning" title="Not scientific evidence" compact>
            This relationship has no publication citation or confidence estimate and must not be
            interpreted biologically.
          </StatusNotice>
        </div>
      )}
    </aside>
  )
}
