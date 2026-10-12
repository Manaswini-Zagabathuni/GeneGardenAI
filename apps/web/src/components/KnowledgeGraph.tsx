import type { Core, ElementDefinition } from 'cytoscape'
import { useEffect, useRef, useState } from 'react'

import { Icon } from './Icon'
import { Spinner } from './Spinner'

interface KnowledgeGraphProps {
  elements: readonly ElementDefinition[]
  state?: 'ready' | 'loading' | 'empty' | 'error'
  selectedId?: string
  onNodeSelect?: (nodeId: string) => void
  onEdgeSelect?: (edgeId: string) => void
  onRetry?: () => void
  ariaLabel?: string
  loadingLabel?: string
  emptyMessage?: string
}

export function KnowledgeGraph({
  elements,
  state = elements.length > 0 ? 'ready' : 'empty',
  selectedId,
  onNodeSelect,
  onEdgeSelect,
  onRetry,
  ariaLabel = 'Interactive biomedical knowledge graph',
  loadingLabel = 'Rendering the knowledge graph…',
  emptyMessage = 'No verified paths are available for this query.',
}: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<Core | null>(null)
  const [graphReady, setGraphReady] = useState(false)
  const [renderFailed, setRenderFailed] = useState(false)
  const [renderAttempt, setRenderAttempt] = useState(0)

  useEffect(() => {
    if (!containerRef.current || state !== 'ready' || elements.length === 0) return

    const container = containerRef.current
    let graph: Core | undefined
    let cancelled = false

    async function renderGraph() {
      try {
        const { default: cytoscape } = await import('cytoscape')
        if (cancelled) return

        graph = cytoscape({
          container,
          elements: [...elements],
          minZoom: 0.55,
          maxZoom: 2.2,
          layout: {
            name: 'cose',
            animate: false,
            fit: true,
            padding: 48,
            nodeRepulsion: () => 6400,
            idealEdgeLength: () => 110,
          },
          style: [
            {
              selector: 'node',
              style: {
                width: 48,
                height: 48,
                'background-color': '#9eaf91',
                'border-color': '#fffdf7',
                'border-width': 4,
                color: '#24372f',
                label: 'data(label)',
                'font-family': 'DM Sans, ui-sans-serif, system-ui',
                'font-size': 10,
                'font-weight': 600,
                'text-valign': 'bottom',
                'text-margin-y': 8,
                'text-wrap': 'wrap',
                'text-max-width': '88px',
                'overlay-opacity': 0,
              },
            },
            {
              selector: 'node[kind = "gene"]',
              style: { 'background-color': '#87a77f', shape: 'ellipse' },
            },
            {
              selector: 'node[kind = "protein"]',
              style: { 'background-color': '#c7b4df', shape: 'round-rectangle' },
            },
            {
              selector: 'node[kind = "pathway"]',
              style: { 'background-color': '#e6b2c4', shape: 'hexagon' },
            },
            {
              selector: 'node[kind = "disease"]',
              style: { 'background-color': '#e7b18e', shape: 'diamond' },
            },
            {
              selector: 'node:selected',
              style: {
                'border-color': '#4e725f',
                'border-width': 5,
                'underlay-color': '#dfe9d8',
                'underlay-opacity': 0.8,
                'underlay-padding': 8,
              },
            },
            {
              selector: 'node.path-highlight',
              style: {
                'border-color': '#765f8a',
                'border-width': 5,
              },
            },
            {
              selector: 'edge',
              style: {
                'line-color': '#aebbad',
                'target-arrow-color': '#aebbad',
                'target-arrow-shape': 'triangle',
                'arrow-scale': 0.7,
                width: 2,
                'curve-style': 'bezier',
                label: 'data(label)',
                color: '#6d7b74',
                'font-size': 8,
                'text-background-color': '#fffdf8',
                'text-background-opacity': 0.9,
                'text-background-padding': '3px',
                'overlay-opacity': 0,
              },
            },
            {
              selector: 'edge:selected',
              style: { 'line-color': '#765f8a', 'target-arrow-color': '#765f8a', width: 4 },
            },
            {
              selector: 'edge.path-highlight',
              style: { 'line-color': '#765f8a', 'target-arrow-color': '#765f8a', width: 4 },
            },
          ],
        })

        graph.on('tap', 'node', (event) => onNodeSelect?.(event.target.id()))
        graph.on('tap', 'edge', (event) => onEdgeSelect?.(event.target.id()))
        graphRef.current = graph
        setGraphReady(true)
      } catch {
        if (!cancelled) setRenderFailed(true)
      }
    }

    void renderGraph()

    return () => {
      cancelled = true
      graphRef.current = null
      graph?.destroy()
      setGraphReady(false)
    }
  }, [elements, onEdgeSelect, onNodeSelect, renderAttempt, state])

  useEffect(() => {
    const graph = graphRef.current
    if (!graphReady || !graph) return
    graph.$(':selected').unselect()
    if (selectedId) graph.$id(selectedId).select()
  }, [graphReady, selectedId])

  function adjustZoom(amount: number) {
    const graph = graphRef.current
    if (!graph) return
    graph.animate({ zoom: Math.min(2.2, Math.max(0.55, graph.zoom() + amount)), duration: 180 })
  }

  return (
    <div className="graph-frame">
      <div
        ref={containerRef}
        className="h-full min-h-[430px] w-full"
        aria-label={ariaLabel}
        role="img"
      />
      {state === 'ready' && !renderFailed && (
        <div className="graph-controls" aria-label="Graph controls">
          <button
            disabled={!graphReady}
            onClick={() => adjustZoom(0.18)}
            type="button"
            aria-label="Zoom in"
          >
            +
          </button>
          <button
            disabled={!graphReady}
            onClick={() => adjustZoom(-0.18)}
            type="button"
            aria-label="Zoom out"
          >
            −
          </button>
          <button
            disabled={!graphReady}
            onClick={() => graphRef.current?.fit(undefined, 45)}
            type="button"
            aria-label="Fit graph to view"
          >
            ⌗
          </button>
        </div>
      )}
      {state === 'loading' && (
        <GraphOverlay>
          <Spinner label={loadingLabel} />
        </GraphOverlay>
      )}
      {state === 'ready' && renderFailed && (
        <GraphOverlay>
          <span className="graph-seed" aria-hidden="true">
            !
          </span>
          <strong>The graph could not be rendered</strong>
          <span>Your selection is safe. Retry the visualization when ready.</span>
          <button
            className="secondary-button mt-3"
            type="button"
            onClick={() => {
              setRenderFailed(false)
              setRenderAttempt((attempt) => attempt + 1)
              onRetry?.()
            }}
          >
            Retry <Icon name="arrow" className="h-4 w-4" />
          </button>
        </GraphOverlay>
      )}
      {state === 'empty' && (
        <GraphOverlay>
          <span className="graph-seed" aria-hidden="true">
            ❀
          </span>
          <strong>No graph records to display</strong>
          <span>{emptyMessage}</span>
        </GraphOverlay>
      )}
      {state === 'error' && (
        <GraphOverlay>
          <span className="graph-seed" aria-hidden="true">
            !
          </span>
          <strong>The graph could not be rendered</strong>
          <span>Your selection is safe. Retry the visualization when ready.</span>
          {onRetry && (
            <button className="secondary-button mt-3" type="button" onClick={onRetry}>
              Retry <Icon name="arrow" className="h-4 w-4" />
            </button>
          )}
        </GraphOverlay>
      )}
    </div>
  )
}

function GraphOverlay({ children }: { children: React.ReactNode }) {
  return (
    <div className="graph-overlay" aria-live="polite">
      {children}
    </div>
  )
}
