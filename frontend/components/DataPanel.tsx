'use client'
import { useState } from 'react'
import { ChevronDown, ChevronRight, Loader2, Zap } from 'lucide-react'
import type { SchoolData } from '@/lib/types'

interface Props {
  data: SchoolData
  assignments: Record<string, any>[]
  onGenerate: () => void
  isSolving: boolean
}

function Section({
  title,
  count,
  children,
}: {
  title: string
  count: number
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(false)
  const done = count > 0

  return (
    <div
      className={`border rounded-lg mb-2 overflow-hidden ${
        done
          ? 'border-teal-200 dark:border-teal-800'
          : 'border-gray-200 dark:border-gray-700'
      }`}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
      >
        <div className="flex items-center gap-2">
          {done && <span className="w-2 h-2 rounded-full bg-teal-500 flex-shrink-0" />}
          {!done && <span className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600 flex-shrink-0" />}
          <span className="text-gray-800 dark:text-gray-200">{title}</span>
          {count > 0 && (
            <span className="text-xs bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300 px-2 py-0.5 rounded-full">
              {count}
            </span>
          )}
        </div>
        {open
          ? <ChevronDown size={14} className="text-gray-400 flex-shrink-0" />
          : <ChevronRight size={14} className="text-gray-400 flex-shrink-0" />
        }
      </button>
      {open && (
        <div className="px-4 pb-3 text-sm text-gray-600 dark:text-gray-400 border-t border-gray-100 dark:border-gray-800 pt-2">
          {children}
        </div>
      )}
    </div>
  )
}

export default function DataPanel({ data, assignments, onGenerate, isSolving }: Props) {
  // Steps: École, Enseignants, Classes, Salles, Affectations, Programme
  const steps = [
    data.name ? 1 : 0,
    (data.teachers?.length ?? 0) > 0 ? 1 : 0,
    (data.classes?.length ?? 0) > 0 ? 1 : 0,
    (data.rooms?.length ?? 0) > 0 ? 1 : 0,
    assignments.length > 0 ? 1 : 0,
    (data.curriculum?.length ?? 0) > 0 ? 1 : 0,
  ] as const
  const stepsDone = steps.reduce((a, b) => a + b, 0)
  const totalSteps = 6
  const progressPct = Math.round((stepsDone / totalSteps) * 100)

  const canGenerate =
    (data.classes?.length ?? 0) > 0 &&
    (data.teachers?.length ?? 0) > 0 &&
    assignments.length > 0 &&
    (data.curriculum?.length ?? 0) > 0

  return (
    <div className="flex flex-col h-full">
      <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 px-1">
        Données collectées
      </h2>

      {/* Progress */}
      <div className="mb-4 px-1">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {stepsDone} sur {totalSteps} étapes
          </span>
          <span className="text-xs font-medium text-teal-600 dark:text-teal-400">
            {progressPct}%
          </span>
        </div>
        <div className="h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-teal-500 rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Sections */}
      <div className="flex-1 overflow-y-auto">
        <Section title="École" count={data.name ? 1 : 0}>
          {data.name ? (
            <div className="space-y-0.5">
              <p><span className="font-medium text-gray-700 dark:text-gray-300">Nom :</span> {data.name}</p>
              {data.city && <p><span className="font-medium text-gray-700 dark:text-gray-300">Ville :</span> {data.city}</p>}
              {data.academic_year && <p><span className="font-medium text-gray-700 dark:text-gray-300">Année :</span> {data.academic_year}</p>}
            </div>
          ) : (
            <p className="text-gray-400 italic">Non configuré</p>
          )}
        </Section>

        <Section title="Enseignants" count={data.teachers?.length ?? 0}>
          {data.teachers?.length ? (
            <ul className="space-y-0.5">
              {data.teachers.map((t: any, i: number) => (
                <li key={i}>{t.name || `Enseignant ${i + 1}`}</li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-400 italic">Aucun</p>
          )}
        </Section>

        <Section title="Classes" count={data.classes?.length ?? 0}>
          {data.classes?.length ? (
            <ul className="space-y-0.5">
              {data.classes.map((c: any, i: number) => (
                <li key={i}>{c.name || `Classe ${i + 1}`}</li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-400 italic">Aucune</p>
          )}
        </Section>

        <Section title="Salles" count={data.rooms?.length ?? 0}>
          {data.rooms?.length ? (
            <ul className="space-y-0.5">
              {data.rooms.map((r: any, i: number) => (
                <li key={i}>{r.name || `Salle ${i + 1}`}</li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-400 italic">Aucune</p>
          )}
        </Section>

        <Section title="Affectations" count={assignments.length}>
          {assignments.length ? (
            <ul className="space-y-0.5">
              {assignments.slice(0, 5).map((a: any, i: number) => (
                <li key={i} className="truncate">
                  {a.teacher} → {a.subject} ({a.school_class})
                </li>
              ))}
              {assignments.length > 5 && (
                <li className="text-gray-400">+{assignments.length - 5} autre(s)</li>
              )}
            </ul>
          ) : (
            <p className="text-gray-400 italic">Aucune</p>
          )}
        </Section>

        <Section title="Programme" count={data.curriculum?.length ?? 0}>
          {data.curriculum?.length ? (
            <p>{data.curriculum.length} entrée(s)</p>
          ) : (
            <p className="text-gray-400 italic">Non configuré</p>
          )}
        </Section>

        <Section title="Contraintes" count={data.constraints?.length ?? 0}>
          {data.constraints?.length ? (
            <p>{data.constraints.length} contrainte(s)</p>
          ) : (
            <p className="text-gray-400 italic">Aucune</p>
          )}
        </Section>
      </div>

      {/* Generate button */}
      {canGenerate && (
        <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800">
          <button
            onClick={onGenerate}
            disabled={isSolving}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-teal-600 hover:bg-teal-700 disabled:opacity-60 text-white text-sm font-medium rounded-xl transition-colors"
          >
            {isSolving ? (
              <>
                <Loader2 size={15} className="animate-spin" />
                Génération en cours…
              </>
            ) : (
              <>
                <Zap size={15} />
                Générer l'emploi du temps
              </>
            )}
          </button>
        </div>
      )}
    </div>
  )
}
