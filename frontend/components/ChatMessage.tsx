import type { ChatMessage as ChatMessageType } from '@/lib/types'

interface Props {
  message: ChatMessageType
  onConfirm?: () => void
  onReject?: () => void
}

export default function ChatMessage({ message, onConfirm, onReject }: Props) {
  // ── User bubble ────────────────────────────────────────────────────────
  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-3 animate-fade-in">
        <div className="max-w-[78%] bg-teal-600 text-white text-sm px-4 py-2.5 rounded-2xl rounded-tr-sm leading-relaxed shadow-sm">
          {message.content}
        </div>
      </div>
    )
  }

  // ── Confirm card ───────────────────────────────────────────────────────
  if (message.role === 'confirm') {
    return (
      <div className="mb-3 animate-fade-in">
        <div className="border border-teal-200 dark:border-teal-800 bg-teal-50 dark:bg-teal-900/20 rounded-xl p-4">
          <p className="text-sm font-semibold mb-2 text-gray-800 dark:text-gray-100">
            Données extraites — veuillez confirmer
          </p>
          <pre className="text-xs text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-all mb-3 max-h-44 leading-relaxed">
            {message.content}
          </pre>
          <div className="flex gap-2">
            {onConfirm && (
              <button
                onClick={onConfirm}
                className="px-4 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-sm rounded-lg transition-colors font-medium"
              >
                Confirmer
              </button>
            )}
            {onReject && (
              <button
                onClick={onReject}
                className="px-4 py-1.5 border border-gray-300 dark:border-gray-600 text-sm rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                Corriger
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }

  // ── AI bubble ──────────────────────────────────────────────────────────
  return (
    <div className="flex justify-start mb-3 animate-fade-in">
      <div className="max-w-[78%] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-sm px-4 py-2.5 rounded-2xl rounded-tl-sm text-gray-800 dark:text-gray-200 leading-relaxed shadow-sm whitespace-pre-wrap">
        {message.content}
      </div>
    </div>
  )
}
