export function Spinner({ label = 'Loading' }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </span>
  )
}
