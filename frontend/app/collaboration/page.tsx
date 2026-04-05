'use client'
import { useState } from 'react'
import { Users, Link2, Clock, Copy, Check, RefreshCw, Loader2 } from 'lucide-react'
import { useSession } from '@/hooks/useSession'
import { useToast } from '@/components/Toast'
import { generateCollabLinks } from '@/lib/api'

// Computed client-side only — safe because this component renders after hydration
function getBaseUrl() {
  if (typeof window === 'undefined') return ''
  return window.location.origin
}

export default function CollaborationPage() {
  const { sessionId, schoolData } = useSession()
  const { toast } = useToast()

  const [generating, setGenerating] = useState(false)
  const [copiedIdx, setCopiedIdx]   = useState<number | null>(null)
  const [links, setLinks] = useState<{ teacher: string; token: string; status: string }[]>([])

  const teacherNames: string[] = (schoolData.teachers ?? []).map(
    (t: any) => t.name ?? t.id ?? 'Enseignant',
  )

  const responded = links.filter(l => l.status === 'soumis').length

  async function handleGenerate() {
    if (!sessionId || generating) return
    setGenerating(true)
    try {
      const data = await generateCollabLinks(sessionId)
      setLinks(data.links)
      toast('Liens générés')
    } catch {
      toast('Erreur lors de la génération des liens', 'error')
    } finally {
      setGenerating(false)
    }
  }

  async function copyLink(token: string, idx: number) {
    const url = `${getBaseUrl()}/collab/${token}`
    try {
      await navigator.clipboard.writeText(url)
      setCopiedIdx(idx)
      setTimeout(() => setCopiedIdx(null), 2000)
      toast('Lien copié')
    } catch {
      toast('Impossible de copier', 'error')
    }
  }

  const generatedCount = links.length

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Collaboration</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Générez des liens de disponibilité pour chaque enseignant
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {[
          { icon: Users,  label: 'Enseignants',          value: teacherNames.length.toString() },
          { icon: Link2,  label: 'Liens générés',         value: generatedCount.toString() },
          { icon: Clock,  label: 'Réponses reçues',       value: responded.toString() },
        ].map(stat => (
          <div
            key={stat.label}
            className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-5 shadow-sm flex items-center gap-4"
          >
            <div className="w-10 h-10 rounded-xl bg-teal-50 dark:bg-teal-900/30 text-teal-600 dark:text-teal-400 flex items-center justify-center flex-shrink-0">
              <stat.icon size={18} />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400 leading-tight">{stat.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Teacher list */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h2 className="font-semibold text-gray-800 dark:text-gray-200">Liste des enseignants</h2>
          <button
            onClick={handleGenerate}
            disabled={teacherNames.length === 0 || generating}
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm rounded-xl transition-colors disabled:opacity-50"
          >
            {generating
              ? <Loader2 size={15} className="animate-spin" />
              : <RefreshCw size={15} />
            }
            {generatedCount > 0 ? 'Régénérer les liens' : 'Générer les liens'}
          </button>
        </div>

        {teacherNames.length === 0 ? (
          <p className="text-sm text-gray-400 dark:text-gray-500 italic text-center py-8">
            Aucun enseignant configuré. Commencez dans l'espace de travail.
          </p>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {teacherNames.map((name, i) => {
              const linkData = links.find(l => l.teacher === name)
              return (
                <div key={i} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300 flex items-center justify-center text-xs font-bold flex-shrink-0">
                      {name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{name}</p>
                      {linkData ? (
                        <p className="text-xs text-gray-400 dark:text-gray-500 font-mono truncate max-w-[240px]">
                          {`${getBaseUrl()}/collab/${linkData.token}`}
                        </p>
                      ) : (
                        <p className="text-xs text-gray-400 dark:text-gray-500 italic">Aucun lien généré</p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {linkData && (
                      <button
                        onClick={() => copyLink(linkData.token, i)}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-gray-600 dark:text-gray-400"
                      >
                        {copiedIdx === i
                          ? <><Check size={13} className="text-teal-500" /> Copié</>
                          : <><Copy size={13} /> Copier</>
                        }
                      </button>
                    )}

                    <span className={`text-xs px-2.5 py-1 rounded-full ${
                      linkData?.status === 'soumis'
                        ? 'bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300'
                        : linkData
                        ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400'
                    }`}>
                      {linkData?.status === 'soumis' ? 'Répondu' : linkData ? 'En attente' : 'Non envoyé'}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
