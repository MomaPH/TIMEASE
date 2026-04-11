'use client'
import { ChevronRight } from 'lucide-react'
import type { SchoolData } from '@/lib/types'
import type { SolveMode } from '@/lib/api'
import EcoleStep      from './steps/EcoleStep'
import ClassCardsStep from './steps/ClassCardsStep'
import GenerationStep from './steps/GenerationStep'

const STEP_TITLES = [
  'École & Semaine',
  'Classes & Programme',
  'Génération',
]

interface Props {
  step: number
  schoolData: SchoolData
  assignments: any[]
  onUpdateSchoolData: (d: SchoolData) => void
  onUpdateAssignments: (a: any[]) => void
  onNext: () => void
  onGenerate: () => void
  isSolving: boolean
  solveEstimate: any | null
  solveMode: SolveMode
  onSolveModeChange: (mode: SolveMode) => void
}

export default function StepPanel({
  step,
  schoolData,
  assignments,
  onUpdateSchoolData,
  onUpdateAssignments,
  onNext,
  onGenerate,
  isSolving,
  solveEstimate,
  solveMode,
  onSolveModeChange,
}: Props) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
        <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
          {STEP_TITLES[step] ?? ''}
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {step === 0 && (
          <EcoleStep data={schoolData} onUpdate={onUpdateSchoolData} />
        )}
        {step === 1 && (
          <ClassCardsStep
            data={schoolData}
            assignments={assignments}
            onUpdateData={onUpdateSchoolData}
            onUpdateAssignments={onUpdateAssignments}
          />
        )}
        {step === 2 && (
          <GenerationStep
            data={schoolData}
            assignments={assignments}
            onGenerate={onGenerate}
            isSolving={isSolving}
            solveEstimate={solveEstimate}
            solveMode={solveMode}
            onSolveModeChange={onSolveModeChange}
          />
        )}
      </div>

      {step < 2 && (
        <div className="px-5 py-3 border-t border-gray-100 dark:border-gray-800 flex-shrink-0">
          <button
            onClick={onNext}
            className="w-full py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-xl flex items-center justify-center gap-2 transition-colors"
          >
            Suivant <ChevronRight size={15} />
          </button>
        </div>
      )}
    </div>
  )
}
