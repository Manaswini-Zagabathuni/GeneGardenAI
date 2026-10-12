import { Icon } from './Icon'

interface StatusNoticeProps {
  tone: 'info' | 'warning' | 'error' | 'success'
  title: string
  children: React.ReactNode
  compact?: boolean
}

export function StatusNotice({ tone, title, children, compact = false }: StatusNoticeProps) {
  return (
    <div
      className={`notice notice-${tone} ${compact ? 'p-3' : 'p-4'}`}
      role={tone === 'error' ? 'alert' : 'status'}
    >
      <span className="notice-icon">
        <Icon name={tone === 'success' ? 'leaf' : 'sparkle'} className="h-4 w-4" />
      </span>
      <div>
        <p className="text-sm font-bold text-ink">{title}</p>
        <div className="mt-0.5 text-xs leading-5 text-ink-soft">{children}</div>
      </div>
    </div>
  )
}
