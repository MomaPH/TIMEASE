'use client'
import type { TimetableAssignment, BreakSlot } from '@/lib/types'

interface Props {
  assignments: TimetableAssignment[]
  days: string[]
  view: 'class' | 'teacher' | 'room'
  breaks?: BreakSlot[]
}

const DAY_LABELS: Record<string, string> = {
  lundi: 'Lun',
  mardi: 'Mar',
  mercredi: 'Mer',
  jeudi: 'Jeu',
  vendredi: 'Ven',
  samedi: 'Sam',
}

export default function TimetableGrid({ assignments, days, view, breaks = [] }: Props) {
  if (!assignments.length) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-zinc-400 dark:text-zinc-500">
        Aucune donnée à afficher
      </div>
    )
  }

  // Unique time slots sorted chronologically, including break times
  const sessionTimes = [...new Set(assignments.map(a => a.start_time))]
  const breakTimes = breaks.map(b => b.start_time)
  const allTimes = [...new Set([...sessionTimes, ...breakTimes])].sort()

  // Fast lookup: "day||time" → assignment
  const lookup = new Map<string, TimetableAssignment>()
  for (const a of assignments) {
    lookup.set(`${a.day}||${a.start_time}`, a)
  }

  // Break lookup by day + start_time
  const breakLookup = new Map<string, BreakSlot>()
  for (const b of breaks) {
    breakLookup.set(`${b.day}||${b.start_time}`, b)
  }

  function getCell(day: string, time: string): TimetableAssignment | undefined {
    return lookup.get(`${day}||${time}`)
  }

  function isContinuation(day: string, slotIndex: number): boolean {
    if (slotIndex === 0) return false
    const prev = getCell(day, allTimes[slotIndex - 1])
    const curr = getCell(day, allTimes[slotIndex])
    if (!prev || !curr) return false
    return (
      prev.teacher === curr.teacher &&
      prev.subject === curr.subject &&
      prev.school_class === curr.school_class
    )
  }

  function subLine(a: TimetableAssignment): string {
    if (view === 'class') return `${a.teacher} · ${a.room}`
    if (view === 'teacher') return `${a.school_class} · ${a.room}`
    return `${a.school_class} · ${a.teacher}`
  }

  return (
    <div className="overflow-x-auto">
      <div
        className="grid border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden"
        style={{ gridTemplateColumns: `60px repeat(${days.length}, 1fr)` }}
      >
        {/* Header row */}
        <div className="bg-zinc-50 dark:bg-zinc-800/50 border-b border-zinc-200 dark:border-zinc-700" />
        {days.map(d => (
          <div
            key={d}
            className="px-3 py-3 text-center text-xs font-semibold text-zinc-600 dark:text-zinc-400 border-b border-zinc-200 dark:border-zinc-700 uppercase tracking-wide"
          >
            {DAY_LABELS[d.toLowerCase()] || d}
          </div>
        ))}

        {/* Time rows */}
        {allTimes.map((time, ti) => {
          return (
            <div key={time} className="contents">
              {/* Time label */}
              <div className="bg-zinc-50 dark:bg-zinc-800/50 px-2 py-2 text-right text-[11px] font-mono text-zinc-400 dark:text-zinc-500 border-r border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-end">
                {time}
              </div>

              {/* Day cells */}
              {days.map((day, di) => {
                const a = getCell(day, time)
                const cont = isContinuation(day, ti)
                const isLast = di === days.length - 1
                const dayBreak = breakLookup.get(`${day}||${time}`)

                if (dayBreak) {
                  return (
                    <div
                      key={day}
                      className={`px-1.5 py-1.5 min-h-[56px] border-b border-zinc-100 dark:border-zinc-800 ${!isLast ? 'border-r' : ''}`}
                    >
                      <div className="rounded-md p-1.5 text-xs bg-zinc-100 dark:bg-zinc-800/70 text-zinc-600 dark:text-zinc-300 text-center h-full min-h-[44px] flex items-center justify-center">
                        {dayBreak.label || 'Pause'}
                      </div>
                    </div>
                  )
                }

                if (!a) {
                  return (
                    <div
                      key={day}
                      className={`px-1.5 py-1.5 min-h-[56px] border-b border-zinc-100 dark:border-zinc-800 ${!isLast ? 'border-r' : ''}`}
                    >
                      {view === 'teacher' ? (
                        <div className="rounded-md p-1.5 text-xs bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 text-center h-full min-h-[44px] flex items-center justify-center">
                          Libre
                        </div>
                      ) : (
                        <div className="h-full min-h-[44px] rounded-md bg-zinc-50 dark:bg-zinc-800/30" />
                      )}
                    </div>
                  )
                }

                const bg = a.color + '20'
                const border = a.color

                return (
                  <div
                    key={day}
                    className={`px-1.5 py-1.5 min-h-[56px] border-b border-zinc-100 dark:border-zinc-800 ${!isLast ? 'border-r' : ''}`}
                  >
                    <div
                      className="timetable-event rounded-md p-2 text-xs leading-tight h-full cursor-pointer"
                      style={{
                        backgroundColor: bg,
                        borderLeft: `3px solid ${border}`,
                        borderTop: cont ? `2px dashed ${border}` : undefined,
                      }}
                    >
                      <p className="font-semibold text-zinc-800 dark:text-zinc-100 truncate">
                        {a.subject}
                      </p>
                      <p className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate mt-0.5">
                        {subLine(a)}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
          )
        })}
      </div>
    </div>
  )
}
