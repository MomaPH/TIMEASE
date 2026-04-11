'use client'
import { useState } from 'react'
import { Plus, Trash2, ChevronRight, ChevronDown, Info } from 'lucide-react'
import type { SchoolData } from '@/lib/types'
import { FORM_SCENARIOS } from '@/lib/test-scenarios'
import { applyScenarioPreset } from '@/lib/scenario-prefill'

const LEVELS = ['Maternelle', 'Primaire', 'Collège', 'Lycée', 'Autre']

type ConstraintType = 'hard' | 'soft'
type FieldType = 'teacher' | 'class' | 'subject' | 'day' | 'session' | 'time' | 'number' | 'text' | 'subjects' | 'days' | 'choice'

type FieldDef = {
  key: string
  label: string
  type: FieldType
  required?: boolean
  min?: number
  max?: number
  placeholder?: string
  help: string
  choices?: string[]
}

type ConstraintDef = {
  value: string
  label: string
  type: ConstraintType
  fields: FieldDef[]
  description: string
  whenToUse: string
  example: string
}

const DAY_NAMES = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi']

const CONSTRAINT_DEFS: ConstraintDef[] = [
  {
    value: 'start_time', label: 'Heure de début minimum', type: 'hard',
    fields: [{ key: 'hour', label: 'Heure minimum', type: 'time', required: true, help: "Les cours ne commenceront pas avant cette heure." }],
    description: "Bloque tous les créneaux avant l'heure choisie.",
    whenToUse: 'Utile pour éviter des débuts trop tôt.',
    example: '08:00 pour démarrer à partir de 8h.',
  },
  {
    value: 'day_off', label: 'Jour bloqué', type: 'hard',
    fields: [
      { key: 'day', label: 'Jour', type: 'day', required: true, help: 'Jour à bloquer.' },
      { key: 'session', label: 'Session', type: 'session', required: true, help: "Choisissez 'all' pour toute la journée." },
    ],
    description: "Interdit de placer des cours sur le jour/session visé.",
    whenToUse: 'Ex: samedi après-midi indisponible.',
    example: 'Jour: samedi, Session: Après-midi',
  },
  {
    value: 'max_consecutive', label: 'Max heures consécutives', type: 'hard',
    fields: [{ key: 'max_hours', label: 'Heures max', type: 'number', required: true, min: 1, max: 8, help: 'Nombre maximum d’heures d’affilée pour une classe.' }],
    description: "Limite les blocs trop longs sans pause.",
    whenToUse: 'Pour réduire la fatigue des élèves.',
    example: '3 ou 4 heures consécutives maximum.',
  },
  {
    value: 'subject_on_days', label: 'Matière sur jours précis', type: 'hard',
    fields: [
      { key: 'subject', label: 'Matière', type: 'subject', required: true, help: 'Matière concernée.' },
      { key: 'days', label: 'Jours autorisés', type: 'days', required: true, help: 'La matière ne pourra être placée que sur ces jours.' },
    ],
    description: "Autorise une matière uniquement sur certains jours.",
    whenToUse: 'Quand une matière doit être regroupée sur des jours fixes.',
    example: 'Mathématiques sur lundi + mercredi.',
  },
  {
    value: 'subject_not_on_days', label: 'Matière interdite certains jours', type: 'hard',
    fields: [
      { key: 'subject', label: 'Matière', type: 'subject', required: true, help: 'Matière concernée.' },
      { key: 'days', label: 'Jours interdits', type: 'days', required: true, help: 'La matière sera exclue de ces jours.' },
    ],
    description: "Empêche une matière sur des jours spécifiques.",
    whenToUse: 'Ex: éviter EPS le mardi.',
    example: 'EPS interdit le mardi.',
  },
  {
    value: 'subject_not_last_slot', label: 'Matière pas en dernière heure', type: 'hard',
    fields: [{ key: 'subject', label: 'Matière', type: 'subject', required: true, help: 'Matière à éviter en fin de journée.' }],
    description: "Empêche la matière en tout dernier créneau.",
    whenToUse: 'Pour matières qui demandent forte concentration.',
    example: 'Maths jamais au dernier créneau.',
  },
  {
    value: 'min_break_between', label: 'Pause minimale entre séances', type: 'hard',
    fields: [
      { key: 'subject', label: 'Matière', type: 'subject', required: true, help: 'Matière concernée.' },
      { key: 'min_break_minutes', label: 'Pause min (minutes)', type: 'number', required: true, min: 30, max: 240, help: 'Pause minimale entre deux séances de cette matière.' },
    ],
    description: "Impose un écart minimum entre deux cours d'une même matière.",
    whenToUse: 'Pour éviter 2 séances trop rapprochées.',
    example: 'Français: 60 minutes minimum.',
  },
  {
    value: 'fixed_assignment', label: 'Créneau imposé', type: 'hard',
    fields: [
      { key: 'class', label: 'Classe', type: 'class', required: true, help: 'Classe ciblée.' },
      { key: 'subject', label: 'Matière', type: 'subject', required: true, help: 'Matière ciblée.' },
      { key: 'day', label: 'Jour', type: 'day', required: true, help: 'Jour imposé.' },
      { key: 'slot_start', label: 'Heure de début', type: 'time', required: true, help: 'Heure exacte de début du cours.' },
    ],
    description: "Force un cours à un créneau précis.",
    whenToUse: 'Pour ateliers/salles partagées déjà réservées.',
    example: '3ème A + Physique + jeudi 10:00.',
  },
  {
    value: 'one_teacher_per_subject_per_class', label: 'Un seul enseignant par matière/classe', type: 'hard',
    fields: [],
    description: "Garantit la continuité pédagogique sur l'année.",
    whenToUse: 'Activé dans la plupart des établissements.',
    example: 'Pas de paramètre à saisir.',
  },
  {
    value: 'min_sessions_per_day', label: 'Minimum de sessions par jour', type: 'hard',
    fields: [{ key: 'min_sessions', label: 'Sessions min / jour', type: 'number', required: true, min: 1, max: 6, help: 'Nombre minimum de cours par classe et par jour.' }],
    description: "Évite des journées vides pour une classe.",
    whenToUse: 'Quand la présence quotidienne est requise.',
    example: '1 session minimum par jour.',
  },
  {
    value: 'teacher_time_preference', label: 'Préférence horaire enseignant', type: 'soft',
    fields: [
      { key: 'teacher', label: 'Enseignant', type: 'teacher', required: true, help: 'Enseignant concerné.' },
      { key: 'preferred_session', label: 'Session préférée', type: 'choice', required: true, choices: ['Matin', 'Après-midi'], help: 'Période souhaitée.' },
    ],
    description: "Favorise les créneaux préférés d'un enseignant.",
    whenToUse: "Pour améliorer le confort sans bloquer la solution.",
    example: 'Mme Fall préfère Matin.',
  },
  {
    value: 'teacher_fallback_preference', label: 'Préférence horaire (fallback)', type: 'soft',
    fields: [
      { key: 'teacher', label: 'Enseignant', type: 'teacher', required: true, help: 'Enseignant concerné.' },
      { key: 'preferred_session', label: 'Session préférée', type: 'choice', required: true, choices: ['Matin', 'Après-midi'], help: 'Période souhaitée.' },
    ],
    description: "Préférence de secours, plus faible.",
    whenToUse: 'Si vous voulez une préférence moins prioritaire.',
    example: 'M. Sy préfère Après-midi en second choix.',
  },
  {
    value: 'balanced_daily_load', label: 'Charge équilibrée par jour', type: 'soft',
    fields: [],
    description: "Répartit les cours de manière homogène sur la semaine.",
    whenToUse: 'Pour éviter des journées trop lourdes.',
    example: 'Pas de paramètre à saisir.',
  },
  {
    value: 'subject_spread', label: 'Même matière pas 2x/jour', type: 'soft',
    fields: [],
    description: "Évite de répéter la même matière plusieurs fois le même jour.",
    whenToUse: 'Pour varier les apprentissages dans la journée.',
    example: 'Pas de paramètre à saisir.',
  },
  {
    value: 'heavy_subjects_morning', label: 'Matières difficiles le matin', type: 'soft',
    fields: [
      { key: 'subjects', label: 'Matières ciblées', type: 'subjects', required: true, help: 'Sélectionnez les matières à placer de préférence le matin.' },
      { key: 'preferred_session', label: 'Session préférée', type: 'choice', required: true, choices: ['Matin', 'Après-midi'], help: 'Période prioritaire.' },
    ],
    description: "Privilégie les matières exigeantes à des heures favorables.",
    whenToUse: 'Typiquement Maths, Français, Physique.',
    example: 'Mathématiques + Français en Matin.',
  },
  {
    value: 'teacher_compact_schedule', label: 'Emploi du temps compact enseignant', type: 'soft',
    fields: [{ key: 'teacher', label: 'Enseignant (optionnel)', type: 'teacher', help: 'Laissez vide pour appliquer à tous.' }],
    description: "Réduit les trous dans la journée d'un enseignant.",
    whenToUse: 'Pour limiter les longues attentes entre deux cours.',
    example: 'Vide = tous les enseignants.',
  },
  {
    value: 'same_room_for_class', label: 'Même salle par classe', type: 'soft',
    fields: [],
    description: "Favorise la stabilité de salle pour chaque classe.",
    whenToUse: 'Pour réduire les déplacements.',
    example: 'Pas de paramètre à saisir.',
  },
  {
    value: 'teacher_day_off', label: 'Jour de repos enseignant', type: 'soft',
    fields: [
      { key: 'teacher', label: 'Enseignant', type: 'teacher', required: true, help: 'Enseignant concerné.' },
      { key: 'day', label: 'Jour souhaité', type: 'day', required: true, help: 'Jour idéal sans cours.' },
    ],
    description: "Tente de libérer une journée pour un enseignant.",
    whenToUse: "Pour contraintes personnelles sans bloquer l'algorithme.",
    example: 'M. Diallo repos le mercredi.',
  },
  {
    value: 'no_subject_back_to_back', label: 'Pas de matière enchaînée', type: 'soft',
    fields: [{ key: 'subject', label: 'Matière (optionnel)', type: 'subject', help: 'Laissez vide pour toutes les matières.' }],
    description: "Évite deux séances consécutives de la même matière.",
    whenToUse: 'Pour limiter la monotonie dans une même journée.',
    example: 'Vide = toutes les matières.',
  },
  {
    value: 'light_last_day', label: 'Dernier jour allégé', type: 'soft',
    fields: [{ key: 'day', label: 'Jour ciblé (optionnel)', type: 'day', help: 'Laissez vide pour utiliser le dernier jour configuré.' }],
    description: "Allège la charge de cours sur le dernier jour.",
    whenToUse: 'Souvent utile pour samedi.',
    example: 'Jour: samedi.',
  },
]

const CATEGORY_ALIASES: Record<string, string> = {
  one_teacher_per_subject_class: 'one_teacher_per_subject_per_class',
}

interface Props {
  data: SchoolData
  assignments: any[]
  onUpdateData: (d: SchoolData) => void
  onUpdateAssignments: (a: any[]) => void
}


function normalizeSubject(value: string): string {
  return value.trim()
}

function parseSubjectsInput(raw: string): string[] {
  const parts = raw
    .split(/[,;\n]+/)
    .map(normalizeSubject)
    .filter(Boolean)

  const seen = new Set<string>()
  const result: string[] = []
  for (const subject of parts) {
    const key = subject.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    result.push(subject)
  }
  return result
}

function getTeacherDeclaredSubjects(data: SchoolData): string[] {
  const teachers = data.teachers ?? []
  const seen = new Set<string>()
  const result: string[] = []

  for (const teacher of teachers) {
    for (const subjectRaw of teacher.subjects ?? []) {
      const subject = normalizeSubject(String(subjectRaw || ''))
      if (!subject) continue
      const key = subject.toLowerCase()
      if (seen.has(key)) continue
      seen.add(key)
      result.push(subject)
    }
  }

  return result
}

// ── Teacher section ───────────────────────────────────────────────────────────

function TeachersSection({
  data,
  assignments,
  onUpdateData,
  onUpdateAssignments,
}: {
  data: SchoolData
  assignments: any[]
  onUpdateData: (d: SchoolData) => void
  onUpdateAssignments: (a: any[]) => void
}) {
  const teachers = data.teachers ?? []
  const [open, setOpen] = useState(teachers.length === 0)

  function addTeacher() {
    onUpdateData({ ...data, teachers: [...teachers, { name: '', subjects: [] }] })
  }

  function updateTeacher(idx: number, field: string, val: string | string[]) {
    if (field === 'name') {
      const oldName = teachers[idx]?.name as string
      const newName = val as string
      onUpdateData({ ...data, teachers: teachers.map((t, i) => i === idx ? { ...t, [field]: val } : t) })
      // cascade rename in assignments
      if (oldName && oldName !== newName) {
        onUpdateAssignments(assignments.map(a => a.teacher === oldName ? { ...a, teacher: newName } : a))
      }
    } else if (field === 'subjects') {
      const teacherName = String(teachers[idx]?.name || '')
      const parsed = Array.isArray(val)
        ? val.map(v => normalizeSubject(String(v))).filter(Boolean)
        : parseSubjectsInput(String(val || ''))

      onUpdateData({ ...data, teachers: teachers.map((t, i) => i === idx ? { ...t, subjects: parsed } : t) })

      if (teacherName) {
        const allowed = new Set(parsed.map(s => s.toLowerCase()))
        onUpdateAssignments(
          assignments.filter(a => {
            if (a.teacher !== teacherName) return true
            return allowed.has(String(a.subject || '').trim().toLowerCase())
          })
        )
      }
    } else {
      onUpdateData({ ...data, teachers: teachers.map((t, i) => i === idx ? { ...t, [field]: val } : t) })
    }
  }

  function deleteTeacher(idx: number) {
    const deletedName = teachers[idx]?.name as string
    onUpdateData({ ...data, teachers: teachers.filter((_, i) => i !== idx) })
    // remove assignments that reference the deleted teacher
    if (deletedName) {
      onUpdateAssignments(assignments.filter(a => a.teacher !== deletedName))
    }
  }

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      >
        <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          Enseignants
          {teachers.length > 0 && (
            <span className="ml-2 text-xs font-normal text-gray-400">({teachers.length})</span>
          )}
        </span>
        <ChevronRight size={14} className={`text-gray-400 transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>

      {open && (
        <div className="p-3 space-y-2 bg-white dark:bg-gray-900">
          {teachers.length === 0 && (
            <p className="text-xs text-gray-400 italic">Aucun enseignant défini.</p>
          )}
          {teachers.map((t, idx) => (
            <div key={idx} className="flex gap-2 items-center">
              <input
                value={t.name ?? ''}
                onChange={e => updateTeacher(idx, 'name', e.target.value)}
                placeholder="Nom de l'enseignant"
                className="flex-1 min-w-0 px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
              <input
                value={(t.subjects ?? []).join(', ')}
                onChange={e => updateTeacher(idx, 'subjects', parseSubjectsInput(e.target.value))}
                placeholder="Matieres (ex: Maths, Physique, SVT)"
                className="flex-1 min-w-0 px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
              <button onClick={() => deleteTeacher(idx)} className="text-gray-400 hover:text-red-500 transition-colors flex-shrink-0">
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          <button onClick={addTeacher} className="flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 hover:text-teal-700 transition-colors">
            <Plus size={13} /> Enseignant
          </button>
        </div>
      )}
    </div>
  )
}

// ── Class card ────────────────────────────────────────────────────────────────

function ClassCard({
  cls,
  clsIdx,
  data,
  assignments,
  onUpdateData,
  onUpdateAssignments,
}: {
  cls: any
  clsIdx: number
  data: SchoolData
  assignments: any[]
  onUpdateData: (d: SchoolData) => void
  onUpdateAssignments: (a: any[]) => void
}) {
  const teacherRecords = (data.teachers ?? []).filter((t: any) => (t.name ?? '').trim() !== '')
  const teachers  = teacherRecords.map((t: any) => String(t.name))
  const availableSubjects = getTeacherDeclaredSubjects(data)
  const curriculum = (data.curriculum ?? []).filter((c: any) => c.school_class === cls.name)
  const selectedSubjects = new Set(
    curriculum
      .map((c: any) => normalizeSubject(String(c.subject || '')))
      .filter(Boolean)
      .map((s: string) => s.toLowerCase())
  )
  const [copyOpen, setCopyOpen] = useState(false)
  const otherClasses = (data.classes ?? []).filter((c: any) => c.name !== cls.name).map((c: any) => c.name)

  function getEligibleTeachersForSubject(subject: string): string[] {
    const key = normalizeSubject(subject).toLowerCase()
    if (!key) return []
    return teacherRecords
      .filter((t: any) =>
        (t.subjects ?? []).some((s: string) => normalizeSubject(String(s)).toLowerCase() === key)
      )
      .map((t: any) => String(t.name))
  }

  // ── Helpers ──────────────────────────────────────────────────────────────────

  function renameClass(newName: string) {
    const oldName = cls.name
    const nextClasses   = (data.classes ?? []).map((c: any) => c.name === oldName ? { ...c, name: newName } : c)
    const nextCurriculum = (data.curriculum ?? []).map((c: any) => c.school_class === oldName ? { ...c, school_class: newName } : c)
    const nextAssignments = assignments.map(a => a.school_class === oldName ? { ...a, school_class: newName } : a)
    onUpdateData({ ...data, classes: nextClasses, curriculum: nextCurriculum })
    onUpdateAssignments(nextAssignments)
  }

  function updateLevel(level: string) {
    const nextClasses = (data.classes ?? []).map((c: any, i: number) => i === clsIdx ? { ...c, level } : c)
    onUpdateData({ ...data, classes: nextClasses })
  }

  function deleteClass() {
    const nextClasses    = (data.classes ?? []).filter((_: any, i: number) => i !== clsIdx)
    const nextCurriculum = (data.curriculum ?? []).filter((c: any) => c.school_class !== cls.name)
    const nextSubjects   = deriveSubjects({ ...data, classes: nextClasses, curriculum: nextCurriculum })
    const nextAssignments = assignments.filter(a => a.school_class !== cls.name)
    onUpdateData({ ...data, classes: nextClasses, curriculum: nextCurriculum, subjects: nextSubjects })
    onUpdateAssignments(nextAssignments)
  }

  function addCurriculumRow() {
    const newRow = {
      school_class: cls.name,
      subject: '',
      weekly_hours: 2,
      sessions_per_week: 2,
      minutes_per_session: 60,
      total_minutes_per_week: 120,
    }
    onUpdateData({ ...data, curriculum: [...(data.curriculum ?? []), newRow] })
  }

  function toggleClassSubject(subject: string, enabled: boolean) {
    const allCurriculum = data.curriculum ?? []
    const subjectNorm = normalizeSubject(subject)
    const subjectKey = subjectNorm.toLowerCase()
    const classRows = allCurriculum.filter((c: any) => c.school_class === cls.name)

    const hasSubject = classRows.some(
      (row: any) => normalizeSubject(String(row.subject || '')).toLowerCase() === subjectKey
    )

    let nextCurriculum = allCurriculum

    if (enabled && !hasSubject) {
      nextCurriculum = [
        ...allCurriculum,
        {
          school_class: cls.name,
          subject: subjectNorm,
          weekly_hours: 2,
          sessions_per_week: 2,
          minutes_per_session: 60,
          total_minutes_per_week: 120,
        },
      ]
    }

    if (!enabled) {
      nextCurriculum = allCurriculum.filter((row: any) => {
        if (row.school_class !== cls.name) return true
        return normalizeSubject(String(row.subject || '')).toLowerCase() !== subjectKey
      })
    }

    const nextSubjects = deriveSubjects({ ...data, curriculum: nextCurriculum })

    const nextAssignments = assignments.filter((a: any) => {
      if (a.school_class !== cls.name) return true
      if (!enabled && normalizeSubject(String(a.subject || '')).toLowerCase() === subjectKey) {
        return false
      }
      return true
    })

    onUpdateData({ ...data, curriculum: nextCurriculum, subjects: nextSubjects })
    onUpdateAssignments(nextAssignments)
  }

  function updateCurriculumRow(globalIdx: number, field: string, val: string | number) {
    const allCurriculum = data.curriculum ?? []
    const updated = allCurriculum.map((c: any, i: number) => {
      if (i !== globalIdx) return c
      const next = { ...c, [field]: val }
      if (field === 'weekly_hours') {
        const wh = Math.max(1, Number(val) || 1)
        next.weekly_hours = wh
        next.total_minutes_per_week = wh * 60
        next.sessions_per_week = Math.max(1, Math.round(wh))
        next.minutes_per_session = 60
      }
      if (field === 'subject') {
        // upsert subject
      }
      return next
    })
    const nextSubjects = deriveSubjects({ ...data, curriculum: updated })
    onUpdateData({ ...data, curriculum: updated, subjects: nextSubjects })
    // update assignment if subject changed: delete old, upsert new to avoid duplicates
    if (field === 'subject') {
      const oldRow    = allCurriculum[globalIdx]
      const oldSubject = oldRow.subject as string
      const newSubject = val as string
      // drop any assignment for (class, old subject)
      let nextAssignments = assignments.filter(
        a => !(a.school_class === cls.name && a.subject === oldSubject)
      )
      // if there was a teacher on the old assignment, re-attach it to the new subject name (only when non-empty)
      if (newSubject) {
        const oldAssignment = assignments.find(a => a.school_class === cls.name && a.subject === oldSubject)
        if (oldAssignment) {
          // remove any existing assignment for (class, new subject) first, then add
          nextAssignments = nextAssignments.filter(
            a => !(a.school_class === cls.name && a.subject === newSubject)
          )
          nextAssignments = [...nextAssignments, { ...oldAssignment, subject: newSubject }]
        }
      }
      onUpdateAssignments(nextAssignments)
    }
  }

  function updateCurriculumTeacher(globalIdx: number, teacher: string) {
    const allCurriculum = data.curriculum ?? []
    const row = allCurriculum[globalIdx]
    if (!row || !row.subject) return  // guard: no subject yet
    const existing = assignments.findIndex(a => a.school_class === cls.name && a.subject === row.subject)
    let nextAssignments: any[]
    if (teacher === '') {
      nextAssignments = assignments.filter(a => !(a.school_class === cls.name && a.subject === row.subject))
    } else if (existing >= 0) {
      nextAssignments = assignments.map((a, i) => i === existing ? { ...a, teacher } : a)
    } else {
      nextAssignments = [...assignments, { school_class: cls.name, subject: row.subject, teacher }]
    }
    onUpdateAssignments(nextAssignments)
  }

  function deleteCurriculumRow(globalIdx: number) {
    const allCurriculum = data.curriculum ?? []
    const row = allCurriculum[globalIdx]
    const nextCurriculum = allCurriculum.filter((_: any, i: number) => i !== globalIdx)
    const nextSubjects   = deriveSubjects({ ...data, curriculum: nextCurriculum })
    const nextAssignments = assignments.filter(a => !(a.school_class === cls.name && a.subject === row?.subject))
    onUpdateData({ ...data, curriculum: nextCurriculum, subjects: nextSubjects })
    onUpdateAssignments(nextAssignments)
  }

  function copyCurriculumFrom(sourceClass: string) {
    const allCurriculum = data.curriculum ?? []
    const sourceCurriculum = allCurriculum.filter((c: any) => c.school_class === sourceClass)
    const copied = sourceCurriculum.map((c: any) => ({ ...c, school_class: cls.name }))
    const filtered = allCurriculum.filter((c: any) => c.school_class !== cls.name)
    const nextCurriculum = [...filtered, ...copied]
    const nextSubjects = deriveSubjects({ ...data, curriculum: nextCurriculum })
    // Purge assignments for target class that no longer have a matching curriculum entry
    const newSubjectSet = new Set(copied.map((c: any) => c.subject).filter(Boolean))
    const nextAssignments = assignments.filter(
      a => a.school_class !== cls.name || newSubjectSet.has(a.subject)
    )
    onUpdateData({ ...data, curriculum: nextCurriculum, subjects: nextSubjects })
    onUpdateAssignments(nextAssignments)
    setCopyOpen(false)
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
      {/* Card header */}
      <div className="flex items-center gap-2 px-4 py-3 bg-gray-50 dark:bg-gray-800">
        <input
          value={cls.name ?? ''}
          onChange={e => renameClass(e.target.value)}
          placeholder="Nom de la classe"
          className="flex-1 min-w-0 px-2 py-1 text-sm font-semibold border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
        />
        <select
          value={cls.level ?? ''}
          onChange={e => updateLevel(e.target.value)}
          className="px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-teal-500"
        >
          <option value="">Niveau…</option>
          {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
        </select>
        <button onClick={deleteClass} className="text-gray-400 hover:text-red-500 transition-colors flex-shrink-0">
          <Trash2 size={14} />
        </button>
      </div>

      {/* Curriculum table */}
      <div className="p-3 bg-white dark:bg-gray-900 space-y-2">
        <div className="space-y-1.5 pb-1">
          <div className="text-xs font-medium text-gray-500 uppercase">Matières de la classe</div>
          {availableSubjects.length === 0 ? (
            <p className="text-xs text-gray-400 italic">Ajoutez d'abord des matières dans la section Enseignants.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {availableSubjects.map((subject) => {
                const checked = selectedSubjects.has(subject.toLowerCase())
                return (
                  <label key={subject} className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md border border-gray-200 dark:border-gray-700 text-xs text-gray-700 dark:text-gray-300">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={e => toggleClassSubject(subject, e.target.checked)}
                      className="h-3.5 w-3.5 rounded border-gray-300 text-teal-600 focus:ring-teal-500"
                    />
                    {subject}
                  </label>
                )
              })}
            </div>
          )}
        </div>

        {curriculum.length === 0 && (
          <p className="text-xs text-gray-400 italic">Aucune matière dans le programme.</p>
        )}

        {(data.curriculum ?? []).map((row: any, globalIdx: number) => {
          if (row.school_class !== cls.name) return null
          const eligibleTeachers = getEligibleTeachersForSubject(String(row.subject || ''))
          const assignedTeacher = assignments.find(a => a.school_class === cls.name && a.subject === row.subject)?.teacher ?? ''
          return (
            <div key={globalIdx} className="flex gap-2 items-center">
              <div className="flex-1 min-w-0 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-200">
                {row.subject || 'Matiere'}
              </div>
              <input
                type="number"
                min={1}
                max={40}
                value={row.weekly_hours ?? Math.round((row.total_minutes_per_week ?? 120) / 60)}
                onChange={e => updateCurriculumRow(globalIdx, 'weekly_hours', Number(e.target.value))}
                className="w-14 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500 text-center"
                title="Heures par semaine"
              />
              <span className="text-xs text-gray-400 flex-shrink-0">h/sem</span>
              <select
                value={assignedTeacher}
                onChange={e => updateCurriculumTeacher(globalIdx, e.target.value)}
                className="flex-1 min-w-0 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-teal-500"
              >
                <option value="">Enseignant…</option>
                {eligibleTeachers.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <button onClick={() => deleteCurriculumRow(globalIdx)} className="text-gray-400 hover:text-red-500 transition-colors flex-shrink-0">
                <Trash2 size={12} />
              </button>
            </div>
          )
        })}

        {availableSubjects.length === 0 && (
          <button onClick={addCurriculumRow} className="flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 hover:text-teal-700 transition-colors">
            <Plus size={13} /> Ajouter une matière
          </button>
        )}

        {/* Copy from class */}
        {otherClasses.length > 0 && (
          <div className="mt-1">
            <button
              onClick={() => setCopyOpen(o => !o)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-teal-600 transition-colors"
            >
              {copyOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              Copier d'une autre classe
            </button>
            {copyOpen && (
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {otherClasses.map(oc => (
                  <button
                    key={oc}
                    onClick={() => copyCurriculumFrom(oc)}
                    className="px-2 py-1 text-xs bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 rounded hover:bg-teal-200 dark:hover:bg-teal-900/50 transition-colors"
                  >
                    {oc}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Constraints section ───────────────────────────────────────────────────────

function ConstraintsSection({
  data,
  onUpdateData,
}: {
  data: SchoolData
  onUpdateData: (d: SchoolData) => void
}) {
  const items = data.constraints ?? []
  const [open, setOpen] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState<any>(null)
  const [editIdx, setEditIdx] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<any>(null)

  const teachers = (data.teachers ?? []).map((t: any) => String(t.name || '')).filter(Boolean)
  const classes = (data.classes ?? []).map((c: any) => String(c.name || '')).filter(Boolean)
  const fromSubjects = (data.subjects ?? []).map((s: any) => String(s.name || '')).filter(Boolean)
  const fromCurriculum = (data.curriculum ?? []).map((c: any) => String(c.subject || '')).filter(Boolean)
  const fromTeachers = getTeacherDeclaredSubjects(data)
  const subjects = Array.from(new Set([...fromSubjects, ...fromCurriculum, ...fromTeachers])).sort()
  const days = (data.days ?? []).map((d: any) => String(d.name || '')).filter(Boolean)
  const allSessions = (data.days ?? []).flatMap((d: any) => (d.sessions ?? []).map((s: any) => String(s.name || '')))
  const sessionChoices = ['all', ...Array.from(new Set(allSessions.filter(Boolean)))]

  function aliasCategory(value: string): string {
    return CATEGORY_ALIASES[value] ?? value
  }

  function getDef(category: string): ConstraintDef {
    const normalized = aliasCategory(category)
    return CONSTRAINT_DEFS.find(c => c.value === normalized) ?? CONSTRAINT_DEFS[0]
  }

  function defaultParams(def: ConstraintDef): Record<string, unknown> {
    const params: Record<string, unknown> = {}
    for (const f of def.fields) {
      if (f.type === 'subjects' || f.type === 'days') {
        params[f.key] = []
      } else if (f.type === 'session') {
        params[f.key] = 'all'
      } else if (f.type === 'choice') {
        params[f.key] = f.choices?.[0] ?? ''
      } else if (f.type === 'number') {
        params[f.key] = f.min ?? 1
      } else {
        params[f.key] = ''
      }
    }
    return params
  }

  function normalizeEntry(raw: any): any {
    const def = getDef(String(raw?.category || 'start_time'))
    return {
      id: raw?.id ?? '',
      type: def.type,
      category: def.value,
      description_fr: raw?.description_fr || def.label,
      priority: Number(raw?.priority ?? 5),
      parameters: { ...defaultParams(def), ...(raw?.parameters ?? {}) },
    }
  }

  function makeEmpty(category: string = CONSTRAINT_DEFS[0].value): any {
    const def = getDef(category)
    return {
      id: '',
      type: def.type,
      category: def.value,
      description_fr: def.label,
      priority: 5,
      parameters: defaultParams(def),
    }
  }

  function categoryHelp(def: ConstraintDef): string {
    return `A quoi ca sert: ${def.description}\nQuand l'utiliser: ${def.whenToUse}\nExemple: ${def.example}`
  }

  function fieldChoices(field: FieldDef): string[] {
    if (field.type === 'teacher') return teachers
    if (field.type === 'class') return classes
    if (field.type === 'subject') return subjects
    if (field.type === 'day') return (days.length ? days : DAY_NAMES)
    if (field.type === 'session') return sessionChoices
    return field.choices ?? []
  }

  function validateForm(entry: any): string[] {
    const def = getDef(entry.category)
    const errors: string[] = []
    for (const field of def.fields) {
      const value = entry.parameters?.[field.key]
      if (!field.required) continue
      if (Array.isArray(value) && value.length === 0) {
        errors.push(`${field.label} requis`)
      } else if (!Array.isArray(value) && (value === '' || value === null || value === undefined)) {
        errors.push(`${field.label} requis`)
      }
      if (field.type === 'number' && value !== '' && value !== null && value !== undefined) {
        const n = Number(value)
        if (Number.isNaN(n)) errors.push(`${field.label} invalide`)
        if (field.min !== undefined && n < field.min) errors.push(`${field.label} >= ${field.min}`)
        if (field.max !== undefined && n > field.max) errors.push(`${field.label} <= ${field.max}`)
      }
    }
    return errors
  }

  function updateCategory(target: any, setTarget: (v: any) => void, value: string) {
    const def = getDef(value)
    setTarget({
      ...target,
      type: def.type,
      category: def.value,
      description_fr: target.description_fr || def.label,
      parameters: defaultParams(def),
    })
  }

  function updateParam(target: any, setTarget: (v: any) => void, key: string, value: unknown) {
    setTarget({
      ...target,
      parameters: { ...(target.parameters ?? {}), [key]: value },
    })
  }

  function InfoTip({ content }: { content: string }) {
    return (
      <span className="relative inline-flex group align-middle">
        <button
          type="button"
          aria-label="Aide"
          className="inline-flex items-center justify-center h-4 w-4 rounded-full text-teal-600 hover:text-teal-700"
        >
          <Info size={12} />
        </button>
        <span className="pointer-events-none absolute left-1/2 top-full z-20 mt-1 hidden w-64 -translate-x-1/2 rounded-lg border border-gray-200 bg-white p-2 text-[11px] leading-snug text-gray-700 shadow-lg group-hover:block group-focus-within:block dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200">
          {content}
        </span>
      </span>
    )
  }

  function openAdd() {
    setAddForm(makeEmpty())
    setShowAdd(true)
    setEditIdx(null)
  }

  function openEdit(idx: number) {
    const item = normalizeEntry(items[idx])
    setEditIdx(idx)
    setEditForm(item)
    setShowAdd(false)
  }

  function cancel() {
    setShowAdd(false)
    setEditIdx(null)
  }

  function save(form: any, idx: number | null) {
    const def = getDef(form.category)
    const entry = {
      ...form,
      category: def.value,
      type: def.type,
      id: form.id || (idx !== null ? (items[idx]?.id || `C${idx + 1}`) : `C${items.length + 1}`),
    }
    if (idx === null) {
      onUpdateData({ ...data, constraints: [...items, entry] })
    } else {
      onUpdateData({ ...data, constraints: items.map((x: any, i: number) => i === idx ? entry : x) })
    }
    setShowAdd(false)
    setEditIdx(null)
  }

  function renderForm(
    f: any,
    setF: (v: any) => void,
    saveIdx: number | null,
  ) {
    const def = getDef(f.category)
    const errors = validateForm(f)
    const hasErrors = errors.length > 0

    function renderField(field: FieldDef) {
      const value = f.parameters?.[field.key]
      const choices = fieldChoices(field)

      if (field.type === 'subjects' || field.type === 'days') {
        const selected: string[] = Array.isArray(value) ? value as string[] : []
        return (
          <div className="flex flex-wrap gap-1.5">
            {choices.map(choice => {
              const checked = selected.includes(choice)
              return (
                <label key={choice} className="inline-flex items-center gap-1.5 px-2 py-1 rounded border border-gray-200 dark:border-gray-700 text-xs">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={e => {
                      const next = e.target.checked
                        ? [...selected, choice]
                        : selected.filter(x => x !== choice)
                      updateParam(f, setF, field.key, next)
                    }}
                    className="h-3.5 w-3.5 rounded border-gray-300 text-teal-600 focus:ring-teal-500"
                  />
                  {choice}
                </label>
              )
            })}
          </div>
        )
      }

      if (field.type === 'teacher' || field.type === 'class' || field.type === 'subject' || field.type === 'day' || field.type === 'session' || field.type === 'choice') {
        return (
          <select
            value={String(value ?? '')}
            onChange={e => updateParam(f, setF, field.key, e.target.value)}
            className="w-full px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
          >
            <option value="">{field.required ? 'Choisir…' : 'Optionnel'}</option>
            {choices.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        )
      }

      if (field.type === 'time') {
        return (
          <input
            type="time"
            value={String(value ?? '')}
            onChange={e => updateParam(f, setF, field.key, e.target.value)}
            className="w-full px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        )
      }

      if (field.type === 'number') {
        return (
          <input
            type="number"
            min={field.min}
            max={field.max}
            value={Number(value ?? field.min ?? 1)}
            onChange={e => updateParam(f, setF, field.key, Number(e.target.value))}
            className="w-full px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        )
      }

      return (
        <input
          type="text"
          value={String(value ?? '')}
          placeholder={field.placeholder}
          onChange={e => updateParam(f, setF, field.key, e.target.value)}
          className="w-full px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
        />
      )
    }

    return (
      <div className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <label className="text-xs text-gray-500 inline-flex items-center gap-1">
              Catégorie <InfoTip content={categoryHelp(def)} />
            </label>
            <select value={f.category} onChange={e => updateCategory(f, setF, e.target.value)}
              className="w-full px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500">
              {CONSTRAINT_DEFS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Type</label>
            <div className={`px-3 py-2 text-xs rounded-lg border ${f.type === 'hard' ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-400' : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400'}`}>
              {f.type === 'hard' ? '🔴 Dure (obligatoire)' : '🟡 Souple (préférence)'}
            </div>
          </div>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-gray-500">Description</label>
          <input
            value={f.description_fr ?? ''}
            onChange={e => setF({ ...f, description_fr: e.target.value })}
            placeholder="Description de la contrainte"
            className="w-full px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        </div>
        {f.type === 'soft' && (
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Priorité (1-10)</label>
            <input type="range" min={1} max={10} value={f.priority} onChange={e => setF({ ...f, priority: Number(e.target.value) })} className="w-full accent-teal-600" />
            <div className="text-xs text-gray-500 text-center">Priorité : {f.priority}</div>
          </div>
        )}
        {def.fields.map(field => (
          <div key={field.key} className="space-y-1">
            <label className="text-xs text-gray-500 inline-flex items-center gap-1">
              {field.label}{field.required ? ' *' : ''} <InfoTip content={field.help} />
            </label>
            {renderField(field)}
          </div>
        ))}
        <p className="text-[11px] text-gray-500 dark:text-gray-400">{def.whenToUse} Exemple: {def.example}</p>
        {hasErrors && (
          <div className="text-xs text-red-600 dark:text-red-400">
            {errors.join(' · ')}
          </div>
        )}
        <div className="flex gap-2">
          <button
            onClick={() => !hasErrors && save(f, saveIdx)}
            disabled={hasErrors}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${hasErrors ? 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed' : 'bg-teal-600 text-white hover:bg-teal-700'}`}
          >
            Enregistrer
          </button>
          <button onClick={cancel} className="px-3 py-1.5 text-xs text-gray-500 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">Annuler</button>
        </div>
      </div>
    )
  }

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      >
        <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          Contraintes
          {items.length > 0 && <span className="ml-2 text-xs font-normal text-gray-400">({items.length})</span>}
        </span>
        <ChevronRight size={14} className={`text-gray-400 transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>

      {open && (
        <div className="p-3 space-y-2 bg-white dark:bg-gray-900">
          {items.length === 0 && !showAdd && (
            <p className="text-xs text-gray-400 italic">Aucune contrainte — optionnel.</p>
          )}
          {items.map((item: any, idx: number) => (
            <div key={idx}>
              <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-gray-800/60 rounded-lg text-xs">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${item.type === 'hard' ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400' : 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400'}`}>
                  {item.type === 'hard' ? 'Dure' : 'Souple'}
                </span>
                <span className="text-gray-600 dark:text-gray-400 inline-flex items-center gap-1">
                  {getDef(item.category).label}
                  <InfoTip content={categoryHelp(getDef(item.category))} />
                </span>
                <span className="ml-auto text-gray-500 truncate">{item.description_fr || '—'}</span>
                <button onClick={() => openEdit(idx)} className="text-gray-400 hover:text-teal-600 transition-colors"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
                <button onClick={() => onUpdateData({ ...data, constraints: items.filter((_: any, i: number) => i !== idx) })} className="text-gray-400 hover:text-red-500 transition-colors"><Trash2 size={12} /></button>
              </div>
              {editIdx === idx && editForm && (
                <div className="mt-1 mb-2 p-3 border border-teal-200 dark:border-teal-800 rounded-lg bg-teal-50 dark:bg-teal-900/10">
                  {renderForm(editForm, setEditForm, idx)}
                </div>
              )}
            </div>
          ))}
          {showAdd && (
            <div className="p-3 border border-teal-200 dark:border-teal-800 rounded-lg bg-teal-50 dark:bg-teal-900/10">
              {addForm && renderForm(addForm, setAddForm, null)}
            </div>
          )}
          {!showAdd && editIdx === null && (
            <button onClick={openAdd} className="flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 hover:text-teal-700 transition-colors">
              <Plus size={13} /> Ajouter une contrainte
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function deriveSubjects(data: SchoolData): any[] {
  const curriculum = data.curriculum ?? []
  const existing   = data.subjects   ?? []
  const existingNames = new Set(existing.map((s: any) => s.name))
  const subjectNames  = new Set(curriculum.map((c: any) => c.subject).filter(Boolean))
  const added = Array.from(subjectNames)
    .filter(n => !existingNames.has(n))
    .map(n => ({ name: n, short_name: (n as string).slice(0, 4).toUpperCase(), color: '#0d9488', needs_room: true }))
  const kept = existing.filter((s: any) => subjectNames.has(s.name))
  return [...kept, ...added]
}


// ── Main component ────────────────────────────────────────────────────────────

export default function ClassCardsStep({ data, assignments, onUpdateData, onUpdateAssignments }: Props) {
  function addClass() {
    const classes = data.classes ?? []
    onUpdateData({ ...data, classes: [...classes, { name: '', level: '', student_count: 0 }] })
  }

  return (
    <div className="space-y-4">
      <div className="border border-indigo-200 dark:border-indigo-800 rounded-xl p-3 bg-indigo-50 dark:bg-indigo-900/20">
        <p className="text-xs font-semibold text-indigo-800 dark:text-indigo-200">Remplissage rapide (tests progressifs)</p>
        <p className="text-[11px] text-indigo-700 dark:text-indigo-300 mt-1">
          Ces jeux remplissent toute la chaîne: École, jours/sessions, salles, classes, enseignants, programme, affectations et contraintes.
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {FORM_SCENARIOS.map((preset) => (
            <button
              key={preset.id}
              onClick={() => {
                const prefilled = applyScenarioPreset(data, preset)
                onUpdateData(prefilled.data)
                onUpdateAssignments(prefilled.assignments)
              }}
              className="px-2.5 py-1.5 rounded border border-indigo-300 dark:border-indigo-700 text-xs text-indigo-700 dark:text-indigo-300 bg-white dark:bg-gray-900 hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition-colors"
              title={`${preset.category.toUpperCase()} · ${preset.description}\nAttendu: ${preset.expectedOutcome}`}
            >
              {preset.level} · {preset.label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-[11px] text-indigo-700 dark:text-indigo-300">
          Types: ✅ feature · ⚠️ fail attendu · 🏫 réaliste (voir infobulle du bouton).
        </p>
      </div>

      {/* Enseignants */}
      <TeachersSection data={data} assignments={assignments} onUpdateData={onUpdateData} onUpdateAssignments={onUpdateAssignments} />

      {/* Class cards */}
      {(data.classes ?? []).map((cls: any, idx: number) => (
        <ClassCard
          key={idx}
          cls={cls}
          clsIdx={idx}
          data={data}
          assignments={assignments}
          onUpdateData={onUpdateData}
          onUpdateAssignments={onUpdateAssignments}
        />
      ))}

      <button
        onClick={addClass}
        className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-teal-600 dark:text-teal-400 border-2 border-dashed border-teal-300 dark:border-teal-700 rounded-xl hover:border-teal-500 dark:hover:border-teal-500 hover:bg-teal-50 dark:hover:bg-teal-900/20 transition-colors w-full justify-center"
      >
        <Plus size={15} /> Ajouter une classe
      </button>

      {/* Constraints */}
      <ConstraintsSection data={data} onUpdateData={onUpdateData} />
    </div>
  )
}
