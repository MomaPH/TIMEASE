'use client'
import type { TimetableAssignment } from '@/lib/types'

interface Props {
  assignments: TimetableAssignment[]
  days: string[]
  view: 'class' | 'teacher' | 'room'
}

export default function TimetableGrid({ assignments, days, view }: Props) {
  if (!assignments.length) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-gray-400 dark:text-gray-500">
        Aucune donnée à afficher
      </div>
    )
  }

  // Unique time slots sorted chronologically
  const timeSlots = [...new Set(assignments.map(a => a.start_time))].sort()

  // Fast lookup: "day||time" → assignment
  const lookup = new Map<string, TimetableAssignment>()
  for (const a of assignments) {
    lookup.set(`${a.day}||${a.start_time}`, a)
  }

  function getCell(day: string, time: string): TimetableAssignment | undefined {
    return lookup.get(`${day}||${time}`)
  }

  // True when this (day, slotIndex) continues the previous slot's session
  function isContinuation(day: string, slotIndex: number): boolean {
    if (slotIndex === 0) return false
    const prev = getCell(day, timeSlots[slotIndex - 1])
    const curr = getCell(day, timeSlots[slotIndex])
    if (!prev || !curr) return false
    return (
      prev.teacher === curr.teacher &&
      prev.subject === curr.subject &&
      prev.school_class === curr.school_class
    )
  }

  // Secondary info line changes depending on perspective
  function subLine(a: TimetableAssignment): string {
    if (view === 'class') return `${a.teacher} · ${a.room}`
    if (view === 'teacher') return `${a.school_class} · ${a.room}`
    return `${a.school_class} · ${a.teacher}`
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            {/* Time label column header */}
            <th className="w-14 border-b border-gray-200 dark:border-gray-700" />
            {days.map(d => (
              <th
                key={d}
                className="px-3 py-2.5 text-center text-xs font-semibold text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700 capitalize min-w-[130px]"
              >
                {d}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {timeSlots.map((time, ti) => (
            <tr key={time} className="border-b border-gray-100 dark:border-gray-800 last:border-0">
              {/* Time label */}
              <td className="pr-2 pl-1 py-1.5 text-right text-[11px] font-mono text-gray-400 dark:text-gray-500 whitespace-nowrap align-top pt-2.5">
                {time}
              </td>

              {days.map(day => {
                const a = getCell(day, time)
                const cont = isContinuation(day, ti)

                if (!a) {
                  return (
                    <td key={day} className="px-1.5 py-1.5 align-top">
                      {view === 'teacher' ? (
                        <div className="rounded-md p-1.5 text-xs bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 text-center h-10 flex items-center justify-center">
                          Libre
                        </div>
                      ) : (
                        <div className="h-10 rounded-md bg-gray-50 dark:bg-gray-800/50" />
                      )}
                    </td>
                  )
                }

                // Hex color → 20% opacity background
                const bg = a.color + '33'
                const border = a.color

                return (
                  <td key={day} className="px-1.5 py-1.5 align-top">
                    <div
                      className="rounded-md p-1.5 text-xs leading-tight"
                      style={{
                        backgroundColor: bg,
                        borderLeft: `3px solid ${border}`,
                        borderTop: cont ? `2px dashed ${border}` : undefined,
                      }}
                    >
                      <p className="font-medium text-gray-900 dark:text-gray-100 truncate">
                        {a.subject}
                      </p>
                      <p className="text-[11px] text-gray-500 dark:text-gray-400 truncate mt-0.5">
                        {subLine(a)}
                      </p>
                    </div>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
