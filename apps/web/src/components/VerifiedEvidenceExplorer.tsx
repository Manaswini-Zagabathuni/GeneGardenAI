import type { ApiPathEvidenceView } from '../lib/api'
import { StatusNotice } from './StatusNotice'

interface VerifiedEvidenceExplorerProps {
  evidence: ApiPathEvidenceView
}

export function VerifiedEvidenceExplorer({ evidence }: VerifiedEvidenceExplorerProps) {
  return (
    <section className="evidence-panel" aria-labelledby="verified-evidence-heading">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <span className="eyebrow">Verified-source evidence</span>
          <h2 id="verified-evidence-heading" className="section-title mt-2">
            Claim-level provenance
          </h2>
        </div>
        <span className="status-chip status-chip-neutral">
          {evidence.claim_scope === 'inferred_path' ? 'Inferred path' : 'Direct relationship'}
        </span>
      </div>

      {evidence.claim_scope === 'inferred_path' && (
        <div className="mt-4">
          <StatusNotice tone="warning" title="Hypothesis, not a reported causal chain" compact>
            Each edge is stored evidence, but their multi-step combination is an algorithmic
            inference.
          </StatusNotice>
        </div>
      )}

      <div className="mt-5 grid gap-4">
        {evidence.relationships.map((item) => (
          <article
            className="rounded-2xl border border-sage-200 bg-cream-50 p-4"
            key={item.claim_id}
          >
            <p className="text-sm font-bold text-ink">
              {item.source_entity.label} <span className="text-ink-soft">→</span>{' '}
              {item.target_entity.label}
            </p>
            <p className="mt-1 break-all text-xs text-ink-soft">
              {item.source_entity.canonical_id} · {item.relationship.relationship_type} ·{' '}
              {item.target_entity.canonical_id}
            </p>
            <dl className="evidence-list">
              <div>
                <dt>Direction</dt>
                <dd>{item.direction}</dd>
              </div>
              <div>
                <dt>Original source</dt>
                <dd>{item.relationship.source}</dd>
              </div>
              <div>
                <dt>Source identifier</dt>
                <dd className="break-all">{item.relationship.source_identifier}</dd>
              </div>
              <div>
                <dt>Conflict</dt>
                <dd>{item.conflict_status.replace('_', ' ')}</dd>
              </div>
            </dl>
            {item.evidence_items.map((evidenceItem) => (
              <div
                className="mt-3 rounded-xl bg-sage-50 p-3 text-sm"
                key={evidenceItem.evidence_id}
              >
                <strong>{evidenceItem.record.evidence_type.replaceAll('_', ' ')}</strong>
                <p className="mt-1 leading-6 text-ink-soft">{evidenceItem.interpretation}</p>
                <small className="mt-1 block break-all text-ink-soft">
                  {evidenceItem.record.source} · {evidenceItem.record.source_record_id}
                </small>
                {evidenceItem.missing_publication_ids.length > 0 && (
                  <p className="mt-2 text-xs text-clay">
                    Unresolved publication IDs: {evidenceItem.missing_publication_ids.join(', ')}
                  </p>
                )}
              </div>
            ))}
          </article>
        ))}
      </div>

      <div className="mt-5">
        <h3 className="text-sm font-bold">Verified publication metadata</h3>
        {evidence.publications.length === 0 ? (
          <p className="mt-2 text-sm text-ink-soft">
            No publication metadata is linked to this path.
          </p>
        ) : (
          <ul className="mt-3 grid gap-3">
            {evidence.publications.map((publication) => (
              <li className="rounded-2xl bg-lavender-50 p-4" key={publication.citation_id}>
                <a
                  className="font-bold text-lavender-700 underline decoration-lavender-300 underline-offset-4"
                  href={publication.web_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {publication.title}
                </a>
                <p className="mt-1 text-xs text-ink-soft">
                  {publication.source_identifier}
                  {publication.publication_year ? ` · ${publication.publication_year}` : ''}
                </p>
                {publication.abstract && (
                  <details className="mt-3 text-sm leading-6 text-ink-soft">
                    <summary className="cursor-pointer font-bold text-ink">
                      Available abstract
                    </summary>
                    <p className="mt-2">{publication.abstract}</p>
                  </details>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {evidence.uncertainty.length > 0 && (
        <div className="mt-5">
          <StatusNotice tone="warning" title="Uncertainty and limits" compact>
            <ul className="list-disc space-y-1 pl-5">
              {evidence.uncertainty.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </StatusNotice>
        </div>
      )}
    </section>
  )
}
