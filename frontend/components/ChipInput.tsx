'use client'
import { useRef, useState, type ClipboardEvent, type KeyboardEvent } from 'react'
import { X } from 'lucide-react'

const SPLIT_REGEX = /[,;\n\t]+/

interface Props {
  value: string[]
  onChange: (next: string[]) => void
  placeholder?: string
  disabled?: boolean
  className?: string
}

function normalize(raw: string): string {
  return raw.trim()
}

function addChips(existing: string[], additions: string[]): string[] {
  const seen = new Set(existing.map(s => s.toLowerCase()))
  const next = [...existing]
  for (const raw of additions) {
    const chip = normalize(raw)
    if (!chip) continue
    const key = chip.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    next.push(chip)
  }
  return next
}

export default function ChipInput({
  value,
  onChange,
  placeholder,
  disabled,
  className,
}: Props) {
  const [draft, setDraft] = useState('')
  const inputRef = useRef<HTMLInputElement | null>(null)

  function commitDraft(extra?: string): boolean {
    const text = (extra ?? draft).trim()
    if (!text) return false
    const parts = text.split(SPLIT_REGEX).map(normalize).filter(Boolean)
    if (parts.length === 0) return false
    const next = addChips(value, parts)
    if (next.length !== value.length) onChange(next)
    setDraft('')
    return true
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    // Space and comma both commit when draft is non-empty.
    if ((e.key === ' ' || e.key === ',' || e.key === ';') && draft.trim()) {
      e.preventDefault()
      commitDraft()
      return
    }
    if (e.key === 'Enter' || e.key === 'Tab') {
      if (draft.trim()) {
        e.preventDefault()
        commitDraft()
      }
      return
    }
    if (e.key === 'Backspace' && !draft && value.length > 0) {
      e.preventDefault()
      onChange(value.slice(0, -1))
    }
  }

  function handlePaste(e: ClipboardEvent<HTMLInputElement>) {
    const pasted = e.clipboardData.getData('text')
    if (!pasted || !/[,;\n\t]|\s{2,}/.test(pasted)) return
    e.preventDefault()
    const merged = (draft + ' ' + pasted).split(/[,;\n\t\s]+/).map(normalize).filter(Boolean)
    const next = addChips(value, merged)
    if (next.length !== value.length) onChange(next)
    setDraft('')
  }

  function removeChip(idx: number) {
    onChange(value.filter((_, i) => i !== idx))
    inputRef.current?.focus()
  }

  return (
    <div
      className={
        'flex-1 min-w-0 flex flex-wrap gap-1 px-1.5 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 focus-within:ring-1 focus-within:ring-teal-500 ' +
        (className ?? '')
      }
      onClick={() => inputRef.current?.focus()}
    >
      {value.map((chip, idx) => (
        <span
          key={`${chip}-${idx}`}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-teal-50 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300"
        >
          {chip}
          {!disabled && (
            <button
              type="button"
              onClick={e => {
                e.stopPropagation()
                removeChip(idx)
              }}
              className="hover:text-teal-900 dark:hover:text-teal-100"
              aria-label={`Supprimer ${chip}`}
            >
              <X size={11} />
            </button>
          )}
        </span>
      ))}
      <input
        ref={inputRef}
        value={draft}
        onChange={e => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        onBlur={() => commitDraft()}
        placeholder={value.length === 0 ? placeholder : ''}
        disabled={disabled}
        className="flex-1 min-w-[6rem] px-1 py-0.5 text-xs bg-transparent text-gray-900 dark:text-gray-100 outline-none"
      />
    </div>
  )
}
