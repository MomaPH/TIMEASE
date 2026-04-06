'use client'
import { AlertCircle, AlertTriangle, X } from 'lucide-react'
import type { ValidationError } from '@/lib/validation'

interface Props {
  errors: ValidationError[]
  onDismiss?: () => void
  onAskAI?: () => void
}

export default function ValidationErrorPanel({ errors, onDismiss, onAskAI }: Props) {
  if (errors.length === 0) return null

  const criticalErrors = errors.filter(e => e.severity === 'error')
  const warnings = errors.filter(e => e.severity === 'warning')

  return (
    <div className="space-y-2 mb-4">
      {/* Critical errors */}
      {criticalErrors.map((error, idx) => (
        <div
          key={`error-${idx}`}
          className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-xl p-4 animate-fade-in"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" size={18} />
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold text-sm text-red-900 dark:text-red-200 mb-1">
                {error.message}
              </h4>
              {error.details && (
                <p className="text-xs text-red-700 dark:text-red-300 whitespace-pre-line leading-relaxed">
                  {error.details}
                </p>
              )}
              {error.affectedItems && error.affectedItems.length > 0 && (
                <ul className="mt-2 text-xs text-red-700 dark:text-red-300 space-y-1 list-disc list-inside">
                  {error.affectedItems.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              )}
            </div>
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="text-red-400 hover:text-red-600 dark:hover:text-red-200 p-1"
                title="Fermer"
              >
                <X size={14} />
              </button>
            )}
          </div>
        </div>
      ))}

      {/* Warnings */}
      {warnings.map((warning, idx) => (
        <div
          key={`warning-${idx}`}
          className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-xl p-4 animate-fade-in"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" size={18} />
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold text-sm text-amber-900 dark:text-amber-200 mb-1">
                {warning.message}
              </h4>
              {warning.details && (
                <p className="text-xs text-amber-700 dark:text-amber-300 whitespace-pre-line leading-relaxed">
                  {warning.details}
                </p>
              )}
            </div>
          </div>
        </div>
      ))}

      {/* Ask AI button (only for errors) */}
      {criticalErrors.length > 0 && onAskAI && (
        <button
          onClick={onAskAI}
          className="w-full mt-2 px-4 py-2.5 text-sm font-medium rounded-xl border-2 border-teal-300 dark:border-teal-700 text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-900/20 hover:bg-teal-100 dark:hover:bg-teal-900/40 transition-all flex items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          Demander à l'IA de m'aider
        </button>
      )}
    </div>
  )
}
