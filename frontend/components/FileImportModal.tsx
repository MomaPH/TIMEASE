'use client'
import { Check, X, AlertCircle, FileCheck } from 'lucide-react'

interface ImportedData {
  school_data?: any
  teacher_assignments?: any[]
}

interface Props {
  data: ImportedData
  onClose: () => void
  onContinue: (firstIncompleteStep: number) => void
}

export default function FileImportModal({ data, onClose, onContinue }: Props) {
  const sd = data.school_data || {}
  const ta = data.teacher_assignments || []

  const checks = [
    { label: 'Informations de l\'école', done: !!(sd.name && sd.days?.length) },
    { label: `Classes (${sd.classes?.length ?? 0})`,       done: (sd.classes?.length ?? 0) > 0 },
    { label: `Enseignants (${sd.teachers?.length ?? 0})`,  done: (sd.teachers?.length ?? 0) > 0 },
    { label: `Salles (${sd.rooms?.length ?? 0})`,          done: (sd.rooms?.length ?? 0) > 0 },
    { label: `Matières (${sd.subjects?.length ?? 0})`,     done: (sd.subjects?.length ?? 0) > 0 },
    { label: `Affectations (${ta.length})`,                done: ta.length > 0 },
    { label: `Programme (${sd.curriculum?.length ?? 0} entrées)`, done: (sd.curriculum?.length ?? 0) > 0 },
  ]

  // Find first incomplete step index
  function firstIncompleteStep(): number {
    if (!sd.name || !sd.days?.length) return 0
    if ((sd.classes?.length ?? 0) === 0) return 1
    if ((sd.teachers?.length ?? 0) === 0) return 2
    if ((sd.rooms?.length ?? 0) === 0) return 3
    if ((sd.subjects?.length ?? 0) === 0) return 4
    if (ta.length === 0) return 5
    if ((sd.curriculum?.length ?? 0) === 0) return 6
    return 8 // summary
  }

  const missing = checks.filter(c => !c.done)
  const allDone = missing.length === 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-100 dark:border-gray-800">
          <div className="w-9 h-9 rounded-xl bg-teal-100 dark:bg-teal-900/40 flex items-center justify-center">
            <FileCheck size={18} className="text-teal-600 dark:text-teal-400" />
          </div>
          <div className="flex-1">
            <h2 className="font-semibold text-gray-900 dark:text-white">Fichier importé</h2>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {allDone ? 'Toutes les données ont été importées' : `${missing.length} section(s) manquante(s)`}
            </p>
          </div>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Checklist */}
        <div className="px-6 py-4 space-y-2.5">
          {checks.map((c, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
                c.done
                  ? 'bg-teal-500'
                  : 'bg-gray-100 dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700'
              }`}>
                {c.done && <Check size={11} className="text-white" strokeWidth={3} />}
              </div>
              <span className={`text-sm ${c.done ? 'text-gray-800 dark:text-gray-200' : 'text-gray-400 dark:text-gray-500'}`}>
                {c.label}
              </span>
              {!c.done && (
                <span className="ml-auto text-xs text-amber-500 dark:text-amber-400 flex items-center gap-1">
                  <AlertCircle size={11} /> À compléter
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-800/50 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
          >
            Fermer
          </button>
          <button
            onClick={() => { onContinue(firstIncompleteStep()); onClose() }}
            className="px-5 py-2 text-sm font-medium bg-teal-600 text-white rounded-xl hover:bg-teal-700 transition-colors"
          >
            {allDone ? 'Voir le résumé →' : 'Compléter les données →'}
          </button>
        </div>
      </div>
    </div>
  )
}
