import type { ApiEntity, ApiRelationship } from '../lib/api'
import { StatusNotice } from './StatusNotice'

interface VerifiedGraphInspectorProps {
  entity?: ApiEntity
  relationship?: ApiRelationship
  pathCount?: number
}

export function VerifiedGraphInspector({
  entity,
  relationship,
  pathCount = 0,
}: VerifiedGraphInspectorProps) {
  if (relationship) {
    return (
      <aside className="evidence-panel" aria-labelledby="graph-inspector-heading">
        <span className="eyebrow">Stored relationship</span>
        <h2 id="graph-inspector-heading" className="section-title mt-2">
          Relationship details
        </h2>
        <p className="mt-4 break-all text-sm font-bold">
          {relationship.source_entity_id} → {relationship.target_entity_id}
        </p>
        <dl className="evidence-list">
          <div>
            <dt>Relationship</dt>
            <dd>{relationship.relationship_type.replaceAll('_', ' ')}</dd>
          </div>
          <div>
            <dt>Original source</dt>
            <dd>{relationship.source}</dd>
          </div>
          <div>
            <dt>Source record</dt>
            <dd className="break-all">{relationship.source_identifier}</dd>
          </div>
          <div>
            <dt>Retrieved</dt>
            <dd>{formatDate(relationship.retrieved_at)}</dd>
          </div>
          <div>
            <dt>Candidate paths</dt>
            <dd>{pathCount}</dd>
          </div>
        </dl>
        {relationship.score_interpretation && (
          <StatusNotice tone="info" title="Source score interpretation" compact>
            {relationship.score_interpretation}
          </StatusNotice>
        )}
        <div className="mt-4 grid gap-3">
          {relationship.evidence.length === 0 ? (
            <StatusNotice tone="warning" title="No attached evidence records" compact>
              The backend returned this relationship without an evidence record.
            </StatusNotice>
          ) : (
            relationship.evidence.map((evidence) => (
              <article className="rounded-2xl bg-sage-50 p-4" key={evidence.source_record_id}>
                <strong className="text-xs uppercase tracking-wider text-sage-700">
                  {evidence.evidence_type.replaceAll('_', ' ')}
                </strong>
                <p className="mt-2 break-all text-xs text-ink-soft">
                  {evidence.source} · {evidence.source_record_id}
                </p>
                {evidence.summary && <p className="mt-2 text-sm leading-6">{evidence.summary}</p>}
              </article>
            ))
          )}
        </div>
      </aside>
    )
  }

  if (entity) {
    return (
      <aside className="evidence-panel" aria-labelledby="graph-inspector-heading">
        <span className="eyebrow">Verified entity</span>
        <h2 id="graph-inspector-heading" className="section-title mt-2">
          {entity.label}
        </h2>
        <p className="mt-2 break-all text-sm text-ink-soft">{entity.canonical_id}</p>
        <dl className="evidence-list">
          <div>
            <dt>Entity type</dt>
            <dd>{entity.entity_type}</dd>
          </div>
          <div>
            <dt>Original source</dt>
            <dd>{entity.source}</dd>
          </div>
          <div>
            <dt>Source record</dt>
            <dd className="break-all">{entity.source_identifier}</dd>
          </div>
          <div>
            <dt>Retrieved</dt>
            <dd>{formatDate(entity.retrieved_at)}</dd>
          </div>
        </dl>
        {entity.description && (
          <p className="text-sm leading-6 text-ink-soft">{entity.description}</p>
        )}
      </aside>
    )
  }

  return (
    <aside className="evidence-panel" aria-labelledby="graph-inspector-heading">
      <span className="eyebrow">Graph inspector</span>
      <h2 id="graph-inspector-heading" className="section-title mt-2">
        Select a verified node or edge
      </h2>
      <div className="evidence-empty">
        <span aria-hidden="true">❁</span>
        <p>The Cytoscape graph and keyboard-accessible lists select the same backend records.</p>
      </div>
    </aside>
  )
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString()
}
