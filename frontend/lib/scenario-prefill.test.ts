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

  it('provides FET-based prefills grouped by easy, medium and hard with gradual complexity', () => {
    const expectedIds = [
      'fet-easy-01',
      'fet-easy-02',
      'fet-medium-01',
      'fet-medium-02',
      'fet-hard-01',
      'fet-hard-02',
    ]
    expect(FORM_SCENARIOS.map((s) => s.id)).toEqual(expectedIds)

    const sizes = FORM_SCENARIOS.map((s) => ({
      id: s.id,
      classes: s.schoolData.classes?.length ?? 0,
      teachers: s.schoolData.teachers?.length ?? 0,
      curriculum: s.schoolData.curriculum?.length ?? 0,
      assignments: s.assignments.length,
      constraints: s.schoolData.constraints?.length ?? 0,
      hardConstraints: (s.schoolData.constraints ?? []).filter((c: any) => c.type === 'hard').length,
      softConstraints: (s.schoolData.constraints ?? []).filter((c: any) => c.type === 'soft').length,
    }))

    expect(sizes[0].curriculum).toBeLessThan(sizes[1].curriculum)
    expect(sizes[1].curriculum).toBeLessThan(sizes[2].curriculum)
    expect(sizes[2].curriculum).toBeLessThan(sizes[3].curriculum)
    expect(sizes[3].curriculum).toBeLessThan(sizes[4].curriculum)
    expect(sizes[4].curriculum).toBeGreaterThanOrEqual(sizes[5].curriculum)

    for (const row of sizes) {
      expect(row.assignments).toBe(row.curriculum)
      expect(row.classes).toBeGreaterThan(0)
      expect(row.teachers).toBeGreaterThan(0)
      expect(row.constraints).toBeGreaterThanOrEqual(8)
      expect(row.hardConstraints).toBeGreaterThanOrEqual(5)
      expect(row.softConstraints).toBeGreaterThanOrEqual(3)
    }

    const [e1, e2, m1, m2, h1, h2] = sizes
    expect(m1.hardConstraints).toBeGreaterThan(e2.hardConstraints)
    expect(m2.hardConstraints).toBeGreaterThan(e2.hardConstraints)
    expect(h1.hardConstraints).toBeGreaterThan(m2.hardConstraints)
    expect(h2.hardConstraints).toBeGreaterThan(m2.hardConstraints)
  })
})
