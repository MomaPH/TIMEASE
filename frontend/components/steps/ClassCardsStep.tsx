'use client'
import { useState } from 'react'
import { Plus, Trash2, ChevronRight, ChevronDown } from 'lucide-react'
import type { SchoolData } from '@/lib/types'

const LEVELS = ['Maternelle', 'Primaire', 'Collège', 'Lycée', 'Autre']

const CONSTRAINT_CATEGORIES = [
  { value: 'start_time',              label: 'Heure de début minimum',           type: 'hard' },
  { value: 'day_off',                 label: 'Jour bloqué',                      type: 'hard' },
  { value: 'max_consecutive',         label: 'Max heures consécutives',          type: 'hard' },
  { value: 'teacher_day_off',         label: 'Congé enseignant',                 type: 'hard' },
  { value: 'subject_on_days',         label: 'Matière sur jours précis',         type: 'hard' },
  { value: 'teacher_time_preference', label: 'Préférence horaire enseignant',    type: 'soft' },
  { value: 'heavy_subjects_morning',  label: 'Matières difficiles le matin',     type: 'soft' },
  { value: 'balanced_daily_load',     label: 'Charge équilibrée par jour',       type: 'soft' },
  { value: 'subject_spread',          label: 'Même matière pas 2x/jour',        type: 'soft' },
  { value: 'light_last_day',          label: 'Peu de cours le dernier jour',     type: 'soft' },
]

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
  const [addForm, setAddForm] = useState<any>({ id: '', type: 'hard', category: 'start_time', description_fr: '', priority: 5 })
  const [addParamsRaw, setAddParamsRaw] = useState('{}')
  const [addParamsParsed, setAddParamsParsed] = useState<Record<string, unknown>>({})
  const [addParamsError, setAddParamsError] = useState(false)
  const [editIdx, setEditIdx] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<any>(null)
  const [editParamsRaw, setEditParamsRaw] = useState('{}')
  const [editParamsParsed, setEditParamsParsed] = useState<Record<string, unknown>>({})
  const [editParamsError, setEditParamsError] = useState(false)

  function openAdd() {
    setAddForm({ id: '', type: 'hard', category: 'start_time', description_fr: '', priority: 5 })
    setAddParamsRaw('{}')
    setAddParamsParsed({})
    setAddParamsError(false)
    setShowAdd(true)
    setEditIdx(null)
  }

  function openEdit(idx: number) {
    const item = items[idx]
    setEditIdx(idx)
    setEditForm({ ...item })
    const raw = JSON.stringify(item.parameters ?? {})
    setEditParamsRaw(raw)
    setEditParamsParsed(item.parameters ?? {})
    setEditParamsError(false)
    setShowAdd(false)
  }

  function cancel() {
    setShowAdd(false)
    setEditIdx(null)
  }

  function save(form: any, parameters: Record<string, unknown>, idx: number | null) {
    const entry = { ...form, parameters, id: form.id || `C${items.length + 1}` }
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
    paramsRaw: string,
    setParamsRaw: (s: string) => void,
    paramsParsed: Record<string, unknown>,
    setParamsParsed: (p: Record<string, unknown>) => void,
    paramsError: boolean,
    setParamsError: (b: boolean) => void,
    saveIdx: number | null,
  ) {
    return (
      <div className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Catégorie</label>
            <select value={f.category} onChange={e => {
              const c = CONSTRAINT_CATEGORIES.find(x => x.value === e.target.value)
              setF({ ...f, category: e.target.value, type: c?.type ?? 'hard' })
            }}
              className="w-full px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500">
              {CONSTRAINT_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
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
        <div className="space-y-1">
          <label className="text-xs text-gray-500">
            Paramètres (JSON)
            {paramsError && <span className="ml-1 text-red-500">— JSON invalide</span>}
          </label>
          <textarea
            value={paramsRaw}
            onChange={e => {
              setParamsRaw(e.target.value)
              try {
                const parsed = JSON.parse(e.target.value)
                setParamsParsed(parsed)
                setParamsError(false)
              } catch {
                setParamsError(true)
              }
            }}
            rows={2}
            className={`w-full px-2 py-1.5 text-xs font-mono border rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500 ${paramsError ? 'border-red-400 dark:border-red-600' : 'border-gray-200 dark:border-gray-700'}`}
            placeholder='{"hour": "08:00"}'
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => !paramsError && save(f, paramsParsed, saveIdx)}
            disabled={paramsError}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${paramsError ? 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed' : 'bg-teal-600 text-white hover:bg-teal-700'}`}
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
                <span className="text-gray-600 dark:text-gray-400">{CONSTRAINT_CATEGORIES.find(c => c.value === item.category)?.label ?? item.category}</span>
                <span className="ml-auto text-gray-500 truncate">{item.description_fr || '—'}</span>
                <button onClick={() => openEdit(idx)} className="text-gray-400 hover:text-teal-600 transition-colors"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
                <button onClick={() => onUpdateData({ ...data, constraints: items.filter((_: any, i: number) => i !== idx) })} className="text-gray-400 hover:text-red-500 transition-colors"><Trash2 size={12} /></button>
              </div>
              {editIdx === idx && editForm && (
                <div className="mt-1 mb-2 p-3 border border-teal-200 dark:border-teal-800 rounded-lg bg-teal-50 dark:bg-teal-900/10">
                  {renderForm(editForm, setEditForm, editParamsRaw, setEditParamsRaw, editParamsParsed, setEditParamsParsed, editParamsError, setEditParamsError, idx)}
                </div>
              )}
            </div>
          ))}
          {showAdd && (
            <div className="p-3 border border-teal-200 dark:border-teal-800 rounded-lg bg-teal-50 dark:bg-teal-900/10">
              {renderForm(addForm, setAddForm, addParamsRaw, setAddParamsRaw, addParamsParsed, setAddParamsParsed, addParamsError, setAddParamsError, null)}
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
