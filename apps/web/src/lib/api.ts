import { z } from 'zod'

const biomedicalSourceSchema = z.enum(['open_targets', 'europe_pmc'])
const entityTypeSchema = z.enum(['gene', 'protein', 'pathway', 'disease'])
const relationshipTypeSchema = z.literal('gene_associated_with_disease')
const evidenceTypeSchema = z.enum([
  'association_datasource_score',
  'association_overall_score',
  'literature_context',
])
const conflictStatusSchema = z.enum(['none_reported', 'conflicting', 'not_assessed'])
const nullableString = z.string().nullable()

const healthResponseSchema = z.object({
  status: z.literal('ok'),
  service: z.string().min(1),
  version: z.string().min(1),
})

const entitySchema = z.object({
  canonical_id: z.string().min(3),
  entity_type: entityTypeSchema,
  label: z.string().min(1),
  description: nullableString,
  source: biomedicalSourceSchema,
  source_identifier: z.string().min(1),
  aliases: z.array(z.string()),
  attributes: z.record(z.string(), z.unknown()),
  retrieved_at: z.string().min(1),
})

const evidenceRecordSchema = z.object({
  source: biomedicalSourceSchema,
  source_record_id: z.string().min(1),
  evidence_type: evidenceTypeSchema,
  score: z.number().min(0).max(1).nullable(),
  summary: nullableString,
  publication_ids: z.array(z.string()),
  attributes: z.record(z.string(), z.unknown()),
  retrieved_at: z.string().min(1),
})

const relationshipSchema = z.object({
  canonical_key: z.string().min(1),
  source_entity_id: z.string().min(3),
  target_entity_id: z.string().min(3),
  relationship_type: relationshipTypeSchema,
  source: biomedicalSourceSchema,
  source_identifier: z.string().min(1),
  score: z.number().min(0).max(1).nullable(),
  score_interpretation: nullableString,
  evidence: z.array(evidenceRecordSchema),
  attributes: z.record(z.string(), z.unknown()),
  retrieved_at: z.string().min(1),
})

const scoreComponentSchema = z.object({
  name: z.string().min(1),
  raw_value: z.number().nullable(),
  normalized_value: z.number().min(0).max(1).nullable(),
  weight: z.number().min(0).max(1),
  contribution: z.number().min(0).max(1),
  explanation: z.string().min(1),
})

const traversedEdgeSchema = z.object({
  traversed_from: z.string().min(3),
  traversed_to: z.string().min(3),
  direction: z.enum(['forward', 'reverse']),
  relationship_type: relationshipTypeSchema,
  relationships: z.array(relationshipSchema).min(1),
})

const candidatePathSchema = z.object({
  path_id: z.string().min(1),
  nodes: z.array(entitySchema).min(2),
  edges: z.array(traversedEdgeSchema).min(1),
  score: z.object({
    ranking_utility: z.number().min(0).max(1),
    method: z.string().min(1),
    components: z.array(scoreComponentSchema),
    interpretation: z.string().min(1),
  }),
  limitations: z.array(z.string()),
})

const discoveryResponseSchema = z.object({
  query: z.object({
    source_id: z.string().min(3),
    target_id: z.string().nullable(),
    target_entity_types: z.array(entityTypeSchema),
    intermediate_entity_types: z.array(entityTypeSchema),
    relationship_types: z.array(relationshipTypeSchema),
    max_path_length: z.number().int().min(1).max(4),
    result_count: z.number().int().min(1).max(5000),
    max_enumerated_paths: z.number().int().positive(),
    max_path_expansions: z.number().int().positive(),
  }),
  paths: z.array(candidatePathSchema),
  graph_node_count: z.number().int().nonnegative(),
  graph_relationship_count: z.number().int().nonnegative(),
  enumerated_path_count: z.number().int().nonnegative(),
  path_expansion_count: z.number().int().nonnegative(),
  warnings: z.array(z.string()),
})

const publicationReferenceSchema = z.object({
  citation_id: z.string().min(1),
  source_identifier: z.string().min(1),
  title: z.string().min(1),
  web_url: z.string().url(),
  author_string: nullableString,
  journal: nullableString,
  publication_year: z.number().int().nullable(),
  abstract: nullableString,
  doi: nullableString,
  pmid: nullableString,
  pmcid: nullableString,
  is_open_access: z.boolean().nullable(),
  verified_from: z.enum(['persisted_europe_pmc', 'live_europe_pmc']),
})

const evidenceItemViewSchema = z.object({
  evidence_id: z.string().min(1),
  record: evidenceRecordSchema,
  publications: z.array(publicationReferenceSchema),
  missing_publication_ids: z.array(z.string()),
  interpretation: z.string().min(1),
})

const relationshipEvidenceViewSchema = z.object({
  claim_id: z.string().min(1),
  claim_scope: z.literal('direct_relationship'),
  source_entity: entitySchema,
  target_entity: entitySchema,
  traversed_from: z.string().min(3),
  traversed_to: z.string().min(3),
  direction: z.enum(['forward', 'reverse']),
  relationship: relationshipSchema,
  evidence_items: z.array(evidenceItemViewSchema),
  conflict_status: conflictStatusSchema,
  uncertainty: z.array(z.string()),
})

const pathEvidenceViewSchema = z.object({
  path_id: z.string().min(1),
  claim_scope: z.enum(['direct_relationship', 'inferred_path']),
  path: candidatePathSchema,
  relationships: z.array(relationshipEvidenceViewSchema),
  publications: z.array(publicationReferenceSchema),
  missing_evidence: z.boolean(),
  conflict_status: conflictStatusSchema,
  uncertainty: z.array(z.string()),
})

const assistantAnswerSchema = z.object({
  question: z.string().min(1),
  mode: z.enum(['evidence_summary', 'llm_grounded']),
  provider_available: z.boolean(),
  claims: z.array(
    z.object({
      text: z.string().min(1),
      category: z.enum([
        'reported_finding',
        'hypothesis',
        'model_interpretation',
        'insufficient_evidence',
      ]),
      citation_ids: z.array(z.string()),
    }),
  ),
  references: z.array(publicationReferenceSchema),
  unsupported_claims: z.array(z.string()),
  limitations: z.array(z.string()),
})

const knowledgeGraphResponseSchema = z.object({
  entities: z.array(entitySchema),
  relationships: z.array(relationshipSchema),
  publications: z.array(
    z.object({
      source: biomedicalSourceSchema,
      source_identifier: z.string().min(1),
      title: z.string().min(1),
      author_string: nullableString,
      journal: nullableString,
      publication_year: z.number().int().nullable(),
      abstract: nullableString,
      doi: nullableString,
      pmid: nullableString,
      pmcid: nullableString,
      is_open_access: z.boolean().nullable(),
      attributes: z.record(z.string(), z.unknown()),
      retrieved_at: z.string().min(1),
    }),
  ),
  generated_at: z.string().min(1),
})

const errorEnvelopeSchema = z.object({
  error: z.object({ code: z.string(), message: z.string() }),
})

export type HealthResponse = z.infer<typeof healthResponseSchema>
export type BiomedicalSource = z.infer<typeof biomedicalSourceSchema>
export type EntityType = z.infer<typeof entityTypeSchema>
export type RelationshipType = z.infer<typeof relationshipTypeSchema>
export type ApiEntity = z.infer<typeof entitySchema>
export type ApiEvidenceRecord = z.infer<typeof evidenceRecordSchema>
export type ApiRelationship = z.infer<typeof relationshipSchema>
export type ApiScoreComponent = z.infer<typeof scoreComponentSchema>
export type ApiTraversedEdge = z.infer<typeof traversedEdgeSchema>
export type ApiCandidatePath = z.infer<typeof candidatePathSchema>
export type DiscoveryResponse = z.infer<typeof discoveryResponseSchema>
export type ApiPublicationReference = z.infer<typeof publicationReferenceSchema>
export type ApiEvidenceItemView = z.infer<typeof evidenceItemViewSchema>
export type ApiRelationshipEvidenceView = z.infer<typeof relationshipEvidenceViewSchema>
export type ApiPathEvidenceView = z.infer<typeof pathEvidenceViewSchema>
export type AssistantAnswer = z.infer<typeof assistantAnswerSchema>
export type KnowledgeGraphResponse = z.infer<typeof knowledgeGraphResponseSchema>

export interface DiscoveryRequest {
  source_id: string
  target_id?: string
  target_entity_types?: EntityType[]
  intermediate_entity_types?: EntityType[]
  relationship_types?: RelationshipType[]
  max_path_length?: number
  result_count?: number
}

export interface VerifiedDiscoverySession {
  request: DiscoveryRequest
  result: DiscoveryResponse
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1').replace(
  /\/$/,
  '',
)

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export function createGeneDiscoveryRequest(sourceId: string): DiscoveryRequest {
  return {
    source_id: sourceId.trim(),
    target_entity_types: ['disease'],
    relationship_types: ['gene_associated_with_disease'],
    max_path_length: 3,
    result_count: 10,
  }
}

export function isSupportedGeneId(value: string): boolean {
  return /^ensembl:ENSG\d{11}$/.test(value.trim())
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await apiFetch('/health', { signal }, 'API health check')
  return parseResponse(response, healthResponseSchema, 'API health check')
}

export async function getKnowledgeGraph(
  canonicalId: string,
  signal?: AbortSignal,
): Promise<KnowledgeGraphResponse> {
  const response = await apiFetch(
    `/knowledge/graph/${encodeURIComponent(canonicalId)}`,
    { signal },
    'Knowledge graph request',
  )
  return parseResponse(response, knowledgeGraphResponseSchema, 'Knowledge graph request')
}

export async function discoverPaths(
  request: DiscoveryRequest,
  signal?: AbortSignal,
): Promise<DiscoveryResponse> {
  const response = await apiFetch(
    '/discovery/paths',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal,
    },
    'Discovery request',
  )
  return parseResponse(response, discoveryResponseSchema, 'Discovery request')
}

export async function explorePathEvidence(
  discovery: DiscoveryRequest,
  pathId: string,
  signal?: AbortSignal,
): Promise<ApiPathEvidenceView> {
  const response = await apiFetch(
    '/evidence/paths',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ discovery, path_id: pathId }),
      signal,
    },
    'Evidence request',
  )
  return parseResponse(response, pathEvidenceViewSchema, 'Evidence request')
}

export async function askResearchAssistant(
  question: string,
  discovery: DiscoveryRequest,
  pathId: string,
  signal?: AbortSignal,
): Promise<AssistantAnswer> {
  const response = await apiFetch(
    '/assistant/answer',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, path: { discovery, path_id: pathId }, use_llm: true }),
      signal,
    },
    'Assistant request',
  )
  return parseResponse(response, assistantAnswerSchema, 'Assistant request')
}

async function apiFetch(path: string, init: RequestInit, context: string): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...init.headers },
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(`${context} could not reach the API.`)
  }
  if (!response.ok) {
    const errorPayload = errorEnvelopeSchema.safeParse(await safeJson(response))
    throw new ApiError(
      errorPayload.success ? errorPayload.data.error.message : `${context} could not be completed.`,
      response.status,
      errorPayload.success ? errorPayload.data.error.code : undefined,
    )
  }
  return response
}

async function parseResponse<T>(
  response: Response,
  schema: z.ZodType<T>,
  context: string,
): Promise<T> {
  const payload = await safeJson(response)
  const parsed = schema.safeParse(payload)
  if (!parsed.success) {
    throw new ApiError(`${context} returned malformed data.`, response.status, 'invalid_response')
  }
  return parsed.data
}

async function safeJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}
