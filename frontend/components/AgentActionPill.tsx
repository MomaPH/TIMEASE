'use client'
import { Loader2 } from 'lucide-react'

/** Map internal tool names to French user-friendly labels */
const TOOL_LABELS: Record<string, string> = {
  save_school_info:     'Enregistrement des informations école…',
  save_teachers:        'Enregistrement des enseignants…',
  save_classes:         'Enregistrement des classes…',
  save_rooms:           'Enregistrement des salles…',
  save_subjects:        'Enregistrement des matières…',
  save_curriculum:      'Enregistrement du programme…',
  save_constraints:     'Enregistrement des contraintes…',
  save_assignments:     'Enregistrement des affectations…',
  get_school_data:      'Lecture des données…',
  get_assignments:      'Lecture des affectations…',
  analyze_conflicts:    'Analyse des conflits…',
  validate_data:        'Validation des données…',
  generate_timetable:   "Génération de l'emploi du temps…",
  export_excel:         'Export Excel…',
  export_pdf:           'Export PDF…',
}

interface Props {
  toolName: string
  onDismiss?: () => void
}

export default function AgentActionPill({ toolName }: Props) {
  const label = TOOL_LABELS[toolName] ?? `Exécution : ${toolName}…`

  return (
    <div className="flex justify-start mb-2 animate-fade-in">
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-teal-50 dark:bg-teal-900/30 border border-teal-200 dark:border-teal-700 animate-pulse-glow">
        <Loader2 size={13} className="text-teal-600 dark:text-teal-400 animate-spin-slow" />
        <span className="text-xs font-medium text-teal-700 dark:text-teal-300">
          {label}
        </span>
      </div>
    </div>
  )
}
