import React, { createContext, useContext, useState, useCallback } from 'react'
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react'

export type ToastType = 'success' | 'info' | 'warning' | 'error'

export interface Toast {
  id: string
  title: string
  message?: string
  type: ToastType
  duration?: number
}

interface ToastContextType {
  toast: (title: string, options?: { message?: string; type?: ToastType; duration?: number }) => void
  success: (title: string, message?: string) => void
  error: (title: string, message?: string) => void
  info: (title: string, message?: string) => void
  warning: (title: string, message?: string) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback(
    (title: string, options?: { message?: string; type?: ToastType; duration?: number }) => {
      const id = Math.random().toString(36).substring(2, 9)
      const duration = options?.duration ?? 4000
      const newToast: Toast = {
        id,
        title,
        message: options?.message,
        type: options?.type || 'info',
        duration,
      }

      setToasts((prev) => [...prev.slice(-4), newToast]) // keep max 5 toasts

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id)
        }, duration)
      }
    },
    [removeToast]
  )

  const success = useCallback((title: string, message?: string) => {
    toast(title, { message, type: 'success' })
  }, [toast])

  const error = useCallback((title: string, message?: string) => {
    toast(title, { message, type: 'error', duration: 6000 })
  }, [toast])

  const info = useCallback((title: string, message?: string) => {
    toast(title, { message, type: 'info' })
  }, [toast])

  const warning = useCallback((title: string, message?: string) => {
    toast(title, { message, type: 'warning' })
  }, [toast])

  return (
    <ToastContext.Provider value={{ toast, success, error, info, warning }}>
      {children}
      {/* Toast Render Container */}
      <aside
        aria-live="polite"
        aria-label="Notifications"
        className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none px-4 sm:px-0"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className="pointer-events-auto flex items-start gap-3 p-3.5 rounded-lg border bg-[#0d1322] shadow-xl text-xs backdrop-blur-md transition-all animate-in fade-in slide-in-from-bottom-2 border-slate-800"
          >
            <div className="shrink-0 mt-0.5">
              {t.type === 'success' && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
              {t.type === 'error' && <AlertCircle className="h-4 w-4 text-rose-400" />}
              {t.type === 'warning' && <AlertTriangle className="h-4 w-4 text-amber-400" />}
              {t.type === 'info' && <Info className="h-4 w-4 text-blue-400" />}
            </div>
            <div className="flex-1 space-y-0.5 min-w-0">
              <p className="font-medium text-slate-100 truncate">{t.title}</p>
              {t.message && (
                <p className="text-[11px] text-slate-400 break-words leading-relaxed">{t.message}</p>
              )}
            </div>
            <button
              onClick={() => removeToast(t.id)}
              aria-label="Dismiss notification"
              className="shrink-0 text-slate-500 hover:text-slate-300 p-0.5 rounded transition"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </aside>
    </ToastContext.Provider>
  )
}

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
