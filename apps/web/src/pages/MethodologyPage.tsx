import { Icon } from '../components/Icon'
import { StatusNotice } from '../components/StatusNotice'

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
            Typed clients will retrieve structured target–disease information from Open Targets and
            publication metadata from Europe PMC.
          </p>
        </article>
        <article>
          <span className="method-icon">02</span>
          <h2>Normalize</h2>
          <p>
            Identifiers, entity types, relationship semantics, source versions, and retrieval dates
            will be retained explicitly.
          </p>
        </article>
        <article>
          <span className="method-icon">03</span>
          <h2>Connect</h2>
          <p>
            NetworkX will construct evidence-bearing graphs and run documented path-finding and
            ranking strategies.
          </p>
        </article>
        <article>
          <span className="method-icon">04</span>
          <h2>Explain</h2>
          <p>
            Cytoscape.js views will expose candidate paths, evidence records, missing coverage, and
            algorithm limitations.
          </p>
        </article>
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <section className="card p-6 sm:p-8" aria-labelledby="sources-heading">
          <span className="eyebrow">Planned data sources</span>
          <h2 id="sources-heading" className="section-title mt-2">
            Where verified records will come from
          </h2>
          <div className="source-list">
            <article>
              <span>OT</span>
              <div>
                <h3>Open Targets Platform</h3>
                <p>
                  Structured target–disease associations and supporting evidence. Integration is
                  configured but not implemented.
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
                  Publication metadata and stable identifiers. Integration is configured but not
                  implemented.
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
            <li>Every result requires domain-expert review against primary sources.</li>
          </ul>
        </section>
      </div>

      <section className="card p-6 sm:p-8" aria-labelledby="integration-heading">
        <span className="eyebrow">Integration boundary</span>
        <h2 id="integration-heading" className="section-title mt-2">
          Current implementation status
        </h2>
        <div className="integration-flow">
          <span>
            React research workspace<small>Implemented</small>
          </span>
          <i>→</i>
          <span>
            FastAPI contracts<small>Health only</small>
          </span>
          <i>→</i>
          <span>
            Source adapters<small>Not implemented</small>
          </span>
          <i>→</i>
          <span>
            PostgreSQL evidence store<small>Configured only</small>
          </span>
        </div>
      </section>
    </div>
  )
}
