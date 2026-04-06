'use client'
import { useState } from 'react'
import { Check, Copy } from 'lucide-react'

interface Props {
  code: string
  language?: string
  inline?: boolean
}

export default function CodeBlock({ code, language, inline = false }: Props) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (inline) {
    return (
      <code className="bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-[11px] font-mono text-gray-900 dark:text-gray-100">
        {code}
      </code>
    )
  }

  return (
    <div className="relative group my-3">
      {/* Language label */}
      {language && (
        <div className="absolute top-2 left-3 text-[10px] font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          {language}
        </div>
      )}

      {/* Copy button */}
      <button
        onClick={handleCopy}
        title="Copier le code"
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300"
      >
        {copied ? (
          <Check size={14} className="text-teal-500" />
        ) : (
          <Copy size={14} />
        )}
      </button>

      {/* Code content */}
      <pre className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 pt-8 overflow-x-auto text-[11px] font-mono leading-relaxed border border-gray-200 dark:border-gray-700">
        <code className="text-gray-900 dark:text-gray-100">{code}</code>
      </pre>
    </div>
  )
}
