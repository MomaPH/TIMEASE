'use client'
import { Check } from 'lucide-react'
import { STEPS, getStepStatus } from '@/lib/types'
import type { SchoolData, StepStatus } from '@/lib/types'

interface Props {
  currentStep: number
  schoolData: SchoolData
  assignments: any[]
  onStepClick: (idx: number) => void
}

function dot(status: StepStatus, isActive: boolean) {
  if (isActive) {
    return (
      <span className="w-5 h-5 rounded-full bg-teal-600 flex items-center justify-center flex-shrink-0">
        <span className="w-2 h-2 rounded-full bg-white" />
      </span>
    )
  }
  if (status === 'done') {
    return (
      <span className="w-5 h-5 rounded-full bg-teal-500 flex items-center justify-center flex-shrink-0">
        <Check size={11} className="text-white" strokeWidth={3} />
      </span>
    )
  }
  if (status === 'partial') {
    return (
      <span className="w-5 h-5 rounded-full border-2 border-amber-400 bg-amber-50 dark:bg-amber-900/20 flex-shrink-0" />
    )
  }
  return (
    <span className="w-5 h-5 rounded-full border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex-shrink-0" />
  )
}

export default function StepIndicator({ currentStep, schoolData, assignments, onStepClick }: Props) {
  return (
    <div className="flex items-start gap-0 px-4 py-3 border-b border-gray-100 dark:border-gray-800 overflow-x-auto">
      {STEPS.map((step, idx) => {
        const status   = getStepStatus(idx, schoolData, assignments)
        const isActive = idx === currentStep
        const isLast   = idx === STEPS.length - 1

        return (
          <div key={step.id} className="flex items-center min-w-0">
            {/* Step button */}
            <button
              onClick={() => onStepClick(idx)}
              title={step.label}
              className={[
                'flex flex-col items-center gap-1 px-1 py-0.5 rounded-lg transition-colors min-w-[42px]',
                isActive
                  ? 'text-teal-700 dark:text-teal-400'
                  : 'text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300',
              ].join(' ')}
            >
              {dot(status, isActive)}
              <span className={`text-[9px] font-medium leading-none text-center whitespace-nowrap ${isActive ? 'text-teal-700 dark:text-teal-400' : ''}`}>
                {step.shortLabel}
              </span>
            </button>

            {/* Connector line */}
            {!isLast && (
              <div className={[
                'h-px w-4 flex-shrink-0 mx-0.5',
                status === 'done' ? 'bg-teal-400' : 'bg-gray-200 dark:bg-gray-700',
              ].join(' ')} />
            )}
          </div>
        )
      })}
    </div>
  )
}
