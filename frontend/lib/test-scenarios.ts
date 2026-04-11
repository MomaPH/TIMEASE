import type { SchoolData } from '@/lib/types'

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

function makeDays(dayNames: string[], withBreaks = false): any[] {
  return dayNames.map((name) => ({
    name,
    sessions: [
      { name: 'Matin', start_time: '08:00', end_time: '12:00' },
      { name: 'Après-midi', start_time: '14:00', end_time: '17:00' },
    ],
    breaks: withBreaks ? [{ name: 'Récréation', start_time: '10:00', end_time: '10:15' }] : [],
  }))
}

export const FORM_SCENARIOS: FormScenario[] = [
  {
    id: 'f-l1-smoke',
    level: 'L1',
    label: 'Smoke minimal',
    category: 'feature',
    description: 'Cas d’entrée rapide pour valider toute la chaîne sans complexité.',
    expectedOutcome: 'Doit générer rapidement.',
    schoolData: {
      name: 'Collège Horizon',
      city: 'Dakar',
      academic_year: '2026-2027',
      base_unit_minutes: 30,
      days: makeDays(['lundi']),
      rooms: [{ name: 'Salle A', types: ['Standard'], capacity: 40 }],
      classes: [{ name: '6e A', level: 'Collège', student_count: 0 }],
      teachers: [
        { name: 'Mme Diallo', subjects: ['Mathématiques'] },
        { name: 'M. Ba', subjects: ['Français'] },
      ],
      curriculum: [
        { school_class: '6e A', subject: 'Mathématiques', weekly_hours: 4, sessions_per_week: 4, minutes_per_session: 60, total_minutes_per_week: 240 },
        { school_class: '6e A', subject: 'Français', weekly_hours: 4, sessions_per_week: 4, minutes_per_session: 60, total_minutes_per_week: 240 },
      ],
      subjects: [
        { name: 'Mathématiques', short_name: 'MATH', color: '#0d9488', needs_room: true },
        { name: 'Français', short_name: 'FRAN', color: '#0d9488', needs_room: true },
      ],
      constraints: [],
    },
    assignments: [
      { school_class: '6e A', subject: 'Mathématiques', teacher: 'Mme Diallo' },
      { school_class: '6e A', subject: 'Français', teacher: 'M. Ba' },
    ],
  },
  {
    id: 'f-l4-sessions',
    level: 'L4',
    label: 'Volume sessions',
    category: 'feature',
    description: 'Augmente le volume horaire hebdomadaire avec pauses et salles spécialisées.',
    expectedOutcome: 'Doit générer, potentiellement plus lent.',
    schoolData: {
      name: 'Lycée Mermoz',
      city: 'Dakar',
      academic_year: '2026-2027',
      base_unit_minutes: 30,
      days: makeDays(['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi'], true),
      rooms: [
        { name: 'Salle D1', types: ['Standard'], capacity: 45 },
        { name: 'Salle D2', types: ['Standard'], capacity: 45 },
        { name: 'Lab SVT', types: ['Laboratoire'], capacity: 30 },
      ],
      classes: [
        { name: '6e A', level: 'Collège', student_count: 0 },
        { name: '6e B', level: 'Collège', student_count: 0 },
        { name: '5e A', level: 'Collège', student_count: 0 },
      ],
      teachers: [
        { name: 'Mme Diallo', subjects: ['Mathématiques'] },
        { name: 'M. Ba', subjects: ['Français'] },
        { name: 'Mme Sy', subjects: ['Histoire'] },
      ],
      curriculum: [
        { school_class: '6e A', subject: 'Mathématiques', weekly_hours: 6, sessions_per_week: 6, minutes_per_session: 60, total_minutes_per_week: 360 },
        { school_class: '6e B', subject: 'Mathématiques', weekly_hours: 6, sessions_per_week: 6, minutes_per_session: 60, total_minutes_per_week: 360 },
        { school_class: '5e A', subject: 'Mathématiques', weekly_hours: 6, sessions_per_week: 6, minutes_per_session: 60, total_minutes_per_week: 360 },
        { school_class: '6e A', subject: 'Français', weekly_hours: 5, sessions_per_week: 5, minutes_per_session: 60, total_minutes_per_week: 300 },
      ],
      subjects: [
        { name: 'Mathématiques', short_name: 'MATH', color: '#0d9488', needs_room: true },
        { name: 'Français', short_name: 'FRAN', color: '#0d9488', needs_room: true },
        { name: 'Histoire', short_name: 'HIST', color: '#0d9488', needs_room: true },
      ],
      constraints: [],
    },
    assignments: [
      { school_class: '6e A', subject: 'Mathématiques', teacher: 'Mme Diallo' },
      { school_class: '6e B', subject: 'Mathématiques', teacher: 'Mme Diallo' },
      { school_class: '5e A', subject: 'Mathématiques', teacher: 'Mme Diallo' },
      { school_class: '6e A', subject: 'Français', teacher: 'M. Ba' },
    ],
  },
  {
    id: 'x-missing-assignments',
    level: 'X1',
    label: 'Échec: affectations manquantes',
    category: 'fail',
    description: 'Le programme existe mais les enseignants ne sont pas affectés partout.',
    expectedOutcome: 'Doit bloquer avant génération (checklist rouge).',
    schoolData: {
      name: 'Collège Test Fail',
      city: 'Thiès',
      academic_year: '2026-2027',
      base_unit_minutes: 30,
      days: makeDays(['lundi', 'mardi']),
      rooms: [{ name: 'Salle X', types: ['Standard'], capacity: 35 }],
      classes: [{ name: '6e A', level: 'Collège', student_count: 0 }],
      teachers: [{ name: 'Mme Diallo', subjects: ['Mathématiques'] }],
      curriculum: [
        { school_class: '6e A', subject: 'Mathématiques', weekly_hours: 4, sessions_per_week: 4, minutes_per_session: 60, total_minutes_per_week: 240 },
        { school_class: '6e A', subject: 'Français', weekly_hours: 4, sessions_per_week: 4, minutes_per_session: 60, total_minutes_per_week: 240 },
      ],
      subjects: [
        { name: 'Mathématiques', short_name: 'MATH', color: '#0d9488', needs_room: true },
        { name: 'Français', short_name: 'FRAN', color: '#0d9488', needs_room: true },
      ],
      constraints: [],
    },
    assignments: [{ school_class: '6e A', subject: 'Mathématiques', teacher: 'Mme Diallo' }],
  },
  {
    id: 'x-conflicting-hard',
    level: 'X2',
    label: 'Échec: contraintes dures conflictuelles',
    category: 'fail',
    description: 'Contraintes hard incompatibles pour forcer un échec explicite.',
    expectedOutcome: 'Doit échouer avec conflit de contraintes.',
    schoolData: {
      name: 'Collège Conflit',
      city: 'Mbour',
      academic_year: '2026-2027',
      base_unit_minutes: 30,
      days: makeDays(['lundi', 'mardi', 'mercredi']),
      rooms: [{ name: 'Salle Y', types: ['Standard'], capacity: 35 }],
      classes: [{ name: '6e A', level: 'Collège', student_count: 0 }],
      teachers: [{ name: 'Mme Diallo', subjects: ['Mathématiques'] }],
      curriculum: [
        { school_class: '6e A', subject: 'Mathématiques', weekly_hours: 6, sessions_per_week: 6, minutes_per_session: 60, total_minutes_per_week: 360 },
      ],
      subjects: [{ name: 'Mathématiques', short_name: 'MATH', color: '#0d9488', needs_room: true }],
      constraints: [
        { id: 'c1', type: 'hard', category: 'day_off', description_fr: 'Lundi bloqué', priority: 5, parameters: { day: 'lundi', session: 'all' } },
        { id: 'c2', type: 'hard', category: 'day_off', description_fr: 'Mardi bloqué', priority: 5, parameters: { day: 'mardi', session: 'all' } },
        { id: 'c3', type: 'hard', category: 'day_off', description_fr: 'Mercredi bloqué', priority: 5, parameters: { day: 'mercredi', session: 'all' } },
      ],
    },
    assignments: [{ school_class: '6e A', subject: 'Mathématiques', teacher: 'Mme Diallo' }],
  },
  {
    id: 'r-shared-teacher',
    level: 'R1',
    label: 'Réaliste: enseignant partagé',
    category: 'realistic',
    description: 'Un enseignant couvre plusieurs classes, cas terrain classique.',
    expectedOutcome: 'Doit générer avec éventuels compromis de placement.',
    schoolData: {
      name: 'Collège Lumière',
      city: 'Kaolack',
      academic_year: '2026-2027',
      base_unit_minutes: 30,
      days: makeDays(['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi']),
      rooms: [
        { name: 'Salle E1', types: ['Standard'], capacity: 40 },
        { name: 'Salle E2', types: ['Standard'], capacity: 40 },
      ],
      classes: [
        { name: '6e A', level: 'Collège', student_count: 0 },
        { name: '6e B', level: 'Collège', student_count: 0 },
        { name: '5e A', level: 'Collège', student_count: 0 },
        { name: '4e A', level: 'Collège', student_count: 0 },
      ],
      teachers: [
        { name: 'Mme Diallo', subjects: ['Mathématiques', 'Sciences'] },
        { name: 'M. Ba', subjects: ['Français'] },
        { name: 'Mme Sy', subjects: ['Histoire'] },
      ],
      curriculum: [
        { school_class: '6e A', subject: 'Mathématiques', weekly_hours: 5, sessions_per_week: 5, minutes_per_session: 60, total_minutes_per_week: 300 },
        { school_class: '6e B', subject: 'Mathématiques', weekly_hours: 5, sessions_per_week: 5, minutes_per_session: 60, total_minutes_per_week: 300 },
        { school_class: '5e A', subject: 'Mathématiques', weekly_hours: 5, sessions_per_week: 5, minutes_per_session: 60, total_minutes_per_week: 300 },
        { school_class: '4e A', subject: 'Sciences', weekly_hours: 4, sessions_per_week: 4, minutes_per_session: 60, total_minutes_per_week: 240 },
        { school_class: '6e A', subject: 'Français', weekly_hours: 4, sessions_per_week: 4, minutes_per_session: 60, total_minutes_per_week: 240 },
      ],
      subjects: [
        { name: 'Mathématiques', short_name: 'MATH', color: '#0d9488', needs_room: true },
        { name: 'Sciences', short_name: 'SCIE', color: '#0d9488', needs_room: true },
        { name: 'Français', short_name: 'FRAN', color: '#0d9488', needs_room: true },
      ],
      constraints: [],
    },
    assignments: [
      { school_class: '6e A', subject: 'Mathématiques', teacher: 'Mme Diallo' },
      { school_class: '6e B', subject: 'Mathématiques', teacher: 'Mme Diallo' },
      { school_class: '5e A', subject: 'Mathématiques', teacher: 'Mme Diallo' },
      { school_class: '4e A', subject: 'Sciences', teacher: 'Mme Diallo' },
      { school_class: '6e A', subject: 'Français', teacher: 'M. Ba' },
    ],
  },
]
