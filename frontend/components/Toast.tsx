'use client'
import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
} from 'react'
import { CheckCircle2, XCircle, Info, X } from 'lucide-react'

// ── Types ────────────────────────────────────────────────────────────────────
export type ToastType = 'success' | 'error' | 'info'

interface ToastItem {
  id: number
  message: string
  type: ToastType
}

interface ToastContextType {
  toast: (message: string, type?: ToastType) => void
}

// ── Context ──────────────────────────────────────────────────────────────────
const ToastContext = createContext<ToastContextType>({ toast: () => {} })

// ── Provider ─────────────────────────────────────────────────────────────────
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const counter = useRef(0)

  const toast = useCallback((message: string, type: ToastType = 'success') => {
    const id = ++counter.current
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 3500)
  }, [])

  function dismiss(id: number) {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Toast stack — bottom-right, above everything */}
      <div
        className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map(t => (
          <ToastBubble key={t.id} item={t} onDismiss={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// ── Single toast bubble ───────────────────────────────────────────────────────
const ICON_MAP = {
  success: CheckCircle2,
  error:   XCircle,
  info:    Info,
}

const COLOR_MAP: Record<ToastType, { wrap: string; icon: string }> = {
  success: {
    wrap: 'bg-white dark:bg-gray-800 border border-teal-200 dark:border-teal-700 text-gray-800 dark:text-gray-100',
    icon: 'text-teal-500',
  },
  error: {
    wrap: 'bg-white dark:bg-gray-800 border border-red-200 dark:border-red-700 text-gray-800 dark:text-gray-100',
    icon: 'text-red-500',
  },
  info: {
    wrap: 'bg-white dark:bg-gray-800 border border-blue-200 dark:border-blue-700 text-gray-800 dark:text-gray-100',
    icon: 'text-blue-500',
  },
}

function ToastBubble({
  item,
  onDismiss,
}: {
  item: ToastItem
  onDismiss: () => void
}) {
  const Icon = ICON_MAP[item.type]
  const c    = COLOR_MAP[item.type]

  return (
    <div
      className={`pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-sm font-medium min-w-[220px] max-w-xs animate-slide-up ${c.wrap}`}
    >
      <Icon size={16} className={`flex-shrink-0 ${c.icon}`} />
      <span className="flex-1 leading-snug">{item.message}</span>
      <button
        onClick={onDismiss}
        className="flex-shrink-0 opacity-40 hover:opacity-100 transition-opacity"
        aria-label="Fermer"
      >
        <X size={14} />
      </button>
    </div>
  )
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function useToast() {
  return useContext(ToastContext)
}
