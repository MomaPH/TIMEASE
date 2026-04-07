import Link from 'next/link'
import { CalendarDays, BrainCircuit, FileDown, Sparkles, ArrowRight } from 'lucide-react'

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
    desc: 'PDF, Excel, Word, iCal, JSON — tous les formats pour tous les usages.',
  },
]

export default function HomePage() {
  return (
    <div className="max-w-3xl mx-auto pt-8 md:pt-16 animate-fade-in">
      {/* Hero */}
      <div className="mb-16 text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 mb-6 shadow-lg shadow-indigo-500/20">
          <svg viewBox="0 0 24 24" className="w-7 h-7 fill-white">
            <path d="M19 4H5a2 2 0 00-2 2v12a2 2 0 002 2h14a2 2 0 002-2V6a2 2 0 00-2-2zm0 14H5V8h14v10z"/>
          </svg>
        </div>
        <h1 className="text-4xl md:text-5xl font-bold text-zinc-900 dark:text-white mb-4 tracking-tight">
          TIMEASE
        </h1>
        <p className="text-lg text-zinc-500 dark:text-zinc-400 max-w-lg mx-auto leading-relaxed">
          Générateur d&apos;emplois du temps pour écoles privées.
          Simple, rapide, intelligent.
        </p>
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/workspace"
            className="inline-flex items-center gap-2 px-6 py-3 bg-zinc-900 dark:bg-white hover:bg-black dark:hover:bg-zinc-200 text-white dark:text-zinc-900 font-medium rounded-xl transition-colors shadow-sm"
          >
            Commencer
            <ArrowRight size={16} />
          </Link>
          <Link
            href="/results"
            className="inline-flex items-center gap-2 px-6 py-3 bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 font-medium rounded-xl transition-colors shadow-sm border border-zinc-200 dark:border-zinc-700 hover:border-zinc-300 dark:hover:border-zinc-600"
          >
            Voir un exemple
          </Link>
        </div>
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {FEATURES.map((f, i) => (
          <div
            key={f.title}
            className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-sm hover:shadow-md hover:border-zinc-300 dark:hover:border-zinc-700 transition-all duration-200 animate-fade-in"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-4">
              <f.icon size={20} />
            </div>
            <h3 className="font-semibold text-zinc-900 dark:text-white mb-2 tracking-tight">{f.title}</h3>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>

      {/* Trust badge */}
      <div className="mt-16 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-zinc-100 dark:bg-zinc-800 rounded-full text-sm text-zinc-600 dark:text-zinc-400">
          <Sparkles size={14} className="text-amber-500" />
          <span>Propulsé par Google OR-Tools & Claude AI</span>
        </div>
      </div>
    </div>
  )
}
