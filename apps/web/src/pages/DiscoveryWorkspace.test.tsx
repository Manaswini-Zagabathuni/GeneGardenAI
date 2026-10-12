import { useState } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import * as api from '../lib/api'
import {
  emptyDiscoveryResponse,
  verifiedDiscoveryResponse,
  verifiedDiscoverySession,
  verifiedPathEvidence,
} from '../test/verifiedFixtures'
import { DiscoveryWorkspace } from './DiscoveryWorkspace'

vi.mock('../components/KnowledgeGraph', () => ({
  KnowledgeGraph: ({ state }: { state: string }) => (
    <div aria-label="Test graph state">Graph state: {state}</div>
  ),
}))

function renderWorkspace(overrides: Partial<React.ComponentProps<typeof DiscoveryWorkspace>> = {}) {
  const observer = overrides.onSessionChange
  function TestHost() {
    const [session, setSession] = useState(overrides.session ?? null)
    return (
      <DiscoveryWorkspace
        apiOnline
        {...overrides}
        session={session}
        onSessionChange={(nextSession) => {
          setSession(nextSession)
          observer?.(nextSession)
        }}
      />
    )
  }
  return render(<TestHost />)
}

function enterSupportedGene() {
  fireEvent.change(screen.getByLabelText(/Source gene ID/i), {
    target: { value: 'ensembl:ENSG00000141510' },
  })
}

describe('DiscoveryWorkspace verified integration', () => {
  afterEach(() => vi.restoreAllMocks())

  it('renders returned paths, graph records, score components, and evidence', async () => {
    vi.spyOn(api, 'discoverPaths').mockResolvedValue(verifiedDiscoveryResponse)
    vi.spyOn(api, 'explorePathEvidence').mockResolvedValue(verifiedPathEvidence)
    const onSessionChange = vi.fn()
    renderWorkspace({ onSessionChange })

    enterSupportedGene()
    fireEvent.click(screen.getByRole('button', { name: /Discover paths/i }))

    expect(screen.getByText(/Retrieving paths/i)).toBeInTheDocument()
    expect(await screen.findByText('Graph state: ready')).toBeInTheDocument()
    expect(screen.getByText(/Path utility 0.730000/i)).toBeInTheDocument()
    expect(screen.getByText(/Not probability or confidence/i)).toBeInTheDocument()
    expect(
      await screen.findByRole('link', { name: /Verified fixture publication metadata/i }),
    ).toHaveAttribute('href', 'https://europepmc.org/article/MED/12345')
    expect(screen.getByText(/fixture:datasource:eva/i)).toBeInTheDocument()
    expect(onSessionChange).toHaveBeenCalledWith(
      expect.objectContaining({ result: verifiedDiscoveryResponse }),
    )
  })

  it('uses the accessible relationship list to inspect the actual stored direction', async () => {
    renderWorkspace({ session: verifiedDiscoverySession })

    fireEvent.click(
      screen.getByRole('button', {
        name: /ensembl:ENSG00000141510.*mondo:MONDO_0000001/i,
      }),
    )

    const inspector = screen
      .getByRole('heading', { name: /Relationship details/i })
      .closest('aside')
    expect(inspector).toHaveTextContent('ensembl:ENSG00000141510 → mondo:MONDO_0000001')
    expect(inspector).toHaveTextContent('fixture-source-pair')
    expect(inspector).toHaveTextContent('fixture:datasource:eva')
  })

  it('shows a completed empty-result state', async () => {
    vi.spyOn(api, 'discoverPaths').mockResolvedValue(emptyDiscoveryResponse)
    renderWorkspace()

    enterSupportedGene()
    fireEvent.click(screen.getByRole('button', { name: /Discover paths/i }))

    expect(await screen.findByText(/No paths returned/i)).toBeInTheDocument()
    expect(screen.queryByText('Graph state: ready')).not.toBeInTheDocument()
  })

  it('rejects unsupported identifiers before calling the endpoint', () => {
    const request = vi.spyOn(api, 'discoverPaths')
    renderWorkspace()

    fireEvent.change(screen.getByLabelText(/Source gene ID/i), { target: { value: 'TP53' } })
    fireEvent.click(screen.getByRole('button', { name: /Discover paths/i }))

    expect(screen.getByText(/Use a canonical Ensembl gene identifier/i)).toBeInTheDocument()
    expect(request).not.toHaveBeenCalled()
  })

  it('renders backend request failures without stale results', async () => {
    vi.spyOn(api, 'discoverPaths').mockRejectedValue(
      new api.ApiError('The canonical entity is not present in the graph.', 404, 'not_found'),
    )
    const onSessionChange = vi.fn()
    renderWorkspace({ onSessionChange })

    enterSupportedGene()
    fireEvent.click(screen.getByRole('button', { name: /Discover paths/i }))

    expect(await screen.findByText(/not present in the graph/i)).toBeInTheDocument()
    expect(onSessionChange).toHaveBeenCalledWith(null)
  })

  it('renders assistant failures beside the evidence-grounded controls', async () => {
    vi.spyOn(api, 'discoverPaths').mockResolvedValue(verifiedDiscoveryResponse)
    vi.spyOn(api, 'explorePathEvidence').mockResolvedValue(verifiedPathEvidence)
    vi.spyOn(api, 'askResearchAssistant').mockRejectedValue(
      new api.ApiError('The assistant service is unavailable.', 503),
    )
    renderWorkspace()

    enterSupportedGene()
    fireEvent.click(screen.getByRole('button', { name: /Discover paths/i }))
    await screen.findByRole('heading', { name: /Ask about this path/i })

    fireEvent.change(screen.getByLabelText(/^Question$/i), {
      target: { value: 'What does this path support?' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Summarize evidence/i }))

    await waitFor(() => {
      expect(screen.getByText(/assistant service is unavailable/i)).toBeInTheDocument()
    })
  })
})
