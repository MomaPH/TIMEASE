import { describe, expect, it } from 'vitest'

import { FORM_SCENARIOS } from '@/lib/test-scenarios'
import { applyScenarioPreset } from '@/lib/scenario-prefill'
import type { SchoolData } from '@/lib/types'

const BASE_DATA: SchoolData = {
  name: 'Base',
  city: 'BaseCity',
  academic_year: '2020-2021',
  base_unit_minutes: 30,
  days: [],
  rooms: [],
  classes: [],
  teachers: [],
  subjects: [],
  curriculum: [],
  constraints: [],
}

describe('applyScenarioPreset', () => {
  it('applies every form scenario exactly into form payload', () => {
    for (const scenario of FORM_SCENARIOS) {
      const result = applyScenarioPreset(BASE_DATA, scenario)

      expect(result.data.name).toBe(scenario.schoolData.name)
      expect(result.data.city).toBe(scenario.schoolData.city)
      expect(result.data.academic_year).toBe(scenario.schoolData.academic_year)
      expect(result.data.base_unit_minutes).toBe(scenario.schoolData.base_unit_minutes)
      expect(result.data.days).toEqual(scenario.schoolData.days ?? [])
      expect(result.data.rooms).toEqual(scenario.schoolData.rooms ?? [])
      expect(result.data.classes).toEqual(scenario.schoolData.classes ?? [])
      expect(result.data.teachers).toEqual(scenario.schoolData.teachers ?? [])
      expect(result.data.curriculum).toEqual(scenario.schoolData.curriculum ?? [])
      expect(result.data.subjects).toEqual(scenario.schoolData.subjects ?? [])
      expect(result.data.constraints).toEqual(scenario.schoolData.constraints ?? [])
      expect(result.assignments).toEqual(scenario.assignments)
    }
  })

  it('does not mutate source scenario definitions', () => {
    const scenario = FORM_SCENARIOS[0]
    const result = applyScenarioPreset(BASE_DATA, scenario)

    if (result.data.classes && result.data.classes.length > 0) {
      ;(result.data.classes[0] as any).name = 'MUTATED'
    }
    if (result.assignments.length > 0) {
      result.assignments[0].teacher = 'Mutated Teacher'
    }

    expect((FORM_SCENARIOS[0].schoolData.classes?.[0] as any)?.name).not.toBe('MUTATED')
    expect(FORM_SCENARIOS[0].assignments[0]?.teacher).not.toBe('Mutated Teacher')
  })

  it('contains a no-compromise realistic school scenario with expected complexity', () => {
    const realistic = FORM_SCENARIOS.find((s) => s.id === 'r-l4-real-school')
    expect(realistic).toBeTruthy()
    if (!realistic) return

    expect(realistic.schoolData.days?.length).toBe(5)
    expect(realistic.schoolData.subjects?.length).toBe(14)
    expect(realistic.schoolData.classes?.length).toBe(6)
    expect(realistic.schoolData.teachers?.length).toBe(17)
    expect(realistic.schoolData.rooms?.length).toBe(6)
    expect(realistic.schoolData.curriculum?.length).toBe(84) // 6 classes * 14 subjects
    expect(realistic.assignments.length).toBe(84)

    const ids = new Set((realistic.schoolData.constraints ?? []).map((c: any) => c.id))
    for (const expected of ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'S1', 'S2', 'S3', 'S4']) {
      expect(ids.has(expected)).toBe(true)
    }

    const teachers = realistic.schoolData.teachers ?? []
    const manga = teachers.find((t: any) => t.name === 'T_MANGA')
    const thiongane = teachers.find((t: any) => t.name === 'T_THIONGANE')
    const diaw = teachers.find((t: any) => t.name === 'T_DIAW_YAHYA')
    const evral = teachers.find((t: any) => t.name === 'T_EVRAL')

    expect(manga?.unavailable_slots?.[0]?.day).toBe('jeudi')
    expect(thiongane?.unavailable_slots?.[0]?.day).toBe('vendredi')
    expect(diaw?.max_hours_per_week).toBe(28)
    expect(evral?.max_hours_per_week).toBe(20)
  })

  it('aligns realistic curriculum hours with Senegal references while preserving non-typical subjects', () => {
    const realistic = FORM_SCENARIOS.find((s) => s.id === 'r-l4-real-school')
    expect(realistic).toBeTruthy()
    if (!realistic) return

    const curriculum = realistic.schoolData.curriculum ?? []
    const subjects = new Set((realistic.schoolData.subjects ?? []).map((s: any) => s.name))

    // Keep TIMEASE-specific non-typical subjects.
    for (const subject of ['CORAN', 'EDU_ISL', 'SCI_PROJ', 'RENF', 'SS']) {
      expect(subjects.has(subject)).toBe(true)
    }

    const findHours = (schoolClass: string, subject: string): number | undefined => {
      const row = curriculum.find((c: any) => c.school_class === schoolClass && c.subject === subject)
      return row?.weekly_hours
    }

    // Collège loads (realistic middle-cycle baseline, feasible profile).
    expect(findHours('6e', 'FR')).toBe(4)
    expect(findHours('6e', 'MATH')).toBe(4)
    expect(findHours('6e', 'HG')).toBe(2)
    expect(findHours('3e', 'ESP')).toBe(2)
    expect(findHours('3e', 'ECO')).toBe(2)

    // Lycée-aligned 2nde profiles (from official secondary credit table, adjusted to fit weekly capacity).
    expect(findHours('2nde', 'FR')).toBe(4)
    expect(findHours('2nde', 'MATH')).toBe(3)
    expect(findHours('2nde', 'HG')).toBe(3)
    expect(findHours('2nde_S', 'MATH')).toBe(4)
    expect(findHours('2nde_S', 'PC')).toBe(4)
    expect(findHours('2nde_S', 'FR')).toBe(4)
  })

  it('keeps an explicit overloaded realistic variant for breakage diagnostics', () => {
    const overloaded = FORM_SCENARIOS.find((s) => s.id === 'r-l4-real-school-overloaded')
    expect(overloaded).toBeTruthy()
    if (!overloaded) return

    const curriculum = overloaded.schoolData.curriculum ?? []
    const totalByClass: Record<string, number> = {}
    for (const entry of curriculum as any[]) {
      const schoolClass = String(entry.school_class || '')
      totalByClass[schoolClass] = (totalByClass[schoolClass] || 0) + Number(entry.weekly_hours || 0)
    }

    expect(totalByClass['2nde_S']).toBeGreaterThan(30)
    expect(totalByClass['6e']).toBeGreaterThan(30)
  })
})
