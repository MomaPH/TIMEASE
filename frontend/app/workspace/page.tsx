'use client'
import { useEffect, useState, Suspense } from 'react'
import { RotateCcw, Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import StepIndicator from '@/components/StepIndicator'
import StepPanel from '@/components/StepPanel'
import { useSession } from '@/hooks/useSession'
import { useToast } from '@/components/Toast'
import { solve } from '@/lib/api'
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

  useEffect(() => {
    if (sessionError) {
      toast(sessionError, 'error')
    }
  }, [sessionError, toast])

  // ── Solve / generate ────────────────────────────────────────────────────────
  async function handleGenerate() {
    if (!sessionId || isSolving) return
    setIsSolving(true)
    try {
      const result = await solve(sessionId)
      if (result.solved) {
        setTimetable(result)
        toast('Emploi du temps généré !')
        router.push('/results')
      } else if (result.status === 'INFEASIBLE') {
        toast(result.conflict_summary || 'Aucune solution trouvée.', 'error')
      } else if (result.errors) {
        toast(result.errors.join(' '), 'error')
      } else {
        toast('Erreur inconnue lors de la génération.', 'error')
      }
    } catch (err: any) {
      toast(err?.message || 'Erreur réseau.', 'error')
    } finally {
      setIsSolving(false)
    }
  }

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
        />
      </div>

      {/* Solving overlay */}
      {isSolving && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center">
          <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-xl px-8 py-6 flex flex-col items-center gap-3">
            <Loader2 size={28} className="animate-spin text-indigo-500" />
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Génération en cours…
            </p>
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
