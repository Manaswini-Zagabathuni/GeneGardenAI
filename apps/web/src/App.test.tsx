import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App } from './App'

function mockHealthyApi() {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true,
    json: async () => ({ status: 'ok', service: 'genegarden-api', version: '0.1.0' }),
  } as Response)
}

describe('App', () => {
  afterEach(() => {
    window.location.hash = ''
    vi.restoreAllMocks()
  })

  it('renders the home research dashboard and enables verified search after health succeeds', async () => {
    mockHealthyApi()
    render(<App />)

    expect(screen.getByRole('heading', { name: /grow a clearer view/i })).toBeInTheDocument()
    expect(
      screen.getByRole('searchbox', { name: /canonical Ensembl gene identifier/i }),
    ).toBeEnabled()
    await waitFor(() => expect(screen.getByRole('button', { name: /Explore/i })).toBeEnabled())
    expect(screen.getByText(/never use for diagnosis or clinical decisions/i)).toBeInTheDocument()
  })

  it('supports direct navigation to the evaluation screen', () => {
    window.location.hash = '#evaluation'
    mockHealthyApi()
    render(<App />)

    expect(screen.getByRole('heading', { name: /benchmark the method/i })).toBeInTheDocument()
    expect(screen.getByText(/frozen run · 3 cases/i)).toBeInTheDocument()
    expect(screen.getByText(/engineering regression check/i)).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: /transparent baseline v1/i })).toBeInTheDocument()
  })

  it('does not populate comparison with synthetic paths when no query has run', () => {
    window.location.hash = '#compare'
    mockHealthyApi()
    render(<App />)

    expect(screen.getByText(/No discovery result to compare/i)).toBeInTheDocument()
    expect(screen.getByText(/does not use demonstration candidates/i)).toBeInTheDocument()
  })
})
