import React from 'react'

export type BadgeVariant =
  | 'critical'
  | 'high'
  | 'medium'
  | 'low'
  | 'ready'
  | 'analyzing'
  | 'failed'
  | 'completed'
  | 'current'
  | 'outdated'
  | 'vulnerable'
  | 'unknown'
  | 'improved'
  | 'worsened'
  | 'unchanged'

interface StatusBadgeProps {
  status: string
  variant?: BadgeVariant
  size?: 'sm' | 'md'
  showDot?: boolean
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  variant,
  size = 'sm',
  showDot = true,
}) => {
  const norm = (variant || status || '').toLowerCase().trim()

  let style = 'bg-slate-800 text-slate-300 border-slate-700'
  let dotColor = 'bg-slate-400'

  if (norm === 'critical' || norm === 'failed' || norm === 'vulnerable' || norm === 'worsened') {
    style = 'bg-rose-500/10 text-rose-400 border-rose-500/30'
    dotColor = 'bg-rose-400'
  } else if (norm === 'high') {
    style = 'bg-orange-500/10 text-orange-400 border-orange-500/30'
    dotColor = 'bg-orange-400'
  } else if (norm === 'medium' || norm === 'outdated' || norm === 'analyzing') {
    style = 'bg-amber-500/10 text-amber-400 border-amber-500/30'
    dotColor = 'bg-amber-400'
  } else if (norm === 'low') {
    style = 'bg-blue-500/10 text-blue-400 border-blue-500/30'
    dotColor = 'bg-blue-400'
  } else if (norm === 'ready' || norm === 'completed' || norm === 'current' || norm === 'improved') {
    style = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
    dotColor = 'bg-emerald-400'
  } else if (norm === 'unchanged' || norm === 'unknown') {
    style = 'bg-slate-800 text-slate-400 border-slate-700'
    dotColor = 'bg-slate-400'
  }

  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs'

  return (
    <span
      className={`inline-flex items-center space-x-1.5 font-mono uppercase font-semibold rounded border ${style} ${sizeClass}`}
    >
      {showDot && <span className={`h-1.5 w-1.5 rounded-full ${dotColor}`} />}
      <span>{status}</span>
    </span>
  )
}

export default StatusBadge
