import React from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, FolderTree, RefreshCw, Plus } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  message?: string
  actionLabel?: string
  actionHref?: string
  actionIcon?: React.ReactNode
  onAction?: () => void
  loading?: boolean
  secondaryLabel?: string
  onSecondary?: () => void
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = FolderTree,
  title,
  description,
  message,
  actionLabel,
  actionHref,
  actionIcon,
  onAction,
  loading = false,
  secondaryLabel,
  onSecondary,
}) => {
  const displayText = description || message || ''

  return (
    <div className="p-8 sm:p-12 text-center rounded-xl border border-slate-800/80 bg-[#0d1322]/60 flex flex-col items-center justify-center space-y-3 max-w-md mx-auto my-6">
      <div className="h-11 w-11 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-400">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      {displayText && (
        <p className="text-xs text-slate-400 leading-relaxed max-w-xs">{displayText}</p>
      )}
      {(actionLabel || secondaryLabel) && (
        <div className="pt-2 flex items-center justify-center gap-2">
          {actionLabel && actionHref && (
            <Link
              to={actionHref}
              className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition"
            >
              {actionIcon || <Plus className="h-3.5 w-3.5" />}
              <span>{actionLabel}</span>
            </Link>
          )}

          {actionLabel && onAction && !actionHref && (
            <button
              type="button"
              onClick={onAction}
              disabled={loading}
              className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition disabled:opacity-50"
            >
              {loading ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                actionIcon || <Plus className="h-3.5 w-3.5" />
              )}
              <span>{actionLabel}</span>
            </button>
          )}

          {secondaryLabel && onSecondary && (
            <button
              type="button"
              onClick={onSecondary}
              className="px-3 py-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-white text-xs transition"
            >
              {secondaryLabel}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export const ErrorState: React.FC<{
  title?: string
  message: string
  onRetry?: () => void
}> = ({ title = 'Something went wrong', message, onRetry }) => {
  return (
    <div className="p-6 text-center rounded-xl border border-rose-900/40 bg-rose-950/10 flex flex-col items-center justify-center space-y-2.5 max-w-md mx-auto my-6">
      <div className="h-9 w-9 rounded-lg bg-rose-950/40 border border-rose-900/60 flex items-center justify-center text-rose-400">
        <AlertCircle className="h-4 w-4" />
      </div>
      <h4 className="text-xs font-semibold text-rose-300">{title}</h4>
      <p className="text-[11px] text-slate-400 leading-relaxed max-w-xs">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 inline-flex items-center space-x-1.5 px-3 py-1 rounded-md bg-rose-600/20 border border-rose-500/40 text-rose-300 hover:bg-rose-600/30 text-xs font-mono transition"
        >
          <RefreshCw className="h-3 w-3" />
          <span>Try Again</span>
        </button>
      )}
    </div>
  )
}
