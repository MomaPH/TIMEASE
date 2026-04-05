'use client'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { LayoutDashboard, Table2, Users, Home, Sun, Moon, X } from 'lucide-react'
import { useState, useEffect } from 'react'

const NAV = [
  { href: '/',              label: 'Accueil',           icon: Home },
  { href: '/workspace',     label: 'Espace de travail', icon: LayoutDashboard },
  { href: '/results',       label: 'Résultats',         icon: Table2 },
  { href: '/collaboration', label: 'Collaboration',     icon: Users },
]

interface Props {
  mobileOpen: boolean
  onMobileClose: () => void
}

export default function Sidebar({ mobileOpen, onMobileClose }: Props) {
  const path = usePathname()
  const [dark, setDark] = useState(false)

  // Pick up any class already on <html> (e.g. set by system preference or previous toggle)
  useEffect(() => {
    setDark(document.documentElement.classList.contains('dark'))
  }, [])

  function toggleDark() {
    const next = !dark
    setDark(next)
    document.documentElement.classList.toggle('dark', next)
  }

  return (
    <aside
      className={[
        // Layout
        'fixed top-0 left-0 h-screen w-60 z-50',
        'flex flex-col p-3',
        // Colours
        'bg-white dark:bg-gray-950',
        'border-r border-gray-200 dark:border-gray-800',
        // Mobile slide animation; always visible on md+
        'transition-transform duration-300 ease-in-out',
        mobileOpen ? 'translate-x-0' : '-translate-x-full',
        'md:translate-x-0',
      ].join(' ')}
      aria-label="Navigation principale"
    >
      {/* ── Logo row ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 px-3 py-2 mb-4">
        <div className="w-9 h-9 rounded-full bg-teal-600 text-white flex items-center justify-center font-bold text-sm flex-shrink-0 select-none">
          T
        </div>
        <span className="font-semibold text-gray-900 dark:text-white text-lg flex-1 truncate">
          TIMEASE
        </span>
        {/* Close button — mobile only */}
        <button
          onClick={onMobileClose}
          className="md:hidden p-1 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          aria-label="Fermer le menu"
        >
          <X size={16} />
        </button>
      </div>

      {/* ── Navigation ────────────────────────────────────────────────────── */}
      <nav className="flex-1 flex flex-col gap-1" aria-label="Pages">
        {NAV.map(n => {
          const active =
            path === n.href || (n.href !== '/' && path.startsWith(n.href))
          return (
            <Link
              key={n.href}
              href={n.href}
              onClick={onMobileClose}
              className={[
                'flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-colors',
                active
                  ? 'bg-teal-50 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300 font-medium'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-200',
              ].join(' ')}
            >
              <n.icon size={18} className="flex-shrink-0" />
              <span className="truncate">{n.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* ── Dark mode toggle ──────────────────────────────────────────────── */}
      <button
        onClick={toggleDark}
        className="flex items-center gap-2 px-3 py-2.5 text-gray-500 dark:text-gray-400 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-700 dark:hover:text-gray-200 rounded-lg transition-colors w-full"
        aria-label={dark ? 'Passer en mode clair' : 'Passer en mode sombre'}
      >
        {dark ? <Sun size={16} className="flex-shrink-0" /> : <Moon size={16} className="flex-shrink-0" />}
        <span>{dark ? 'Mode clair' : 'Mode sombre'}</span>
      </button>
    </aside>
  )
}
