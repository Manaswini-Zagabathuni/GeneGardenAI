import { useEffect, useState } from 'react'

import { AppShell, type ApiStatus, type RouteId } from './components/AppShell'
import { ApiError, getHealth, type VerifiedDiscoverySession } from './lib/api'
import { ComparisonView } from './pages/ComparisonView'
import { DiscoveryWorkspace } from './pages/DiscoveryWorkspace'
import { EvaluationPage } from './pages/EvaluationPage'
import { HomeDashboard } from './pages/HomeDashboard'
import { MethodologyPage } from './pages/MethodologyPage'

const validRoutes = new Set<RouteId>(['home', 'discover', 'compare', 'evaluation', 'methodology'])

function routeFromHash(): RouteId {
  const candidate = window.location.hash.slice(1) as RouteId
  return validRoutes.has(candidate) ? candidate : 'home'
}

export function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const [activeRoute, setActiveRoute] = useState<RouteId>(routeFromHash)
  const [discoverySession, setDiscoverySession] = useState<VerifiedDiscoverySession | null>(null)
  const [initialSourceId, setInitialSourceId] = useState<string>()

  useEffect(() => {
    const handleHashChange = () => {
      setActiveRoute(routeFromHash())
      window.requestAnimationFrame(() => {
        document.getElementById('main-content')?.focus({ preventScroll: true })
        window.scrollTo({ top: 0, behavior: 'auto' })
      })
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    getHealth(controller.signal)
      .then(() => setApiStatus('online'))
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) {
          setApiStatus('offline')
          if (!(error instanceof ApiError)) console.error(error)
        }
      })
    return () => controller.abort()
  }, [])

  function saveDiscoverySession(session: VerifiedDiscoverySession | null) {
    setDiscoverySession(session)
    if (session) setInitialSourceId(session.request.source_id)
  }

  return (
    <AppShell activeRoute={activeRoute} apiStatus={apiStatus}>
      {activeRoute === 'home' && (
        <HomeDashboard
          apiStatus={apiStatus}
          session={discoverySession}
          onDiscovery={saveDiscoverySession}
        />
      )}
      {activeRoute === 'discover' && (
        <DiscoveryWorkspace
          initialSourceId={initialSourceId}
          apiOnline={apiStatus === 'online'}
          session={discoverySession}
          onSessionChange={saveDiscoverySession}
        />
      )}
      {activeRoute === 'compare' && <ComparisonView session={discoverySession} />}
      {activeRoute === 'evaluation' && <EvaluationPage />}
      {activeRoute === 'methodology' && <MethodologyPage />}
    </AppShell>
  )
}
