'use client'
import { useState } from 'react'
import { Plus, X, ChevronRight } from 'lucide-react'
import type { SchoolData, DayConfig, SessionConfig, BreakConfig } from '@/lib/types'

const DAYS_FR  = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
const DAYS_VAL = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi']

const ROOM_TYPES = ['Standard', 'Laboratoire', 'Salle informatique', 'Salle de sport', 'Salle de musique']

interface Props {
  data: SchoolData
  onUpdate: (d: SchoolData) => void
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</label>
      {children}
    </div>
  )
}

function TextInput({ value, onChange, placeholder, type = 'text' }: {
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

export default function EcoleStep({ data, onUpdate }: Props) {
  const days    = data.days ?? []
  const dayNames = days.map(d => d.name)
  const rooms   = data.rooms ?? []

  const [expandedDay,   setExpandedDay]   = useState<string | null>(null)
  const [roomsOpen,     setRoomsOpen]     = useState(false)

  // ── Day helpers ──────────────────────────────────────────────────────────────

  function toggleDay(dayVal: string) {
    if (dayNames.includes(dayVal)) {
      onUpdate({ ...data, days: days.filter(d => d.name !== dayVal) })
    } else {
      const newDay: DayConfig = {
        name: dayVal,
        sessions: [{ name: '', start_time: '07:30', end_time: '12:30' }],
        breaks: [],
      }
      const next = [...days, newDay].sort((a, b) => DAYS_VAL.indexOf(a.name) - DAYS_VAL.indexOf(b.name))
      onUpdate({ ...data, days: next })
    }
  }

  function updateDay(dayName: string, updates: Partial<DayConfig>) {
    onUpdate({ ...data, days: days.map(d => d.name === dayName ? { ...d, ...updates } : d) })
  }

  function addSession(dayName: string) {
    const day = days.find(d => d.name === dayName)
    if (!day) return
    const s: SessionConfig = { name: '', start_time: '08:00', end_time: '10:00' }
    updateDay(dayName, { sessions: [...day.sessions, s] })
  }

  function updateSession(dayName: string, idx: number, field: keyof SessionConfig, val: string) {
    const day = days.find(d => d.name === dayName)
    if (!day) return
    updateDay(dayName, { sessions: day.sessions.map((s, i) => i === idx ? { ...s, [field]: val } : s) })
  }

  function removeSession(dayName: string, idx: number) {
    const day = days.find(d => d.name === dayName)
    if (!day) return
    updateDay(dayName, { sessions: day.sessions.filter((_, i) => i !== idx) })
  }

  function addBreak(dayName: string) {
    const day = days.find(d => d.name === dayName)
    if (!day) return
    const b: BreakConfig = { name: 'Récréation', start_time: '10:00', end_time: '10:15' }
    updateDay(dayName, { breaks: [...day.breaks, b] })
  }

  function updateBreak(dayName: string, idx: number, field: keyof BreakConfig, val: string) {
    const day = days.find(d => d.name === dayName)
    if (!day) return
    updateDay(dayName, { breaks: day.breaks.map((b, i) => i === idx ? { ...b, [field]: val } : b) })
  }

  function removeBreak(dayName: string, idx: number) {
    const day = days.find(d => d.name === dayName)
    if (!day) return
    updateDay(dayName, { breaks: day.breaks.filter((_, i) => i !== idx) })
  }

  // ── Room helpers ─────────────────────────────────────────────────────────────

  function addRoom() {
    onUpdate({ ...data, rooms: [...rooms, { name: '', types: ['Standard'], capacity: 30 }] })
  }

  function updateRoom(idx: number, field: string, val: string) {
    const update = field === 'types' ? { [field]: [val] } : { [field]: val }
    onUpdate({ ...data, rooms: rooms.map((r, i) => i === idx ? { ...r, ...update } : r) })
  }

  function deleteRoom(idx: number) {
    onUpdate({ ...data, rooms: rooms.filter((_, i) => i !== idx) })
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-5">

      {/* A) École */}
      <section className="space-y-3">
        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">École</h4>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Nom de l'école">
            <TextInput value={data.name ?? ''} onChange={v => onUpdate({ ...data, name: v })} placeholder="Ex : Collège Saint-Paul" />
          </Field>
          <Field label="Ville">
            <TextInput value={data.city ?? ''} onChange={v => onUpdate({ ...data, city: v })} placeholder="Ex : Abidjan" />
          </Field>
        </div>
        <Field label="Année scolaire">
          <TextInput value={data.academic_year ?? ''} onChange={v => onUpdate({ ...data, academic_year: v })} placeholder="2025-2026" />
        </Field>
      </section>

      {/* B) Jours de la semaine */}
      <section className="space-y-2">
        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Jours de la semaine</h4>
        <div className="flex flex-wrap gap-2">
          {DAYS_FR.map((d, i) => {
            const val      = DAYS_VAL[i]
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
      </section>

      {/* C) Emploi du temps par jour */}
      {days.length > 0 && (
        <section className="space-y-2">
          <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Emploi du temps par jour</h4>
          {days.map(day => {
            const dayLabel  = DAYS_FR[DAYS_VAL.indexOf(day.name)] ?? day.name
            const expanded  = expandedDay === day.name
            return (
              <div key={day.name} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedDay(expanded ? null : day.name)}
                  className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <span>{dayLabel}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">
                      {day.sessions.length} session{day.sessions.length !== 1 ? 's' : ''}
                      {day.breaks.length > 0 && `, ${day.breaks.length} pause${day.breaks.length !== 1 ? 's' : ''}`}
                    </span>
                    <ChevronRight size={14} className={`transition-transform ${expanded ? 'rotate-90' : ''}`} />
                  </div>
                </button>

                {expanded && (
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
                          <input type="time" value={s.start_time} onChange={e => updateSession(day.name, i, 'start_time', e.target.value)}
                            className="w-24 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500" />
                          <span className="text-xs text-gray-400">→</span>
                          <input type="time" value={s.end_time} onChange={e => updateSession(day.name, i, 'end_time', e.target.value)}
                            className="w-24 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500" />
                          <button onClick={() => removeSession(day.name, i)} className="text-gray-400 hover:text-red-500 transition-colors">
                            <X size={13} />
                          </button>
                        </div>
                      ))}
                      <button onClick={() => addSession(day.name)} className="flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 hover:text-teal-700 transition-colors">
                        <Plus size={13} /> Ajouter une session
                      </button>
                    </div>

                    {/* Breaks (collapsible) */}
                    <BreaksEditor
                      dayName={day.name}
                      breaks={day.breaks}
                      onAdd={() => addBreak(day.name)}
                      onUpdate={(idx, field, val) => updateBreak(day.name, idx, field, val)}
                      onRemove={(idx) => removeBreak(day.name, idx)}
                    />
                  </div>
                )}
              </div>
            )
          })}
        </section>
      )}

      {/* D) Salles (collapsible, default closed) */}
      <section className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
        <button
          onClick={() => setRoomsOpen(o => !o)}
          className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Salles <span className="font-normal normal-case text-gray-400">(optionnel)</span>
          </span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">{rooms.length > 0 ? `${rooms.length} salle${rooms.length > 1 ? 's' : ''}` : 'aucune'}</span>
            <ChevronRight size={14} className={`transition-transform ${roomsOpen ? 'rotate-90' : ''}`} />
          </div>
        </button>

        {roomsOpen && (
          <div className="p-3 space-y-2 bg-white dark:bg-gray-900">
            {rooms.length === 0 && (
              <p className="text-xs text-gray-400 italic">Aucune salle définie.</p>
            )}
            {rooms.map((room, idx) => (
              <div key={idx} className="flex gap-2 items-center">
                <input
                  value={room.name}
                  onChange={e => updateRoom(idx, 'name', e.target.value)}
                  placeholder="Nom de la salle"
                  className="flex-1 min-w-0 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
                />
                <select
                  value={(room.types ?? ['Standard'])[0] ?? 'Standard'}
                  onChange={e => updateRoom(idx, 'types', e.target.value)}
                  className="px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
                >
                  {ROOM_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <button onClick={() => deleteRoom(idx)} className="text-gray-400 hover:text-red-500 transition-colors">
                  <X size={13} />
                </button>
              </div>
            ))}
            <button onClick={addRoom} className="flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 hover:text-teal-700 transition-colors">
              <Plus size={13} /> Ajouter une salle
            </button>
          </div>
        )}
      </section>

    </div>
  )
}

// ── Breaks sub-component ──────────────────────────────────────────────────────

function BreaksEditor({
  dayName,
  breaks,
  onAdd,
  onUpdate,
  onRemove,
}: {
  dayName: string
  breaks: BreakConfig[]
  onAdd: () => void
  onUpdate: (idx: number, field: keyof BreakConfig, val: string) => void
  onRemove: (idx: number) => void
}) {
  const [open, setOpen] = useState(false)

  return (
    <div className="border border-gray-100 dark:border-gray-800 rounded overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-2 py-1.5 text-xs font-medium text-gray-500 bg-gray-50 dark:bg-gray-800/60 hover:bg-gray-100 dark:hover:bg-gray-700/60 transition-colors"
      >
        <span>Pauses / Récréations</span>
        <div className="flex items-center gap-1.5">
          <span className="text-gray-400">{breaks.length > 0 ? `${breaks.length}` : 'aucune'}</span>
          <ChevronRight size={12} className={`transition-transform ${open ? 'rotate-90' : ''}`} />
        </div>
      </button>

      {open && (
        <div className="p-2 space-y-2 bg-white dark:bg-gray-900">
          {breaks.length === 0 && <p className="text-xs text-gray-400 italic">Aucune pause</p>}
          {breaks.map((b, i) => (
            <div key={i} className="flex gap-2 items-center">
              <input
                value={b.name}
                onChange={e => onUpdate(i, 'name', e.target.value)}
                placeholder="Nom"
                className="flex-1 min-w-0 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500"
              />
              <input type="time" value={b.start_time} onChange={e => onUpdate(i, 'start_time', e.target.value)}
                className="w-24 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500" />
              <span className="text-xs text-gray-400">→</span>
              <input type="time" value={b.end_time} onChange={e => onUpdate(i, 'end_time', e.target.value)}
                className="w-24 px-2 py-1 text-xs border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-teal-500" />
              <button onClick={() => onRemove(i)} className="text-gray-400 hover:text-red-500 transition-colors">
                <X size={13} />
              </button>
            </div>
          ))}
          <button onClick={onAdd} className="flex items-center gap-1.5 text-xs text-teal-600 dark:text-teal-400 hover:text-teal-700 transition-colors">
            <Plus size={13} /> Ajouter une pause
          </button>
        </div>
      )}
    </div>
  )
}
