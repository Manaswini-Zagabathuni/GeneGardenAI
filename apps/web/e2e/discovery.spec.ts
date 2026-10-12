import { expect, test, type Page, type Route } from '@playwright/test'

import {
  emptyDiscoveryResponse,
  verifiedDiscoveryResponse,
  verifiedPathEvidence,
} from '../src/test/verifiedFixtures'

const supportedGeneId = 'ensembl:ENSG00000141510'

interface MockApiOptions {
  discoveryFailureCount?: number
  empty?: boolean
}

async function installMockApi(page: Page, options: MockApiOptions = {}) {
  let discoveryRequests = 0
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/health')) {
      await fulfillJson(route, { status: 'ok', service: 'genegarden-api', version: '0.1.0' })
      return
    }
    if (path.endsWith('/discovery/paths')) {
      discoveryRequests += 1
      if (discoveryRequests <= (options.discoveryFailureCount ?? 0)) {
        await fulfillJson(
          route,
          { error: { code: 'service_unavailable', message: 'Test API temporarily unavailable.' } },
          503,
        )
        return
      }
      await fulfillJson(route, options.empty ? emptyDiscoveryResponse : verifiedDiscoveryResponse)
      return
    }
    if (path.endsWith('/evidence/paths')) {
      await fulfillJson(route, verifiedPathEvidence)
      return
    }
    await fulfillJson(
      route,
      { error: { code: 'not_found', message: 'Unhandled test route.' } },
      404,
    )
  })
  return () => discoveryRequests
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
}

async function runSuccessfulSearch(page: Page) {
  await page.goto('/')
  await expect(page.locator('.api-badge:visible').getByText('API online')).toBeVisible()
  await page
    .getByRole('searchbox', { name: /canonical Ensembl gene identifier/i })
    .fill(supportedGeneId)
  await page.getByRole('button', { name: 'Explore' }).click()
  await expect(page).toHaveURL(/#discover$/)
  await expect(page.getByRole('heading', { name: /Returned path graph/i })).toBeVisible()
}

test('search renders Cytoscape and preserves graph and evidence provenance', async ({ page }) => {
  await installMockApi(page)
  await runSuccessfulSearch(page)

  const graph = page.getByRole('img', { name: /verified discovery paths/i })
  await expect(graph.locator('canvas').first()).toBeVisible()

  await page.evaluate((entityId) => {
    const container = document.querySelector<
      HTMLElement & {
        _cyreg?: { cy?: { getElementById: (id: string) => { emit: (name: string) => void } } }
      }
    >('[aria-label="Interactive graph of verified discovery paths"]')
    container?._cyreg?.cy?.getElementById(entityId).emit('tap')
  }, supportedGeneId)
  await expect(page.getByRole('heading', { name: 'Fixture source gene' })).toBeVisible()

  await page.evaluate(() => {
    const container = document.querySelector<
      HTMLElement & {
        _cyreg?: { cy?: { getElementById: (id: string) => { emit: (name: string) => void } } }
      }
    >('[aria-label="Interactive graph of verified discovery paths"]')
    container?._cyreg?.cy?.getElementById('fixture-relationship-0001').emit('tap')
  })
  const inspector = page.getByRole('heading', { name: /Relationship details/i }).locator('..')
  await expect(inspector).toContainText('fixture-source-pair')
  await expect(inspector).toContainText('fixture:datasource:eva')

  const publication = page.getByRole('link', { name: /Verified fixture publication metadata/i })
  await expect(publication).toHaveAttribute('href', 'https://europepmc.org/article/MED/12345')
  await expect(page.getByText(/Not probability or confidence/i)).toBeVisible()
})

test('empty results and unsupported identifiers stay explicit', async ({ page }) => {
  const getDiscoveryRequests = await installMockApi(page, { empty: true })
  await page.goto('/')
  await expect(page.locator('.api-badge:visible').getByText('API online')).toBeVisible()

  const search = page.getByRole('searchbox', { name: /canonical Ensembl gene identifier/i })
  await search.fill('TP53')
  await page.getByRole('button', { name: 'Explore' }).click()
  await expect(page.getByText(/Use a canonical Ensembl gene identifier/i)).toBeVisible()
  expect(getDiscoveryRequests()).toBe(0)

  await search.fill(supportedGeneId)
  await page.getByRole('button', { name: 'Explore' }).click()
  await expect(page.getByText(/No paths returned/i)).toBeVisible()
  await expect(page.getByText(/No synthetic result was substituted/i)).toBeVisible()
  expect(getDiscoveryRequests()).toBe(1)
})

test('API failures are visible and the same query can be retried', async ({ page }) => {
  const getDiscoveryRequests = await installMockApi(page, { discoveryFailureCount: 1 })
  await page.goto('/')
  await expect(page.getByText('API online').first()).toBeVisible()

  await page
    .getByRole('searchbox', { name: /canonical Ensembl gene identifier/i })
    .fill(supportedGeneId)
  await page.getByRole('button', { name: 'Explore' }).click()
  await expect(page.getByRole('alert')).toContainText('Test API temporarily unavailable.')

  await page.getByRole('button', { name: 'Explore' }).click()
  await expect(page).toHaveURL(/#discover$/)
  await expect(page.getByRole('heading', { name: /Returned path graph/i })).toBeVisible()
  expect(getDiscoveryRequests()).toBe(2)
})

test('mobile layout retains keyboard-operable graph alternatives', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await installMockApi(page)
  await runSuccessfulSearch(page)

  await expect(page.getByRole('navigation', { name: /Mobile navigation/i })).toBeVisible()
  const relationship = page.getByRole('button', {
    name: /ensembl:ENSG00000141510.*mondo:MONDO_0000001/i,
  })
  await relationship.focus()
  await expect(relationship).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: /Relationship details/i })).toBeVisible()

  await page.reload()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: /Skip to main content/i })).toBeFocused()
})
