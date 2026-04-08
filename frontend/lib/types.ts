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

export interface SessionConfig {
  name: string
  start_time: string
  end_time: string
}

export interface BreakConfig {
  name: string
  start_time: string
  end_time: string
}

export interface DayConfig {
  name: string
  sessions: SessionConfig[]
  breaks: BreakConfig[]
}

export interface SchoolData {
  name?: string
  city?: string
  academic_year?: string
  // New format: days is list of DayConfig objects
  days?: DayConfig[]
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

export interface BreakSlot {
  type: 'break'
  start_time: string
  end_time: string
  label: string
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
      // New format: days is array of DayConfig objects
      const days = data.days ?? []
      const hasDays = days.length > 0
      const hasSessionsInDays = days.some(d => d.sessions?.length > 0)
      if (data.name && hasDays && hasSessionsInDays) return 'done'
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
      // Phase D: Rooms are optional - always show as 'done' (skippable)
      if ((data.rooms?.length ?? 0) >= 1) return 'done'
      return 'done'  // Empty rooms is valid
    case 4:
      if ((data.subjects?.length ?? 0) >= 1) return 'done'
      return 'empty'
    case 5: {
      if (assignments.length === 0 && (data.curriculum?.length ?? 0) === 0) return 'empty'
      // Check coverage: each curriculum entry (class+subject) must have an assignment
      const curriculum = data.curriculum ?? []
      const pairSet = new Set(assignments.map(a => `${a.school_class}__${a.subject}`))
      const allCovered = curriculum.every(c => pairSet.has(`${c.school_class}__${c.subject}`))
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

/** Returns list of curriculum entries that have no matching assignment */
export function getMissingAssignments(data: SchoolData, assignments: any[]): { school_class: string; subject: string }[] {
  const curriculum = data.curriculum ?? []
  const pairSet = new Set(assignments.map(a => `${a.school_class}__${a.subject}`))
  return curriculum
    .filter(c => !pairSet.has(`${c.school_class}__${c.subject}`))
    .map(c => ({ school_class: c.school_class, subject: c.subject }))
}

/** Returns warnings for the current data state */
export function getDataWarnings(data: SchoolData, assignments: any[]): { step: number; message: string }[] {
  const warnings: { step: number; message: string }[] = []

  // Step 2: Teachers without subjects
  const teachersNoSubjects = (data.teachers ?? []).filter((t: any) => !t.subjects || t.subjects.length === 0)
  if (teachersNoSubjects.length > 0) {
    warnings.push({
      step: 2,
      message: `${teachersNoSubjects.length} enseignant(s) sans matière: ${teachersNoSubjects.map((t: any) => t.name).slice(0, 3).join(', ')}${teachersNoSubjects.length > 3 ? '...' : ''}`
    })
  }

  // Step 5: Missing assignments
  const missing = getMissingAssignments(data, assignments)
  if (missing.length > 0) {
    warnings.push({
      step: 5,
      message: `${missing.length} matière(s) sans enseignant: ${missing.slice(0, 3).map(m => `${m.school_class}/${m.subject}`).join(', ')}${missing.length > 3 ? '...' : ''}`
    })
  }

  // Step 6: Classes with 0 curriculum hours
  const classesWithCurriculum = new Set((data.curriculum ?? []).map((c: any) => c.school_class))
  const classesNoCurriculum = (data.classes ?? []).filter((c: any) => !classesWithCurriculum.has(c.name))
  if (classesNoCurriculum.length > 0 && (data.curriculum ?? []).length > 0) {
    warnings.push({
      step: 6,
      message: `${classesNoCurriculum.length} classe(s) sans programme: ${classesNoCurriculum.map((c: any) => c.name).slice(0, 3).join(', ')}${classesNoCurriculum.length > 3 ? '...' : ''}`
    })
  }

  return warnings
}

export function getChecklistItems(data: SchoolData, assignments: any[]) {
  const classes    = data.classes    ?? []
  const teachers   = data.teachers   ?? []
  const rooms      = data.rooms      ?? []
  const subjects   = data.subjects   ?? []
  const curriculum = data.curriculum ?? []
  const days       = data.days       ?? []
  const hasSessionsInDays = days.some(d => d.sessions?.length > 0)

  // Class-based curriculum: check each (school_class, subject) pair has an assignment
  const pairSet = new Set(assignments.map(a => `${a.school_class}__${a.subject}`))
  const allAssigned = curriculum.length === 0 || curriculum.every(c =>
    pairSet.has(`${c.school_class}__${c.subject}`)
  )

  return [
    { label: 'École configurée (nom, jours, sessions)', done: !!(data.name && days.length > 0 && hasSessionsInDays) },
    { label: 'Au moins 1 classe',                       done: classes.length > 0    },
    { label: 'Au moins 1 enseignant',                   done: teachers.length > 0   },
    { label: 'Salles (optionnel)',                      done: true                  },  // Phase D: rooms optional
    { label: 'Au moins 1 matière',                      done: subjects.length > 0   },
    { label: 'Programme défini',                        done: curriculum.length > 0 },
    { label: 'Toutes les affectations renseignées',     done: allAssigned           },
  ]
}

export function getChecklistStatus(data: SchoolData, assignments: any[]): boolean {
  return getChecklistItems(data, assignments).every(i => i.done)
}
