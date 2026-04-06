/**
 * Validation utilities for detecting hour conflicts before solving
 */

import type { SchoolData } from './types'

export interface ValidationError {
  type: 'hour_overflow' | 'missing_data' | 'invalid_config'
  severity: 'error' | 'warning'
  message: string
  details?: string
  affectedItems?: string[]
}

/**
 * Calculate total school hours available per week
 */
export function calculateSchoolHours(schoolData: SchoolData): number {
  const days = schoolData.days?.length || 0
  const sessions = schoolData.sessions || []
  
  let totalMinutesPerDay = 0
  for (const session of sessions) {
    const start = timeToMinutes(session.start_time)
    const end = timeToMinutes(session.end_time)
    totalMinutesPerDay += (end - start)
  }
  
  // Convert to hours
  return (days * totalMinutesPerDay) / 60
}

/**
 * Calculate total teacher hours requested in curriculum
 */
export function calculateRequestedTeacherHours(schoolData: SchoolData): number {
  const curriculum = schoolData.curriculum || []
  
  let totalMinutes = 0
  for (const entry of curriculum) {
    if (entry.total_minutes_per_week != null) {
      totalMinutes += Number(entry.total_minutes_per_week) || 0
      continue
    }
    const sessionsPerWeek = Number(entry.sessions_per_week) || 0
    const minutesPerSession = Number(entry.minutes_per_session) || 0
    totalMinutes += sessionsPerWeek * minutesPerSession
  }
  
  // Convert to hours
  return totalMinutes / 60
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
  const classesByLevel: Record<string, string[]> = {}
  for (const c of schoolData.classes || []) {
    const level = c.level || c.name
    if (!classesByLevel[level]) classesByLevel[level] = []
    classesByLevel[level].push(c.name)
  }
  
  for (const entry of curriculum) {
    const totalMinutes = Number(entry.total_minutes_per_week) || (
      (Number(entry.sessions_per_week) || 0) * (Number(entry.minutes_per_session) || 0)
    )
    const levelClasses = classesByLevel[entry.level] || []
    for (const schoolClass of levelClasses) {
      const teacher = teacherByClassSubject[`${schoolClass}::${entry.subject}`]
      if (!teacher) continue
      workloads[teacher] = (workloads[teacher] || 0) + totalMinutes
    }
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
  
  if (!schoolData.days?.length || !schoolData.sessions?.length) {
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
  const requestedHours = calculateRequestedTeacherHours(schoolData)
  
  // Check if requested hours exceed school capacity
  if (requestedHours > schoolHours) {
    errors.push({
      type: 'hour_overflow',
      severity: 'error',
      message: `Heures demandées (${requestedHours.toFixed(1)}h) dépassent la capacité scolaire (${schoolHours.toFixed(1)}h)`,
      details: `Vous demandez ${requestedHours.toFixed(1)} heures de cours par semaine, mais l'école ne dispose que de ${schoolHours.toFixed(1)} heures disponibles. Réduisez le nombre de sessions ou augmentez les créneaux horaires.`
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
