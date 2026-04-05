'use client'
import { useState, useMemo } from 'react'
import Link from 'next/link'
import { FileDown, CalendarDays, Loader2 } from 'lucide-react'
import TimetableGrid from '@/components/TimetableGrid'
import { useSession } from '@/hooks/useSession'
import { useToast } from '@/components/Toast'
import { exportFile } from '@/lib/api'
import type { TimetableAssignment } from '@/lib/types'

type TabId = 'class' | 'teacher' | 'room' | 'subject'

const TABS: { id: TabId; label: string }[] = [
  { id: 'class',   label: 'Par classe' },
  { id: 'teacher', label: 'Par enseignant' },
  { id: 'room',    label: 'Par salle' },
  { id: 'subject', label: 'Par matière' },
]

const EXPORT_FORMATS = [
  { id: 'xlsx', label: 'Excel' },
  { id: 'pdf',  label: 'PDF'   },
  { id: 'docx', label: 'Word'  },
  { id: 'md',   label: 'Markdown' },
]

// ── Skeleton ──────────────────────────────────────────────────────────────────
function GridSkeleton() {
  return (
    <div className="animate-pulse space-y-2 p-4">
      <div className="h-8 bg-gray-100 dark:bg-gray-800 rounded" />
      {[...Array(6)].map((_, i) => (
        <div key={i} className="h-12 bg-gray-50 dark:bg-gray-800/60 rounded" />
      ))}
    </div>
  )
}

export default function ResultsPage() {
  const { sessionId, timetable }  = useSession()
  const { toast }                 = useToast()

  const [activeTab, setActiveTab]     = useState<TabId>('class')
  const [selected, setSelected]       = useState<string>('')
  const [downloading, setDownloading] = useState<string | null>(null)

  const assignments: TimetableAssignment[] = timetable?.assignments ?? []
  const isLoading = !sessionId

  // ── Derived entity lists ───────────────────────────────────────────────────
  const classes  = useMemo(() => [...new Set(assignments.map(a => a.school_class))].sort(), [assignments])
  const teachers = useMemo(() => [...new Set(assignments.map(a => a.teacher))].sort(),      [assignments])
  const rooms    = useMemo(() => [...new Set(assignments.map(a => a.room))].sort(),         [assignments])
  const subjects = useMemo(() => [...new Set(assignments.map(a => a.subject))].sort(),      [assignments])

  const days = useMemo<string[]>(() => {
    if (timetable?.days?.length) return timetable.days
    return [...new Set(assignments.map(a => a.day))]
  }, [assignments, timetable])

  const options = useMemo(() => {
    if (activeTab === 'class')   return classes
    if (activeTab === 'teacher') return teachers
    if (activeTab === 'room')    return rooms
    return subjects
  }, [activeTab, classes, teachers, rooms, subjects])

  const resolvedSelected = options.includes(selected) ? selected : (options[0] ?? '')

  const filtered = useMemo(() => {
    if (!resolvedSelected || activeTab === 'subject') return []
    if (activeTab === 'class')   return assignments.filter(a => a.school_class === resolvedSelected)
    if (activeTab === 'teacher') return assignments.filter(a => a.teacher      === resolvedSelected)
    return                              assignments.filter(a => a.room         === resolvedSelected)
  }, [assignments, activeTab, resolvedSelected])

  const subjectSummary = useMemo(() =>
    subjects.map(s => {
      const rows = assignments.filter(a => a.subject === s)
      return {
        subject:  s,
        sessions: rows.length,
        teachers: [...new Set(rows.map(a => a.teacher))].sort(),
        classes:  [...new Set(rows.map(a => a.school_class))].sort(),
      }
    }),
    [assignments, subjects],
  )

  const softResults: { description: string; satisfied: boolean; score: number }[] =
    timetable?.soft_results ?? []

  // ── Export ─────────────────────────────────────────────────────────────────
  async function handleExport(format: string) {
    if (!sessionId || downloading) return
    setDownloading(format)
    try {
      const blob = await exportFile(sessionId, format)
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `emploi_du_temps.${format}`
      a.click()
      URL.revokeObjectURL(url)
      toast('Fichier exporté')
    } catch {
      toast('Erreur lors de l\'export', 'error')
    } finally {
      setDownloading(null)
    }
  }

  // ── Empty state (session loaded but no timetable yet) ──────────────────────
  if (!isLoading && !assignments.length) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center px-4">
        <div className="w-16 h-16 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
          <CalendarDays size={28} className="text-gray-400 dark:text-gray-500" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-gray-700 dark:text-gray-300">
            Aucun emploi du temps généré
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-xs mx-auto">
            Configurez vos données et lancez la génération depuis l'espace de travail.
          </p>
        </div>
        <Link
          href="/workspace"
          className="mt-2 px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-xl hover:bg-teal-700 transition-colors"
        >
          Aller à l'espace de travail
        </Link>
      </div>
    )
  }

  // ── Main ───────────────────────────────────────────────────────────────────
  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Résultats</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {isLoading
              ? 'Chargement…'
              : `${assignments.length} session(s) · ${classes.length} classe(s) · ${teachers.length} enseignant(s)`
            }
          </p>
        </div>

        {/* Export buttons */}
        <div className="flex flex-wrap gap-2">
          {EXPORT_FORMATS.map(fmt => (
            <button
              key={fmt.id}
              onClick={() => handleExport(fmt.id)}
              disabled={!!downloading || isLoading}
              className="flex items-center gap-1.5 px-3 py-2 border border-gray-200 dark:border-gray-700 text-sm rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-50 text-gray-700 dark:text-gray-300"
            >
              {downloading === fmt.id
                ? <Loader2 size={14} className="animate-spin" />
                : <FileDown size={14} />
              }
              {fmt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-5 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl w-fit overflow-x-auto">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setSelected('') }}
            className={[
              'px-3 sm:px-4 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap',
              activeTab === tab.id
                ? 'bg-white dark:bg-gray-900 text-teal-700 dark:text-teal-400 shadow-sm'
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200',
            ].join(' ')}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Par matière: summary table ── */}
      {activeTab === 'subject' ? (
        isLoading ? <GridSkeleton /> : (
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm overflow-hidden overflow-x-auto">
            <table className="w-full text-sm min-w-[480px]">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                  <th className="px-5 py-3 text-left font-semibold text-gray-700 dark:text-gray-300">Matière</th>
                  <th className="px-5 py-3 text-center font-semibold text-gray-700 dark:text-gray-300">Sessions</th>
                  <th className="px-5 py-3 text-left font-semibold text-gray-700 dark:text-gray-300">Enseignants</th>
                  <th className="px-5 py-3 text-left font-semibold text-gray-700 dark:text-gray-300">Classes</th>
                </tr>
              </thead>
              <tbody>
                {subjectSummary.map((row, i) => (
                  <tr
                    key={row.subject}
                    className={`border-b border-gray-100 dark:border-gray-800 last:border-0 ${
                      i % 2 !== 0 ? 'bg-gray-50/50 dark:bg-gray-800/20' : ''
                    }`}
                  >
                    <td className="px-5 py-3 font-medium text-gray-900 dark:text-gray-100">{row.subject}</td>
                    <td className="px-5 py-3 text-center">
                      <span className="bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300 text-xs px-2.5 py-0.5 rounded-full font-medium">
                        {row.sessions}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-gray-600 dark:text-gray-400">{row.teachers.join(', ')}</td>
                    <td className="px-5 py-3 text-gray-600 dark:text-gray-400">{row.classes.join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : (
        /* ── Grid views ── */
        <>
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <label className="text-sm text-gray-600 dark:text-gray-400 whitespace-nowrap">
              {activeTab === 'class'   && 'Classe :'}
              {activeTab === 'teacher' && 'Enseignant :'}
              {activeTab === 'room'    && 'Salle :'}
            </label>
            {isLoading ? (
              <div className="h-9 w-40 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse" />
            ) : (
              <select
                value={resolvedSelected}
                onChange={e => setSelected(e.target.value)}
                className="px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
              >
                {options.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            )}
          </div>

          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm overflow-x-auto">
            {isLoading ? (
              <GridSkeleton />
            ) : (
              <div className="p-4 min-w-[560px]">
                <TimetableGrid assignments={filtered} days={days} view={activeTab as 'class' | 'teacher' | 'room'} />
              </div>
            )}
          </div>
        </>
      )}

      {/* Soft constraints satisfaction panel */}
      {softResults.length > 0 && (
        <div className="mt-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">
            Contraintes souples
          </h2>
          <div className="space-y-3">
            {softResults.map((s, i) => (
              <div key={i} className="flex items-center gap-3">
                <div
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    s.satisfied ? 'bg-teal-500' : 'bg-amber-400'
                  }`}
                />
                <span className="flex-1 text-sm text-gray-700 dark:text-gray-300 leading-snug">
                  {s.description}
                </span>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <div className="w-20 h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${
                        s.satisfied ? 'bg-teal-500' : 'bg-amber-400'
                      }`}
                      style={{ width: `${s.score}%` }}
                    />
                  </div>
                  <span
                    className={`text-xs font-semibold w-8 text-right tabular-nums ${
                      s.satisfied ? 'text-teal-600 dark:text-teal-400' : 'text-amber-600 dark:text-amber-400'
                    }`}
                  >
                    {s.score}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
