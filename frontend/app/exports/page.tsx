'use client'

import { useState, useEffect } from 'react'
import { Download, FileText, FileSpreadsheet, FileJson, FileCode, FileCheck, Loader2, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { getSession, exportFile } from '@/lib/api'
import type { SchoolData } from '@/lib/types'

const EXPORT_FORMATS = [
  {
    id: 'pdf',
    name: 'PDF',
    description: 'Document prêt à imprimer',
    icon: FileText,
    gradient: 'from-red-500 to-red-600',
    bg: 'bg-red-50 dark:bg-red-950/30',
    iconColor: 'text-red-600 dark:text-red-400',
  },
  {
    id: 'xlsx',
    name: 'Excel',
    description: 'Feuille de calcul modifiable',
    icon: FileSpreadsheet,
    gradient: 'from-emerald-500 to-emerald-600',
    bg: 'bg-emerald-50 dark:bg-emerald-950/30',
    iconColor: 'text-emerald-600 dark:text-emerald-400',
  },
  {
    id: 'docx',
    name: 'Word',
    description: 'Document texte éditable',
    icon: FileText,
    gradient: 'from-blue-500 to-blue-600',
    bg: 'bg-blue-50 dark:bg-blue-950/30',
    iconColor: 'text-blue-600 dark:text-blue-400',
  },
  {
    id: 'csv',
    name: 'CSV',
    description: 'Import vers autres logiciels',
    icon: FileCode,
    gradient: 'from-amber-500 to-amber-600',
    bg: 'bg-amber-50 dark:bg-amber-950/30',
    iconColor: 'text-amber-600 dark:text-amber-400',
  },
  {
    id: 'json',
    name: 'JSON',
    description: 'Données structurées (API)',
    icon: FileJson,
    gradient: 'from-violet-500 to-violet-600',
    bg: 'bg-violet-50 dark:bg-violet-950/30',
    iconColor: 'text-violet-600 dark:text-violet-400',
  },
  {
    id: 'md',
    name: 'Markdown',
    description: 'Documentation / notes',
    icon: FileCheck,
    gradient: 'from-zinc-500 to-zinc-600',
    bg: 'bg-zinc-100 dark:bg-zinc-800/50',
    iconColor: 'text-zinc-600 dark:text-zinc-400',
  },
]

export default function ExportsPage() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [schoolData, setSchoolData] = useState<SchoolData | null>(null)
  const [loading, setLoading] = useState(true)
  const [exportingFormat, setExportingFormat] = useState<string | null>(null)

  useEffect(() => {
    const sid = localStorage.getItem('timease_session')
    if (sid) {
      setSessionId(sid)
      getSession(sid)
        .then(data => {
          setSchoolData(data.school_data)
        })
        .catch(() => {})
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  async function handleExport(format: string) {
    if (!sessionId) return
    setExportingFormat(format)
    try {
      const blob = await exportFile(sessionId, format)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `emploi-du-temps.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed:', err)
    } finally {
      setExportingFormat(null)
    }
  }

  const hasData = schoolData && (
    (schoolData.classes?.length ?? 0) > 0 ||
    (schoolData.teachers?.length ?? 0) > 0
  )

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-950">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 py-12 px-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-10">
          <Link
            href="/results"
            className="inline-flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white mb-4 transition-colors"
          >
            <ArrowLeft size={16} />
            Retour à l'emploi du temps
          </Link>
          <h1 className="text-3xl font-bold text-zinc-900 dark:text-white tracking-tight">
            Centre d'exportation
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-2">
            Téléchargez votre emploi du temps dans le format de votre choix
          </p>
        </div>

        {!hasData ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mx-auto mb-4">
              <Download size={28} className="text-zinc-400" />
            </div>
            <h2 className="text-lg font-semibold text-zinc-700 dark:text-zinc-300">
              Aucune donnée à exporter
            </h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1 max-w-xs mx-auto">
              Commencez par créer un emploi du temps dans l'espace de travail
            </p>
            <Link
              href="/workspace"
              className="mt-4 inline-block px-5 py-2.5 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-sm font-medium rounded-xl hover:bg-black dark:hover:bg-zinc-200 transition-colors"
            >
              Aller à l'espace de travail
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {EXPORT_FORMATS.map((fmt) => {
              const Icon = fmt.icon
              const isExporting = exportingFormat === fmt.id

              return (
                <button
                  key={fmt.id}
                  onClick={() => handleExport(fmt.id)}
                  disabled={isExporting}
                  className="group relative bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 text-left hover:border-zinc-300 dark:hover:border-zinc-700 hover:shadow-lg transition-all duration-200 disabled:opacity-50"
                >
                  {/* Icon */}
                  <div className={`w-12 h-12 rounded-xl ${fmt.bg} flex items-center justify-center mb-4`}>
                    {isExporting ? (
                      <Loader2 size={24} className={`${fmt.iconColor} animate-spin`} />
                    ) : (
                      <Icon size={24} className={fmt.iconColor} />
                    )}
                  </div>

                  {/* Content */}
                  <h3 className="text-lg font-semibold text-zinc-900 dark:text-white mb-1">
                    {fmt.name}
                  </h3>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400">
                    {fmt.description}
                  </p>

                  {/* Hover indicator */}
                  <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Download size={16} className="text-zinc-400" />
                  </div>

                  {/* Gradient accent on hover */}
                  <div className={`absolute inset-x-0 bottom-0 h-1 rounded-b-2xl bg-gradient-to-r ${fmt.gradient} opacity-0 group-hover:opacity-100 transition-opacity`} />
                </button>
              )
            })}
          </div>
        )}

        {/* Format info */}
        {hasData && (
          <div className="mt-10 p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl">
            <h3 className="font-semibold text-zinc-900 dark:text-white mb-3">
              Quel format choisir ?
            </h3>
            <ul className="space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
              <li>
                <strong className="text-zinc-900 dark:text-white">PDF</strong> — Pour imprimer ou partager un document final
              </li>
              <li>
                <strong className="text-zinc-900 dark:text-white">Excel</strong> — Pour modifier les données ou faire des calculs
              </li>
              <li>
                <strong className="text-zinc-900 dark:text-white">Word</strong> — Pour personnaliser la mise en page
              </li>
              <li>
                <strong className="text-zinc-900 dark:text-white">CSV</strong> — Pour importer dans d'autres logiciels scolaires
              </li>
              <li>
                <strong className="text-zinc-900 dark:text-white">JSON</strong> — Pour les développeurs ou intégrations API
              </li>
              <li>
                <strong className="text-zinc-900 dark:text-white">Markdown</strong> — Pour la documentation ou les wikis
              </li>
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
