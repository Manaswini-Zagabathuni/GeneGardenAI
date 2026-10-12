import { useEffect, useState } from 'react'

import { Icon } from '../components/Icon'
import { Spinner } from '../components/Spinner'
import { StatusNotice } from '../components/StatusNotice'
import {
  explorePathEvidence,
  type ApiPathEvidenceView,
  type VerifiedDiscoverySession,
} from '../lib/api'

interface ComparisonViewProps {
  session: VerifiedDiscoverySession | null
}

export function ComparisonView({ session }: ComparisonViewProps) {
  const [evidenceState, setEvidenceState] = useState<{
    session: VerifiedDiscoverySession | null
    evidence: Record<string, ApiPathEvidenceView>
    errors: Record<string, string>
  }>({ session: null, evidence: {}, errors: {} })

  useEffect(() => {
    if (!session || session.result.paths.length === 0) return
    const controller = new AbortController()
    Promise.allSettled(
      session.result.paths.map(async (path) => ({
        pathId: path.path_id,
        evidence: await explorePathEvidence(session.request, path.path_id, controller.signal),
      })),
    ).then((outcomes) => {
      if (controller.signal.aborted) return
      const nextEvidence: Record<string, ApiPathEvidenceView> = {}
      const nextErrors: Record<string, string> = {}
      outcomes.forEach((outcome, index) => {
        const pathId = session.result.paths[index].path_id
        if (outcome.status === 'fulfilled') nextEvidence[pathId] = outcome.value.evidence
        else {
          nextErrors[pathId] =
            outcome.reason instanceof Error
              ? outcome.reason.message
              : 'Evidence details could not be loaded.'
        }
      })
      setEvidenceState({ session, evidence: nextEvidence, errors: nextErrors })
    })
    return () => controller.abort()
  }, [session])

  if (!session) {
    return (
      <div className="page-stack">
        <header className="page-header">
          <div>
            <span className="eyebrow">
              <Icon name="compare" className="h-3.5 w-3.5" /> Candidate comparison
            </span>
            <h1 className="page-title">Compare returned paths</h1>
          </div>
        </header>
        <StatusNotice tone="info" title="No discovery result to compare">
          Run a verified discovery query first. This view does not use demonstration candidates.
        </StatusNotice>
        <a className="primary-button w-fit" href="#discover">
          Open discovery
        </a>
      </div>
    )
  }

  const { result } = session
  const source = result.paths[0]?.nodes[0]
  const evidenceByPath = evidenceState.session === session ? evidenceState.evidence : {}
  const evidenceErrors = evidenceState.session === session ? evidenceState.errors : {}
  const loadingEvidence = result.paths.length > 0 && evidenceState.session !== session

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">
            <Icon name="compare" className="h-3.5 w-3.5" /> Candidate comparison
          </span>
          <h1 className="page-title">Compare returned paths</h1>
          <p>
            Inspect path structure, provenance, and the backend&apos;s ranking inputs side by side.
            The utility is a heuristic ordering value, not a probability or confidence estimate.
          </p>
        </div>
        <button className="secondary-button" type="button" onClick={() => window.print()}>
          Export view <span aria-hidden="true">↗</span>
        </button>
      </header>

      {result.paths.length === 0 ? (
        <StatusNotice tone="info" title="No paths returned">
          The verified query completed without candidates, so there is nothing to compare.
        </StatusNotice>
      ) : (
        <>
          <StatusNotice tone="warning" title="Heuristic ranking">
            Scores preserve the backend&apos;s actual components and assumptions. A multi-step path
            is an inference over reported relationships and does not establish causality.
          </StatusNotice>

          <section className="comparison-summary" aria-label="Comparison summary">
            <div>
              <span>Origin</span>
              <strong>{source?.label ?? session.request.source_id}</strong>
              <small>{source?.canonical_id ?? session.request.source_id}</small>
            </div>
            <span className="comparison-vine" aria-hidden="true">
              ••• ❀ •••
            </span>
            <div>
              <span>Returned candidates</span>
              <strong>{result.paths.length}</strong>
              <small>Backend-ranked paths</small>
            </div>
          </section>

          {loadingEvidence && (
            <StatusNotice tone="info" title="Loading supporting evidence">
              <Spinner label="Resolving path publications" />
            </StatusNotice>
          )}

          <section aria-labelledby="ranked-paths-heading">
            <div className="section-heading-row">
              <div>
                <span className="eyebrow">Backend-ranked candidates</span>
                <h2 id="ranked-paths-heading" className="section-title">
                  {result.paths.length} verified result{result.paths.length === 1 ? '' : 's'}
                </h2>
              </div>
              <span className="text-xs text-ink-soft">
                Ranking method: {result.paths[0]?.score.method}
              </span>
            </div>
            <div className="space-y-4">
              {result.paths.map((path, index) => {
                const evidence = evidenceByPath[path.path_id]
                return (
                  <article className="path-card items-start" key={path.path_id}>
                    <div className="path-rank">
                      <span>Rank</span>
                      <strong>{index + 1}</strong>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="path-nodes">
                        {path.nodes.map((node, nodeIndex) => (
                          <span key={node.canonical_id}>
                            <i className={`node-dot node-${node.entity_type}`} />
                            <b>{node.label}</b>
                            <small>{node.canonical_id}</small>
                            {nodeIndex < path.nodes.length - 1 && <em>→</em>}
                          </span>
                        ))}
                      </div>
                      <p className="mt-4 text-sm leading-6 text-ink-soft">
                        {path.score.interpretation}
                      </p>
                      <p className="mt-2 break-all text-xs leading-5 text-ink-soft">
                        Source records:{' '}
                        {[
                          ...new Set(
                            path.edges.flatMap((edge) =>
                              edge.relationships.flatMap((relationship) => [
                                relationship.source_identifier,
                                ...relationship.evidence.map((item) => item.source_record_id),
                              ]),
                            ),
                          ),
                        ].join(', ')}
                      </p>
                      <details className="mt-4">
                        <summary className="text-link cursor-pointer">
                          Inspect score components
                        </summary>
                        <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                          {path.score.components.map((component) => (
                            <div className="rounded-xl bg-sage-50 p-3" key={component.name}>
                              <dt className="font-bold capitalize">
                                {component.name.replaceAll('_', ' ')}
                              </dt>
                              <dd className="mt-1 text-ink-soft">
                                contribution {component.contribution} · weight {component.weight} ·
                                normalized {component.normalized_value ?? 'excluded'}
                              </dd>
                              <dd className="mt-2 leading-5">{component.explanation}</dd>
                            </div>
                          ))}
                        </dl>
                      </details>
                      {evidence && (
                        <div className="mt-4 rounded-xl bg-lavender-50 p-3 text-xs leading-5">
                          <strong>
                            {evidence.claim_scope === 'inferred_path'
                              ? 'Inferred multi-step path'
                              : 'Direct reported relationship'}
                          </strong>
                          <p className="mt-1 text-ink-soft">
                            {evidence.relationships.length} relationship claim
                            {evidence.relationships.length === 1 ? '' : 's'} ·{' '}
                            {evidence.publications.length} verified publication
                            {evidence.publications.length === 1 ? '' : 's'}
                          </p>
                          {evidence.publications.map((publication) => (
                            <a
                              className="text-link mt-2 flex w-fit"
                              href={publication.web_url}
                              target="_blank"
                              rel="noreferrer"
                              key={publication.citation_id}
                            >
                              {publication.title} ({publication.source_identifier})
                            </a>
                          ))}
                        </div>
                      )}
                      {evidenceErrors[path.path_id] && (
                        <p className="mt-3 text-xs text-clay" role="alert">
                          Evidence unavailable: {evidenceErrors[path.path_id]}
                        </p>
                      )}
                    </div>
                    <div className="path-score">
                      <span>Ranking utility</span>
                      <strong>{path.score.ranking_utility.toFixed(3)}</strong>
                      <small>Not probability</small>
                    </div>
                  </article>
                )
              })}
            </div>
          </section>

          <section className="card overflow-hidden" aria-labelledby="comparison-table-heading">
            <div className="card-header">
              <div>
                <span className="eyebrow">Method detail</span>
                <h2 id="comparison-table-heading" className="section-title mt-2">
                  Path comparison matrix
                </h2>
              </div>
            </div>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Candidate</th>
                    <th>Edges</th>
                    <th>Source records</th>
                    <th>Publications</th>
                    <th>Uncertainty</th>
                    <th>Claim scope</th>
                  </tr>
                </thead>
                <tbody>
                  {result.paths.map((path, index) => {
                    const evidence = evidenceByPath[path.path_id]
                    const sourceRecords = new Set(
                      path.edges.flatMap((edge) =>
                        edge.relationships.flatMap((relationship) => [
                          relationship.source_identifier,
                          ...relationship.evidence.map((item) => item.source_record_id),
                        ]),
                      ),
                    )
                    return (
                      <tr key={path.path_id}>
                        <td>Path {index + 1}</td>
                        <td>{path.edges.length}</td>
                        <td>{sourceRecords.size}</td>
                        <td>{evidence ? evidence.publications.length : 'Unavailable'}</td>
                        <td>{evidence ? evidence.uncertainty.length : 'Unavailable'}</td>
                        <td>
                          {evidence
                            ? evidence.claim_scope.replaceAll('_', ' ')
                            : path.edges.length > 1
                              ? 'inferred path'
                              : 'direct relationship'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
