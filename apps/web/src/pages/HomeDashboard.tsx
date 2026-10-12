import { useState } from 'react'

import type { ApiStatus } from '../components/AppShell'
import { Icon } from '../components/Icon'
import { Spinner } from '../components/Spinner'
import { StatusNotice } from '../components/StatusNotice'
import {
  createGeneDiscoveryRequest,
  discoverPaths,
  isSupportedGeneId,
  type VerifiedDiscoverySession,
} from '../lib/api'

type SearchState = 'idle' | 'loading' | 'success' | 'empty' | 'error'

interface HomeDashboardProps {
  apiStatus: ApiStatus
  session: VerifiedDiscoverySession | null
  onDiscovery: (session: VerifiedDiscoverySession) => void
}

export function HomeDashboard({ apiStatus, session, onDiscovery }: HomeDashboardProps) {
  const [query, setQuery] = useState(session?.request.source_id ?? '')
  const [searchState, setSearchState] = useState<SearchState>('idle')
  const [searchError, setSearchError] = useState('')

  async function handleSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const sourceId = query.trim()
    if (!isSupportedGeneId(sourceId)) {
      setSearchState('error')
      setSearchError('Use a canonical Ensembl gene identifier such as ensembl:ENSG00000141510.')
      return
    }

    const request = createGeneDiscoveryRequest(sourceId)
    setSearchState('loading')
    setSearchError('')
    try {
      const result = await discoverPaths(request)
      const nextSession = { request, result }
      onDiscovery(nextSession)
      if (result.paths.length === 0) {
        setSearchState('empty')
        return
      }
      setSearchState('success')
      window.location.hash = 'discover'
    } catch (error) {
      setSearchState('error')
      setSearchError(error instanceof Error ? error.message : 'The discovery request failed.')
    }
  }

  return (
    <div className="page-stack">
      <section className="hero-card">
        <div className="hero-bloom hero-bloom-one" aria-hidden="true" />
        <div className="hero-bloom hero-bloom-two" aria-hidden="true" />
        <div className="relative z-10 max-w-3xl">
          <span className="eyebrow">
            <Icon name="sparkle" className="h-3.5 w-3.5" /> Evidence-aware exploration
          </span>
          <h1 className="page-title mt-5 max-w-2xl">
            Grow a clearer view of biological connections.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-ink-soft sm:text-lg">
            Trace potential paths among genes, proteins, pathways, and diseases while keeping
            provenance, uncertainty, and method limits visible.
          </p>

          <form className="research-search mt-8" onSubmit={handleSearch} role="search">
            <Icon name="search" className="h-5 w-5 shrink-0 text-sage-700" />
            <label className="sr-only" htmlFor="home-research-search">
              Enter a canonical Ensembl gene identifier
            </label>
            <input
              id="home-research-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="ensembl:ENSG00000141510"
              type="search"
              aria-describedby="home-search-help"
            />
            <button
              className="primary-button"
              type="submit"
              disabled={apiStatus !== 'online' || searchState === 'loading'}
            >
              {searchState === 'loading' ? (
                <Spinner label="Retrieving verified paths" />
              ) : (
                <>
                  Explore <Icon name="arrow" className="h-4 w-4" />
                </>
              )}
            </button>
          </form>
          <p id="home-search-help" className="mt-3 text-xs text-ink-soft">
            Queries the verified backend. The source gene must already exist in the ingested graph.
          </p>

          {searchState === 'error' && (
            <div className="mt-4 max-w-xl" aria-live="polite">
              <StatusNotice tone="error" title="Discovery search failed" compact>
                {searchError}
              </StatusNotice>
            </div>
          )}
          {searchState === 'empty' && (
            <div className="mt-4 max-w-xl" aria-live="polite">
              <StatusNotice tone="info" title="No paths returned" compact>
                The request completed successfully, but no candidate path matched the bounded query.
                No synthetic result was substituted.
              </StatusNotice>
            </div>
          )}
        </div>
      </section>

      {apiStatus === 'offline' && (
        <StatusNotice tone="warning" title="Verified data services are unavailable">
          The local API cannot be reached, so biomedical discovery is disabled. GeneGarden will not
          substitute synthetic relationships.
        </StatusNotice>
      )}

      <section aria-labelledby="recent-heading">
        <div className="section-heading-row">
          <div>
            <span className="eyebrow">Workspace</span>
            <h2 id="recent-heading" className="section-title">
              Current exploration
            </h2>
          </div>
          <a className="text-link" href="#discover">
            Open discovery <Icon name="arrow" className="h-4 w-4" />
          </a>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {session ? (
            <a className="exploration-card text-left" href="#discover">
              <span className="flower-index" aria-hidden="true">
                ✿
              </span>
              <span className="status-chip status-chip-success">Backend result</span>
              <h3>{session.request.source_id}</h3>
              <p>
                {session.result.paths.length} returned path
                {session.result.paths.length === 1 ? '' : 's'} ·{' '}
                {session.result.graph_relationship_count} graph relationships
              </p>
              <span className="mt-6 inline-flex items-center gap-2 text-xs font-bold text-sage-700">
                Reopen workspace <Icon name="arrow" className="h-4 w-4" />
              </span>
            </a>
          ) : (
            <div className="exploration-card text-left">
              <span className="flower-index" aria-hidden="true">
                ❀
              </span>
              <span className="status-chip status-chip-neutral">No query yet</span>
              <h3>Your verified exploration will appear here</h3>
              <p>Run a canonical gene query to begin.</p>
            </div>
          )}
          <a className="new-exploration-card" href="#discover">
            <span className="grid h-11 w-11 place-items-center rounded-full bg-lavender-100 text-xl text-lavender-700">
              +
            </span>
            <span>
              <strong>Configure an exploration</strong>
              <small>Set target and bounded-query limits</small>
            </span>
          </a>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3" aria-label="Product principles">
        {[
          [
            '01',
            'Evidence stays attached',
            'Source identifiers and uncertainty travel with every verified relationship.',
          ],
          [
            '02',
            'Methods stay inspectable',
            'Candidate paths expose their algorithm and ranking inputs.',
          ],
          [
            '03',
            'Absence stays honest',
            'Unavailable evidence is never replaced with generated biomedical claims.',
          ],
        ].map(([number, title, copy]) => (
          <article className="principle-card" key={number}>
            <span>{number}</span>
            <h3>{title}</h3>
            <p>{copy}</p>
          </article>
        ))}
      </section>
    </div>
  )
}
