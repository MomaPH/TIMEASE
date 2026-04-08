'use client'
import { useState, useMemo } from 'react'
import { Plus, Pencil, Trash2, Check, X, ChevronRight, Loader2, ArrowRight, AlertTriangle } from 'lucide-react'
import type { SchoolData } from '@/lib/types'
import { getChecklistItems, getChecklistStatus, getMissingAssignments, getDataWarnings } from '@/lib/types'
import { validateHourBarriers, type ValidationError } from '@/lib/validation'
import ValidationErrorPanel from './ValidationErrorPanel'

// ── Shared helpers ────────────────────────────────────────────────────────────

const DAYS_FR = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
const DAYS_VAL = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi']

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</label>
      {children}
    </div>
  )
}

function Input({ value, onChange, placeholder, type = 'text' }: {
  value: string; onChange: (v: string) => void; placeholder?: string; type?: string
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500 placeholder-gray-400"
    />
  )
}

function SaveRow({ onSave, onCancel }: { onSave: () => void; onCancel: () => void }) {
  return (
    <div className="flex gap-2 mt-2">
      <button onClick={onSave} className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors">
        <Check size={12} /> Enregistrer
      </button>
      <button onClick={onCancel} className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-500 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
        <X size={12} /> Annuler
      </button>
    </div>
  )
}

function RowActions({ onEdit, onDelete }: { onEdit: () => void; onDelete: () => void }) {
  return (
    <div className="flex gap-1 ml-auto flex-shrink-0">
      <button onClick={onEdit} className="p-1 text-gray-400 hover:text-teal-600 dark:hover:text-teal-400 transition-colors rounded">
        <Pencil size={13} />
      </button>
      <button onClick={onDelete} className="p-1 text-gray-400 hover:text-red-500 transition-colors rounded">
        <Trash2 size={13} />
      </button>
    </div>
  )
}

function SectionEmpty({ text }: { text: string }) {
  return <p className="text-xs text-gray-400 dark:text-gray-500 italic py-2">{text}</p>
}

// ── Step 1: École ─────────────────────────────────────────────────────────────

import type { DayConfig, SessionConfig, BreakConfig } from '@/lib/types'

const DEFAULT_SESSIONS: SessionConfig[] = [
  { name: 'Matin', start_time: '08:00', end_time: '12:00' },
  { name: 'Après-midi', start_time: '15:00', end_time: '17:00' },
]

function SchoolStep({ data, onUpdate }: { data: SchoolData; onUpdate: (d: SchoolData) => void }) {
  const days = data.days || []
  const dayNames = days.map(d => d.name)
  const [expandedDay, setExpandedDay] = useState<string | null>(null)

  function toggleDay(dayVal: string) {
    if (dayNames.includes(dayVal)) {
      // Remove day
      onUpdate({ ...data, days: days.filter(d => d.name !== dayVal) })
    } else {
      // Add day with default sessions
      const newDay: DayConfig = { name: dayVal, sessions: [...DEFAULT_SESSIONS], breaks: [] }
      onUpdate({ ...data, days: [...days, newDay].sort((a, b) => DAYS_VAL.indexOf(a.name) - DAYS_VAL.indexOf(b.name)) })
    }
  }

  function updateDayConfig(dayName: string, updates: Partial<DayConfig>) {
    const nextDays = days.map(d => d.name === dayName ? { ...d, ...updates } : d)
    onUpdate({ ...data, days: nextDays })
  }

  function addSession(dayName: string) {
    const day = days.find(d => d.name === dayName)
    if (!day) return
    const newSession: SessionConfig = { name: '', start_time: '08:00', end_time: '10:00' }
    updateDayConfig(dayName, { sessions: [...day.sessions, newSession] })
  }

  function updateSession(dayName: string, idx: number, field: keyof SessionConfig, val: string) {
    const day = days.find(d => d.name === dayName)
    if (!day) return
    const nextSessions = day.sessions.map((s, i) => i === idx ? { ...s, [field]: val } : s)
    updateDayConfig(dayName, { sessions: nextSessions })
  }

  function removeSession(dayName: string, idx: number) {
    const day = days.find(d => d.name === dayName)
    if (!day) return
    updateDayConfig(dayName, { sessions: day.sessions.filter((_, i) => i !== idx) })
  }

  function addBreak(dayName: string) {
    const day = days.find(d => d.name === dayName)
    if (!day) return
    const newBreak: BreakConfig = { name: 'Récréation', start_time: '10:00', end_time: '10:15' }
    updateDayConfig(dayName, { breaks: [...day.breaks, newBreak] })
  }

  function updateBreak(dayName: string, idx: number, field: keyof BreakConfig, val: string) {
    const day = days.find(d => d.name === dayName)
    if (!day) return
    const nextBreaks = day.breaks.map((b, i) => i === idx ? { ...b, [field]: val } : b)
    updateDayConfig(dayName, { breaks: nextBreaks })
  }

  function removeBreak(dayName: string, idx: number) {
    const day = days.find(d => d.name === dayName)
    if (!day) return
    updateDayConfig(dayName, { breaks: day.breaks.filter((_, i) => i !== idx) })
  }

  function copyToAllDays(sourceDay: string) {
    const source = days.find(d => d.name === sourceDay)
    if (!source) return
    const nextDays = days.map(d => ({
      ...d,
      sessions: [...source.sessions],
      breaks: [...source.breaks],
    }))
    onUpdate({ ...data, days: nextDays })
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <Field label="Nom de l'école">
          <Input value={data.name || ''} onChange={v => onUpdate({ ...data, name: v })} placeholder="Ex : Collège Saint-Paul" />
        </Field>
        <Field label="Ville">
          <Input value={data.city || ''} onChange={v => onUpdate({ ...data, city: v })} placeholder="Ex : Abidjan" />
        </Field>
      </div>

      <Field label="Année scolaire">
        <Input value={data.academic_year || ''} onChange={v => onUpdate({ ...data, academic_year: v })} placeholder="2025-2026" />
      </Field>

      <Field label="Unité de base">
        <select
          value={data.base_unit_minutes || 30}
          onChange={e => onUpdate({ ...data, base_unit_minutes: Number(e.target.value) })}
          className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          <option value={15}>15 minutes</option>
          <option value={30}>30 minutes</option>
          <option value={60}>1 heure</option>
        </select>
      </Field>

      <Field label="Jours de cours">
        <div className="flex flex-wrap gap-2">
          {DAYS_FR.map((d, i) => {
            const val = DAYS_VAL[i]
            const selected = dayNames.includes(val)
            return (
              <button
                key={val}
                onClick={() => toggleDay(val)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                  selected
                    ? 'bg-teal-600 text-white border-teal-600'
                    : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-teal-400'
                }`}
              >
                {d}
              </button>
            )
          })}
        </div>
      </Field>

      {days.length > 0 && (
        <Field label="Horaires par jour">
          <div className="space-y-2">
            {days.map(day => {
              const dayLabel = DAYS_FR[DAYS_VAL.indexOf(day.name)] || day.name
              const isExpanded = expandedDay === day.name
              return (
                <div key={day.name} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setExpandedDay(isExpanded ? null : day.name)}
                    className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  >
                    <span>{dayLabel}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">
                        {day.sessions.length} session{day.sessions.length !== 1 ? 's' : ''}
                        {day.breaks.length > 0 && `, ${day.breaks.length} pause${day.breaks.length !== 1 ? 's' : ''}`}
                      </span>
                      <ChevronRight size={14} className={`transform transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                    </div>
                  </button>
                  {isExpanded && (
                    <div className="p-3 space-y-3 bg-white dark:bg-gray-900">
                      {/* Sessions */}
                      <div className="space-y-2">
                        <div className="text-xs font-medium text-gray-500 uppercase">Sessions</div>
                        {day.sessions.map((s, i) => (
                          <div key={i} className="flex gap-2 items-center">
                            <input
                              value={s.name}
                              onChange={e => updateSession(day.name, i, 'name', e.target.value)}
                              placeholder="Nom"
                              className="flex-1 min-w-0 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
                            />
                            <input
                              type="time"
                              value={s.start_time}
                              onChange={e => updateSession(day.name, i, 'start_time', e.target.value)}
                              className="w-20 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
                            />
                            <span className="text-xs text-gray-400">→</span>
                            <input
                              type="time"
                              value={s.end_time}
                              onChange={e => updateSession(day.name, i, 'end_time', e.target.value)}
                              className="w-20 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
                            />
                            <button onClick={() => removeSession(day.name, i)} className="text-gray-400 hover:text-red-500 transition-colors">
                              <X size={13} />
                            </button>
                          </div>
                        ))}
                        <button onClick={() => addSession(day.name)} className="flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 hover:text-teal-700 transition-colors">
                          <Plus size={13} /> Ajouter une session
                        </button>
                      </div>

                      {/* Breaks */}
                      <div className="space-y-2">
                        <div className="text-xs font-medium text-gray-500 uppercase">Pauses / Récréations</div>
                        {day.breaks.length === 0 && (
                          <p className="text-xs text-gray-400 italic">Aucune pause définie</p>
                        )}
                        {day.breaks.map((b, i) => (
                          <div key={i} className="flex gap-2 items-center">
                            <input
                              value={b.name}
                              onChange={e => updateBreak(day.name, i, 'name', e.target.value)}
                              placeholder="Nom"
                              className="flex-1 min-w-0 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
                            />
                            <input
                              type="time"
                              value={b.start_time}
                              onChange={e => updateBreak(day.name, i, 'start_time', e.target.value)}
                              className="w-20 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
                            />
                            <span className="text-xs text-gray-400">→</span>
                            <input
                              type="time"
                              value={b.end_time}
                              onChange={e => updateBreak(day.name, i, 'end_time', e.target.value)}
                              className="w-20 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
                            />
                            <button onClick={() => removeBreak(day.name, i)} className="text-gray-400 hover:text-red-500 transition-colors">
                              <X size={13} />
                            </button>
                          </div>
                        ))}
                        <button onClick={() => addBreak(day.name)} className="flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 hover:text-teal-700 transition-colors">
                          <Plus size={13} /> Ajouter une pause
                        </button>
                      </div>

                      {/* Copy to all days */}
                      {days.length > 1 && (
                        <button
                          onClick={() => copyToAllDays(day.name)}
                          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-teal-600 transition-colors mt-2"
                        >
                          <ArrowRight size={13} /> Copier cet horaire vers tous les jours
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </Field>
      )}
    </div>
  )
}

// ── Generic list step ─────────────────────────────────────────────────────────

function ListStep<T extends Record<string, any>>({
  items,
  columns,
  defaultItem,
  renderRow,
  renderForm,
  onAdd,
  onEdit,
  onDelete,
  emptyText,
}: {
  items: T[]
  columns: string[]
  defaultItem: T
  renderRow: (item: T) => React.ReactNode[]
  renderForm: (form: T, onChange: (f: T) => void) => React.ReactNode
  onAdd: (item: T) => void
  onEdit: (idx: number, item: T) => void
  onDelete: (idx: number) => void
  emptyText: string
}) {
  const [editIdx, setEditIdx] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<T>(defaultItem)
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState<T>(defaultItem)

  function handleEdit(idx: number) {
    setEditIdx(idx)
    setEditForm({ ...items[idx] })
    setShowAdd(false)
  }

  function handleSaveEdit() {
    if (editIdx === null) return
    onEdit(editIdx, editForm)
    setEditIdx(null)
  }

  function handleSaveAdd() {
    onAdd(addForm)
    setAddForm(defaultItem)
    setShowAdd(false)
  }

  return (
    <div className="space-y-1">
      {items.length === 0 && !showAdd && <SectionEmpty text={emptyText} />}

      {items.map((item, idx) => (
        <div key={idx}>
          <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-gray-800/60 rounded-lg text-sm">
            {renderRow(item).map((cell, ci) => (
              <span key={ci} className="text-gray-700 dark:text-gray-300 truncate">{cell}</span>
            ))}
            <RowActions
              onEdit={() => handleEdit(idx)}
              onDelete={() => onDelete(idx)}
            />
          </div>

          {editIdx === idx && (
            <div className="mt-1 mb-2 p-3 border border-teal-200 dark:border-teal-800 rounded-lg bg-teal-50 dark:bg-teal-900/10 space-y-3">
              {renderForm(editForm, setEditForm)}
              <SaveRow onSave={handleSaveEdit} onCancel={() => setEditIdx(null)} />
            </div>
          )}
        </div>
      ))}

      {showAdd && (
        <div className="p-3 border border-teal-200 dark:border-teal-800 rounded-lg bg-teal-50 dark:bg-teal-900/10 space-y-3">
          {renderForm(addForm, setAddForm)}
          <SaveRow onSave={handleSaveAdd} onCancel={() => { setShowAdd(false); setAddForm(defaultItem) }} />
        </div>
      )}

      {!showAdd && (
        <button
          onClick={() => { setShowAdd(true); setEditIdx(null) }}
          className="flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 hover:text-teal-700 transition-colors mt-2"
        >
          <Plus size={13} /> Ajouter
        </button>
      )}
    </div>
  )
}

// ── Step 2: Classes ───────────────────────────────────────────────────────────

function ClassesStep({ data, onUpdate }: { data: SchoolData; onUpdate: (d: SchoolData) => void }) {
  const items = data.classes || []
  const def = { name: '', level: '', student_count: 0 }

  function form(f: any, setF: (v: any) => void) {
    return (
      <div className="grid grid-cols-3 gap-2">
        <div className="space-y-1">
          <label className="text-xs text-gray-500">Nom</label>
          <Input value={f.name} onChange={v => setF({ ...f, name: v })} placeholder="6ème A" />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-gray-500">Niveau</label>
          <Input value={f.level} onChange={v => setF({ ...f, level: v })} placeholder="6ème" />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-gray-500">Effectif</label>
          <Input type="number" value={String(f.student_count)} onChange={v => setF({ ...f, student_count: Number(v) })} placeholder="30" />
        </div>
      </div>
    )
  }

  return (
    <ListStep
      items={items}
      columns={['Nom', 'Niveau', 'Effectif']}
      defaultItem={def}
      renderRow={item => [
        <span className="font-medium">{item.name}</span>,
        <span className="text-gray-500 dark:text-gray-400 text-xs">{item.level}</span>,
        <span className="ml-auto text-xs text-gray-500">{item.student_count} élèves</span>,
      ]}
      renderForm={form}
      onAdd={item => onUpdate({ ...data, classes: [...items, item] })}
      onEdit={(i, item) => onUpdate({ ...data, classes: items.map((x, idx) => idx === i ? item : x) })}
      onDelete={i => onUpdate({ ...data, classes: items.filter((_, idx) => idx !== i) })}
      emptyText="Aucune classe — ajoutez-en une ou demandez à l'assistant."
    />
  )
}

// ── Step 3: Enseignants ───────────────────────────────────────────────────────

function TeachersStep({ data, onUpdate }: { data: SchoolData; onUpdate: (d: SchoolData) => void }) {
  const items = data.teachers || []
  const subjects = (data.subjects || []).map((s: any) => s.name).filter(Boolean)
  const def = { name: '', subjects: [], max_hours_per_week: undefined }

  function form(f: any, setF: (v: any) => void) {
    return (
      <div className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Nom</label>
            <Input value={f.name} onChange={v => setF({ ...f, name: v })} placeholder="Prénom Nom" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Max h/sem <span className="text-gray-400">(optionnel)</span></label>
            <Input
              type="number"
              value={f.max_hours_per_week != null ? String(f.max_hours_per_week) : ''}
              onChange={v => setF({ ...f, max_hours_per_week: v ? Number(v) : undefined })}
              placeholder="Illimité"
            />
          </div>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-gray-500">Matières enseignées</label>
          {subjects.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {subjects.map((s: string) => {
                const sel = (f.subjects || []).includes(s)
                return (
                  <button
                    key={s}
                    onClick={() => setF({ ...f, subjects: sel ? f.subjects.filter((x: string) => x !== s) : [...(f.subjects || []), s] })}
                    className={`px-2 py-1 text-xs rounded-md border transition-colors ${sel ? 'bg-teal-600 text-white border-teal-600' : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-teal-400'}`}
                  >
                    {s}
                  </button>
                )
              })}
            </div>
          ) : (
            <Input value={(f.subjects || []).join(', ')} onChange={v => setF({ ...f, subjects: v.split(',').map((x: string) => x.trim()).filter(Boolean) })} placeholder="Maths, Physique (séparées par virgule)" />
          )}
        </div>
      </div>
    )
  }

  return (
    <ListStep
      items={items}
      columns={['Nom', 'Matières', 'Max h']}
      defaultItem={def}
      renderRow={item => [
        <span className="font-medium">{item.name}</span>,
        <span className="text-gray-500 dark:text-gray-400 text-xs truncate">{(item.subjects || []).join(', ') || '—'}</span>,
        <span className="ml-auto text-xs text-gray-500">{item.max_hours_per_week != null ? `${item.max_hours_per_week}h/sem` : '∞'}</span>,
      ]}
      renderForm={form}
      onAdd={item => onUpdate({ ...data, teachers: [...items, item] })}
      onEdit={(i, item) => onUpdate({ ...data, teachers: items.map((x, idx) => idx === i ? item : x) })}
      onDelete={i => onUpdate({ ...data, teachers: items.filter((_, idx) => idx !== i) })}
      emptyText="Aucun enseignant — ajoutez-en un ou demandez à l'assistant."
    />
  )
}

// ── Step 4: Salles ────────────────────────────────────────────────────────────

const ROOM_TYPES = ['Standard', 'Laboratoire', 'Salle informatique', 'Salle de sport', 'Salle de musique']

function RoomsStep({ data, onUpdate }: { data: SchoolData; onUpdate: (d: SchoolData) => void }) {
  const items = data.rooms || []
  const def = { name: '', capacity: 30, types: ['Standard'] }

  function form(f: any, setF: (v: any) => void) {
    return (
      <div className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Nom</label>
            <Input value={f.name} onChange={v => setF({ ...f, name: v })} placeholder="Salle A" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Capacité</label>
            <Input type="number" value={String(f.capacity)} onChange={v => setF({ ...f, capacity: Number(v) })} placeholder="35" />
          </div>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-gray-500">Types</label>
          <div className="flex flex-wrap gap-1.5">
            {ROOM_TYPES.map(t => {
              const sel = (f.types || []).includes(t)
              return (
                <button
                  key={t}
                  onClick={() => setF({ ...f, types: sel ? f.types.filter((x: string) => x !== t) : [...(f.types || []), t] })}
                  className={`px-2 py-1 text-xs rounded-md border transition-colors ${sel ? 'bg-teal-600 text-white border-teal-600' : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-teal-400'}`}
                >
                  {t}
                </button>
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  return (
    <ListStep
      items={items}
      columns={['Nom', 'Capacité', 'Types']}
      defaultItem={def}
      renderRow={item => [
        <span className="font-medium">{item.name}</span>,
        <span className="text-xs text-gray-500">{item.capacity} places</span>,
        <span className="ml-auto text-xs text-gray-500">{(item.types || []).join(', ') || 'Standard'}</span>,
      ]}
      renderForm={form}
      onAdd={item => onUpdate({ ...data, rooms: [...items, item] })}
      onEdit={(i, item) => onUpdate({ ...data, rooms: items.map((x, idx) => idx === i ? item : x) })}
      onDelete={i => onUpdate({ ...data, rooms: items.filter((_, idx) => idx !== i) })}
      emptyText="Aucune salle — ajoutez-en une ou demandez à l'assistant."
    />
  )
}

// ── Step 5: Matières ──────────────────────────────────────────────────────────

const SUBJECT_COLORS = ['#0d9488','#2563eb','#7c3aed','#db2777','#ea580c','#65a30d','#ca8a04']

function SubjectsStep({ data, onUpdate }: { data: SchoolData; onUpdate: (d: SchoolData) => void }) {
  const items = data.subjects || []
  const def = { name: '', short_name: '', color: '#0d9488', required_room_type: '', needs_room: true }

  function form(f: any, setF: (v: any) => void) {
    return (
      <div className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Nom complet</label>
            <Input value={f.name} onChange={v => setF({ ...f, name: v, short_name: f.short_name || v.slice(0, 4).toUpperCase() })} placeholder="Mathématiques" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Abréviation</label>
            <Input value={f.short_name} onChange={v => setF({ ...f, short_name: v })} placeholder="MATH" />
          </div>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-gray-500">Couleur</label>
          <div className="flex gap-2 flex-wrap items-center">
            {SUBJECT_COLORS.map(c => (
              <button
                key={c}
                onClick={() => setF({ ...f, color: c })}
                style={{ backgroundColor: c }}
                className={`w-6 h-6 rounded-full border-2 transition-all ${f.color === c ? 'border-gray-900 dark:border-white scale-110' : 'border-transparent'}`}
              />
            ))}
            <input type="color" value={f.color} onChange={e => setF({ ...f, color: e.target.value })} className="w-7 h-7 rounded cursor-pointer border border-gray-200" />
          </div>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-gray-500">Type de salle requis (optionnel)</label>
          <Input value={f.required_room_type || ''} onChange={v => setF({ ...f, required_room_type: v || null })} placeholder="Laboratoire, Salle informatique…" />
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={f.needs_room} onChange={e => setF({ ...f, needs_room: e.target.checked })} className="accent-teal-600" />
          <span className="text-xs text-gray-600 dark:text-gray-400">Nécessite une salle</span>
        </label>
      </div>
    )
  }

  return (
    <ListStep
      items={items}
      columns={['Matière', 'Abrév', 'Salle']}
      defaultItem={def}
      renderRow={item => [
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: item.color || '#0d9488' }} />
          <span className="font-medium">{item.name}</span>
        </span>,
        <span className="text-xs text-gray-500">{item.short_name}</span>,
        <span className="ml-auto text-xs text-gray-500">{item.required_room_type || 'Standard'}</span>,
      ]}
      renderForm={form}
      onAdd={item => onUpdate({ ...data, subjects: [...items, item] })}
      onEdit={(i, item) => onUpdate({ ...data, subjects: items.map((x, idx) => idx === i ? item : x) })}
      onDelete={i => onUpdate({ ...data, subjects: items.filter((_, idx) => idx !== i) })}
      emptyText="Aucune matière — ajoutez-en une ou demandez à l'assistant."
    />
  )
}

// ── Step 6: Affectations ──────────────────────────────────────────────────────

function AssignmentsStep({
  data,
  assignments,
  onUpdateAssignments,
}: {
  data: SchoolData
  assignments: any[]
  onUpdateAssignments: (a: any[]) => void
}) {
  const teachers = (data.teachers || []).map((t: any) => t.name).filter(Boolean)
  const subjects = (data.subjects || []).map((s: any) => s.name).filter(Boolean)
  const classes  = (data.classes  || []).map((c: any) => c.name).filter(Boolean)
  const def = { teacher: teachers[0] || '', subject: subjects[0] || '', school_class: classes[0] || '' }

  const [editIdx, setEditIdx] = useState<number | null>(null)
  const [editForm, setEditForm] = useState(def)
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState(def)

  // Calculate missing assignments
  const missing = useMemo(() => getMissingAssignments(data, assignments), [data, assignments])

  function renderForm(f: any, setF: (v: any) => void) {
    return (
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Enseignant', key: 'teacher', opts: teachers },
          { label: 'Matière', key: 'subject', opts: subjects },
          { label: 'Classe', key: 'school_class', opts: classes },
        ].map(({ label, key, opts }) => (
          <div key={key} className="space-y-1">
            <label className="text-xs text-gray-500">{label}</label>
            {opts.length > 0 ? (
              <select
                value={f[key]}
                onChange={e => setF({ ...f, [key]: e.target.value })}
                className="w-full px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
              >
                <option value="">—</option>
                {opts.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            ) : (
              <Input value={f[key]} onChange={v => setF({ ...f, [key]: v })} placeholder={label} />
            )}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {/* Warning banner for missing assignments */}
      {missing.length > 0 && (
        <div className="mb-3 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertTriangle size={16} className="text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs">
              <p className="font-medium text-amber-800 dark:text-amber-200">
                {missing.length} matière(s) sans enseignant assigné
              </p>
              <ul className="mt-1 text-amber-700 dark:text-amber-300 space-y-0.5">
                {missing.slice(0, 5).map((m, i) => (
                  <li key={i}>• {m.school_class} — {m.subject}</li>
                ))}
                {missing.length > 5 && <li className="italic">...et {missing.length - 5} autres</li>}
              </ul>
            </div>
          </div>
        </div>
      )}

      {assignments.length === 0 && !showAdd && missing.length === 0 && (
        <SectionEmpty text="Aucune affectation — assignez un enseignant à chaque matière et classe." />
      )}
      {assignments.map((a, idx) => (
        <div key={idx}>
          <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-gray-800/60 rounded-lg text-sm">
            <span className="font-medium text-gray-700 dark:text-gray-300 truncate">{a.teacher}</span>
            <ArrowRight size={12} className="text-gray-400 flex-shrink-0" />
            <span className="text-gray-600 dark:text-gray-400 text-xs truncate">{a.subject}</span>
            <ArrowRight size={12} className="text-gray-400 flex-shrink-0" />
            <span className="text-gray-600 dark:text-gray-400 text-xs truncate">{a.school_class}</span>
            <RowActions
              onEdit={() => { setEditIdx(idx); setEditForm({ ...a }); setShowAdd(false) }}
              onDelete={() => onUpdateAssignments(assignments.filter((_, i) => i !== idx))}
            />
          </div>
          {editIdx === idx && (
            <div className="mt-1 mb-2 p-3 border border-teal-200 dark:border-teal-800 rounded-lg bg-teal-50 dark:bg-teal-900/10 space-y-3">
              {renderForm(editForm, setEditForm)}
              <SaveRow
                onSave={() => { onUpdateAssignments(assignments.map((x, i) => i === idx ? editForm : x)); setEditIdx(null) }}
                onCancel={() => setEditIdx(null)}
              />
            </div>
          )}
        </div>
      ))}
      {showAdd && (
        <div className="p-3 border border-teal-200 dark:border-teal-800 rounded-lg bg-teal-50 dark:bg-teal-900/10 space-y-3">
          {renderForm(addForm, setAddForm)}
          <SaveRow
            onSave={() => { onUpdateAssignments([...assignments, addForm]); setAddForm(def); setShowAdd(false) }}
            onCancel={() => { setShowAdd(false); setAddForm(def) }}
          />
        </div>
      )}
      {!showAdd && (
        <button onClick={() => { setShowAdd(true); setEditIdx(null) }} className="flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 hover:text-teal-700 transition-colors mt-2">
          <Plus size={13} /> Ajouter une affectation
        </button>
      )}
    </div>
  )
}

// ── Step 7: Programme ─────────────────────────────────────────────────────────

function CurriculumStep({ data, onUpdate }: { data: SchoolData; onUpdate: (d: SchoolData) => void }) {
  const items = data.curriculum || []
  const classes = (data.classes || []).map((c: any) => c.name).filter(Boolean) as string[]
  const subjects = (data.subjects || []).map((s: any) => s.name).filter(Boolean) as string[]
  const [copySource, setCopySource] = useState<string | null>(null)

  const def = {
    school_class: classes[0] || '',
    subject: subjects[0] || '',
    sessions_per_week: 2,
    minutes_per_session: 60,
    total_minutes_per_week: 120,
  }

  function copyFromClass(sourceClass: string, targetClass: string) {
    if (sourceClass === targetClass) return
    const sourceEntries = items.filter((item: any) => item.school_class === sourceClass)
    const copiedEntries = sourceEntries.map((entry: any) => ({
      ...entry,
      school_class: targetClass,
    }))
    // Remove existing entries for target class, then add copied ones
    const filtered = items.filter((item: any) => item.school_class !== targetClass)
    onUpdate({ ...data, curriculum: [...filtered, ...copiedEntries] })
  }

  function form(f: any, setF: (v: any) => void) {
    return (
      <div className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Classe</label>
            {classes.length > 0 ? (
              <select value={f.school_class} onChange={e => setF({ ...f, school_class: e.target.value })}
                className="w-full px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500">
                <option value="">—</option>
                {classes.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            ) : (
              <Input value={f.school_class} onChange={v => setF({ ...f, school_class: v })} placeholder="6ème A" />
            )}
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Matière</label>
            {subjects.length > 0 ? (
              <select value={f.subject} onChange={e => setF({ ...f, subject: e.target.value })}
                className="w-full px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500">
                <option value="">—</option>
                {subjects.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            ) : (
              <Input value={f.subject} onChange={v => setF({ ...f, subject: v })} placeholder="Mathématiques" />
            )}
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2">
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Sessions / semaine</label>
            <Input
              type="number"
              value={String(f.sessions_per_week ?? 2)}
              onChange={v => {
                const sessions = Math.max(1, Number(v) || 1)
                const minutes = Math.max(1, Number(f.minutes_per_session) || 60)
                setF({
                  ...f,
                  sessions_per_week: sessions,
                  total_minutes_per_week: sessions * minutes,
                })
              }}
              placeholder="2"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Minutes / session</label>
            <Input
              type="number"
              value={String(f.minutes_per_session ?? 60)}
              onChange={v => {
                const minutes = Math.max(1, Number(v) || 1)
                const sessions = Math.max(1, Number(f.sessions_per_week) || 2)
                setF({
                  ...f,
                  minutes_per_session: minutes,
                  total_minutes_per_week: sessions * minutes,
                })
              }}
              placeholder="60"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Total / semaine</label>
            <Input
              type="number"
              value={String(f.total_minutes_per_week ?? 120)}
              onChange={v => {
                const total = Math.max(1, Number(v) || 1)
                const sessions = Math.max(1, Number(f.sessions_per_week) || 1)
                const minutes = Math.max(1, Math.floor(total / sessions))
                setF({
                  ...f,
                  total_minutes_per_week: total,
                  minutes_per_session: minutes,
                })
              }}
              placeholder="120"
            />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Copy from class feature */}
      {classes.length > 1 && (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 space-y-2">
          <div className="text-xs font-medium text-gray-500 uppercase">Copier le programme d'une classe</div>
          <div className="flex gap-2 items-center flex-wrap">
            <select
              value={copySource || ''}
              onChange={e => setCopySource(e.target.value || null)}
              className="px-2 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
            >
              <option value="">Source...</option>
              {classes.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
            <span className="text-xs text-gray-400">→</span>
            {copySource && classes.filter(c => c !== copySource).map(targetClass => (
              <button
                key={targetClass}
                onClick={() => copyFromClass(copySource, targetClass)}
                className="px-2 py-1 text-xs bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 rounded hover:bg-teal-200 dark:hover:bg-teal-900/50 transition-colors"
              >
                {targetClass}
              </button>
            ))}
            {!copySource && <span className="text-xs text-gray-400 italic">Sélectionnez une classe source</span>}
          </div>
        </div>
      )}

      <ListStep
        items={items}
        columns={['Classe', 'Matière', 'Min/sem']}
        defaultItem={def}
        renderRow={item => [
          <span className="font-medium text-xs">{item.school_class}</span>,
          <span className="text-gray-700 dark:text-gray-300 text-xs">{item.subject}</span>,
          <span className="ml-auto text-xs text-gray-500">
            {(item.sessions_per_week ?? '?')}×{(item.minutes_per_session ?? '?')} = {item.total_minutes_per_week} min
          </span>,
        ]}
        renderForm={form}
        onAdd={item => onUpdate({ ...data, curriculum: [...items, item] })}
        onEdit={(i, item) => onUpdate({ ...data, curriculum: items.map((x, idx) => idx === i ? item : x) })}
        onDelete={i => onUpdate({ ...data, curriculum: items.filter((_, idx) => idx !== i) })}
        emptyText="Aucune entrée de programme — définissez les heures par matière et classe."
      />
    </div>
  )
}

// ── Step 8: Contraintes ───────────────────────────────────────────────────────

const CONSTRAINT_CATEGORIES = [
  { value: 'start_time',          label: 'Heure de début minimum',         type: 'hard' },
  { value: 'day_off',             label: 'Jour bloqué',                    type: 'hard' },
  { value: 'max_consecutive',     label: 'Max heures consécutives',        type: 'hard' },
  { value: 'teacher_day_off',     label: 'Congé enseignant',               type: 'hard' },
  { value: 'subject_on_days',     label: 'Matière sur jours précis',       type: 'hard' },
  { value: 'teacher_time_preference', label: 'Préférence horaire enseignant', type: 'soft' },
  { value: 'heavy_subjects_morning',  label: 'Matières difficiles le matin',  type: 'soft' },
  { value: 'balanced_daily_load', label: 'Charge équilibrée par jour',     type: 'soft' },
  { value: 'subject_spread',      label: 'Même matière pas 2x/jour',      type: 'soft' },
  { value: 'light_last_day',      label: 'Peu de cours le dernier jour',   type: 'soft' },
]

function ConstraintsStep({ data, onUpdate }: { data: SchoolData; onUpdate: (d: SchoolData) => void }) {
  const items = data.constraints || []
  const def = { id: '', type: 'hard', category: 'start_time', description_fr: '', priority: 5, parameters: {} }

  function form(f: any, setF: (v: any) => void) {
    const cat = CONSTRAINT_CATEGORIES.find(c => c.value === f.category)
    return (
      <div className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Catégorie</label>
            <select value={f.category} onChange={e => {
              const c = CONSTRAINT_CATEGORIES.find(x => x.value === e.target.value)
              setF({ ...f, category: e.target.value, type: c?.type || 'hard' })
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
          <Input value={f.description_fr} onChange={v => setF({ ...f, description_fr: v })} placeholder="Description de la contrainte" />
        </div>
        {f.type === 'soft' && (
          <div className="space-y-1">
            <label className="text-xs text-gray-500">Priorité (1-10)</label>
            <input type="range" min={1} max={10} value={f.priority} onChange={e => setF({ ...f, priority: Number(e.target.value) })}
              className="w-full accent-teal-600" />
            <div className="text-xs text-gray-500 text-center">Priorité : {f.priority}</div>
          </div>
        )}
        <div className="space-y-1">
          <label className="text-xs text-gray-500">Paramètres (JSON)</label>
          <textarea
            value={JSON.stringify(f.parameters || {})}
            onChange={e => {
              try { setF({ ...f, parameters: JSON.parse(e.target.value) }) } catch {}
            }}
            rows={2}
            className="w-full px-2 py-1.5 text-xs font-mono border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
            placeholder='{"hour": "08:00"}'
          />
        </div>
      </div>
    )
  }

  function badge(type: string) {
    return type === 'hard'
      ? <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 font-medium">Dure</span>
      : <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 font-medium">Souple</span>
  }

  return (
    <ListStep
      items={items}
      columns={['Type', 'Catégorie', 'Description']}
      defaultItem={def}
      renderRow={item => [
        badge(item.type),
        <span className="text-xs text-gray-600 dark:text-gray-400">{CONSTRAINT_CATEGORIES.find(c => c.value === item.category)?.label || item.category}</span>,
        <span className="ml-auto text-xs text-gray-500 truncate">{item.description_fr || '—'}</span>,
      ]}
      renderForm={form}
      onAdd={item => onUpdate({ ...data, constraints: [...items, { ...item, id: item.id || `C${items.length + 1}` }] })}
      onEdit={(i, item) => onUpdate({ ...data, constraints: items.map((x, idx) => idx === i ? item : x) })}
      onDelete={i => onUpdate({ ...data, constraints: items.filter((_, idx) => idx !== i) })}
      emptyText="Aucune contrainte — optionnel. Ajoutez-en si nécessaire ou demandez à l'assistant."
    />
  )
}

// ── Step 9: Résumé ────────────────────────────────────────────────────────────

function SummaryStep({
  data,
  assignments,
  onGenerate,
  isSolving,
  onAskAI,
}: {
  data: SchoolData
  assignments: any[]
  onGenerate: () => void
  isSolving: boolean
  onAskAI?: (errorContext: string) => void
}) {
  const checklist = getChecklistItems(data, assignments)
  const ready     = getChecklistStatus(data, assignments)

  // Validate hour barriers
  const validationErrors = useMemo(() => validateHourBarriers(data), [data])
  const hasErrors = validationErrors.some(e => e.severity === 'error')

  const stats = [
    { label: 'Classes',       count: data.classes?.length    ?? 0 },
    { label: 'Enseignants',   count: data.teachers?.length   ?? 0 },
    { label: 'Salles',        count: data.rooms?.length      ?? 0 },
    { label: 'Matières',      count: data.subjects?.length   ?? 0 },
    { label: 'Affectations',  count: assignments.length              },
    { label: 'Programme',     count: data.curriculum?.length ?? 0 },
    { label: 'Contraintes',   count: data.constraints?.length ?? 0 },
  ]

  const handleAskAI = () => {
    if (!onAskAI) return

    // Format error context for AI
    const errorSummary = validationErrors
      .filter(e => e.severity === 'error')
      .map(e => `${e.message}: ${e.details || ''}`)
      .join('\n\n')

    onAskAI(`J'ai des erreurs de validation :\n\n${errorSummary}\n\nComment puis-je les résoudre ?`)
  }

  return (
    <div className="space-y-5">
      {/* School header */}
      {data.name && (
        <div className="bg-teal-50 dark:bg-teal-900/20 border border-teal-200 dark:border-teal-800 rounded-xl p-4">
          <h3 className="font-semibold text-teal-800 dark:text-teal-200 text-sm">{data.name}</h3>
          {(data.city || data.academic_year) && (
            <p className="text-xs text-teal-600 dark:text-teal-400 mt-0.5">
              {[data.city, data.academic_year].filter(Boolean).join(' · ')}
            </p>
          )}
          {data.days && data.days.length > 0 && (
            <p className="text-xs text-teal-600 dark:text-teal-400 mt-0.5">
              {data.days.map(d => d.name).join(', ')} · {data.days[0]?.sessions?.length ?? 0} session(s)
            </p>
          )}
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-2">
        {stats.map(s => (
          <div key={s.label} className="text-center bg-gray-50 dark:bg-gray-800/50 rounded-lg py-2 px-1">
            <div className="text-lg font-bold text-gray-900 dark:text-white">{s.count}</div>
            <div className="text-[10px] text-gray-500 dark:text-gray-400 leading-tight">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Validation errors */}
      {validationErrors.length > 0 && (
        <ValidationErrorPanel
          errors={validationErrors}
          onAskAI={onAskAI ? handleAskAI : undefined}
        />
      )}

      {/* Readiness checklist */}
      <div className="space-y-1.5">
        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          Conditions pour générer
        </h4>
        {checklist.map((item, i) => (
          <div key={i} className="flex items-center gap-2.5">
            <div className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 ${item.done ? 'bg-teal-500' : 'bg-gray-200 dark:bg-gray-700'}`}>
              {item.done && <Check size={9} className="text-white" strokeWidth={3} />}
            </div>
            <span className={`text-xs ${item.done ? 'text-gray-700 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500'}`}>
              {item.label}
            </span>
          </div>
        ))}
      </div>

      {/* Generate button */}
      <button
        onClick={onGenerate}
        disabled={!ready || isSolving || hasErrors}
        className={`w-full py-3 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all ${
          ready && !isSolving && !hasErrors
            ? 'bg-teal-600 hover:bg-teal-700 text-white shadow-md hover:shadow-lg'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600 cursor-not-allowed'
        }`}
      >
        {isSolving ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            Génération en cours…
          </>
        ) : (
          <>
            Générer l&apos;emploi du temps
            <ChevronRight size={16} />
          </>
        )}
      </button>

      {!ready && !isSolving && !hasErrors && (
        <p className="text-xs text-center text-gray-400 dark:text-gray-500">
          Complétez les éléments manquants ci-dessus pour activer la génération.
        </p>
      )}

      {hasErrors && (
        <p className="text-xs text-center text-red-600 dark:text-red-400">
          Corrigez les erreurs ci-dessus avant de générer l'emploi du temps.
        </p>
      )}
    </div>
  )
}

// ── Main StepPanel ────────────────────────────────────────────────────────────

interface Props {
  step: number
  schoolData: SchoolData
  assignments: any[]
  onUpdateSchoolData: (d: SchoolData) => void
  onUpdateAssignments: (a: any[]) => void
  onNext: () => void
  onGenerate: () => void
  isSolving: boolean
  onAskAI?: (errorContext: string) => void
}

const STEP_TITLES = [
  'Informations de l\'école',
  'Classes',
  'Enseignants',
  'Salles',
  'Matières',
  'Affectations enseignant → matière → classe',
  'Programme (heures par semaine)',
  'Contraintes',
  'Résumé & Génération',
]

export default function StepPanel({
  step,
  schoolData,
  assignments,
  onUpdateSchoolData,
  onUpdateAssignments,
  onNext,
  onGenerate,
  isSolving,
  onAskAI,
}: Props) {
  const isLast = step === 8

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Step title */}
      <div className="px-5 py-3 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
        <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
          {STEP_TITLES[step]}
        </h3>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        {step === 0 && <SchoolStep      data={schoolData} onUpdate={onUpdateSchoolData} />}
        {step === 1 && <ClassesStep     data={schoolData} onUpdate={onUpdateSchoolData} />}
        {step === 2 && <TeachersStep    data={schoolData} onUpdate={onUpdateSchoolData} />}
        {step === 3 && <RoomsStep       data={schoolData} onUpdate={onUpdateSchoolData} />}
        {step === 4 && <SubjectsStep    data={schoolData} onUpdate={onUpdateSchoolData} />}
        {step === 5 && (
          <AssignmentsStep
            data={schoolData}
            assignments={assignments}
            onUpdateAssignments={onUpdateAssignments}
          />
        )}
        {step === 6 && <CurriculumStep  data={schoolData} onUpdate={onUpdateSchoolData} />}
        {step === 7 && <ConstraintsStep data={schoolData} onUpdate={onUpdateSchoolData} />}
        {step === 8 && (
          <SummaryStep
            data={schoolData}
            assignments={assignments}
            onGenerate={onGenerate}
            isSolving={isSolving}
            onAskAI={onAskAI}
          />
        )}
      </div>

      {/* Next button (not on summary step) */}
      {!isLast && (
        <div className="px-5 py-3 border-t border-gray-100 dark:border-gray-800 flex-shrink-0">
          <button
            onClick={onNext}
            className="w-full py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-xl flex items-center justify-center gap-2 transition-colors"
          >
            Suivant <ChevronRight size={15} />
          </button>
        </div>
      )}
    </div>
  )
}
