import { afterEach, describe, expect, it, vi } from 'vitest'

import { verifiedDiscoveryResponse } from '../test/verifiedFixtures'
import { discoverPaths, getHealth } from './api'

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('typed API client', () => {
  afterEach(() => vi.restoreAllMocks())

  it('accepts a discovery response matching the backend contract', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(verifiedDiscoveryResponse))

    const result = await discoverPaths({ source_id: 'ensembl:ENSG00000141510' })

    expect(result.paths[0].edges[0].relationships[0].source_identifier).toBe('fixture-source-pair')
    expect(result.paths[0].edges[0].relationships[0].evidence[0].source_record_id).toBe(
      'fixture:datasource:eva',
    )
  })

  it('rejects malformed successful responses at runtime', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse({ ...verifiedDiscoveryResponse, paths: [{ path_id: 'missing-fields' }] }),
    )

    await expect(discoverPaths({ source_id: 'ensembl:ENSG00000141510' })).rejects.toMatchObject({
      message: 'Discovery request returned malformed data.',
      code: 'invalid_response',
    })
  })

  it('preserves backend error messages and unsupported-identifier status', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: 'validation_error',
            message: 'source_id must be a canonical identifier',
          },
        },
        422,
      ),
    )

    await expect(discoverPaths({ source_id: 'TP53' })).rejects.toMatchObject({
      status: 422,
      code: 'validation_error',
      message: 'source_id must be a canonical identifier',
    })
  })

  it('turns network failures into a clear API error', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Network unavailable'))

    await expect(getHealth()).rejects.toMatchObject({
      message: 'API health check could not reach the API.',
    })
  })
})
