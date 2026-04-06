'use client'
import { useState, useCallback, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Check, Copy, Bot, RefreshCw, Pencil } from 'lucide-react'
import type { ChatMessage as ChatMessageType } from '@/lib/types'
import CodeBlock from './CodeBlock'

interface Props {
  message: ChatMessageType & { _streamingId?: string }
  onOptionSelect?: (value: string) => void
  onEdit?: () => void
  onRegenerate?: () => void
  isLastMessage?: boolean
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

function EditableCell({ 
  value, 
  onChange, 
  cellKey,
  isHeader 
}: { 
  value: string
  onChange: (cellKey: string, newValue: string) => void
  cellKey: string
  isHeader?: boolean
}) {
  const [localValue, setLocalValue] = useState(value)
  const [isFocused, setIsFocused] = useState(false)

  const handleBlur = () => {
    setIsFocused(false)
    if (localValue !== value) {
      onChange(cellKey, localValue)
    }
  }

  if (isHeader) {
    return <span>{value}</span>
  }

  return (
    <input
      type="text"
      value={localValue}
      onChange={(e) => setLocalValue(e.target.value)}
      onFocus={() => setIsFocused(true)}
      onBlur={handleBlur}
      onKeyDown={(e) => {
        if (e.key === 'Enter') {
          e.currentTarget.blur()
        }
      }}
      className={`
        w-full bg-transparent border-0 outline-none px-0 py-0
        transition-all
        ${isFocused ? 'ring-1 ring-teal-500 rounded px-1' : 'hover:bg-teal-50 dark:hover:bg-teal-900/20'}
      `}
      title="Cliquez pour modifier"
    />
  )
}

export default function ChatMessage({ message, onOptionSelect, onEdit, onRegenerate, isLastMessage }: Props) {
  // Track editable table data: stores cell values by their position in the original markdown
  const [tableEdits, setTableEdits] = useState<{ [key: string]: string }>({})
  
  // Detect if this message has confirmation options (editable table context)
  const hasConfirmation = useMemo(() => {
    return message.options?.some(opt => 
      opt.label.includes('Confirmer') || 
      opt.label.includes('✅')
    )
  }, [message.options])

  // Track if content contains a table
  const hasTable = useMemo(() => {
    return message.content.includes('|') && message.content.split('\n').filter(line => line.includes('|')).length >= 2
  }, [message.content])

  const shouldUseEditableTables = hasTable && hasConfirmation

  const handleCellEdit = useCallback((key: string, newValue: string) => {
    setTableEdits(prev => ({
      ...prev,
      [key]: newValue
    }))
  }, [])

  // Handle option selection with edited table data
  const handleOptionClick = useCallback((optValue: string) => {
    if (!onOptionSelect) return

    // If there are table edits and this is a confirmation, reconstruct the table
    if (Object.keys(tableEdits).length > 0 && shouldUseEditableTables) {
      // Parse the markdown table from the message
      const lines = message.content.split('\n')
      const tableLines = lines.filter(line => line.trim().startsWith('|'))
      
      if (tableLines.length > 0) {
        // Reconstruct the table with edits applied
        const updatedTable = tableLines.map((line, lineIdx) => {
          const cells = line.split('|').map(c => c.trim()).filter(c => c !== '')
          // Skip separator lines (contains only dashes and colons)
          if (cells.every(c => /^[-:]+$/.test(c))) return line
          
          return '| ' + cells.map((cell, cellIdx) => {
            const key = `${lineIdx}-${cellIdx}`
            return tableEdits[key] !== undefined ? tableEdits[key] : cell
          }).join(' | ') + ' |'
        }).join('\n')

        // Send the option value followed by the edited table
        const messageWithEdits = `${optValue}\n\nTableau modifié :\n${updatedTable}`
        onOptionSelect(messageWithEdits)
        return
      }
    }

    // No edits or no table - just send the option value
    onOptionSelect(optValue)
  }, [onOptionSelect, tableEdits, shouldUseEditableTables, message.content])

  // Custom markdown components with conditional editable tables
  const mdComponents = useMemo(() => ({
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
        <table className={`text-xs border-collapse w-full ${shouldUseEditableTables ? 'editable-table' : ''}`}>
          {children}
        </table>
        {shouldUseEditableTables && (
          <div className="text-[10px] text-teal-600 dark:text-teal-400 mt-1 italic">
            💡 Cliquez sur une cellule pour modifier les valeurs avant de confirmer
          </div>
        )}
      </div>
    ),
    thead: ({ children }: any) => (
      <thead className="bg-gray-100 dark:bg-gray-700">{children}</thead>
    ),
    tbody: ({ children }: any) => (
      <tbody>{children}</tbody>
    ),
    tr: ({ children, isHeader }: any) => (
      <tr className={shouldUseEditableTables && !isHeader ? 'hover:bg-teal-50/30 dark:hover:bg-teal-900/10 transition-colors' : ''}>
        {children}
      </tr>
    ),
    th: ({ children }: any) => (
      <th className="border border-gray-200 dark:border-gray-600 px-2 py-1 text-left font-semibold">{children}</th>
    ),
    td: ({ children, node }: any) => {
      if (!shouldUseEditableTables) {
        return (
          <td className="border border-gray-200 dark:border-gray-600 px-2 py-1">
            {children}
          </td>
        )
      }

      // Extract text content from children
      const extractText = (node: any): string => {
        if (typeof node === 'string') return node
        if (Array.isArray(node)) return node.map(extractText).join('')
        if (node?.props?.children) return extractText(node.props.children)
        return ''
      }

      const cellText = extractText(children)
      
      const cellKey = `${node?.position?.start?.line || 0}-${node?.position?.start?.column || 0}`
      const displayValue = tableEdits[cellKey] !== undefined ? tableEdits[cellKey] : cellText
      
      return (
        <td className="border border-gray-200 dark:border-gray-600 px-2 py-1">
          <EditableCell
            value={String(displayValue)}
            onChange={handleCellEdit}
            cellKey={cellKey}
          />
        </td>
      )
    },
    code: ({ inline, children, className }: any) => {
      const match = /language-(\w+)/.exec(className || '')
      const language = match ? match[1] : undefined
      const codeString = String(children).replace(/\n$/, '')
      
      return (
        <CodeBlock 
          code={codeString} 
          language={language}
          inline={inline}
        />
      )
    },
    blockquote: ({ children }: any) => (
      <blockquote className="border-l-2 border-teal-400 pl-3 italic text-gray-600 dark:text-gray-400 mb-2">
        {children}
      </blockquote>
    ),
    h1: ({ children }: any) => <h3 className="font-bold text-base mb-1 mt-2">{children}</h3>,
    h2: ({ children }: any) => <h3 className="font-semibold text-sm mb-1 mt-2">{children}</h3>,
    h3: ({ children }: any) => <h3 className="font-semibold text-sm mb-1 mt-1">{children}</h3>,
    hr:  () => <hr className="my-2 border-gray-200 dark:border-gray-700" />,
  }), [shouldUseEditableTables, tableEdits, handleCellEdit])

  // ── User bubble ──────────────────────────────────────────────────────────
  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-3 animate-fade-in group">
        <div className="flex flex-col items-end max-w-[80%]">
          <div className="bg-teal-600 text-white text-sm px-4 py-2.5 rounded-2xl rounded-tr-sm leading-relaxed shadow-sm">
            {message.content}
          </div>
          {/* Edit button for user messages */}
          {onEdit && (
            <button
              onClick={onEdit}
              className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 flex items-center gap-1 px-2 py-1"
              title="Modifier le message"
            >
              <Pencil size={11} />
              <span>Modifier</span>
            </button>
          )}
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
        <div className={`bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-sm px-4 py-3 rounded-2xl rounded-tl-sm text-gray-800 dark:text-gray-200 shadow-sm ${shouldUseEditableTables ? 'ring-1 ring-teal-200 dark:ring-teal-800' : ''}`}>
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
                onClick={() => handleOptionClick(opt.value)}
                className="px-3 py-1.5 text-xs font-medium rounded-xl border border-teal-300 dark:border-teal-700 text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-900/20 hover:bg-teal-100 dark:hover:bg-teal-900/40 hover:border-teal-500 transition-all active:scale-95"
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}

        {/* Copy button */}
        <div className="flex mt-1 pl-1 gap-2">
          <CopyButton text={message.content} />
          {/* Regenerate button for last AI message */}
          {message.role === 'ai' && isLastMessage && onRegenerate && !message._streamingId && (
            <button
              onClick={onRegenerate}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
              title="Régénérer la réponse"
            >
              <RefreshCw size={13} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
