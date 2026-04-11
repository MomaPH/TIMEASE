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

const REAL_SUBJECTS = [
  'CORAN', 'EDU_ISL', 'ARABE', 'FR', 'MATH', 'PC', 'SVT',
  'HG', 'ANG', 'ESP', 'ECO', 'SS', 'SCI_PROJ', 'RENF',
]

const REAL_CLASSES = ['6e', '5e', '4e', '3e', '2nde', '2nde_S']

const REAL_TEACHERS: Array<{ name: string; subjects: string[]; max_hours_per_week: number; calendar_variant: 'standard' | 'shifted_break'; unavailable_slots?: any[] }> = [
  { name: 'T_BA', subjects: ['FR', 'ARABE'], max_hours_per_week: 24, calendar_variant: 'shifted_break' },
  { name: 'T_NIANG', subjects: ['ANG', 'ESP'], max_hours_per_week: 24, calendar_variant: 'shifted_break' },
  { name: 'T_KOUNTA', subjects: ['ARABE'], max_hours_per_week: 24, calendar_variant: 'standard' },
  { name: 'T_DIAW_YAHYA', subjects: ['MATH', 'PC'], max_hours_per_week: 28, calendar_variant: 'standard' },
  { name: 'T_MANGA', subjects: ['HG', 'SS'], max_hours_per_week: 24, calendar_variant: 'standard', unavailable_slots: [{ day: 'jeudi', start: '07:50', end: '16:30' }] },
  { name: 'T_THIONGANE', subjects: ['ECO'], max_hours_per_week: 24, calendar_variant: 'standard', unavailable_slots: [{ day: 'vendredi', start: '14:00', end: '16:30' }] },
  { name: 'T_EVRAL', subjects: ['SVT', 'SCI_PROJ'], max_hours_per_week: 20, calendar_variant: 'standard' },
  { name: 'T_DIEME', subjects: ['FR', 'RENF'], max_hours_per_week: 24, calendar_variant: 'standard' },
  { name: 'T_NDIAYE', subjects: ['CORAN', 'EDU_ISL'], max_hours_per_week: 24, calendar_variant: 'standard' },
  { name: 'T_DIOP_MATH', subjects: ['MATH'], max_hours_per_week: 24, calendar_variant: 'standard' },
  { name: 'T_ARAME', subjects: ['PC'], max_hours_per_week: 24, calendar_variant: 'standard' },
  { name: 'T_HG1', subjects: ['HG'], max_hours_per_week: 24, calendar_variant: 'standard' },
  { name: 'T_HG2', subjects: ['SS'], max_hours_per_week: 24, calendar_variant: 'standard' },
  { name: 'T_LANG1', subjects: ['ANG'], max_hours_per_week: 24, calendar_variant: 'standard' },
  { name: 'T_LANG2', subjects: ['ESP'], max_hours_per_week: 24, calendar_variant: 'standard' },
  { name: 'T_ECO', subjects: ['ECO'], max_hours_per_week: 24, calendar_variant: 'standard' },
  { name: 'T_SCI_PROJ', subjects: ['SCI_PROJ'], max_hours_per_week: 24, calendar_variant: 'standard' },
]

function buildRealisticDays(): any[] {
  return [
    {
      name: 'lundi',
      sessions: [{ name: 'Matin', start_time: '07:50', end_time: '13:00' }, { name: 'Après-midi', start_time: '14:00', end_time: '16:30' }],
      breaks: [
        { name: 'Doua', start_time: '07:50', end_time: '08:00' },
        { name: 'Récréation', start_time: '10:00', end_time: '10:10' },
        { name: 'Déjeuner/prière', start_time: '13:00', end_time: '14:00' },
      ],
    },
    {
      name: 'mardi',
      sessions: [{ name: 'Matin', start_time: '07:50', end_time: '13:00' }, { name: 'Après-midi', start_time: '14:00', end_time: '16:30' }],
      breaks: [
        { name: 'Doua', start_time: '07:50', end_time: '08:00' },
        { name: 'Récréation', start_time: '10:00', end_time: '10:10' },
        { name: 'Déjeuner/prière', start_time: '13:00', end_time: '14:00' },
      ],
    },
    {
      name: 'mercredi',
      sessions: [{ name: 'Matin', start_time: '07:50', end_time: '13:00' }],
      breaks: [
        { name: 'Doua', start_time: '07:50', end_time: '08:00' },
        { name: 'Récréation', start_time: '10:00', end_time: '10:10' },
      ],
    },
    {
      name: 'jeudi',
      sessions: [{ name: 'Matin', start_time: '07:50', end_time: '13:00' }, { name: 'Après-midi', start_time: '14:00', end_time: '16:30' }],
      breaks: [
        { name: 'Doua', start_time: '07:50', end_time: '08:00' },
        { name: 'Récréation', start_time: '10:00', end_time: '10:10' },
        { name: 'Déjeuner/prière', start_time: '13:00', end_time: '14:00' },
      ],
    },
    {
      name: 'vendredi',
      sessions: [{ name: 'Matin', start_time: '07:50', end_time: '13:00' }, { name: 'Après-midi', start_time: '14:00', end_time: '16:30' }],
      breaks: [
        { name: 'Doua', start_time: '07:50', end_time: '08:00' },
        { name: 'Récréation', start_time: '10:00', end_time: '10:10' },
        { name: 'Déjeuner/prière', start_time: '13:00', end_time: '14:00' },
      ],
    },
  ]
}

function teacherForSubject(subject: string, cls: string): string {
  const map: Record<string, string[]> = {
    CORAN: ['T_NDIAYE'],
    EDU_ISL: ['T_NDIAYE'],
    ARABE: ['T_KOUNTA', 'T_BA'],
    FR: ['T_DIEME', 'T_BA'],
    MATH: ['T_DIAW_YAHYA', 'T_DIOP_MATH'],
    PC: ['T_DIAW_YAHYA', 'T_ARAME'],
    SVT: ['T_EVRAL'],
    HG: ['T_MANGA', 'T_HG1'],
    ANG: ['T_NIANG', 'T_LANG1'],
    ESP: ['T_NIANG', 'T_LANG2'],
    ECO: ['T_THIONGANE', 'T_ECO'],
    SS: ['T_MANGA', 'T_HG2'],
    SCI_PROJ: ['T_EVRAL', 'T_SCI_PROJ'],
    RENF: ['T_DIEME'],
  }
  const choices = map[subject] ?? ['T_DIEME']
  const idx = (REAL_CLASSES.indexOf(cls) + subject.length) % choices.length
  return choices[idx]
}

function buildRealisticCurriculumAndAssignments() {
  const sessionsBySubject: Record<string, number> = {
    CORAN: 3, EDU_ISL: 2, ARABE: 3, FR: 4, MATH: 4, PC: 2, SVT: 2,
    HG: 2, ANG: 2, ESP: 1, ECO: 1, SS: 1, SCI_PROJ: 1, RENF: 2,
  }

  const curriculum: any[] = []
  const assignments: any[] = []
  for (const cls of REAL_CLASSES) {
    for (const subject of REAL_SUBJECTS) {
      const sessions = sessionsBySubject[subject]
      curriculum.push({
        school_class: cls,
        subject,
        weekly_hours: sessions * 0.5,
        sessions_per_week: sessions,
        minutes_per_session: 30,
        total_minutes_per_week: sessions * 30,
      })
      assignments.push({
        school_class: cls,
        subject,
        teacher: teacherForSubject(subject, cls),
      })
    }
  }
  return { curriculum, assignments }
}

const REAL_L4_BUILD = buildRealisticCurriculumAndAssignments()

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
  {
    id: 'r-l4-real-school',
    level: 'L4',
    label: 'Réaliste école complète',
    category: 'realistic',
    description: 'Scénario terrain complet sans compromis: volumes, contraintes, indisponibilités, caps.',
    expectedOutcome: 'Préfill massif fidèle au réel; prêt pour génération/diagnostic.',
    schoolData: {
      name: 'École Réelle Référence',
      city: 'Dakar',
      academic_year: '2026-2027',
      base_unit_minutes: 30,
      days: buildRealisticDays(),
      rooms: [
        { name: 'R_CLASS_1', types: ['Standard'], capacity: 45 },
        { name: 'R_CLASS_2', types: ['Standard'], capacity: 45 },
        { name: 'R_CLASS_3', types: ['Standard'], capacity: 45 },
        { name: 'R_LAB1', types: ['Laboratoire'], capacity: 25 },
        { name: 'R_LANG1', types: ['Langue'], capacity: 30 },
        { name: 'R_MOSQUE', types: ['Mosquée'], capacity: 200 },
      ],
      classes: REAL_CLASSES.map((name, i) => ({ name, level: i < 4 ? 'Collège' : 'Lycée', student_count: i < 4 ? 38 : 42 })),
      teachers: REAL_TEACHERS,
      curriculum: REAL_L4_BUILD.curriculum,
      subjects: REAL_SUBJECTS.map((name) => ({ name, short_name: name.slice(0, 4), color: '#0d9488', needs_room: true })),
      constraints: [
        { id: 'C1', type: 'hard', category: 'teacher_no_overlap', description_fr: 'Pas de chevauchement enseignant', priority: 10, parameters: {} },
        { id: 'C2', type: 'hard', category: 'class_no_overlap', description_fr: 'Pas de chevauchement classe', priority: 10, parameters: {} },
        { id: 'C3', type: 'hard', category: 'ritual_slots_blocked', description_fr: 'Rituels verrouillés (Doua/BRK/L01/L02)', priority: 10, parameters: { slots: ['S00', 'BRK', 'B1', 'B2', 'L01', 'L02'] } },
        { id: 'C4', type: 'hard', category: 'day_off', description_fr: 'Mercredi après-midi bloqué', priority: 10, parameters: { day: 'mercredi', session: 'Après-midi' } },
        { id: 'C5', type: 'hard', category: 'teacher_subject_declared', description_fr: 'Matière enseignant déclarée', priority: 10, parameters: {} },
        { id: 'C6', type: 'hard', category: 'teacher_calendar_declared', description_fr: 'Calendrier enseignant déclaré', priority: 10, parameters: {} },
        { id: 'S1', type: 'soft', category: 'teacher_compact_schedule', description_fr: 'Minimiser les trous enseignant', priority: 5, parameters: {} },
        { id: 'S2', type: 'soft', category: 'heavy_subjects_morning', description_fr: 'MATH avant 13:00', priority: 3, parameters: { subjects: ['MATH'], preferred_session: 'Matin' } },
        { id: 'S3', type: 'soft', category: 'no_subject_back_to_back', description_fr: 'Même matière ≤ 4 consécutives', priority: 8, parameters: { max_consecutive: 4 } },
        { id: 'S4', type: 'soft', category: 'balanced_daily_load', description_fr: 'Charge quotidienne équilibrée', priority: 4, parameters: { tolerance_slots: 2 } },
      ],
    },
    assignments: REAL_L4_BUILD.assignments,
  },
]
