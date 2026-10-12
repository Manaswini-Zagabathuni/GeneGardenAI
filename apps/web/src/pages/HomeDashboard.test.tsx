import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import * as api from '../lib/api'
import { emptyDiscoveryResponse, verifiedDiscoveryResponse } from '../test/verifiedFixtures'
import { HomeDashboard } from './HomeDashboard'

describe('HomeDashboard discovery search', () => {
  afterEach(() => vi.restoreAllMocks())

  it('queries the backend and passes the validated result into the shared session', async () => {
    vi.spyOn(api, 'discoverPaths').mockResolvedValue(verifiedDiscoveryResponse)
    const onDiscovery = vi.fn()
    render(<HomeDashboard apiStatus="online" session={null} onDiscovery={onDiscovery} />)

    fireEvent.change(
      screen.getByRole('searchbox', { name: /canonical Ensembl gene identifier/i }),
      { target: { value: 'ensembl:ENSG00000141510' } },
    )
    fireEvent.submit(screen.getByRole('search'))

    expect(screen.getByText(/Retrieving verified paths/i)).toBeInTheDocument()
    await waitFor(() => expect(onDiscovery).toHaveBeenCalledOnce())
    expect(api.discoverPaths).toHaveBeenCalledWith(
      expect.objectContaining({ source_id: 'ensembl:ENSG00000141510' }),
    )
    expect(onDiscovery.mock.calls[0][0].result).toBe(verifiedDiscoveryResponse)
  })

  it('renders an honest empty state without substituting fixtures', async () => {
    vi.spyOn(api, 'discoverPaths').mockResolvedValue(emptyDiscoveryResponse)
    render(<HomeDashboard apiStatus="online" session={null} onDiscovery={vi.fn()} />)

    fireEvent.change(
      screen.getByRole('searchbox', { name: /canonical Ensembl gene identifier/i }),
      { target: { value: 'ensembl:ENSG00000141510' } },
    )
    fireEvent.submit(screen.getByRole('search'))

    expect(await screen.findByText(/No paths returned/i)).toBeInTheDocument()
    expect(screen.getByText(/No synthetic result was substituted/i)).toBeInTheDocument()
  })

  it('rejects unsupported identifiers before making a request', () => {
    const request = vi.spyOn(api, 'discoverPaths')
    render(<HomeDashboard apiStatus="online" session={null} onDiscovery={vi.fn()} />)

    fireEvent.change(
      screen.getByRole('searchbox', { name: /canonical Ensembl gene identifier/i }),
      { target: { value: 'TP53' } },
    )
    fireEvent.submit(screen.getByRole('search'))

    expect(screen.getByText(/Use a canonical Ensembl gene identifier/i)).toBeInTheDocument()
    expect(request).not.toHaveBeenCalled()
  })

  it('reports backend request failures', async () => {
    vi.spyOn(api, 'discoverPaths').mockRejectedValue(
      new api.ApiError('Discovery request could not reach the API.'),
    )
    render(<HomeDashboard apiStatus="online" session={null} onDiscovery={vi.fn()} />)

    fireEvent.change(
      screen.getByRole('searchbox', { name: /canonical Ensembl gene identifier/i }),
      { target: { value: 'ensembl:ENSG00000141510' } },
    )
    fireEvent.submit(screen.getByRole('search'))

    expect(await screen.findByText(/could not reach the API/i)).toBeInTheDocument()
  })
})
