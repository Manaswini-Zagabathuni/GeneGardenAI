import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { MethodologyPage } from './MethodologyPage'

describe('MethodologyPage implementation status', () => {
  it('reports implemented capabilities with their real scope and preserves limitations', () => {
    render(<MethodologyPage />)

    expect(screen.getByText('React and FastAPI workflow')).toBeInTheDocument()
    expect(screen.getByText('PostgreSQL evidence store')).toBeInTheDocument()
    expect(screen.getByText('Open Targets adapter')).toBeInTheDocument()
    expect(screen.getByText('Europe PMC adapter')).toBeInTheDocument()
    expect(screen.getByText('Research assistant')).toBeInTheDocument()
    expect(screen.getByText('Scientific validation')).toBeInTheDocument()
    expect(screen.getAllByText('Implemented')).toHaveLength(2)
    expect(screen.getAllByText('Implemented · bounded scope')).toHaveLength(2)
    expect(screen.getByText('Partially implemented')).toBeInTheDocument()
    expect(screen.getByText('Unverified beyond regression scope')).toBeInTheDocument()
    expect(
      screen.getByText(/one relationship type and a small starter domain/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/no concrete provider implementation/i)).toBeInTheDocument()
  })

  it('does not render the superseded roadmap statuses', () => {
    render(<MethodologyPage />)

    expect(screen.queryByText('Health only')).not.toBeInTheDocument()
    expect(screen.queryByText('Not implemented')).not.toBeInTheDocument()
    expect(screen.queryByText('Configured only')).not.toBeInTheDocument()
    expect(screen.queryByText(/configured but not implemented/i)).not.toBeInTheDocument()
  })
})
