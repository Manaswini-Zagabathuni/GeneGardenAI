import { useEffect, useMemo, useState } from 'react'

import { Icon } from '../components/Icon'
import { KnowledgeGraph } from '../components/KnowledgeGraph'
import { Spinner } from '../components/Spinner'
import { StatusNotice } from '../components/StatusNotice'
import { VerifiedEvidenceExplorer } from '../components/VerifiedEvidenceExplorer'
import { VerifiedGraphInspector } from '../components/VerifiedGraphInspector'
import {
  askResearchAssistant,
  createGeneDiscoveryRequest,
  discoverPaths,
  explorePathEvidence,
  isSupportedGeneId,
  type ApiPathEvidenceView,
  type AssistantAnswer,
  type DiscoveryRequest,
  type VerifiedDiscoverySession,
} from '../lib/api'
import { buildVerifiedGraph } from '../lib/discoveryGraph'

interface DiscoveryWorkspaceProps {
  initialSourceId?: string
  apiOnline: boolean
  session: VerifiedDiscoverySession | null
  onSessionChange: (session: VerifiedDiscoverySession | null) => void
}

type RequestStatus = 'idle' | 'loading' | 'success' | 'empty' | 'error'
type Selection = { kind: 'entity' | 'relationship'; id: string } | null
interface EvidenceState {
  session: VerifiedDiscoverySession | null
  pathId: string
  data: ApiPathEvidenceView | null
  error: string
}

export function DiscoveryWorkspace({
  initialSourceId,
  apiOnline,
  session,
  onSessionChange,
}: DiscoveryWorkspaceProps) {
  const [sourceId, setSourceId] = useState(session?.request.source_id ?? initialSourceId ?? '')
  const [targetId, setTargetId] = useState(session?.request.target_id ?? '')
  const [maxPathLength, setMaxPathLength] = useState(session?.request.max_path_length ?? 3)
  const [resultCount, setResultCount] = useState(session?.request.result_count ?? 10)
  const [requestStatus, setRequestStatus] = useState<RequestStatus>(
    session ? (session.result.paths.length ? 'success' : 'empty') : 'idle',
  )
  const [requestError, setRequestError] = useState('')
  const [selectedPathId, setSelectedPathId] = useState(session?.result.paths[0]?.path_id ?? '')
  const [selection, setSelection] = useState<Selection>(null)
  const [entityFilter, setEntityFilter] = useState('')
  const [evidenceState, setEvidenceState] = useState<EvidenceState>({
    session: null,
    pathId: '',
    data: null,
    error: '',
  })
  const [question, setQuestion] = useState('')
  const [assistantAnswer, setAssistantAnswer] = useState<AssistantAnswer | null>(null)
  const [assistantLoading, setAssistantLoading] = useState(false)
  const [assistantError, setAssistantError] = useState('')

  useEffect(() => {
    if (!session || !selectedPathId) return
    if (!session.result.paths.some((path) => path.path_id === selectedPathId)) return
    const controller = new AbortController()
    explorePathEvidence(session.request, selectedPathId, controller.signal)
      .then((data) => setEvidenceState({ session, pathId: selectedPathId, data, error: '' }))
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setEvidenceState({
            session,
            pathId: selectedPathId,
            data: null,
            error: messageFor(error, 'Evidence details could not be loaded.'),
          })
        }
      })
    return () => controller.abort()
  }, [selectedPathId, session])

  const result = session?.result ?? null
  const graph = useMemo(
    () => buildVerifiedGraph(result?.paths ?? [], selectedPathId),
    [result, selectedPathId],
  )
  const selectedPath = result?.paths.find((path) => path.path_id === selectedPathId)
  const selectedEntity =
    selection?.kind === 'entity'
      ? graph.entities.find((entity) => entity.canonical_id === selection.id)
      : undefined
  const selectedRelationship =
    selection?.kind === 'relationship'
      ? graph.relationships.find((item) => item.canonical_key === selection.id)
      : undefined
  const evidenceIsCurrent =
    evidenceState.session === session && evidenceState.pathId === selectedPathId
  const pathEvidence = evidenceIsCurrent ? evidenceState.data : null
  const evidenceError = evidenceIsCurrent ? evidenceState.error : ''
  const evidenceLoading = Boolean(session && selectedPathId && !evidenceIsCurrent)
  const matchingEntities = graph.entities.filter((entity) => {
    const query = entityFilter.trim().toLowerCase()
    return (
      !query ||
      entity.label.toLowerCase().includes(query) ||
      entity.canonical_id.toLowerCase().includes(query)
    )
  })

  async function runDiscovery() {
    const normalizedSource = sourceId.trim()
    if (!isSupportedGeneId(normalizedSource)) {
      setRequestError('Use a canonical Ensembl gene identifier such as ensembl:ENSG00000141510.')
      setRequestStatus('error')
      return
    }
    const request: DiscoveryRequest = {
      ...createGeneDiscoveryRequest(normalizedSource),
      ...(targetId.trim() ? { target_id: targetId.trim() } : {}),
      max_path_length: maxPathLength,
      result_count: resultCount,
    }
    setRequestStatus('loading')
    setRequestError('')
    setAssistantAnswer(null)
    setAssistantError('')
    try {
      const discoveryResult = await discoverPaths(request)
      onSessionChange({ request, result: discoveryResult })
      const firstPathId = discoveryResult.paths[0]?.path_id ?? ''
      setSelectedPathId(firstPathId)
      setSelection(
        discoveryResult.paths[0]?.nodes[0]
          ? { kind: 'entity', id: discoveryResult.paths[0].nodes[0].canonical_id }
          : null,
      )
      setRequestStatus(discoveryResult.paths.length ? 'success' : 'empty')
    } catch (error) {
      onSessionChange(null)
      setRequestError(messageFor(error, 'The discovery query could not be completed.'))
      setRequestStatus('error')
    }
  }

  function selectPath(pathId: string) {
    setSelectedPathId(pathId)
    setSelection(null)
    setAssistantAnswer(null)
    setAssistantError('')
  }

  async function askAboutPath() {
    if (!session || !selectedPathId || !question.trim()) return
    setAssistantLoading(true)
    setAssistantError('')
    try {
      setAssistantAnswer(
        await askResearchAssistant(question.trim(), session.request, selectedPathId),
      )
    } catch (error) {
      setAssistantError(messageFor(error, 'The assistant could not answer.'))
    } finally {
      setAssistantLoading(false)
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">
            <Icon name="discovery" className="h-3.5 w-3.5" /> Verified discovery workspace
          </span>
          <h1 className="page-title">Trace an ingested connection</h1>
          <p>
            Query the bounded FastAPI discovery engine and inspect only relationships returned with
            their stored source records and evidence metadata.
          </p>
        </div>
        <span className="status-chip status-chip-success">Verified records only</span>
      </header>

      {!apiOnline && (
        <StatusNotice tone="warning" title="Verified API unavailable">
          Discovery is disabled because the API health check failed. No synthetic result will be
          substituted.
        </StatusNotice>
      )}

      <section className="verified-lab" aria-labelledby="verified-query-heading">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <span className="eyebrow">Research setup</span>
            <h2 id="verified-query-heading" className="section-title mt-2">
              Bounded gene discovery
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-soft">
              The source must be an ingested canonical Ensembl gene ID. An optional target must be
              another canonical identifier already stored by the backend.
            </p>
          </div>
          <span className="status-chip status-chip-neutral">No synthetic fallback</span>
        </div>
        <div className="verified-query-grid mt-5">
          <label>
            <span>Source gene ID</span>
            <input
              value={sourceId}
              onChange={(event) => setSourceId(event.target.value)}
              placeholder="ensembl:ENSG00000141510"
              aria-describedby="source-id-help"
            />
            <small id="source-id-help">Canonical format: ensembl:ENSG followed by 11 digits</small>
          </label>
          <label>
            <span>Target canonical ID (optional)</span>
            <input
              value={targetId}
              onChange={(event) => setTargetId(event.target.value)}
              placeholder="mondo:MONDO_0000001"
            />
          </label>
          <label>
            <span>Maximum edges</span>
            <select
              value={maxPathLength}
              onChange={(event) => setMaxPathLength(Number(event.target.value))}
            >
              {[1, 2, 3, 4].map((value) => (
                <option value={value} key={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Result limit</span>
            <select
              value={resultCount}
              onChange={(event) => setResultCount(Number(event.target.value))}
            >
              {[5, 10, 15, 25].map((value) => (
                <option value={value} key={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <button
            className="primary-button"
            type="button"
            onClick={runDiscovery}
            disabled={!apiOnline || requestStatus === 'loading'}
          >
            {requestStatus === 'loading' ? <Spinner label="Retrieving paths" /> : 'Discover paths'}
          </button>
        </div>
        {requestStatus === 'error' && (
          <div className="mt-4">
            <StatusNotice tone="error" title="Discovery request failed" compact>
              {requestError}
            </StatusNotice>
          </div>
        )}
        {requestStatus === 'empty' && (
          <div className="mt-4">
            <StatusNotice tone="info" title="No paths returned" compact>
              The bounded query completed successfully, but the backend returned no candidate paths.
            </StatusNotice>
          </div>
        )}
      </section>

      {result && result.paths.length > 0 && (
        <>
          {result.warnings.length > 0 && (
            <StatusNotice tone="warning" title="Backend query warnings">
              <ul className="list-disc space-y-1 pl-5">
                {result.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </StatusNotice>
          )}
          <section aria-labelledby="candidate-paths-heading">
            <div className="section-heading-row">
              <div>
                <span className="eyebrow">Backend-ranked candidates</span>
                <h2 id="candidate-paths-heading" className="section-title">
                  {result.paths.length} returned path{result.paths.length === 1 ? '' : 's'}
                </h2>
              </div>
              <a className="text-link" href="#compare">
                Compare returned paths <Icon name="arrow" className="h-4 w-4" />
              </a>
            </div>
            <div className="flex flex-wrap gap-2" aria-label="Verified candidate paths">
              {result.paths.map((path, index) => (
                <button
                  className={`secondary-button ${selectedPathId === path.path_id ? 'selected' : ''}`}
                  type="button"
                  key={path.path_id}
                  aria-pressed={selectedPathId === path.path_id}
                  onClick={() => selectPath(path.path_id)}
                >
                  Path {index + 1} · {path.edges.length} edge{path.edges.length === 1 ? '' : 's'} ·{' '}
                  utility {path.score.ranking_utility.toFixed(3)}
                </button>
              ))}
            </div>
          </section>

          <div className="workspace-grid">
            <section className="graph-panel" aria-labelledby="graph-heading">
              <div className="graph-toolbar">
                <div>
                  <span className="eyebrow">Interactive verified network</span>
                  <h2 id="graph-heading" className="section-title mt-2">
                    Returned path graph
                  </h2>
                </div>
                <div className="legend" aria-label="Node legend">
                  {(['gene', 'protein', 'pathway', 'disease'] as const).map((kind) => (
                    <span key={kind}>
                      <i className={`node-dot node-${kind}`} />
                      {kind}
                    </span>
                  ))}
                </div>
              </div>
              <KnowledgeGraph
                elements={graph.elements}
                state={graph.elements.length ? 'ready' : 'empty'}
                selectedId={selection?.id}
                onNodeSelect={(id) => setSelection({ kind: 'entity', id })}
                onEdgeSelect={(id) => setSelection({ kind: 'relationship', id })}
                ariaLabel="Interactive graph of verified discovery paths"
                emptyMessage="The backend returned no graph elements."
              />
              <div className="accessible-graph-controls">
                <div>
                  <label htmlFor="verified-entity-filter">Keyboard-accessible entity list</label>
                  <div className="mini-search">
                    <Icon name="search" className="h-4 w-4" />
                    <input
                      id="verified-entity-filter"
                      value={entityFilter}
                      onChange={(event) => setEntityFilter(event.target.value)}
                      placeholder="Filter returned entities"
                    />
                  </div>
                  <div className="entity-button-list">
                    {matchingEntities.map((entity) => (
                      <button
                        className={selection?.id === entity.canonical_id ? 'selected' : ''}
                        onClick={() => setSelection({ kind: 'entity', id: entity.canonical_id })}
                        key={entity.canonical_id}
                        type="button"
                      >
                        <span className={`node-dot node-${entity.entity_type}`} />
                        {entity.label} · {entity.canonical_id}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <span>Keyboard-accessible relationship list</span>
                  <div className="edge-button-list">
                    {graph.relationships.map((relationship) => (
                      <button
                        className={selection?.id === relationship.canonical_key ? 'selected' : ''}
                        onClick={() =>
                          setSelection({ kind: 'relationship', id: relationship.canonical_key })
                        }
                        key={relationship.canonical_key}
                        type="button"
                      >
                        {relationship.source_entity_id} <span>→</span>{' '}
                        {relationship.target_entity_id}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </section>
            <VerifiedGraphInspector
              entity={selectedEntity}
              relationship={selectedRelationship}
              pathCount={
                selectedRelationship
                  ? graph.pathIdsByRelationship.get(selectedRelationship.canonical_key)?.length
                  : 0
              }
            />
          </div>

          {selectedPath && <PathScoreBreakdown path={selectedPath} />}

          {evidenceLoading && (
            <StatusNotice tone="info" title="Loading path evidence">
              <Spinner label="Resolving source records and publications" />
            </StatusNotice>
          )}
          {evidenceError && (
            <StatusNotice tone="error" title="Evidence request failed">
              {evidenceError}
            </StatusNotice>
          )}
          {pathEvidence && (
            <div className="verified-results-grid">
              <VerifiedEvidenceExplorer evidence={pathEvidence} />
              <section className="evidence-panel" aria-labelledby="assistant-heading">
                <span className="eyebrow">Optional research assistant</span>
                <h2 id="assistant-heading" className="section-title mt-2">
                  Ask about this path
                </h2>
                <p className="mt-2 text-sm leading-6 text-ink-soft">
                  Without an LLM provider, GeneGarden returns a deterministic evidence summary. It
                  never adds graph edges.
                </p>
                <label className="mt-5 block text-sm font-bold">
                  Question
                  <textarea
                    className="research-textarea"
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="What does the retrieved evidence support?"
                    maxLength={1000}
                  />
                </label>
                <button
                  className="primary-button mt-4"
                  type="button"
                  onClick={askAboutPath}
                  disabled={!question.trim() || assistantLoading}
                >
                  {assistantLoading ? <Spinner label="Grounding answer" /> : 'Summarize evidence'}
                </button>
                {assistantError && (
                  <div className="mt-4">
                    <StatusNotice tone="error" title="Assistant request failed" compact>
                      {assistantError}
                    </StatusNotice>
                  </div>
                )}
                {assistantAnswer && (
                  <div className="mt-5 grid gap-3">
                    <span className="status-chip status-chip-neutral w-fit">
                      {assistantAnswer.mode.replace('_', ' ')}
                    </span>
                    {assistantAnswer.claims.map((claim) => (
                      <article
                        className="rounded-2xl bg-sage-50 p-4"
                        key={`${claim.category}-${claim.text}`}
                      >
                        <strong className="text-xs uppercase tracking-wider text-sage-700">
                          {claim.category.replaceAll('_', ' ')}
                        </strong>
                        <p className="mt-2 text-sm leading-6">{claim.text}</p>
                        {claim.citation_ids.length > 0 && (
                          <small className="mt-2 block break-all text-ink-soft">
                            Sources: {claim.citation_ids.join(', ')}
                          </small>
                        )}
                      </article>
                    ))}
                    {assistantAnswer.limitations.map((limitation) => (
                      <p className="text-xs leading-5 text-ink-soft" key={limitation}>
                        {limitation}
                      </p>
                    ))}
                  </div>
                )}
              </section>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function PathScoreBreakdown({
  path,
}: {
  path: NonNullable<VerifiedDiscoverySession['result']['paths'][number]>
}) {
  return (
    <section className="card p-5 sm:p-6" aria-labelledby="score-heading">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <span className="eyebrow">Transparent ranking</span>
          <h2 id="score-heading" className="section-title mt-2">
            Path utility {path.score.ranking_utility.toFixed(6)}
          </h2>
        </div>
        <span className="status-chip status-chip-neutral">Not probability or confidence</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-ink-soft">{path.score.interpretation}</p>
      <div className="score-component-grid mt-5">
        {path.score.components.map((component) => (
          <article key={component.name}>
            <strong>{component.name.replaceAll('_', ' ')}</strong>
            <dl>
              <div>
                <dt>Raw</dt>
                <dd>{component.raw_value ?? 'Unavailable'}</dd>
              </div>
              <div>
                <dt>Normalized</dt>
                <dd>{component.normalized_value ?? 'Excluded'}</dd>
              </div>
              <div>
                <dt>Weight</dt>
                <dd>{component.weight}</dd>
              </div>
              <div>
                <dt>Contribution</dt>
                <dd>{component.contribution}</dd>
              </div>
            </dl>
            <p>{component.explanation}</p>
          </article>
        ))}
      </div>
      {path.limitations.length > 0 && (
        <ul className="limitation-list">
          {path.limitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      )}
    </section>
  )
}

function messageFor(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}
