import { Icon } from '../components/Icon'
import { StatusNotice } from '../components/StatusNotice'

const methods = [
  ['Transparent baseline v1', '0.133333', '0.666667', '0.233333'],
  ['Shortest path', '0.133333', '0.666667', '0.233333'],
  ['Unweighted path count', '0.133333', '0.666667', '0.205556'],
] as const

const protocol = [
  [
    '01',
    'Freeze sources',
    'Record source releases, query dates, normalization code, and licenses.',
  ],
  [
    '02',
    'Version benchmarks',
    'Use a reviewable set of positive, negative, and withheld research questions.',
  ],
  [
    '03',
    'Run deterministically',
    'Pin seeds, dependency versions, parameters, and graph snapshots.',
  ],
  [
    '04',
    'Publish uncertainty',
    'Report missing coverage and failure cases alongside every metric.',
  ],
] as const

export function EvaluationPage() {
  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="eyebrow">
            <Icon name="evaluation" className="h-3.5 w-3.5" /> Reproducible evaluation
          </span>
          <h1 className="page-title">Benchmark the method, not the story.</h1>
          <p>
            Track graph retrieval and ranking quality against versioned datasets before presenting
            performance claims.
          </p>
        </div>
        <span className="status-chip status-chip-success">Frozen run · 3 cases</span>
      </header>

      <StatusNotice tone="warning" title="Engineering regression check — not biological validation">
        These results come from three edge-masking cases in one frozen Open Targets 26.09 subset.
        Labels and traversal edges share a source release, so source and aggregation leakage make
        the benchmark unsuitable for performance or superiority claims.
      </StatusNotice>

      <section className="metric-grid" aria-label="Evaluation metrics">
        {[
          ['Benchmark queries', '3', 'Frozen oncology edge-masking cases'],
          ['Recall @ 5', '0.666667', 'Transparent baseline v1'],
          ['Mean reciprocal rank', '0.233333', 'Transparent baseline v1'],
          ['Open Targets release', '26.09', 'Retrieved 2026-10-11'],
        ].map(([label, value, note]) => (
          <article className="metric-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{note}</small>
          </article>
        ))}
      </section>

      <section className="card overflow-hidden" aria-labelledby="method-comparison-heading">
        <div className="card-header">
          <div>
            <span className="eyebrow">Method registry</span>
            <h2 id="method-comparison-heading" className="section-title mt-2">
              Algorithm comparison
            </h2>
          </div>
          <span className="text-xs text-ink-soft">Reproduce with the documented CLI command</span>
        </div>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Method</th>
                <th>Precision @ 5</th>
                <th>Recall @ 5</th>
                <th>MRR</th>
              </tr>
            </thead>
            <tbody>
              {methods.map(([method, precision, recall, mrr]) => (
                <tr key={method}>
                  <td>
                    <strong>{method}</strong>
                  </td>
                  <td>{precision}</td>
                  <td>{recall}</td>
                  <td>{mrr}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="protocol-heading">
        <div className="section-heading-row">
          <div>
            <span className="eyebrow">Protocol</span>
            <h2 id="protocol-heading" className="section-title">
              A defensible evaluation sequence
            </h2>
          </div>
        </div>
        <div className="protocol-grid">
          {protocol.map(([step, title, copy]) => (
            <article key={step}>
              <span>{step}</span>
              <div>
                <h3>{title}</h3>
                <p>{copy}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
