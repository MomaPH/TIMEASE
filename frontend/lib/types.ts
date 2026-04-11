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
  day: string
  start_time: string
  end_time: string
  label: string
}

export type StepId = 'school' | 'classes' | 'generation'

export type StepStatus = 'empty' | 'partial' | 'done'

export interface Step {
  id: StepId
  label: string
  shortLabel: string
}

export const STEPS: Step[] = [
  { id: 'school',     label: 'École & Semaine',    shortLabel: 'École'   },
  { id: 'classes',    label: 'Classes & Programme', shortLabel: 'Classes' },
  { id: 'generation', label: 'Génération',          shortLabel: 'Générer' },
]

export function getStepStatus(stepIdx: number, data: SchoolData, assignments: any[]): StepStatus {
  switch (stepIdx) {
    case 0: {
      const days = data.days ?? []
      const hasDays = days.length > 0
      const hasSessionsInDays = days.some(d => d.sessions?.length > 0)
      if (data.name && hasDays && hasSessionsInDays) return 'done'
      if (data.name || hasDays) return 'partial'
      return 'empty'
    }
    case 1: {
      const classes    = data.classes   ?? []
      const teachers   = data.teachers  ?? []
      const curriculum = data.curriculum ?? []
      if (classes.length === 0) return 'empty'
      if (teachers.length > 0 && curriculum.length > 0) {
        const valid = curriculum.filter(isValidCurriculumEntry)
        const pairSet = new Set(assignments.map(a => `${a.school_class}__${a.subject}`))
        const allCovered = valid.length > 0 && valid.every(c => pairSet.has(`${c.school_class}__${c.subject}`))
        if (allCovered) return 'done'
      }
      return 'partial'
    }
    case 2:
      return getChecklistStatus(data, assignments) ? 'done' : 'partial'
    default:
      return 'empty'
  }
}

/** Returns true if the curriculum entry has a non-empty class and subject */
function isValidCurriculumEntry(c: any): boolean {
  return !!(c.school_class && c.subject)
}

/** Returns list of curriculum entries that have no matching assignment */
export function getMissingAssignments(data: SchoolData, assignments: any[]): { school_class: string; subject: string }[] {
  const curriculum = (data.curriculum ?? []).filter(isValidCurriculumEntry)
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
  const curriculum = data.curriculum ?? []
  const days       = data.days       ?? []
  const hasSessionsInDays = days.some(d => d.sessions?.length > 0)

  // Only count valid curriculum entries (non-empty class and subject)
  const validCurriculum = curriculum.filter(isValidCurriculumEntry)

  // Class-based curriculum: check each valid (school_class, subject) pair has an assignment
  const pairSet = new Set(assignments.map(a => `${a.school_class}__${a.subject}`))
  const allAssigned = validCurriculum.length === 0 || validCurriculum.every(c =>
    pairSet.has(`${c.school_class}__${c.subject}`)
  )

  // Derive subjects from valid curriculum entries
  const subjectNames = new Set(validCurriculum.map((c: any) => c.subject))
  const hasSubjects  = (data.subjects?.length ?? 0) > 0 || subjectNames.size > 0

  return [
    { id: 'school',      label: 'École configurée (nom, jours, sessions)', done: !!(data.name && days.length > 0 && hasSessionsInDays) },
    { id: 'classes',     label: 'Au moins 1 classe',                       done: classes.length > 0    },
    { id: 'teachers',    label: 'Au moins 1 enseignant',                   done: teachers.length > 0   },
    { id: 'subjects',    label: 'Au moins 1 matière',                      done: hasSubjects            },
    { id: 'curriculum',  label: 'Programme défini',                        done: validCurriculum.length > 0 },
    { id: 'assignments', label: 'Toutes les affectations renseignées',     done: allAssigned           },
  ]
}

export function getChecklistStatus(data: SchoolData, assignments: any[]): boolean {
  return getChecklistItems(data, assignments).every(i => i.done)
}
