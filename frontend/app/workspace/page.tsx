'use client'
import { useEffect, useState, Suspense } from 'react'
import { RotateCcw, Loader2, Play, Square, Trash2, Copy } from 'lucide-react'
import { useRouter } from 'next/navigation'
import StepIndicator from '@/components/StepIndicator'
import StepPanel from '@/components/StepPanel'
import { useSession } from '@/hooks/useSession'
import { useToast } from '@/components/Toast'
import {
  createSnapshot,
  listSnapshots,
  renameSnapshot,
  deleteSnapshot,
  duplicateSnapshot,
  createSolveJob,
  listSolveJobs,
  cancelSolveJob,
  deleteSolveJob,
  getSolveEstimate,
} from '@/lib/api'
import type { SnapshotRecord, JobRecord } from '@/lib/api'
import type { SolveMode } from '@/lib/api'
import type { SchoolData } from '@/lib/types'

const TOTAL_STEPS = 3

// ── Workspace page ────────────────────────────────────────────────────────────

function WorkspaceContent() {
  const router    = useRouter()
  const { toast } = useToast()

  const {
    sessionId,
    schoolData,
    assignments,
    sessionError,
    setTimetable,
    updateSchoolData,
    updateAssignments,
    resetSession,
  } = useSession()

  const [currentStep, setCurrentStep] = useState(0)
  const [isSolving,   setIsSolving]   = useState(false)
  const [solveEstimate, setSolveEstimate] = useState<any | null>(null)
  const [solveMode, setSolveMode] = useState<SolveMode>('balanced')
  const [snapshots, setSnapshots] = useState<SnapshotRecord[]>([])
  const [jobs, setJobs] = useState<JobRecord[]>([])
  const [tutorialOpen, setTutorialOpen] = useState(false)
  const [tutorialStep, setTutorialStep] = useState(0)

  useEffect(() => {
    if (sessionError) {
      toast(sessionError, 'error')
    }
  }, [sessionError, toast])

  // ── Solve / generate ────────────────────────────────────────────────────────
  async function handleGenerate() {
    if (!sessionId) {
      toast('Session indisponible. Verifiez la connexion backend puis reessayez.', 'error')
      return
    }
    if (isSolving) return

    setIsSolving(true)
    try {
      const requestId = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
      const snapshotRes = await createSnapshot(sessionId, {
        school_data: schoolData,
        teacher_assignments: assignments,
      })
      const snapshotId = snapshotRes?.snapshot?.id
      if (!snapshotId) throw new Error('Version non créée')
      const jobRes = await createSolveJob(sessionId, {
        snapshot_id: snapshotId,
        mode: solveMode,
        request_id: requestId,
      })
      setJobs(prev => [jobRes.job, ...prev])
      toast('Génération lancée en arrière-plan.')
    } catch (err: any) {
      toast(err?.message || 'Erreur réseau.', 'error')
    } finally {
      setIsSolving(false)
    }
  }

  async function refreshRuns() {
    if (!sessionId) return
    try {
      const [sRes, jRes] = await Promise.all([listSnapshots(sessionId), listSolveJobs(sessionId)])
      setSnapshots(sRes.snapshots ?? [])
      setJobs((jRes.jobs ?? []).slice().reverse())
      const latestDone = (jRes.jobs ?? []).slice().reverse().find((j: JobRecord) => j.status === 'done' && j.result?.solved)
      if (latestDone?.result) {
        setTimetable(latestDone.result)
      }
    } catch {
      // keep UI responsive
    }
  }

  const tutorialSteps = [
    {
      title: 'Étape 1 — École & semaine',
      text: 'On remplit automatiquement le nom, la ville, l’année et un planning de base.',
      action: async () => {
        await updateSchoolData({
          ...schoolData,
          name: 'Académie Démo',
          city: 'Dakar',
          academic_year: '2026-2027',
          base_unit_minutes: 30,
          days: [
            { name: 'lundi', sessions: [{ name: 'Matin', start_time: '08:00', end_time: '12:00' }, { name: 'Après-midi', start_time: '14:00', end_time: '17:00' }], breaks: [] },
            { name: 'mardi', sessions: [{ name: 'Matin', start_time: '08:00', end_time: '12:00' }, { name: 'Après-midi', start_time: '14:00', end_time: '17:00' }], breaks: [] },
            { name: 'mercredi', sessions: [{ name: 'Matin', start_time: '08:00', end_time: '12:00' }], breaks: [] },
            { name: 'jeudi', sessions: [{ name: 'Matin', start_time: '08:00', end_time: '12:00' }, { name: 'Après-midi', start_time: '14:00', end_time: '17:00' }], breaks: [] },
            { name: 'vendredi', sessions: [{ name: 'Matin', start_time: '08:00', end_time: '12:00' }, { name: 'Après-midi', start_time: '14:00', end_time: '17:00' }], breaks: [] },
          ],
          rooms: [{ name: 'Salle Démo', types: ['Standard'], capacity: 40 }],
        } as any)
        setCurrentStep(1)
      },
    },
    {
      title: 'Étape 2 — Classes, enseignants, programme',
      text: 'On injecte une base réaliste pour montrer la structure complète.',
      action: async () => {
        await updateSchoolData({
          ...schoolData,
          name: 'Académie Démo',
          city: 'Dakar',
          academic_year: '2026-2027',
          base_unit_minutes: 30,
          days: [
            { name: 'lundi', sessions: [{ name: 'Matin', start_time: '08:00', end_time: '12:00' }, { name: 'Après-midi', start_time: '14:00', end_time: '17:00' }], breaks: [] },
            { name: 'mardi', sessions: [{ name: 'Matin', start_time: '08:00', end_time: '12:00' }, { name: 'Après-midi', start_time: '14:00', end_time: '17:00' }], breaks: [] },
            { name: 'mercredi', sessions: [{ name: 'Matin', start_time: '08:00', end_time: '12:00' }], breaks: [] },
            { name: 'jeudi', sessions: [{ name: 'Matin', start_time: '08:00', end_time: '12:00' }, { name: 'Après-midi', start_time: '14:00', end_time: '17:00' }], breaks: [] },
            { name: 'vendredi', sessions: [{ name: 'Matin', start_time: '08:00', end_time: '12:00' }, { name: 'Après-midi', start_time: '14:00', end_time: '17:00' }], breaks: [] },
          ],
          rooms: [{ name: 'Salle Démo', types: ['Standard'], capacity: 40 }],
          classes: [{ name: '6e A', level: 'Collège', student_count: 0 }, { name: '6e B', level: 'Collège', student_count: 0 }],
          teachers: [{ name: 'Mme Diallo', subjects: ['Mathématiques'] }, { name: 'M. Ba', subjects: ['Français'] }],
          curriculum: [
            { school_class: '6e A', subject: 'Mathématiques', weekly_hours: 4, sessions_per_week: 4, minutes_per_session: 60, total_minutes_per_week: 240 },
            { school_class: '6e B', subject: 'Mathématiques', weekly_hours: 4, sessions_per_week: 4, minutes_per_session: 60, total_minutes_per_week: 240 },
            { school_class: '6e A', subject: 'Français', weekly_hours: 4, sessions_per_week: 4, minutes_per_session: 60, total_minutes_per_week: 240 },
          ],
          subjects: [
            { name: 'Mathématiques', short_name: 'MATH', color: '#0d9488', needs_room: true },
            { name: 'Français', short_name: 'FRAN', color: '#0d9488', needs_room: true },
          ],
        } as any)
        await updateAssignments([
          { school_class: '6e A', subject: 'Mathématiques', teacher: 'Mme Diallo' },
          { school_class: '6e B', subject: 'Mathématiques', teacher: 'Mme Diallo' },
          { school_class: '6e A', subject: 'Français', teacher: 'M. Ba' },
        ])
      },
    },
    {
      title: 'Étape 3 — Lancer et comparer',
      text: 'Passe en Génération pour lancer un job et comparer les résultats.',
      action: async () => setCurrentStep(2),
    },
  ]

  useEffect(() => {
    if (!sessionId) return
    if (currentStep !== 2) return
    getSolveEstimate(sessionId)
      .then(est => setSolveEstimate(est))
      .catch(() => setSolveEstimate(null))
  }, [sessionId, currentStep, schoolData, assignments])

  useEffect(() => {
    if (!sessionId) return
    refreshRuns()
    const id = window.setInterval(() => {
      void refreshRuns()
    }, 2000)
    return () => window.clearInterval(id)
  }, [sessionId])

  // ── Reset ───────────────────────────────────────────────────────────────────
  async function handleReset() {
    try {
      await resetSession()
      setCurrentStep(0)
      toast('Session reinitialisee.')
    } catch (err: any) {
      toast(err?.message || 'Erreur reseau.', 'error')
    }
  }

  return (
    <div className="flex flex-col min-h-screen bg-gray-50 dark:bg-zinc-950">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex-shrink-0">
        <h1 className="text-sm font-semibold text-gray-800 dark:text-gray-100">
          Espace de travail
        </h1>
        <button
          onClick={handleReset}
          className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
          title="Réinitialiser la session"
        >
          <RotateCcw size={13} />
          Réinitialiser
        </button>
      </div>

      {/* Step indicator */}
      <div className="px-4 pt-4 pb-2 flex-shrink-0">
        <StepIndicator
          currentStep={currentStep}
          schoolData={schoolData}
          assignments={assignments}
          onStepClick={setCurrentStep}
        />
        <div className="mt-2">
          <button
            onClick={() => { setTutorialOpen(true); setTutorialStep(0) }}
            className="text-xs text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
          >
            Tutoriel interactif
          </button>
        </div>
      </div>

      {/* Main form panel */}
      <div className="flex-1 overflow-hidden mx-4 mb-4 bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-800 shadow-sm">
        <StepPanel
          step={currentStep}
          schoolData={schoolData}
          assignments={assignments}
          onUpdateSchoolData={(d: SchoolData) => updateSchoolData(d)}
          onUpdateAssignments={(a: any[]) => updateAssignments(a)}
          onNext={() => setCurrentStep(s => Math.min(s + 1, TOTAL_STEPS - 1))}
          onGenerate={handleGenerate}
          isSolving={isSolving}
          solveEstimate={solveEstimate}
          solveMode={solveMode}
          onSolveModeChange={setSolveMode}
        />
      </div>

      <div className="mx-4 mb-4 bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-800 shadow-sm p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-100">Versions & Jobs</h2>
          <button
            onClick={() => void refreshRuns()}
            className="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          >
            Actualiser
          </button>
        </div>
        <div className="space-y-2 max-h-56 overflow-y-auto">
          {jobs.length === 0 && (
            <p className="text-xs text-gray-500">Aucun job pour le moment.</p>
          )}
          {jobs.map((job, index) => (
            <div key={`${job.id}-${job.created_at ?? index}`} className="flex items-center gap-2 rounded-lg border border-gray-200 dark:border-gray-700 px-2 py-2">
              <div className="text-xs min-w-[130px]">
                <div className="font-medium text-gray-700 dark:text-gray-200">{job.id}</div>
                <div className="text-gray-500">{job.mode}</div>
              </div>
              <span className="text-[11px] px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
                {job.status}
              </span>
              {(job.status === 'failed' || job.status === 'timeout' || job.status === 'cancelled') && (
                <div className="min-w-0 flex-1 text-[11px] text-red-600 dark:text-red-400">
                  <div className="truncate">
                    {job.report?.reason_message || (job.status === 'timeout'
                      ? 'Limite de calcul atteinte.'
                      : "Échec de génération sans détail.")}
                  </div>
                  {job.report?.summary && (
                    <div className="truncate text-red-500/90 dark:text-red-300/90">
                      {job.report.summary}
                    </div>
                  )}
                </div>
              )}
              <div className="ml-auto flex items-center gap-1">
                {job.status === 'done' && (
                  <button
                    onClick={() => {
                      if (job.result) {
                        setTimetable(job.result)
                        toast('Résultat sélectionné.')
                        router.push('/results')
                      }
                    }}
                    className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                    title="Voir résultat"
                  >
                    <Play size={13} />
                  </button>
                )}
                {(job.status === 'running' || job.status === 'queued') && (
                  <button
                    onClick={() => sessionId && cancelSolveJob(sessionId, job.id).then(() => refreshRuns())}
                    className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                    title="Arrêter"
                  >
                    <Square size={13} />
                  </button>
                )}
                {job.status !== 'running' && job.status !== 'queued' && (
                  <button
                    onClick={() => sessionId && deleteSolveJob(sessionId, job.id).then(() => refreshRuns())}
                    className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                    title="Supprimer"
                  >
                    <Trash2 size={13} />
                  </button>
                )}
                <button
                  onClick={() => {
                    const sId = job.snapshot_id
                    if (!sId || !sessionId) return
                    duplicateSnapshot(sessionId, sId).then(() => refreshRuns())
                  }}
                  className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                  title="Dupliquer version"
                >
                  <Copy size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
        {snapshots.length > 0 && (
          <div className="mt-3 border-t border-gray-200 dark:border-gray-700 pt-2 space-y-1">
            <p className="text-[11px] text-gray-500">Versions enregistrées: {snapshots.length}</p>
            {snapshots.slice().reverse().slice(0, 5).map((snap) => (
              <div key={snap.id} className="flex items-center gap-2 text-xs">
                <span className="font-medium text-gray-700 dark:text-gray-200">{snap.name}</span>
                <span className="text-gray-400">{snap.id}</span>
                <div className="ml-auto flex items-center gap-1">
                  <button
                    onClick={async () => {
                      await updateSchoolData(snap.school_data ?? {})
                      await updateAssignments(snap.teacher_assignments ?? [])
                      const linked = jobs.find((j) => j.snapshot_id === snap.id && j.status === 'done' && j.result)
                      if (linked?.result) {
                        setTimetable(linked.result)
                      }
                      toast('Version chargée dans le formulaire.')
                    }}
                    className="px-2 py-1 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
                  >
                    Charger
                  </button>
                  <button
                    onClick={() => sessionId && duplicateSnapshot(sessionId, snap.id).then(() => refreshRuns())}
                    className="px-2 py-1 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
                  >
                    Dupliquer
                  </button>
                  <button
                    onClick={async () => {
                      if (!sessionId) return
                      const next = window.prompt('Nouveau nom de version', snap.name)
                      if (!next || !next.trim()) return
                      await renameSnapshot(sessionId, snap.id, next.trim())
                      await refreshRuns()
                    }}
                    className="px-2 py-1 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
                  >
                    Renommer
                  </button>
                  <button
                    onClick={async () => {
                      if (!sessionId) return
                      const ok = window.confirm(`Supprimer la version "${snap.name}" et ses jobs terminés liés ?`)
                      if (!ok) return
                      await deleteSnapshot(sessionId, snap.id)
                      await refreshRuns()
                      toast('Version supprimée.')
                    }}
                    className="px-2 py-1 rounded border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    Supprimer
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {tutorialOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center">
          <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-xl px-6 py-5 w-[min(520px,92vw)] space-y-3">
            <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-100">
              {tutorialSteps[tutorialStep].title}
            </h3>
            <p className="text-xs text-gray-600 dark:text-gray-300">{tutorialSteps[tutorialStep].text}</p>
            <div className="flex items-center justify-between">
              <button
                onClick={() => setTutorialOpen(false)}
                className="px-3 py-1.5 text-xs rounded border border-gray-200 dark:border-gray-700"
              >
                Fermer
              </button>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setTutorialStep((s) => Math.max(0, s - 1))}
                  disabled={tutorialStep === 0}
                  className="px-3 py-1.5 text-xs rounded border border-gray-200 dark:border-gray-700 disabled:opacity-50"
                >
                  Précédent
                </button>
                <button
                  onClick={async () => {
                    await tutorialSteps[tutorialStep].action()
                    if (tutorialStep < tutorialSteps.length - 1) setTutorialStep((s) => s + 1)
                    else setTutorialOpen(false)
                  }}
                  className="px-3 py-1.5 text-xs rounded bg-indigo-600 text-white"
                >
                  {tutorialStep < tutorialSteps.length - 1 ? 'Auto-fill & Suivant' : 'Terminer'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Solving overlay */}
      {isSolving && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center">
          <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-xl px-8 py-6 flex flex-col items-center gap-3 min-w-[280px]">
            <Loader2 size={28} className="animate-spin text-indigo-500" />
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Generation en cours...
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              Construction des contraintes et recherche d'un planning valide.
            </p>
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse" />
              <span className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse [animation-delay:150ms]" />
              <span className="h-2 w-2 rounded-full bg-indigo-400 animate-pulse [animation-delay:300ms]" />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function WorkspacePage() {
  return (
    <Suspense>
      <WorkspaceContent />
    </Suspense>
  )
}
