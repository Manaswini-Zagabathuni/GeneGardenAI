interface IconProps {
  name:
    | 'about'
    | 'arrow'
    | 'compare'
    | 'discovery'
    | 'evaluation'
    | 'home'
    | 'leaf'
    | 'search'
    | 'sparkle'
  className?: string
}

const paths: Record<IconProps['name'], React.ReactNode> = {
  home: <path d="M3 10.8 12 3l9 7.8v9.7a.5.5 0 0 1-.5.5H15v-6H9v6H3.5a.5.5 0 0 1-.5-.5z" />,
  discovery: (
    <>
      <circle cx="7" cy="7" r="3" />
      <circle cx="17" cy="6" r="2.5" />
      <circle cx="15" cy="17" r="3" />
      <path d="m9.7 8.3 4.8-1.2M8.5 9.6l4.8 5.2M16.3 8.4l-.8 5.6" />
    </>
  ),
  compare: <path d="M5 7h14M15 3l4 4-4 4M19 17H5M9 13l-4 4 4 4" />,
  evaluation: <path d="M4 20V10h4v10M10 20V4h4v16M16 20v-7h4v7M3 20h18" />,
  about: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6M12 7.5v.1" />
    </>
  ),
  search: <path d="m20 20-4.2-4.2M18 11a7 7 0 1 1-14 0 7 7 0 0 1 14 0Z" />,
  arrow: <path d="M5 12h14M14 7l5 5-5 5" />,
  sparkle: (
    <path d="M12 2c.6 5.7 2.3 7.4 8 8-5.7.6-7.4 2.3-8 8-.6-5.7-2.3-7.4-8-8 5.7-.6 7.4-2.3 8-8Z" />
  ),
  leaf: (
    <path d="M20 4C11 4 5 8.2 5 15c0 2.5 1.8 4.5 4.4 4.5C15.8 19.5 20 12.8 20 4ZM4 21c2.4-5.3 6.2-8.7 11-10.7" />
  ),
}

export function Icon({ name, className = 'h-5 w-5' }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  )
}
