'use client'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Check, Copy, Bot } from 'lucide-react'
import type { ChatMessage as ChatMessageType } from '@/lib/types'

interface Props {
  message: ChatMessageType & { _streamingId?: string }
  onOptionSelect?: (value: string) => void
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text).then(() => {
          setCopied(true)
          setTimeout(() => setCopied(false), 1800)
        })
      }}
      title="Copier"
      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
    >
      {copied ? <Check size={13} className="text-teal-500" /> : <Copy size={13} />}
    </button>
  )
}

const mdComponents = {
  p: ({ children }: any) => (
    <div className="mb-2 last:mb-0 leading-relaxed">{children}</div>
  ),
  strong: ({ children }: any) => (
    <strong className="font-semibold text-gray-900 dark:text-gray-100">{children}</strong>
  ),
  ul: ({ children }: any) => (
    <ul className="mb-2 ml-4 space-y-0.5 list-disc">{children}</ul>
  ),
  ol: ({ children }: any) => (
    <ol className="mb-2 ml-4 space-y-0.5 list-decimal">{children}</ol>
  ),
  li: ({ children }: any) => (
    <li className="leading-relaxed">{children}</li>
  ),
  table: ({ children }: any) => (
    <div className="overflow-x-auto mb-2">
      <table className="text-xs border-collapse w-full">{children}</table>
    </div>
  ),
  thead: ({ children }: any) => (
    <thead className="bg-gray-100 dark:bg-gray-700">{children}</thead>
  ),
  th: ({ children }: any) => (
    <th className="border border-gray-200 dark:border-gray-600 px-2 py-1 text-left font-semibold">{children}</th>
  ),
  td: ({ children }: any) => (
    <td className="border border-gray-200 dark:border-gray-600 px-2 py-1">{children}</td>
  ),
  code: ({ inline, children }: any) =>
    inline ? (
      <code className="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded text-xs font-mono">
        {children}
      </code>
    ) : (
      <pre className="bg-gray-100 dark:bg-gray-800 rounded-lg p-3 overflow-x-auto text-xs font-mono mb-2">
        <code>{children}</code>
      </pre>
    ),
  blockquote: ({ children }: any) => (
    <blockquote className="border-l-2 border-teal-400 pl-3 italic text-gray-600 dark:text-gray-400 mb-2">
      {children}
    </blockquote>
  ),
  h1: ({ children }: any) => <h3 className="font-bold text-base mb-1 mt-2">{children}</h3>,
  h2: ({ children }: any) => <h3 className="font-semibold text-sm mb-1 mt-2">{children}</h3>,
  h3: ({ children }: any) => <h3 className="font-semibold text-sm mb-1 mt-1">{children}</h3>,
  hr:  () => <hr className="my-2 border-gray-200 dark:border-gray-700" />,
}

export default function ChatMessage({ message, onOptionSelect }: Props) {
  // ── User bubble ──────────────────────────────────────────────────────────
  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-3 animate-fade-in">
        <div className="max-w-[80%] bg-teal-600 text-white text-sm px-4 py-2.5 rounded-2xl rounded-tr-sm leading-relaxed shadow-sm">
          {message.content}
        </div>
      </div>
    )
  }

  // ── System notification ──────────────────────────────────────────────────
  if (message.role === 'system') {
    return (
      <div className="flex justify-center mb-2 animate-fade-in">
        <span className="text-xs text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-900/20 border border-teal-200 dark:border-teal-800 px-3 py-1 rounded-full">
          {message.content}
        </span>
      </div>
    )
  }

  // ── AI bubble ────────────────────────────────────────────────────────────
  return (
    <div className="flex justify-start mb-3 animate-fade-in group">
      {/* Avatar */}
      <div className="flex-shrink-0 w-7 h-7 rounded-full bg-teal-100 dark:bg-teal-900/40 flex items-center justify-center mr-2 mt-0.5">
        <Bot size={14} className="text-teal-600 dark:text-teal-400" />
      </div>

      <div className="flex flex-col max-w-[82%] min-w-0">
        {/* Message bubble */}
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-sm px-4 py-3 rounded-2xl rounded-tl-sm text-gray-800 dark:text-gray-200 shadow-sm">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={mdComponents as any}
          >
            {message.content}
          </ReactMarkdown>
          {/* Streaming cursor */}
          {(message as any)._streamingId && (
            <span className="inline-block w-[3px] h-[1.1em] bg-teal-500 dark:bg-teal-400 ml-0.5 align-middle animate-cursor-blink" />
          )}
        </div>

        {/* Interactive option chips */}
        {message.options && message.options.length > 0 && onOptionSelect && (
          <div className="flex flex-wrap gap-2 mt-2 pl-1">
            {message.options.map((opt: { label: string; value: string }, i: number) => (
              <button
                key={i}
                onClick={() => onOptionSelect(opt.value)}
                className="px-3 py-1.5 text-xs font-medium rounded-xl border border-teal-300 dark:border-teal-700 text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-900/20 hover:bg-teal-100 dark:hover:bg-teal-900/40 hover:border-teal-500 transition-all active:scale-95"
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}

        {/* Copy button */}
        <div className="flex mt-1 pl-1">
          <CopyButton text={message.content} />
        </div>
      </div>
    </div>
  )
}
