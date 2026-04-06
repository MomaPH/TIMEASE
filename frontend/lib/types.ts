export interface ChatMessage {
  role: 'user' | 'ai' | 'system'
  content: string
  dataSaved?: boolean
  savedTypes?: string[]
  options?: { label: string; value: string }[]
}

export interface PendingChange {
  tool: string
  input: Record<string, any>
  preview: string   // markdown table
  label: string     // human label e.g. "3 enseignants"
}

export interface SchoolData {
  name?: string
  city?: string
  academic_year?: string
  days?: string[]
  sessions?: { name: string; start_time: string; end_time: string }[]
  base_unit_minutes?: number
  teachers?: Record<string, any>[]
  classes?: Record<string, any>[]
  rooms?: Record<string, any>[]
  subjects?: Record<string, any>[]
  curriculum?: Record<string, any>[]
  constraints?: Record<string, any>[]
}

export interface TimetableAssignment {
  school_class: string
  subject: string
  teacher: string
  room: string
  day: string
  start_time: string
  end_time: string
  color: string
}

export type StepId =
  | 'school'
  | 'classes'
  | 'teachers'
  | 'rooms'
  | 'subjects'
  | 'assignments'
  | 'curriculum'
  | 'constraints'
  | 'summary'

export type StepStatus = 'empty' | 'partial' | 'done'

export interface Step {
  id: StepId
  label: string
  shortLabel: string
}

export const STEPS: Step[] = [
  { id: 'school',      label: 'École',        shortLabel: 'École'   },
  { id: 'classes',     label: 'Classes',      shortLabel: 'Classes' },
  { id: 'teachers',    label: 'Enseignants',  shortLabel: 'Enseignants' },
  { id: 'rooms',       label: 'Salles',       shortLabel: 'Salles'  },
  { id: 'subjects',    label: 'Matières',     shortLabel: 'Matières'},
  { id: 'assignments', label: 'Affectations', shortLabel: 'Affect.' },
  { id: 'curriculum',  label: 'Programme',    shortLabel: 'Prog.'   },
  { id: 'constraints', label: 'Contraintes',  shortLabel: 'Contr.'  },
  { id: 'summary',     label: 'Résumé',       shortLabel: 'Résumé'  },
]

export function getStepStatus(stepIdx: number, data: SchoolData, assignments: any[]): StepStatus {
  switch (stepIdx) {
    case 0: {
      const hasDays = (data.days?.length ?? 0) > 0
      const hasSessions = (data.sessions?.length ?? 0) > 0
      if (data.name && hasDays && hasSessions) return 'done'
      if (data.name || hasDays) return 'partial'
      return 'empty'
    }
    case 1:
      if ((data.classes?.length ?? 0) >= 1) return 'done'
      return 'empty'
    case 2:
      if ((data.teachers?.length ?? 0) >= 1) return 'done'
      return 'empty'
    case 3:
      if ((data.rooms?.length ?? 0) >= 1) return 'done'
      return 'empty'
    case 4:
      if ((data.subjects?.length ?? 0) >= 1) return 'done'
      return 'empty'
    case 5: {
      if (assignments.length === 0 && (data.curriculum?.length ?? 0) === 0) return 'empty'
      // Check coverage
      const classes = data.classes ?? []
      const curriculum = data.curriculum ?? []
      const pairSet = new Set(assignments.map(a => `${a.school_class}__${a.subject}`))
      const allCovered = curriculum.every(c => {
        const classesForLevel = classes.filter(cl => (cl.level || cl.name) === c.level)
        return classesForLevel.length === 0 || classesForLevel.every(cl => pairSet.has(`${cl.name}__${c.subject}`))
      })
      if (assignments.length > 0 && allCovered) return 'done'
      if (assignments.length > 0) return 'partial'
      return 'empty'
    }
    case 6:
      if ((data.curriculum?.length ?? 0) >= 1) return 'done'
      return 'empty'
    case 7:
      // Constraints are optional — always 'done'
      return 'done'
    case 8:
      return getChecklistStatus(data, assignments) ? 'done' : 'partial'
    default:
      return 'empty'
  }
}

export function getChecklistItems(data: SchoolData, assignments: any[]) {
  const classes    = data.classes    ?? []
  const teachers   = data.teachers   ?? []
  const rooms      = data.rooms      ?? []
  const subjects   = data.subjects   ?? []
  const curriculum = data.curriculum ?? []
  const days       = data.days       ?? []
  const sess       = data.sessions   ?? []

  const pairSet = new Set(assignments.map(a => `${a.school_class}__${a.subject}`))
  const allAssigned = curriculum.length === 0 || curriculum.every(c => {
    const cls4level = classes.filter(cl => (cl.level || cl.name) === c.level)
    return cls4level.length === 0 || cls4level.every(cl => pairSet.has(`${cl.name}__${c.subject}`))
  })

  return [
    { label: 'École configurée (nom, jours, sessions)', done: !!(data.name && days.length > 0 && sess.length > 0) },
    { label: 'Au moins 1 classe',                       done: classes.length > 0    },
    { label: 'Au moins 1 enseignant',                   done: teachers.length > 0   },
    { label: 'Au moins 1 salle',                        done: rooms.length > 0      },
    { label: 'Au moins 1 matière',                      done: subjects.length > 0   },
    { label: 'Programme défini',                        done: curriculum.length > 0 },
    { label: 'Toutes les affectations renseignées',     done: allAssigned           },
  ]
}

export function getChecklistStatus(data: SchoolData, assignments: any[]): boolean {
  return getChecklistItems(data, assignments).every(i => i.done)
}
