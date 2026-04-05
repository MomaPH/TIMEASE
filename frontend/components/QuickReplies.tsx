interface Props {
  replies: string[]
  onSelect: (reply: string) => void
}

export default function QuickReplies({ replies, onSelect }: Props) {
  if (!replies.length) return null

  return (
    <div className="flex flex-wrap gap-2 mb-1">
      {replies.map((r, i) => (
        <button
          key={r}
          onClick={() => onSelect(r)}
          className="animate-fade-in text-xs px-3 py-1.5 border border-teal-300 dark:border-teal-700 text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-900/20 rounded-full hover:bg-teal-100 dark:hover:bg-teal-800/40 transition-colors"
          style={{ animationDelay: `${i * 45}ms` }}
        >
          {r}
        </button>
      ))}
    </div>
  )
}
