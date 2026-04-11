import type { SchoolData } from '@/lib/types'
import type { FormScenario } from '@/lib/test-scenarios'

export type PrefillPayload = {
  data: SchoolData
  assignments: any[]
}

function deepClone<T>(value: T): T {
  if (typeof structuredClone === 'function') {
    return structuredClone(value)
  }
  return JSON.parse(JSON.stringify(value)) as T
}

export function applyScenarioPreset(current: SchoolData, scenario: FormScenario): PrefillPayload {
  const schoolData = deepClone(scenario.schoolData)
  const assignments = deepClone(scenario.assignments)

  return {
    data: {
      ...current,
      name: schoolData.name,
      city: schoolData.city,
      academic_year: schoolData.academic_year,
      base_unit_minutes: schoolData.base_unit_minutes,
      days: schoolData.days ?? [],
      rooms: schoolData.rooms ?? [],
      classes: schoolData.classes ?? [],
      teachers: schoolData.teachers ?? [],
      curriculum: schoolData.curriculum ?? [],
      subjects: schoolData.subjects ?? [],
      constraints: schoolData.constraints ?? [],
    },
    assignments,
  }
}

