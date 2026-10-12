interface BotanicalMarkProps {
  compact?: boolean
}

export function BotanicalMark({ compact = false }: BotanicalMarkProps) {
  return (
    <div className="flex items-center gap-3">
      <svg
        aria-hidden="true"
        className={`${compact ? 'h-9 w-9' : 'h-11 w-11'} shrink-0 drop-shadow-sm`}
        viewBox="0 0 48 48"
      >
        <rect width="48" height="48" rx="15" fill="#496f5d" />
        <path d="M24 36V20" stroke="#f8f1de" strokeWidth="2" strokeLinecap="round" />
        <path d="M24 28c-7 0-10-4-10-9 7 0 10 3 10 9Z" fill="#c8d9bd" />
        <path d="M24 23c1-7 5-10 10-9 0 6-3 10-10 9Z" fill="#e6bdd0" />
        <circle cx="24" cy="15" r="4.5" fill="#d8c7ec" />
        <circle cx="24" cy="15" r="1.7" fill="#805f87" />
      </svg>
      <span>
        <span
          className={`block font-display font-semibold tracking-tight text-ink ${compact ? 'text-lg' : 'text-xl'}`}
        >
          GeneGarden <em className="not-italic text-sage-700">AI</em>
        </span>
        {!compact && (
          <span className="block text-[9px] font-bold uppercase tracking-[0.28em] text-ink-soft">
            Evidence in bloom
          </span>
        )}
      </span>
    </div>
  )
}
