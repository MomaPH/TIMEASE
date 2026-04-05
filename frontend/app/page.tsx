import Link from 'next/link'
import { CalendarDays, BrainCircuit, FileDown } from 'lucide-react'

const FEATURES = [
  {
    icon: BrainCircuit,
    title: 'Assistant IA',
    desc: 'Configurez votre école en langage naturel. L\'IA extrait automatiquement les données.',
  },
  {
    icon: CalendarDays,
    title: 'Solveur CP-SAT',
    desc: 'Google OR-Tools génère un emploi du temps optimal en respectant toutes vos contraintes.',
  },
  {
    icon: FileDown,
    title: 'Export multi-format',
    desc: 'Exportez vos résultats en Excel, PDF ou Word en un clic.',
  },
]

export default function HomePage() {
  return (
    <div className="max-w-3xl mx-auto pt-12">
      <div className="mb-12 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-teal-600 text-white mb-6 text-2xl font-bold shadow-lg">
          T
        </div>
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
          TIMEASE
        </h1>
        <p className="text-lg text-gray-500 dark:text-gray-400 max-w-xl mx-auto">
          Générateur d&apos;emplois du temps pour écoles privées.
          Simple, rapide, intelligent.
        </p>
        <div className="mt-8">
          <Link
            href="/workspace"
            className="inline-flex items-center gap-2 px-6 py-3 bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-xl transition-colors shadow-sm"
          >
            Commencer
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {FEATURES.map(f => (
          <div
            key={f.title}
            className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-sm"
          >
            <div className="w-10 h-10 rounded-xl bg-teal-50 dark:bg-teal-900/30 text-teal-600 dark:text-teal-400 flex items-center justify-center mb-4">
              <f.icon size={20} />
            </div>
            <h3 className="font-semibold text-gray-900 dark:text-white mb-2">{f.title}</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
