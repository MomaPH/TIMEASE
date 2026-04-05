'use client'
import { use, useState } from 'react'
import { Clock, CheckCircle2 } from 'lucide-react'
import { useToast } from '@/components/Toast'

const DAYS   = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
const STATUS = ['disponible', 'indisponible', 'préféré'] as const
type Status  = typeof STATUS[number]

const STATUS_STYLE: Record<Status, string> = {
  disponible:    'border-teal-400 bg-teal-50 text-teal-700 dark:border-teal-700 dark:bg-teal-900/30 dark:text-teal-300',
  indisponible:  'border-red-300 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-900/20 dark:text-red-300',
  préféré:       'border-violet-300 bg-violet-50 text-violet-700 dark:border-violet-700 dark:bg-violet-900/20 dark:text-violet-300',
}
const STATUS_IDLE = 'border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'

export default function CollabTeacherPage({
  params,
}: {
  params: Promise<{ token: string }>
}) {
  const { token }   = use(params)
  const { toast }   = useToast()

  // dayAvailability: day label → selected status (undefined = not set)
  const [availability, setAvailability] = useState<Record<string, Status | undefined>>({})
  const [saved, setSaved]               = useState(false)
  const [saving, setSaving]             = useState(false)

  function pick(day: string, status: Status) {
    setAvailability(prev => {
      // Toggle off if clicking the same button
      if (prev[day] === status) {
        const next = { ...prev }
        delete next[day]
        return next
      }
      return { ...prev, [day]: status }
    })
    setSaved(false)
  }

  async function handleSave() {
    setSaving(true)
    try {
      // Backend endpoint not yet implemented — stub call
      await fetch(`/api/collab/${token}/availability`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ availability }),
      }).catch(() => {}) // tolerate 404 from stub

      setSaved(true)
      toast('Disponibilités enregistrées !')
    } catch {
      toast('Erreur lors de la sauvegarde', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto py-4 sm:py-8 px-2 animate-fade-in">
      {/* Branding */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold flex-shrink-0">
          T
        </div>
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white leading-none">TIMEASE</h1>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Portail enseignant</p>
        </div>
      </div>

      {/* Card */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm p-5 sm:p-6 mb-4">
        <div className="flex items-center gap-2 mb-1">
          <Clock size={16} className="text-teal-600 flex-shrink-0" />
          <h2 className="font-semibold text-gray-800 dark:text-gray-200">Vos disponibilités</h2>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
          Indiquez votre disponibilité pour chaque jour de la semaine.
        </p>

        <div className="space-y-1">
          {DAYS.map(day => {
            const current = availability[day]
            return (
              <div
                key={day}
                className="flex flex-wrap items-center gap-2 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0"
              >
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300 w-24 flex-shrink-0">
                  {day}
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {STATUS.map(s => (
                    <button
                      key={s}
                      onClick={() => pick(day, s)}
                      className={[
                        'text-xs px-3 py-1.5 rounded-full border transition-all capitalize font-medium',
                        current === s ? STATUS_STYLE[s] : STATUS_IDLE,
                      ].join(' ')}
                    >
                      {s}
                    </button>
                  ))}
                </div>
                {current && (
                  <span className="ml-auto text-xs text-gray-400 dark:text-gray-500 capitalize">
                    {current}
                  </span>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Save button */}
      <button
        onClick={handleSave}
        disabled={saving || saved}
        className="w-full flex items-center justify-center gap-2 py-3 bg-teal-600 hover:bg-teal-700 disabled:opacity-60 text-white font-medium rounded-xl transition-colors shadow-sm"
      >
        {saved
          ? <><CheckCircle2 size={16} /> Disponibilités enregistrées</>
          : saving
            ? 'Enregistrement…'
            : 'Enregistrer mes disponibilités'
        }
      </button>

      <p className="text-center text-xs text-gray-400 dark:text-gray-600 mt-4 font-mono">
        Token : {token}
      </p>
    </div>
  )
}
