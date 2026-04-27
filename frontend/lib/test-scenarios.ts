import type { SchoolData } from '@/lib/types'

import easy01 from '@/data/fet-prefills/easy-01-anonymous-2007.json'
import easy02 from '@/data/fet-prefills/easy-02-anonymous-2008.json'
import medium01 from '@/data/fet-prefills/medium-01-gymnasio.json'
import medium02 from '@/data/fet-prefills/medium-02-oradea-difficult.json'
import hard01 from '@/data/fet-prefills/hard-01-bethlen-difficult.json'
import hard02 from '@/data/fet-prefills/hard-02-hk-yewchung-difficult.json'

export type ScenarioCategory = 'feature' | 'fail' | 'realistic'

export type FormScenario = {
  id: string
  level: string
  label: string
  category: ScenarioCategory
  description: string
  expectedOutcome: string
  schoolData: SchoolData
  assignments: any[]
}

type ConvertedPayload = {
  school: { name: string; city: string; academic_year: string }
  timeslot_config: { base_unit_minutes: number; days: any[] }
  rooms: any[]
  classes: any[]
  teachers: any[]
  subjects: any[]
  curriculum: any[]
  constraints: any[]
  teacher_assignments: any[]
}

type DifficultyTier = 'easy' | 'medium' | 'hard'

function toMinutes(value: string): number {
  const [h, m] = value.split(':').map(Number)
  return h * 60 + m
}

function toHHMM(totalMinutes: number): string {
  const h = Math.floor(totalMinutes / 60)
  const m = totalMinutes % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

function slotStartsForDay(day: any, baseUnitMinutes: number): string[] {
  const starts: string[] = []
  for (const session of day?.sessions ?? []) {
    const start = String(session?.start_time || '')
    const end = String(session?.end_time || '')
    if (!start || !end) continue
    let cursor = toMinutes(start)
    const endMin = toMinutes(end)
    while (cursor + baseUnitMinutes <= endMin) {
      starts.push(toHHMM(cursor))
      cursor += baseUnitMinutes
    }
  }
  return starts
}

function enrichTierConstraints(
  schoolData: SchoolData,
  assignments: any[],
  tier: DifficultyTier,
): any[] {
  const existing = schoolData.constraints ?? []
  const firstTeacher = String(schoolData.teachers?.[0]?.name || '')
  const firstSubject = String(schoolData.subjects?.[0]?.name || '')
  const secondarySubject = String(schoolData.subjects?.[1]?.name || '')
  const firstPair = assignments.find((a) => a.school_class && a.subject)
  const firstClass = String(firstPair?.school_class || schoolData.classes?.[0]?.name || '')
  const pinnedSubject = String(firstPair?.subject || firstSubject)
  const firstDay = schoolData.days?.[0]
  const firstDayName = String(firstDay?.name || '')
  const baseUnit = Number(schoolData.base_unit_minutes || 30)
  const firstSlot = slotStartsForDay(firstDay, baseUnit)[0] || ''
  const maxConsecutive = tier === 'easy' ? 4 : 3
  const secondDayName = String(schoolData.days?.[1]?.name || firstDayName)
  const thirdDayName = String(schoolData.days?.[2]?.name || secondDayName)

  const generatedBase = [
    {
      id: `AUTO-${tier}-H10`,
      type: 'hard',
      category: 'one_teacher_per_subject_per_class',
      description_fr: 'Un seul enseignant par matière et par classe',
      priority: 5,
      parameters: {},
    },
    {
      id: `AUTO-${tier}-H4`,
      type: 'hard',
      category: 'max_consecutive',
      description_fr: `Maximum ${maxConsecutive}h consécutives`,
      priority: 5,
      parameters: { max_hours: maxConsecutive },
    },
    {
      id: `AUTO-${tier}-H7`,
      type: 'hard',
      category: 'subject_not_last_slot',
      description_fr: 'Matière lourde hors dernier créneau',
      priority: 5,
      parameters: { subject: firstSubject },
    },
    {
      id: `AUTO-${tier}-H8`,
      type: 'hard',
      category: 'min_break_between',
      description_fr: 'Pause minimale entre deux séances de la même matière',
      priority: 5,
      parameters: { subject: secondarySubject || firstSubject, min_break_minutes: baseUnit },
    },
    {
      id: `AUTO-${tier}-H9`,
      type: 'hard',
      category: 'fixed_assignment',
      description_fr: 'Séance repère fixée pour stabiliser la solution',
      priority: 5,
      parameters: {
        class: firstClass,
        subject: pinnedSubject,
        day: firstDayName,
        slot_start: firstSlot,
      },
    },
  ]

  const generatedMediumAndHard = [
    {
      id: `AUTO-${tier}-H5`,
      type: 'hard',
      category: 'subject_on_days',
      description_fr: 'Matière prioritaire sur jours ciblés',
      priority: 5,
      parameters: { subject: firstSubject, days: [firstDayName, secondDayName].filter(Boolean) },
    },
    {
      id: `AUTO-${tier}-H6`,
      type: 'hard',
      category: 'subject_not_on_days',
      description_fr: 'Matière secondaire hors jour chargé',
      priority: 5,
      parameters: { subject: secondarySubject || firstSubject, days: [thirdDayName].filter(Boolean) },
    },
  ]

  const generatedHardOnly = [
    {
      id: `AUTO-${tier}-H1`,
      type: 'hard',
      category: 'start_time',
      description_fr: 'Heure de début minimale',
      priority: 5,
      parameters: { hour: '08:00' },
    },
    {
      id: `AUTO-${tier}-H3`,
      type: 'hard',
      category: 'day_off',
      description_fr: 'Blocage d’un créneau',
      priority: 5,
      parameters: { day: thirdDayName, session: 'all' },
    },
  ]

  const generatedSoft = [
    {
      id: `AUTO-${tier}-S3`,
      type: 'soft',
      category: 'balanced_daily_load',
      description_fr: 'Répartition quotidienne équilibrée',
      priority: 8,
      parameters: {},
    },
    {
      id: `AUTO-${tier}-S4`,
      type: 'soft',
      category: 'subject_spread',
      description_fr: 'Éviter deux fois la même matière dans la journée',
      priority: 7,
      parameters: {},
    },
    {
      id: `AUTO-${tier}-S6`,
      type: 'soft',
      category: 'teacher_compact_schedule',
      description_fr: 'Réduire les trous dans la journée enseignant',
      priority: 6,
      parameters: { teacher: firstTeacher },
    },
    {
      id: `AUTO-${tier}-S5`,
      type: 'soft',
      category: 'heavy_subjects_morning',
      description_fr: 'Matières prioritaires le matin',
      priority: 7,
      parameters: {
        subjects: [firstSubject, secondarySubject].filter(Boolean),
        preferred_session: 'Matin',
      },
    },
  ]

  const generated = [
    ...generatedBase,
    ...(tier === 'easy' ? [] : generatedMediumAndHard),
    ...(tier === 'hard' ? generatedHardOnly : []),
    ...generatedSoft,
  ].filter((constraint) => {
    const params = constraint.parameters as Record<string, unknown>
    if (constraint.category === 'fixed_assignment') {
      return Boolean(params.class && params.subject && params.day && params.slot_start)
    }
    if (
      constraint.category === 'subject_not_last_slot' ||
      constraint.category === 'min_break_between' ||
      constraint.category === 'subject_on_days' ||
      constraint.category === 'subject_not_on_days'
    ) {
      return Boolean(params.subject)
    }
    if (constraint.category === 'teacher_compact_schedule') {
      return Boolean(params.teacher)
    }
    if (constraint.category === 'day_off') {
      return Boolean(params.day && params.session)
    }
    return true
  })

  return [...existing, ...generated]
}

function toFormScenarioData(payload: ConvertedPayload): {
  schoolData: SchoolData
  assignments: any[]
} {
  return {
    schoolData: {
      name: payload.school.name,
      city: payload.school.city,
      academic_year: payload.school.academic_year,
      base_unit_minutes: payload.timeslot_config.base_unit_minutes,
      days: payload.timeslot_config.days,
      rooms: payload.rooms,
      classes: payload.classes,
      teachers: payload.teachers,
      subjects: payload.subjects,
      curriculum: payload.curriculum,
      constraints: payload.constraints,
    },
    assignments: payload.teacher_assignments,
  }
}

const EASY_01 = toFormScenarioData(easy01 as ConvertedPayload)
EASY_01.schoolData = {
  ...EASY_01.schoolData,
  constraints: enrichTierConstraints(EASY_01.schoolData, EASY_01.assignments, 'easy'),
}
const EASY_02 = toFormScenarioData(easy02 as ConvertedPayload)
EASY_02.schoolData = {
  ...EASY_02.schoolData,
  constraints: enrichTierConstraints(EASY_02.schoolData, EASY_02.assignments, 'easy'),
}
const MEDIUM_01 = toFormScenarioData(medium01 as ConvertedPayload)
MEDIUM_01.schoolData = {
  ...MEDIUM_01.schoolData,
  constraints: enrichTierConstraints(MEDIUM_01.schoolData, MEDIUM_01.assignments, 'medium'),
}
const MEDIUM_02 = toFormScenarioData(medium02 as ConvertedPayload)
MEDIUM_02.schoolData = {
  ...MEDIUM_02.schoolData,
  constraints: enrichTierConstraints(MEDIUM_02.schoolData, MEDIUM_02.assignments, 'medium'),
}
const HARD_01 = toFormScenarioData(hard01 as ConvertedPayload)
HARD_01.schoolData = {
  ...HARD_01.schoolData,
  constraints: enrichTierConstraints(HARD_01.schoolData, HARD_01.assignments, 'hard'),
}
const HARD_02 = toFormScenarioData(hard02 as ConvertedPayload)
HARD_02.schoolData = {
  ...HARD_02.schoolData,
  constraints: enrichTierConstraints(HARD_02.schoolData, HARD_02.assignments, 'hard'),
}

export const FORM_SCENARIOS: FormScenario[] = [
  {
    id: 'fet-easy-01',
    level: 'E1',
    label: 'FET Easy 01 · Anonymous 2007',
    category: 'feature',
    description: 'Jeu réel FET (petit), sans salles, difficulté d’entrée.',
    expectedOutcome: 'Doit générer rapidement.',
    schoolData: EASY_01.schoolData,
    assignments: EASY_01.assignments,
  },
  {
    id: 'fet-easy-02',
    level: 'E2',
    label: 'FET Easy 02 · Anonymous 2008',
    category: 'feature',
    description: 'Jeu réel FET légèrement plus dense (salles présentes).',
    expectedOutcome: 'Doit rester rapide avec plus de contraintes.',
    schoolData: EASY_02.schoolData,
    assignments: EASY_02.assignments,
  },
  {
    id: 'fet-medium-01',
    level: 'M1',
    label: 'FET Medium 01 · Gymnasio',
    category: 'realistic',
    description: 'Jeu réel FET collège avec densité intermédiaire.',
    expectedOutcome: 'Montée de charge nette vs Easy.',
    schoolData: MEDIUM_01.schoolData,
    assignments: MEDIUM_01.assignments,
  },
  {
    id: 'fet-medium-02',
    level: 'M2',
    label: 'FET Medium 02 · Oradea',
    category: 'realistic',
    description: 'Jeu réel FET intermédiaire difficile, contraintes plus serrées.',
    expectedOutcome: 'Temps de résolution plus élevé que M1.',
    schoolData: MEDIUM_02.schoolData,
    assignments: MEDIUM_02.assignments,
  },
  {
    id: 'fet-hard-01',
    level: 'H1',
    label: 'FET Hard 01 · Bethlen',
    category: 'realistic',
    description: 'Jeu réel FET difficile à grande volumétrie.',
    expectedOutcome: 'Charge lourde, utile pour benchmarks de robustesse.',
    schoolData: HARD_01.schoolData,
    assignments: HARD_01.assignments,
  },
  {
    id: 'fet-hard-02',
    level: 'H2',
    label: 'FET Hard 02 · Hong Kong',
    category: 'realistic',
    description: 'Jeu réel FET très difficile (très grande taille).',
    expectedOutcome: 'Stress test maximal pour le solveur.',
    schoolData: HARD_02.schoolData,
    assignments: HARD_02.assignments,
  },
]
