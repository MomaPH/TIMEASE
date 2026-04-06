'use client'
import { useRef, useEffect, useState, KeyboardEvent } from 'react'
import { Paperclip, Send, Loader2, Square } from 'lucide-react'

interface Props {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  onStop?: () => void
  onFileUpload: (file: File) => void
  isLoading: boolean
  isStreaming: boolean
  disabled: boolean
  placeholder?: string
  sessionId?: string | null
}

export default function ChatInput({
  value,
  onChange,
  onSend,
  onStop,
  onFileUpload,
  isLoading,
  isStreaming,
  disabled,
  placeholder = 'Message…',
  sessionId
}: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const [showHint, setShowHint] = useState(false)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    // Reset height to auto to get correct scrollHeight
    textarea.style.height = 'auto'
    // Set height to scrollHeight, max 200px (roughly 8 lines)
    const newHeight = Math.min(textarea.scrollHeight, 200)
    textarea.style.height = `${newHeight}px`
  }, [value])

  // Focus on mount
  useEffect(() => {
    if (sessionId && !disabled) {
      textareaRef.current?.focus()
    }
  }, [sessionId, disabled])

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Ctrl/Cmd + Enter to send
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      onSend()
      return
    }

    // Enter without Shift sends (unless streaming)
    if (e.key === 'Enter' && !e.shiftKey && !isStreaming) {
      e.preventDefault()
      onSend()
      return
    }

    // Show hint when Enter is pressed with Shift
    if (e.key === 'Enter' && e.shiftKey) {
      setShowHint(true)
      setTimeout(() => setShowHint(false), 2000)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      onFileUpload(file)
      // Reset input
      e.target.value = ''
    }
  }

  const canSend = value.trim() && !isLoading && sessionId && !disabled

  return (
    <div className="flex-shrink-0 border-t border-gray-100 dark:border-gray-800">
      {/* Character count hint (when approaching limit) */}
      {value.length > 8000 && (
        <div className="px-4 py-1 text-xs text-center text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/20">
          {value.length} / 10000 caractères
        </div>
      )}

      <div className="px-3 sm:px-4 py-3">
        <div className="flex items-end gap-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm focus-within:ring-2 focus-within:ring-teal-500/50 focus-within:border-teal-500 transition-all">
          {/* File upload button */}
          <button
            onClick={() => fileRef.current?.click()}
            title="Joindre un fichier"
            disabled={isLoading || !sessionId || disabled}
            suppressHydrationWarning
            className="text-gray-400 hover:text-teal-600 dark:hover:text-teal-400 flex-shrink-0 transition-colors p-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 disabled:opacity-50 disabled:hover:bg-transparent"
          >
            <Paperclip size={18} />
          </button>
          <input
            type="file"
            ref={fileRef}
            className="hidden"
            accept=".xlsx,.xls,.csv,.docx,.txt,.pdf,.json,.md,.markdown,.yaml,.yml"
            onChange={handleFileChange}
          />

          {/* Auto-expanding textarea */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={e => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={isLoading || !sessionId || disabled}
              rows={1}
              suppressHydrationWarning
              className="w-full px-2 py-2.5 bg-transparent text-sm focus:outline-none text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 disabled:opacity-60 resize-none"
              style={{ minHeight: '2.5rem', maxHeight: '200px' }}
            />

            {/* Keyboard shortcut hint */}
            {showHint && (
              <div className="absolute -top-8 left-0 text-[10px] text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded shadow-sm animate-fade-in">
                Ctrl+Entrée pour envoyer
              </div>
            )}
          </div>

          {/* Send or Stop button */}
          {isStreaming && onStop ? (
            <button
              onClick={onStop}
              title="Arrêter la génération"
              suppressHydrationWarning
              className="p-2.5 rounded-xl bg-red-500 text-white hover:bg-red-600 transition-colors flex-shrink-0 mr-1"
            >
              <Square size={16} fill="currentColor" />
            </button>
          ) : (
            <button
              onClick={onSend}
              disabled={!canSend}
              title={canSend ? 'Envoyer (Ctrl+Entrée)' : ''}
              suppressHydrationWarning
              className="p-2.5 rounded-xl bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex-shrink-0 mr-1"
            >
              {isLoading && !isStreaming ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Send size={16} />
              )}
            </button>
          )}
        </div>

        {/* Helper text */}
        <div className="mt-1.5 px-1 flex items-center justify-between text-[10px] text-gray-400 dark:text-gray-500">
          <span>Entrée pour nouvelle ligne • Ctrl+Entrée pour envoyer</span>
          {value.length > 0 && (
            <span className="tabular-nums">{value.length}</span>
          )}
        </div>
      </div>
    </div>
  )
}
