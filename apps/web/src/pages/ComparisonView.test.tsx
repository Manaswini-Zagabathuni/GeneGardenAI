import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import * as api from '../lib/api'
import { verifiedDiscoverySession, verifiedPathEvidence } from '../test/verifiedFixtures'
import { ComparisonView } from './ComparisonView'

describe('ComparisonView', () => {
  afterEach(() => vi.restoreAllMocks())

  it('renders only backend-returned candidates and their retrieved publication metadata', async () => {
    vi.spyOn(api, 'explorePathEvidence').mockResolvedValue(verifiedPathEvidence)
    render(<ComparisonView session={verifiedDiscoverySession} />)

    expect(screen.getAllByText(/Ranking utility/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Not probability/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Fixture source gene').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/fixture-source-pair/i).length).toBeGreaterThan(0)
    expect(
      await screen.findByRole('link', { name: /Verified fixture publication metadata/i }),
    ).toHaveAttribute('href', 'https://europepmc.org/article/MED/12345')
    expect(screen.getByText(/Direct reported relationship/i)).toBeInTheDocument()
  })

  it('shows an explicit state when no discovery session exists', () => {
    render(<ComparisonView session={null} />)

    expect(screen.getByText(/No discovery result to compare/i)).toBeInTheDocument()
    expect(screen.getByText(/does not use demonstration candidates/i)).toBeInTheDocument()
  })
})
