/**
 * Validation utilities for detecting hour conflicts before solving
 */

import type { SchoolData, DayConfig } from './types'

export interface ValidationError {
  type: 'hour_overflow' | 'missing_data' | 'invalid_config' | 'preflight_blocker'
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

function curriculumEntrySessionMinutes(entry: Record<string, any>, baseUnitMinutes: number): number {
  const explicit = Number(entry.minutes_per_session)
  if (Number.isFinite(explicit) && explicit > 0) return explicit

  const sessionsPerWeek = Number(entry.sessions_per_week)
  const totalMinutes = Number(entry.total_minutes_per_week)
  if (Number.isFinite(sessionsPerWeek) && sessionsPerWeek > 0 && Number.isFinite(totalMinutes) && totalMinutes > 0) {
    return Math.max(baseUnitMinutes, Math.round(totalMinutes / sessionsPerWeek))
  }
  return baseUnitMinutes
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
export function calculateTeacherWorkloads(schoolData: SchoolData, assignments: any[]): Record<string, number> {
  const curriculum = schoolData.curriculum || []
  const workloads: Record<string, number> = {}
  const teacherByClassSubject: Record<string, string> = {}

  for (const a of assignments || []) {
    if (!a?.school_class || !a?.subject || !a?.teacher) continue
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

interface DaySlot {
  start: number
  end: number
  sessionName: string
}

function buildDaySlots(day: DayConfig, baseUnitMinutes: number): DaySlot[] {
  const slots: DaySlot[] = []
  const breakIntervals: TimeInterval[] = (day.breaks || []).map((b) => ({
    start: timeToMinutes(b.start_time),
    end: timeToMinutes(b.end_time),
  }))

  for (const session of day.sessions || []) {
    const sessionStart = timeToMinutes(session.start_time)
    const sessionEnd = timeToMinutes(session.end_time)
    if (sessionEnd <= sessionStart) continue
    for (let cursor = sessionStart; cursor + baseUnitMinutes <= sessionEnd; cursor += baseUnitMinutes) {
      const slot: DaySlot = {
        start: cursor,
        end: cursor + baseUnitMinutes,
        sessionName: session.name,
      }
      const overlapsBreak = breakIntervals.some((b) => overlapMinutes(slot, b) > 0)
      if (!overlapsBreak) slots.push(slot)
    }
  }
  return slots
}

function hasContiguousWindow(slots: DaySlot[], requiredMinutes: number): boolean {
  if (requiredMinutes <= 0) return false
  for (let i = 0; i < slots.length; i += 1) {
    let total = slots[i].end - slots[i].start
    let lastEnd = slots[i].end
    if (total >= requiredMinutes) return true
    for (let j = i + 1; j < slots.length; j += 1) {
      if (slots[j].start !== lastEnd) break
      total += slots[j].end - slots[j].start
      lastEnd = slots[j].end
      if (total >= requiredMinutes) return true
    }
  }
  return false
}

function overlapsUnavailability(slotStart: number, slotEnd: number, unavailability: any): boolean {
  const uStart = timeToMinutes(String(unavailability?.start || '00:00'))
  const uEnd = timeToMinutes(String(unavailability?.end || '23:59'))
  return slotStart < uEnd && uStart < slotEnd
}

function extractDayOffBlocks(schoolData: SchoolData): Record<string, Set<string>> {
  const blocks: Record<string, Set<string>> = {}
  for (const c of schoolData.constraints || []) {
    if (c?.type !== 'hard' || c?.category !== 'day_off') continue
    const day = String(c?.parameters?.day || '').trim()
    const session = String(c?.parameters?.session || 'all').trim()
    if (!day) continue
    if (!blocks[day]) blocks[day] = new Set<string>()
    blocks[day].add(session || 'all')
  }
  return blocks
}

/**
 * Validate school data for hour conflicts before solving
 */
export function validateHourBarriers(schoolData: SchoolData, assignments: any[] = []): ValidationError[] {
  const errors: ValidationError[] = []
  const days = schoolData.days || []
  const curriculum = schoolData.curriculum || []
  if (days.length === 0 || curriculum.length === 0) {
    // Optional-safe: if key inputs are absent, defer to checklist and raise no preflag.
    return errors
  }
  const baseUnitMinutes = Number(schoolData.base_unit_minutes) || 30

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
      type: 'preflight_blocker',
      severity: 'error',
      message: `${overCapacityClasses.length} classe(s) depassent la capacite horaire hebdomadaire`,
      details: `Le solveur autorise les cours en parallele entre classes differentes. La capacite doit donc etre verifiee classe par classe.\n\nClasses en excedent:\n${overCapacityClasses.join('\n')}\n\nDetail du calcul de capacite hebdomadaire (par classe):\n${breakdown}`,
      affectedItems: overCapacityClasses,
    })
  }

  // Check individual teacher workloads
  const workloads = calculateTeacherWorkloads(schoolData, assignments)
  const teachers = schoolData.teachers || []
  const overloadedTeachers: string[] = []

  for (const teacher of teachers) {
    const teacherName = teacher.name
    const maxHours = teacher.max_hours_per_week
    if (maxHours == null || !Number.isFinite(maxHours)) {
      continue // Optional-safe: no max set => no overload preflag.
    }
    const assignedHours = workloads[teacherName] || 0

    if (assignedHours > maxHours) {
      overloadedTeachers.push(`${teacherName} (${assignedHours.toFixed(1)}h / ${maxHours}h max)`)
    }
  }

  if (overloadedTeachers.length > 0) {
    errors.push({
      type: 'preflight_blocker',
      severity: 'error',
      message: `${overloadedTeachers.length} enseignant(s) en surcharge horaire`,
      details: `Les enseignants suivants dépassent leur limite hebdomadaire :\n${overloadedTeachers.join('\n')}`,
      affectedItems: overloadedTeachers
    })
  }

  const teacherByName: Record<string, any> = {}
  for (const t of teachers) {
    if (t?.name) teacherByName[t.name] = t
  }
  const assignmentByClassSubject: Record<string, string> = {}
  for (const a of assignments || []) {
    if (!a?.school_class || !a?.subject || !a?.teacher) continue
    assignmentByClassSubject[`${a.school_class}::${a.subject}`] = a.teacher
  }
  const daySlots = new Map<string, DaySlot[]>()
  for (const day of days) {
    daySlots.set(day.name, buildDaySlots(day, baseUnitMinutes))
  }
  const dayOffBlocks = extractDayOffBlocks(schoolData)

  const noSlotEntries: string[] = []
  for (const entry of curriculum) {
    const schoolClass = String(entry.school_class || '').trim()
    const subject = String(entry.subject || '').trim()
    if (!schoolClass || !subject) continue

    const teacherName = assignmentByClassSubject[`${schoolClass}::${subject}`]
    if (!teacherName) continue // Optional-safe: assignment gate handles this elsewhere.
    const teacher = teacherByName[teacherName]
    if (!teacher) continue

    const durationMinutes = curriculumEntrySessionMinutes(entry, baseUnitMinutes)
    let hasSlot = false

    for (const day of days) {
      const blocked = dayOffBlocks[day.name]
      if (blocked?.has('all')) continue

      const slots = (daySlots.get(day.name) || []).filter((slot) => !blocked?.has(slot.sessionName))
      if (!hasContiguousWindow(slots, durationMinutes)) continue

      const unavailable = (teacher.unavailable_slots || []).filter((u: any) => String(u?.day || '') === day.name)
      if (unavailable.length === 0) {
        hasSlot = true
        break
      }

      // Check if at least one contiguous chain avoids all unavailability windows.
      for (let i = 0; i < slots.length; i += 1) {
        let total = slots[i].end - slots[i].start
        let chainStart = slots[i].start
        let chainEnd = slots[i].end
        let lastEnd = slots[i].end

        const firstBlocked = unavailable.some((u: any) => overlapsUnavailability(chainStart, chainEnd, u))
        if (!firstBlocked && total >= durationMinutes) {
          hasSlot = true
          break
        }

        for (let j = i + 1; j < slots.length; j += 1) {
          if (slots[j].start !== lastEnd) break
          total += slots[j].end - slots[j].start
          chainEnd = slots[j].end
          lastEnd = slots[j].end
          const blockedWindow = unavailable.some((u: any) => overlapsUnavailability(chainStart, chainEnd, u))
          if (!blockedWindow && total >= durationMinutes) {
            hasSlot = true
            break
          }
        }
        if (hasSlot) break
      }
      if (hasSlot) break
    }

    if (!hasSlot) {
      noSlotEntries.push(`${schoolClass}/${subject} (${teacherName})`)
    }
  }

  if (noSlotEntries.length > 0) {
    errors.push({
      type: 'preflight_blocker',
      severity: 'error',
      message: `${noSlotEntries.length} entrée(s) sans créneau possible`,
      details: "Aucun créneau valide n'existe avant solve (jours bloqués, indisponibilités enseignant ou durée de séance).",
      affectedItems: noSlotEntries.slice(0, 20),
    })
  }

  // Optional room feasibility preflag:
  // if no room constraints are expressed, this check does nothing.
  const rooms = schoolData.rooms || []
  const subjects = schoolData.subjects || []
  const classes = schoolData.classes || []
  const classByName: Record<string, any> = {}
  for (const c of classes) {
    if (c?.name) classByName[c.name] = c
  }
  const subjectByName: Record<string, any> = {}
  for (const s of subjects) {
    if (s?.name) subjectByName[s.name] = s
  }
  const roomIssues: string[] = []

  for (const entry of curriculum) {
    const schoolClass = String(entry.school_class || '').trim()
    const subjectName = String(entry.subject || '').trim()
    const subject = subjectByName[subjectName]
    if (!subject || subject.needs_room !== true) continue
    const requiredType = String(subject.required_room_type || subject.room_type || '').trim()
    if (!requiredType) continue // Optional-safe: no required room type => no preflag.

    const matching = rooms.filter((r: any) => Array.isArray(r?.types) && r.types.includes(requiredType))
    if (matching.length === 0) {
      roomIssues.push(`${schoolClass}/${subjectName}: aucune salle de type "${requiredType}"`)
      continue
    }
    const studentCount = Number(classByName[schoolClass]?.student_count || 0)
    if (studentCount > 0) {
      const maxCapacity = Math.max(...matching.map((r: any) => Number(r?.capacity || 0)))
      if (maxCapacity < studentCount) {
        roomIssues.push(`${schoolClass}/${subjectName}: capacité max ${maxCapacity} < ${studentCount} élèves`)
      }
    }
  }

  if (roomIssues.length > 0) {
    errors.push({
      type: 'preflight_blocker',
      severity: 'error',
      message: `${roomIssues.length} contrainte(s) salle incompatibles`,
      details: "Certaines matières ne peuvent pas être placées faute de salle compatible.",
      affectedItems: roomIssues.slice(0, 20),
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
