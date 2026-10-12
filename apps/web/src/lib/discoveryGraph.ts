import type { ElementDefinition } from 'cytoscape'

import type { ApiCandidatePath, ApiEntity, ApiRelationship } from './api'

export interface VerifiedGraphModel {
  elements: readonly ElementDefinition[]
  entities: readonly ApiEntity[]
  relationships: readonly ApiRelationship[]
  pathIdsByRelationship: ReadonlyMap<string, readonly string[]>
}

export function buildVerifiedGraph(
  paths: readonly ApiCandidatePath[],
  selectedPathId?: string,
): VerifiedGraphModel {
  const entities = new Map<string, ApiEntity>()
  const relationships = new Map<string, ApiRelationship>()
  const pathIdsByRelationship = new Map<string, Set<string>>()
  const selectedNodeIds = new Set<string>()
  const selectedRelationshipIds = new Set<string>()

  for (const path of paths) {
    for (const entity of path.nodes) {
      entities.set(entity.canonical_id, entity)
      if (path.path_id === selectedPathId) selectedNodeIds.add(entity.canonical_id)
    }
    for (const edge of path.edges) {
      for (const relationship of edge.relationships) {
        relationships.set(relationship.canonical_key, relationship)
        const pathIds = pathIdsByRelationship.get(relationship.canonical_key) ?? new Set<string>()
        pathIds.add(path.path_id)
        pathIdsByRelationship.set(relationship.canonical_key, pathIds)
        if (path.path_id === selectedPathId) {
          selectedRelationshipIds.add(relationship.canonical_key)
        }
      }
    }
  }

  const sortedEntities = [...entities.values()].sort((a, b) =>
    a.canonical_id.localeCompare(b.canonical_id),
  )
  const sortedRelationships = [...relationships.values()].sort((a, b) =>
    a.canonical_key.localeCompare(b.canonical_key),
  )
  const elements: ElementDefinition[] = [
    ...sortedEntities.map((entity) => ({
      data: {
        id: entity.canonical_id,
        label: entity.label,
        kind: entity.entity_type,
        sourceIdentifier: entity.source_identifier,
      },
      classes: selectedNodeIds.has(entity.canonical_id) ? 'path-highlight' : '',
    })),
    ...sortedRelationships.map((relationship) => ({
      data: {
        id: relationship.canonical_key,
        source: relationship.source_entity_id,
        target: relationship.target_entity_id,
        label: relationship.relationship_type.replaceAll('_', ' '),
        sourceIdentifier: relationship.source_identifier,
      },
      classes: selectedRelationshipIds.has(relationship.canonical_key) ? 'path-highlight' : '',
    })),
  ]

  return {
    elements,
    entities: sortedEntities,
    relationships: sortedRelationships,
    pathIdsByRelationship: new Map(
      [...pathIdsByRelationship].map(([key, value]) => [key, [...value].sort()]),
    ),
  }
}
