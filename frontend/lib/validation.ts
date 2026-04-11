/**
 * Validation utilities for detecting hour conflicts before solving
 */

import type { SchoolData, DayConfig } from './types'

export interface ValidationError {
  type: 'hour_overflow' | 'missing_data' | 'invalid_config'
  severity: 'error' | 'warning'
  message: string
  details?: string
  affectedItems?: string[]
}

interface DayMinutesSummary {
  sessionMinutes: number
  breakMinutes: number
  netMinutes: number
  invalidSessions: number
  invalidBreaks: number
}

interface TimeInterval {
  start: number
  end: number
}

function overlapMinutes(a: TimeInterval, b: TimeInterval): number {
  const start = Math.max(a.start, b.start)
  const end = Math.min(a.end, b.end)
  return Math.max(0, end - start)
}

function curriculumEntryMinutes(entry: Record<string, any>): number {
  if (entry.total_minutes_per_week != null) {
    return Number(entry.total_minutes_per_week) || 0
  }
  const sessionsPerWeek = Number(entry.sessions_per_week) || 0
  const minutesPerSession = Number(entry.minutes_per_session) || 0
  return sessionsPerWeek * minutesPerSession
}

function summarizeDayMinutes(day: DayConfig): DayMinutesSummary {
  let sessionMinutes = 0
  let breakMinutes = 0
  let invalidSessions = 0
  let invalidBreaks = 0
  const sessionIntervals: TimeInterval[] = []

  for (const session of day.sessions || []) {
    const start = timeToMinutes(session.start_time)
    const end = timeToMinutes(session.end_time)
    const delta = end - start
    sessionMinutes += delta
    sessionIntervals.push({ start, end })
    if (delta <= 0) invalidSessions += 1
  }

  for (const brk of day.breaks || []) {
    const start = timeToMinutes(brk.start_time)
    const end = timeToMinutes(brk.end_time)
    const delta = end - start
    let effectiveBreak = 0
    for (const session of sessionIntervals) {
      effectiveBreak += overlapMinutes({ start, end }, session)
    }
    breakMinutes += effectiveBreak
    if (delta <= 0) invalidBreaks += 1
  }

  return {
    sessionMinutes,
    breakMinutes,
    netMinutes: sessionMinutes - breakMinutes,
    invalidSessions,
    invalidBreaks,
  }
}

function minutesToHours(minutes: number): number {
  return minutes / 60
}

function formatHours(minutes: number): string {
  return `${minutesToHours(minutes).toFixed(1)}h`
}

function buildSchoolCapacityBreakdown(schoolData: SchoolData): string {
  const days = schoolData.days || []
  if (days.length === 0) {
    return 'Aucun jour configure.'
  }

  const totalSessions = days.reduce((acc, day) => acc + (day.sessions?.length || 0), 0)
  const totalBreaks = days.reduce((acc, day) => acc + (day.breaks?.length || 0), 0)
  const lines: string[] = [
    `Jours: ${days.length}, sessions: ${totalSessions}, pauses: ${totalBreaks}`,
  ]

  for (const day of days) {
    const summary = summarizeDayMinutes(day)
    let line = `- ${day.name}: brut ${formatHours(summary.sessionMinutes)} - pauses ${formatHours(summary.breakMinutes)} = net ${formatHours(summary.netMinutes)}`
    if (summary.invalidSessions > 0 || summary.invalidBreaks > 0) {
      line += ` (creneaux invalides: sessions ${summary.invalidSessions}, pauses ${summary.invalidBreaks})`
    }
    lines.push(line)
  }

  return lines.join('\n')
}

/**
 * Calculate total school hours available per week
 */
export function calculateSchoolHours(schoolData: SchoolData): number {
  const days = schoolData.days || []

  let totalMinutes = 0
  for (const day of days) {
    totalMinutes += summarizeDayMinutes(day).netMinutes
  }

  // Convert to hours
  return minutesToHours(totalMinutes)
}

/**
 * Calculate requested weekly hours per class.
 */
export function calculateRequestedClassHours(schoolData: SchoolData): Record<string, number> {
  const curriculum = schoolData.curriculum || []
  const minutesByClass: Record<string, number> = {}

  for (const entry of curriculum) {
    const schoolClass = String(entry.school_class || '').trim()
    if (!schoolClass) continue
    minutesByClass[schoolClass] = (minutesByClass[schoolClass] || 0) + curriculumEntryMinutes(entry)
  }

  const hoursByClass: Record<string, number> = {}
  for (const schoolClass in minutesByClass) {
    hoursByClass[schoolClass] = minutesToHours(minutesByClass[schoolClass])
  }

  return hoursByClass
}

/**
 * Calculate individual teacher workload from curriculum
 */
export function calculateTeacherWorkloads(schoolData: SchoolData): Record<string, number> {
  const curriculum = schoolData.curriculum || []
  const workloads: Record<string, number> = {}
  const teacherAssignments = (schoolData as any).teacher_assignments || []
  const teacherByClassSubject: Record<string, string> = {}

  for (const a of teacherAssignments) {
    const key = `${a.school_class}::${a.subject}`
    teacherByClassSubject[key] = a.teacher
  }

  for (const entry of curriculum) {
    const schoolClass = String(entry.school_class || '').trim()
    if (!schoolClass) continue
    const teacher = teacherByClassSubject[`${schoolClass}::${entry.subject}`]
    if (!teacher) continue
    workloads[teacher] = (workloads[teacher] || 0) + curriculumEntryMinutes(entry)
  }

  // Convert all to hours
  for (const teacher in workloads) {
    workloads[teacher] = workloads[teacher] / 60
  }

  return workloads
}

/**
 * Validate school data for hour conflicts before solving
 */
export function validateHourBarriers(schoolData: SchoolData): ValidationError[] {
  const errors: ValidationError[] = []

  // Check if we have basic data
  if (!schoolData.teachers?.length) {
    errors.push({
      type: 'missing_data',
      severity: 'error',
      message: 'Aucun enseignant défini',
      details: 'Vous devez ajouter au moins un enseignant avant de générer l\'emploi du temps.'
    })
  }

  if (!schoolData.curriculum?.length) {
    errors.push({
      type: 'missing_data',
      severity: 'error',
      message: 'Aucun programme défini',
      details: 'Vous devez définir le programme horaire (matières, durées, fréquences) avant de générer.'
    })
  }

  if (!schoolData.days?.length || !schoolData.days.some(d => d.sessions?.length > 0)) {
    errors.push({
      type: 'missing_data',
      severity: 'error',
      message: 'Horaires scolaires non définis',
      details: 'Vous devez définir les jours de classe et les créneaux horaires.'
    })
  }

  // If missing basic data, don't check hour conflicts
  if (errors.length > 0) return errors

  // Calculate total hours
  const schoolHours = calculateSchoolHours(schoolData)
  const requestedClassHours = calculateRequestedClassHours(schoolData)
  const schoolClassHoursLimit = schoolHours

  // Check capacity per class (parallel classes are allowed).
  const overCapacityClasses: string[] = []
  const knownClassNames = new Set<string>([
    ...(schoolData.classes || []).map((c: any) => String(c.name || '').trim()).filter(Boolean),
    ...Object.keys(requestedClassHours),
  ])

  for (const schoolClass of knownClassNames) {
    const requested = requestedClassHours[schoolClass] || 0
    if (requested > schoolClassHoursLimit) {
      const overflow = requested - schoolClassHoursLimit
      overCapacityClasses.push(
        `${schoolClass} (${requested.toFixed(1)}h / ${schoolClassHoursLimit.toFixed(1)}h, excedent ${overflow.toFixed(1)}h)`
      )
    }
  }

  if (overCapacityClasses.length > 0) {
    const breakdown = buildSchoolCapacityBreakdown(schoolData)
    errors.push({
      type: 'hour_overflow',
      severity: 'error',
      message: `${overCapacityClasses.length} classe(s) depassent la capacite horaire hebdomadaire`,
      details: `Le solveur autorise les cours en parallele entre classes differentes. La capacite doit donc etre verifiee classe par classe.\n\nClasses en excedent:\n${overCapacityClasses.join('\n')}\n\nDetail du calcul de capacite hebdomadaire (par classe):\n${breakdown}`,
      affectedItems: overCapacityClasses,
    })
  }

  // Check individual teacher workloads
  const workloads = calculateTeacherWorkloads(schoolData)
  const teachers = schoolData.teachers || []
  const overloadedTeachers: string[] = []

  for (const teacher of teachers) {
    const teacherName = teacher.name
    const maxHours = teacher.max_hours_per_week || 0
    const assignedHours = workloads[teacherName] || 0

    if (assignedHours > maxHours) {
      overloadedTeachers.push(`${teacherName} (${assignedHours.toFixed(1)}h / ${maxHours}h max)`)
    }
  }

  if (overloadedTeachers.length > 0) {
    errors.push({
      type: 'hour_overflow',
      severity: 'error',
      message: `${overloadedTeachers.length} enseignant(s) en surcharge horaire`,
      details: `Les enseignants suivants dépassent leur limite hebdomadaire :\n${overloadedTeachers.join('\n')}`,
      affectedItems: overloadedTeachers
    })
  }

  return errors
}

/**
 * Convert time string (HH:MM) to minutes
 */
function timeToMinutes(time: string): number {
  const [hours, minutes] = time.split(':').map(Number)
  return hours * 60 + minutes
}
