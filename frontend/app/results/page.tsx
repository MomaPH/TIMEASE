'use client'
import { useState, useMemo } from 'react'
import Link from 'next/link'
import { FileDown, CalendarDays, Loader2, AlertTriangle, ArrowRight, CheckCircle2, Users, Building2, BookOpen } from 'lucide-react'
import TimetableGrid from '@/components/TimetableGrid'
import { useSession } from '@/hooks/useSession'
import { useToast } from '@/components/Toast'
import { restoreSession } from '@/lib/api'
import type { TimetableAssignment, BreakSlot } from '@/lib/types'

type TabId = 'class' | 'teacher' | 'room' | 'subject'

const TABS: { id: TabId; label: string }[] = [
  { id: 'class',   label: 'Par classe' },
  { id: 'teacher', label: 'Par enseignant' },
  { id: 'room',    label: 'Par salle' },
  { id: 'subject', label: 'Par matière' },
]

// ── Skeleton ──────────────────────────────────────────────────────────────────
function GridSkeleton() {
  return (
    <div className="animate-pulse space-y-2 p-4">
      <div className="h-8 bg-zinc-100 dark:bg-zinc-800 rounded" />
      {[...Array(6)].map((_, i) => (
        <div key={i} className="h-12 bg-zinc-50 dark:bg-zinc-800/60 rounded" />
      ))}
    </div>
  )
}

export default function ResultsPage() {
  const { sessionId, timetable, schoolData, assignments: sessionAssignments } = useSession()
  const { toast }                 = useToast()

  const [activeTab, setActiveTab]     = useState<TabId>('class')
  const [selected, setSelected]       = useState<string>('')

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
  const solverWarnings: string[] = timetable?.warnings ?? []

  const unscheduled: { school_class?: string; subject?: string; teacher?: string; reason?: string }[] =
    (timetable?.unscheduled ?? []).filter((u: any) => u.subject)

  const unscheduledGroups: { cause: string; label: string; sessions: any[]; step?: number }[] =
    useMemo(() => {
      const causeStep: Record<string, number> = {
        missing_teacher: 2, room_unavailable: 3,
        no_valid_slot: 7,   constraint_conflict: 7,
      }
      return (timetable?.unscheduled_groups ?? []).map((g: any) => ({
        ...g,
        step: causeStep[g.cause] ?? undefined,
      }))
    }, [timetable])

  const isPartial = !!(unscheduled.length > 0 || (timetable && !timetable.solved && assignments.length > 0))

  // ── Breaks from school data ─────────────────────────────────────────────────
  const breaks: BreakSlot[] = useMemo(() => {
    // New format: breaks are inside each DayConfig
    const allBreaks: BreakSlot[] = []
    const days = schoolData?.days ?? []
    for (const day of days) {
      for (const brk of day.breaks ?? []) {
        allBreaks.push({
          type: 'break' as const,
          start_time: brk.start_time,
          end_time: brk.end_time,
          label: brk.name || 'Pause',
        })
      }
    }
    return allBreaks
  }, [schoolData])

  // ── Empty state (session loaded but no timetable yet) ──────────────────────
  if (!isLoading && !assignments.length) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center px-4 animate-fade-in">
        <div className="w-16 h-16 rounded-2xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center">
          <CalendarDays size={28} className="text-zinc-400 dark:text-zinc-500" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-zinc-700 dark:text-zinc-300">
            Aucun emploi du temps généré
          </h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1 max-w-xs mx-auto">
            Configurez vos données et lancez la génération depuis l'espace de travail.
          </p>
        </div>
        <Link
          href="/workspace"
          className="mt-2 px-5 py-2.5 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-sm font-medium rounded-xl hover:bg-black dark:hover:bg-zinc-200 transition-colors"
        >
          Aller à l'espace de travail
        </Link>
      </div>
    )
  }

  // ── Main ───────────────────────────────────────────────────────────────────
  return (
    <div className="animate-fade-in space-y-8">
      {/* ════════════════════════════════════════════════════════════════════
          STATS CARDS
          ════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 flex items-center justify-center">
              <Users size={16} className="text-indigo-600 dark:text-indigo-400" />
            </div>
            <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Classes</span>
          </div>
          <div className="text-2xl font-bold text-zinc-900 dark:text-white tracking-tight">{classes.length}</div>
        </div>
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/50 flex items-center justify-center">
              <BookOpen size={16} className="text-emerald-600 dark:text-emerald-400" />
            </div>
            <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Enseignants</span>
          </div>
          <div className="text-2xl font-bold text-zinc-900 dark:text-white tracking-tight">{teachers.length}</div>
        </div>
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg bg-amber-50 dark:bg-amber-950/50 flex items-center justify-center">
              <Building2 size={16} className="text-amber-600 dark:text-amber-400" />
            </div>
            <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Salles</span>
          </div>
          <div className="text-2xl font-bold text-zinc-900 dark:text-white tracking-tight">{rooms.length}</div>
        </div>
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg bg-rose-50 dark:bg-rose-950/50 flex items-center justify-center">
              {unscheduled.length === 0 ? (
                <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400" />
              ) : (
                <AlertTriangle size={16} className="text-amber-600 dark:text-amber-400" />
              )}
            </div>
            <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Conflits</span>
          </div>
          <div className="text-2xl font-bold text-zinc-900 dark:text-white tracking-tight">{unscheduled.length}</div>
          {unscheduled.length === 0 && (
            <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">Résolu ✓</span>
          )}
        </div>
      </div>

      {/* ════════════════════════════════════════════════════════════════════
          TIMETABLE SECTION
          ════════════════════════════════════════════════════════════════════ */}
      <section>
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <h2 className="text-xl font-semibold text-zinc-900 dark:text-white tracking-tight">Emploi du temps</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            {assignments.length} session(s) planifiée(s)
          </p>
        </div>

        {/* Tab bar */}
        <div className="flex gap-1 mb-5 bg-zinc-100 dark:bg-zinc-800 p-1 rounded-xl w-fit overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); setSelected('') }}
              className={[
                'px-3 sm:px-4 py-2 text-sm font-medium rounded-lg transition-all duration-150 whitespace-nowrap',
                activeTab === tab.id
                  ? 'bg-white dark:bg-zinc-900 text-indigo-600 dark:text-indigo-400 shadow-sm'
                  : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200',
              ].join(' ')}
            >
              {tab.label}
            </button>
          ))}
        </div>

      {/* ── Par matière: summary table ── */}
      {activeTab === 'subject' ? (
        isLoading ? <GridSkeleton /> : (
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm overflow-hidden overflow-x-auto">
            <table className="w-full text-sm min-w-[480px]">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/50">
                  <th className="px-5 py-3 text-left font-semibold text-zinc-700 dark:text-zinc-300">Matière</th>
                  <th className="px-5 py-3 text-center font-semibold text-zinc-700 dark:text-zinc-300">Sessions</th>
                  <th className="px-5 py-3 text-left font-semibold text-zinc-700 dark:text-zinc-300">Enseignants</th>
                  <th className="px-5 py-3 text-left font-semibold text-zinc-700 dark:text-zinc-300">Classes</th>
                </tr>
              </thead>
              <tbody>
                {subjectSummary.map((row, i) => (
                  <tr
                    key={row.subject}
                    className={`border-b border-zinc-100 dark:border-zinc-800 last:border-0 ${
                      i % 2 !== 0 ? 'bg-zinc-50/50 dark:bg-zinc-800/20' : ''
                    }`}
                  >
                    <td className="px-5 py-3 font-medium text-zinc-900 dark:text-zinc-100">{row.subject}</td>
                    <td className="px-5 py-3 text-center">
                      <span className="bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 text-xs px-2.5 py-0.5 rounded-full font-medium">
                        {row.sessions}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-zinc-600 dark:text-zinc-400">{row.teachers.join(', ')}</td>
                    <td className="px-5 py-3 text-zinc-600 dark:text-zinc-400">{row.classes.join(', ')}</td>
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
            <label className="text-sm text-zinc-600 dark:text-zinc-400 whitespace-nowrap">
              {activeTab === 'class'   && 'Classe :'}
              {activeTab === 'teacher' && 'Enseignant :'}
              {activeTab === 'room'    && 'Salle :'}
            </label>
            {isLoading ? (
              <div className="h-9 w-40 bg-zinc-200 dark:bg-zinc-700 rounded-lg animate-pulse" />
            ) : (
              <select
                value={resolvedSelected}
                onChange={e => setSelected(e.target.value)}
                className="px-3 py-2 text-sm border border-zinc-200 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {options.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            )}
          </div>

          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm overflow-x-auto">
            {isLoading ? (
              <GridSkeleton />
            ) : (
              <div className="p-4 min-w-[560px]">
                <TimetableGrid assignments={filtered} days={days} view={activeTab as 'class' | 'teacher' | 'room'} breaks={breaks} />
              </div>
            )}
          </div>
        </>
      )}
      </section>

      {/* ════════════════════════════════════════════════════════════════════
          EXPORT LINK
          ════════════════════════════════════════════════════════════════════ */}
      <div className="flex justify-center">
        <Link
          href="/exports"
          className="inline-flex items-center gap-3 px-6 py-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl hover:border-indigo-500 hover:shadow-lg transition-all group"
        >
          <FileDown size={20} className="text-indigo-600 dark:text-indigo-400" />
          <span className="font-medium text-zinc-900 dark:text-white">Exporter l'emploi du temps</span>
          <ArrowRight size={16} className="text-zinc-400 group-hover:text-indigo-500 transition-colors" />
        </Link>
      </div>

      {/* ════════════════════════════════════════════════════════════════════
          CONSTRAINTS PANEL
          ════════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

        {/* Hard constraints / unscheduled */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm p-5">
          <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">
            Sessions planifiées
          </h2>
          {unscheduled.length === 0 ? (
            <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
              Toutes les sessions ont été planifiées
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400">
                <AlertTriangle size={14} className="flex-shrink-0" />
                {unscheduled.length} session(s) non planifiée(s)
              </div>

              {/* Group cards with Corriger button */}
              {unscheduledGroups.map((g, gi) => (
                <div key={gi} className="border border-amber-200 dark:border-amber-800 rounded-xl overflow-hidden">
                  <div className="flex items-center justify-between px-3 py-2 bg-amber-50 dark:bg-amber-950/30">
                    <span className="text-xs font-semibold text-amber-800 dark:text-amber-300">
                      {g.label} — {g.sessions.filter((s: any) => s.subject).length} session(s)
                    </span>
                    {g.step !== undefined && (
                      <Link
                        href={`/workspace?step=${g.step}`}
                        className="flex items-center gap-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 transition-colors"
                      >
                        Corriger <ArrowRight size={12} />
                      </Link>
                    )}
                  </div>
                  <div className="divide-y divide-amber-100 dark:divide-amber-900/40">
                    {g.sessions.filter((s: any) => s.subject).map((u: any, i: number) => (
                      <div key={i} className="px-3 py-2 text-xs">
                        <span className="font-medium text-zinc-800 dark:text-zinc-200">
                          {[u.school_class, u.subject].filter(Boolean).join(' · ')}
                        </span>
                        {u.reason && (
                          <span className="text-zinc-500 dark:text-zinc-400 ml-1">
                            — {u.reason === 'No valid placement after domain filtering'
                              ? 'Aucun créneau valide (contraintes trop restrictives)'
                              : u.reason}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              {/* Fallback: flat list if no groups */}
              {unscheduledGroups.length === 0 && unscheduled.map((u, i) => (
                <div key={i} className="text-xs bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2">
                  <span className="font-medium text-amber-800 dark:text-amber-300">
                    {[u.school_class, u.subject].filter(Boolean).join(' · ')}
                  </span>
                  {u.reason && <span className="text-amber-600 dark:text-amber-400 ml-1">— {u.reason}</span>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Soft constraints */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm p-5">
          <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">
            Contraintes souples
          </h2>
          {softResults.length === 0 ? (
            <div className="flex items-center gap-2 text-sm text-zinc-400 dark:text-zinc-500">
              <span className="w-2 h-2 rounded-full bg-zinc-300 dark:bg-zinc-600 flex-shrink-0" />
              Aucune contrainte souple configurée
            </div>
          ) : (
            <div className="space-y-3">
              {softResults.map((s, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${s.satisfied ? 'bg-emerald-500' : 'bg-amber-400'}`} />
                  <span className="flex-1 text-sm text-zinc-700 dark:text-zinc-300 leading-snug">
                    {s.description}
                  </span>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <div className="w-20 h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${s.satisfied ? 'bg-emerald-500' : 'bg-amber-400'}`}
                        style={{ width: `${s.score}%` }}
                      />
                    </div>
                    <span className={`text-xs font-semibold w-8 text-right tabular-nums ${s.satisfied ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                      {s.score}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {solverWarnings.length > 0 && (
        <div className="mt-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm p-5">
          <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-3">
            Avertissements du solveur
          </h2>
          <div className="space-y-2">
            {solverWarnings.map((w, i) => (
              <div key={i} className="text-xs bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2 text-amber-800 dark:text-amber-200">
                {w}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
