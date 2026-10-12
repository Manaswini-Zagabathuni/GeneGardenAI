import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { KnowledgeGraph } from './KnowledgeGraph'

describe('KnowledgeGraph states', () => {
  it('renders loading and empty states without initializing Cytoscape', () => {
    const { rerender } = render(<KnowledgeGraph elements={[]} state="loading" />)
    expect(screen.getByText(/Rendering the knowledge graph/i)).toBeInTheDocument()

    rerender(<KnowledgeGraph elements={[]} state="empty" />)
    expect(screen.getByText(/No verified paths are available/i)).toBeInTheDocument()
  })

  it('provides a retry control for an explicit graph error', () => {
    const retry = vi.fn()
    render(<KnowledgeGraph elements={[]} state="error" onRetry={retry} />)

    fireEvent.click(screen.getByRole('button', { name: /Retry/i }))
    expect(retry).toHaveBeenCalledOnce()
  })
})
