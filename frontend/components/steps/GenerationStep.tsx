'use client'
import { useMemo } from 'react'
import { Loader2, ChevronRight } from 'lucide-react'
import type { SchoolData } from '@/lib/types'
import { getChecklistItems, getMissingAssignments } from '@/lib/types'
import { validateHourBarriers } from '@/lib/validation'
import ValidationErrorPanel from '@/components/ValidationErrorPanel'

interface Props {
  data: SchoolData
  assignments: any[]
  onGenerate: () => void
  isSolving: boolean
}

export default function GenerationStep({ data, assignments, onGenerate, isSolving }: Props) {
  const checklist        = getChecklistItems(data, assignments)
  const ready            = checklist.every(i => i.done)
  const missing          = getMissingAssignments(data, assignments)
  const validationErrors = useMemo(() => validateHourBarriers(data), [data])
  const hasErrors        = validationErrors.some(e => e.severity === 'error')

  const stats = [
    { label: 'Classes',      count: data.classes?.length    ?? 0 },
    { label: 'Enseignants',  count: data.teachers?.length   ?? 0 },
    { label: 'Salles',       count: data.rooms?.length      ?? 0 },
    { label: 'Matières',     count: data.subjects?.length   ?? 0 },
    { label: 'Affectations', count: assignments.length             },
    { label: 'Programme',    count: data.curriculum?.length ?? 0 },
    { label: 'Contraintes',  count: data.constraints?.length ?? 0 },
  ]

  return (
    <div className="space-y-5">

      {/* School summary */}
      {data.name && (
        <div className="bg-teal-50 dark:bg-teal-900/20 border border-teal-200 dark:border-teal-800 rounded-xl p-4">
          <h3 className="font-semibold text-teal-800 dark:text-teal-200 text-sm">{data.name}</h3>
          {(data.city || data.academic_year) && (
            <p className="text-xs text-teal-600 dark:text-teal-400 mt-0.5">
              {[data.city, data.academic_year].filter(Boolean).join(' · ')}
            </p>
          )}
          {(data.days?.length ?? 0) > 0 && (
            <p className="text-xs text-teal-600 dark:text-teal-400 mt-0.5">
              {data.days?.map(d => d.name).join(', ')} · {data.days?.[0]?.sessions?.length ?? 0} session(s)/jour
            </p>
          )}
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-2">
        {stats.map(s => (
          <div key={s.label} className="text-center bg-gray-50 dark:bg-gray-800/50 rounded-lg py-2 px-1">
            <div className="text-lg font-bold text-gray-900 dark:text-white">{s.count}</div>
            <div className="text-[10px] text-gray-500 dark:text-gray-400 leading-tight">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Validation errors */}
      {validationErrors.length > 0 && (
        <ValidationErrorPanel errors={validationErrors} />
      )}

      {/* Readiness checklist */}
      <div className="space-y-2">
        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          Conditions pour générer
        </h4>
        {checklist.map((item) => (
          <div key={item.id} className="flex items-center gap-2.5">
            <span className="text-base leading-none">
              {item.done ? '✓' : '✗'}
            </span>
            <span className={`text-xs ${item.done ? 'text-gray-700 dark:text-gray-300' : 'text-red-500 dark:text-red-400'}`}>
              {item.label}
            </span>
          </div>
        ))}
      </div>

      {/* Missing assignments list */}
      {missing.length > 0 && (
        <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg space-y-1">
          <p className="text-xs font-medium text-amber-800 dark:text-amber-200">
            ⚠ Affectations manquantes :
          </p>
          <ul className="text-xs text-amber-700 dark:text-amber-300 space-y-0.5">
            {missing.slice(0, 10).map((m, i) => (
              <li key={i}>• {m.school_class}/{m.subject}</li>
            ))}
            {missing.length > 10 && (
              <li className="italic">…et {missing.length - 10} autres</li>
            )}
          </ul>
        </div>
      )}

      {/* Generate button */}
      <button
        onClick={onGenerate}
        disabled={!ready || isSolving || hasErrors}
        className={`w-full py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all ${
          ready && !isSolving && !hasErrors
            ? 'bg-teal-600 hover:bg-teal-700 text-white shadow-md hover:shadow-lg'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600 cursor-not-allowed'
        }`}
      >
        {isSolving ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            Génération en cours…
          </>
        ) : (
          <>
            Générer l&apos;emploi du temps
            <ChevronRight size={16} />
          </>
        )}
      </button>

      {!ready && !isSolving && !hasErrors && (
        <p className="text-xs text-center text-gray-400 dark:text-gray-500">
          Complétez les éléments manquants ci-dessus pour activer la génération.
        </p>
      )}
      {hasErrors && (
        <p className="text-xs text-center text-red-600 dark:text-red-400">
          Corrigez les erreurs ci-dessus avant de générer l&apos;emploi du temps.
        </p>
      )}
    </div>
  )
}
