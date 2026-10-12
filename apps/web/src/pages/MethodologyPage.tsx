import { Icon } from '../components/Icon'
import { StatusNotice } from '../components/StatusNotice'

const capabilityStatuses = [
  {
    name: 'React and FastAPI workflow',
    status: 'Implemented',
    detail:
      'Typed, runtime-validated health, readiness, knowledge, discovery, evidence, and research-assistant contracts are connected to the research workspace.',
  },
  {
    name: 'PostgreSQL evidence store',
    status: 'Implemented',
    detail:
      'Alembic-managed tables and SQLAlchemy repositories persist and reload entities, relationships, evidence records, publication links, and ingestion runs.',
  },
  {
    name: 'Open Targets adapter',
    status: 'Implemented · bounded scope',
    detail:
      'The validated GraphQL client ingests targets and associated diseases. It currently creates only the documented gene-associated-with-disease relationship type.',
  },
  {
    name: 'Europe PMC adapter',
    status: 'Implemented · bounded scope',
    detail:
      'The validated REST client retrieves publication metadata and abstracts as literature context. Search matches are not treated as proof of a relationship.',
  },
  {
    name: 'Research assistant',
    status: 'Partially implemented',
    detail:
      'Deterministic evidence summaries and the provider-neutral boundary work. No concrete external LLM provider adapter is implemented or configured.',
  },
  {
    name: 'Scientific validation',
    status: 'Unverified beyond regression scope',
    detail:
      'The three-case, same-source benchmark checks engineering reproducibility but cannot establish biological validity or ranking superiority.',
  },
] as const

export function MethodologyPage() {
  return (
    <div className="page-stack">
      <header className="methodology-hero">
        <div>
          <span className="eyebrow">
            <Icon name="leaf" className="h-3.5 w-3.5" /> About GeneGarden AI
          </span>
          <h1 className="page-title mt-5">Evidence grows best in the open.</h1>
          <p>
            GeneGarden AI is an educational research platform for investigating possible biomedical
            connections while preserving provenance and uncertainty.
          </p>
        </div>
        <div className="methodology-flower" aria-hidden="true">
          <span>✿</span>
          <i />
          <i />
          <i />
        </div>
      </header>

      <StatusNotice tone="warning" title="Research and education only">
        GeneGarden AI is not a diagnostic system, clinical decision-support tool, or substitute for
        expert review of primary literature.
      </StatusNotice>

      <section className="method-grid" aria-label="Methodology overview">
        <article>
          <span className="method-icon">01</span>
          <h2>Collect</h2>
          <p>
            Typed clients retrieve bounded target–disease information from Open Targets and
            publication metadata and abstracts from Europe PMC.
          </p>
        </article>
        <article>
          <span className="method-icon">02</span>
          <h2>Normalize</h2>
          <p>
            Identifiers, entity types, relationship semantics, source record identifiers, and
            retrieval dates are retained explicitly with evidence-level provenance.
          </p>
        </article>
        <article>
          <span className="method-icon">03</span>
          <h2>Connect</h2>
          <p>
            NetworkX constructs evidence-bearing graphs and runs documented path-finding and ranking
            strategies.
          </p>
        </article>
        <article>
          <span className="method-icon">04</span>
          <h2>Explain</h2>
          <p>
            Cytoscape.js views expose candidate paths, evidence records, missing coverage, and
            algorithm limitations.
          </p>
        </article>
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="card p-6 sm:p-8" aria-labelledby="sources-heading">
          <span className="eyebrow">Implemented data sources</span>
          <h2 id="sources-heading" className="section-title mt-2">
            Where persisted records come from
          </h2>
          <div className="source-list">
            <article>
              <span>OT</span>
              <div>
                <h3>Open Targets Platform</h3>
                <p>
                  The bounded GraphQL adapter retrieves target–disease associations, source-specific
                  scores, stable identifiers, and retrieval timestamps. Broader relationship types
                  are not implemented.
                </p>
                <a href="https://platform.opentargets.org/" target="_blank" rel="noreferrer">
                  Visit official source ↗
                </a>
              </div>
            </article>
            <article>
              <span>EP</span>
              <div>
                <h3>Europe PMC</h3>
                <p>
                  The bounded REST adapter retrieves publication metadata, identifiers, links, and
                  available abstracts. Literature search matches remain contextual records rather
                  than independently verified support for a claim.
                </p>
                <a href="https://europepmc.org/" target="_blank" rel="noreferrer">
                  Visit official source ↗
                </a>
              </div>
            </article>
          </div>
        </section>
        <section className="card p-6 sm:p-8" aria-labelledby="limits-heading">
          <span className="eyebrow">Known limitations</span>
          <h2 id="limits-heading" className="section-title mt-2">
            What the product must not hide
          </h2>
          <ul className="limitation-list">
            <li>Association does not establish causality or clinical relevance.</li>
            <li>Source coverage, update cadence, and identifier mapping may be incomplete.</li>
            <li>Graph rankings depend on edge definitions and scoring choices.</li>
            <li>Publication counts can reflect popularity and indexing bias.</li>
            <li>The current graph supports one relationship type and a small starter domain.</li>
            <li>The optional LLM provider boundary has no concrete provider implementation.</li>
            <li>Every result requires domain-expert review against primary sources.</li>
          </ul>
        </section>
      </div>

      <section className="card p-6 sm:p-8" aria-labelledby="integration-heading">
        <span className="eyebrow">Audited implementation boundary</span>
        <h2 id="integration-heading" className="section-title mt-2">
          Current implementation status
        </h2>
        <p className="mt-3 text-sm leading-6 text-ink-soft">
          These labels describe repository capabilities supported by code and automated tests.
          Deployment availability is checked separately through the health and database-readiness
          endpoints.
        </p>
        <div className="method-grid mt-6" aria-label="Capability implementation statuses">
          {capabilityStatuses.map((capability) => (
            <article key={capability.name}>
              <span className="eyebrow">{capability.status}</span>
              <h3 className="mt-3 text-sm font-extrabold">{capability.name}</h3>
              <p>{capability.detail}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
