import { describe, expect, it } from 'vitest'

import { verifiedDiscoveryResponse } from '../test/verifiedFixtures'
import { buildVerifiedGraph } from './discoveryGraph'

describe('buildVerifiedGraph', () => {
  it('preserves stored relationship direction and provenance identifiers', () => {
    const graph = buildVerifiedGraph(verifiedDiscoveryResponse.paths)
    const edge = graph.elements.find((element) => element.data.id === 'fixture-relationship-0001')

    expect(edge?.data).toMatchObject({
      source: 'ensembl:ENSG00000141510',
      target: 'mondo:MONDO_0000001',
      sourceIdentifier: 'fixture-source-pair',
    })
  })

  it('deduplicates shared entities and relationships across returned paths', () => {
    const original = verifiedDiscoveryResponse.paths[0]
    const duplicatePath = { ...original, path_id: 'fixture-path-0002' }
    const graph = buildVerifiedGraph([original, duplicatePath], duplicatePath.path_id)

    expect(graph.entities).toHaveLength(2)
    expect(graph.relationships).toHaveLength(1)
    expect(graph.elements).toHaveLength(3)
    expect(graph.pathIdsByRelationship.get('fixture-relationship-0001')).toEqual([
      'fixture-path-0001',
      'fixture-path-0002',
    ])
    expect(graph.elements.every((element) => element.classes === 'path-highlight')).toBe(true)
  })
})
