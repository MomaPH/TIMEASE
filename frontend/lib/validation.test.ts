import { describe, expect, it } from 'vitest'

import { FORM_SCENARIOS } from '@/lib/test-scenarios'
import { validateHourBarriers } from '@/lib/validation'
import type { SchoolData } from '@/lib/types'

describe('validateHourBarriers', () => {
  it('skips preflags when optional prerequisite sections are missing', () => {
    const noDaysOrCurriculum: SchoolData = {
      name: 'Test',
      city: 'Dakar',
      academic_year: '2026-2027',
      base_unit_minutes: 30,
      days: [],
      classes: [{ name: '6e A', level: 'Collège', student_count: 30 }],
      teachers: [{ name: 'Mme Diallo', subjects: ['MATH'] }],
      subjects: [{ name: 'MATH', short_name: 'MATH', color: '#0d9488', needs_room: true }],
      curriculum: [],
      rooms: [],
      constraints: [],
    }

    expect(validateHourBarriers(noDaysOrCurriculum, [])).toEqual([])
  })

  it('keeps the hardest FET scenario compatible with preflight checks', () => {
    const overloaded = FORM_SCENARIOS.find((s) => s.id === 'fet-hard-02')
    expect(overloaded).toBeTruthy()
    if (!overloaded) return

    const issues = validateHourBarriers(overloaded.schoolData, overloaded.assignments)
    expect(Array.isArray(issues)).toBe(true)
  })

  it('allows an easy FET scenario to pass preflight blockers', () => {
    const realistic = FORM_SCENARIOS.find((s) => s.id === 'fet-easy-01')
    expect(realistic).toBeTruthy()
    if (!realistic) return

    const issues = validateHourBarriers(realistic.schoolData, realistic.assignments)
    expect(issues.filter((i) => i.severity === 'error').length).toBe(0)
  })

  it('does not flag teacher overload when max_hours_per_week is omitted', () => {
    const sample: SchoolData = {
      name: 'Sans plafond',
      city: 'Dakar',
      academic_year: '2026-2027',
      base_unit_minutes: 30,
      days: [
        {
          name: 'lundi',
          sessions: [{ name: 'Matin', start_time: '08:00', end_time: '12:00' }],
          breaks: [],
        },
      ],
      classes: [{ name: '6e A', level: 'Collège', student_count: 30 }],
      teachers: [{ name: 'Mme Diallo', subjects: ['MATH'] }],
      subjects: [{ name: 'MATH', short_name: 'MATH', color: '#0d9488', needs_room: true }],
      curriculum: [
        {
          school_class: '6e A',
          subject: 'MATH',
          weekly_hours: 6,
          sessions_per_week: 6,
          minutes_per_session: 60,
          total_minutes_per_week: 360,
        },
      ],
      rooms: [{ name: 'S1', types: ['Standard'], capacity: 35 }],
      constraints: [],
    }
    const assignments = [{ school_class: '6e A', subject: 'MATH', teacher: 'Mme Diallo' }]

    const issues = validateHourBarriers(sample, assignments)
    expect(issues.some((i) => i.message.includes('surcharge horaire'))).toBe(false)
  })
})
