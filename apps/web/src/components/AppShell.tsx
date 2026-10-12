import { BotanicalMark } from './BotanicalMark'
import { Icon } from './Icon'

export type RouteId = 'home' | 'discover' | 'compare' | 'evaluation' | 'methodology'
export type ApiStatus = 'checking' | 'online' | 'offline'

interface NavItem {
  id: RouteId
  label: string
  icon: 'about' | 'compare' | 'discovery' | 'evaluation' | 'home'
}

const navigation: readonly NavItem[] = [
  { id: 'home', label: 'Home', icon: 'home' },
  { id: 'discover', label: 'Discovery', icon: 'discovery' },
  { id: 'compare', label: 'Compare paths', icon: 'compare' },
  { id: 'evaluation', label: 'Evaluation', icon: 'evaluation' },
  { id: 'methodology', label: 'Methodology', icon: 'about' },
]

interface AppShellProps {
  activeRoute: RouteId
  apiStatus: ApiStatus
  children: React.ReactNode
}

function ApiBadge({ status }: { status: ApiStatus }) {
  return (
    <span className="api-badge" title="Checks API process availability only">
      <span className={`status-dot status-${status}`} aria-hidden="true" />
      <span>API {status}</span>
    </span>
  )
}

export function AppShell({ activeRoute, apiStatus, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>

      <aside className="sidebar" aria-label="Primary navigation">
        <a href="#home" className="mb-10 block" aria-label="GeneGarden AI home">
          <BotanicalMark />
        </a>
        <nav className="space-y-1.5">
          {navigation.map((item) => (
            <a
              className={`nav-item ${activeRoute === item.id ? 'nav-item-active' : ''}`}
              href={`#${item.id}`}
              key={item.id}
              aria-current={activeRoute === item.id ? 'page' : undefined}
            >
              <Icon name={item.icon} className="h-[18px] w-[18px]" />
              <span>{item.label}</span>
            </a>
          ))}
        </nav>

        <div className="sidebar-note">
          <div className="mb-3 flex items-center gap-2 text-sage-700">
            <Icon name="leaf" className="h-4 w-4" />
            <span className="text-[10px] font-extrabold uppercase tracking-[0.18em]">
              Research note
            </span>
          </div>
          <p>Exploratory software only. Never use for diagnosis or clinical decisions.</p>
        </div>

        <div className="mt-auto pt-6">
          <ApiBadge status={apiStatus} />
        </div>
      </aside>

      <div className="min-w-0 lg:pl-[248px]">
        <header className="mobile-header">
          <a href="#home" aria-label="GeneGarden AI home">
            <BotanicalMark compact />
          </a>
          <ApiBadge status={apiStatus} />
        </header>
        <nav className="mobile-nav" aria-label="Mobile navigation">
          {navigation.map((item) => (
            <a
              className={`mobile-nav-item ${activeRoute === item.id ? 'mobile-nav-item-active' : ''}`}
              href={`#${item.id}`}
              key={item.id}
              aria-current={activeRoute === item.id ? 'page' : undefined}
            >
              <Icon name={item.icon} className="h-4 w-4" />
              {item.label}
            </a>
          ))}
        </nav>

        <main id="main-content" className="page-canvas" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  )
}
