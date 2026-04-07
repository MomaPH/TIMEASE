'use client'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { LayoutDashboard, Table2, Users, Home, Sun, Moon, X, Download, MessageSquare, Calendar } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useState, useEffect } from 'react'

const NAV_MAIN = [
  { href: '/',              label: 'Accueil',           icon: Home },
  { href: '/workspace',     label: 'Espace de travail', icon: LayoutDashboard },
  { href: '/results',       label: 'Emploi du temps',   icon: Calendar },
]

const NAV_TOOLS = [
  { href: '/exports',       label: 'Exports',       icon: Download },
  { href: '/collaboration', label: 'Collaboration', icon: Users },
]

interface Props {
  mobileOpen: boolean
  onMobileClose: () => void
}

export default function Sidebar({ mobileOpen, onMobileClose }: Props) {
  const path = usePathname()
  const { theme, setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => setMounted(true), [])

  const isDark = mounted && resolvedTheme === 'dark'

  function toggleDark() {
    setTheme(isDark ? 'light' : 'dark')
  }

  const isActive = (href: string) => {
    if (href.includes('#')) {
      return path === href.split('#')[0]
    }
    return path === href || (href !== '/' && path.startsWith(href))
  }

  return (
    <aside
      className={[
        'fixed top-0 left-0 h-screen w-60 z-50',
        'flex flex-col p-4',
        'bg-[#09090b]',
        'transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]',
        mobileOpen ? 'translate-x-0' : '-translate-x-full',
        'md:translate-x-0',
      ].join(' ')}
      aria-label="Navigation principale"
    >
      {/* ── Brand ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-3 py-2 mb-4">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
          <svg viewBox="0 0 24 24" className="w-[18px] h-[18px] fill-white">
            <path d="M19 4H5a2 2 0 00-2 2v12a2 2 0 002 2h14a2 2 0 002-2V6a2 2 0 00-2-2zm0 14H5V8h14v10z"/>
          </svg>
        </div>
        <span className="font-semibold text-white text-[15px] flex-1 truncate tracking-tight">
          TIMEASE
        </span>
        <button
          onClick={onMobileClose}
          className="md:hidden p-1 rounded-lg text-zinc-500 hover:bg-white/5 hover:text-zinc-300 transition-colors"
          aria-label="Fermer le menu"
        >
          <X size={16} />
        </button>
      </div>

      {/* ── Main Navigation ────────────────────────────────────────────────── */}
      <nav className="flex-1 flex flex-col gap-0.5" aria-label="Pages">
        {NAV_MAIN.map(n => {
          const active = isActive(n.href)
          return (
            <Link
              key={n.href}
              href={n.href}
              onClick={onMobileClose}
              className={[
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150',
                active
                  ? 'text-white bg-white/10'
                  : 'text-zinc-400 hover:text-white hover:bg-white/[0.06]',
              ].join(' ')}
            >
              <n.icon size={18} className={active ? 'opacity-100' : 'opacity-70'} />
              <span className="truncate">{n.label}</span>
            </Link>
          )
        })}

        {/* ── Section: Outils ────────────────────────────────────────────────── */}
        <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500 px-3 pt-6 pb-2">
          Outils
        </div>

        {NAV_TOOLS.map(n => {
          const active = isActive(n.href)
          return (
            <Link
              key={n.href}
              href={n.href}
              onClick={onMobileClose}
              className={[
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150',
                active
                  ? 'text-white bg-white/10'
                  : 'text-zinc-400 hover:text-white hover:bg-white/[0.06]',
              ].join(' ')}
            >
              <n.icon size={18} className={active ? 'opacity-100' : 'opacity-70'} />
              <span className="truncate">{n.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* ── Dark mode toggle ──────────────────────────────────────────────── */}
      <button
        onClick={toggleDark}
        className="flex items-center gap-3 px-3 py-2 text-zinc-400 text-sm font-medium hover:bg-white/[0.06] hover:text-zinc-200 rounded-lg transition-all duration-150 w-full"
        aria-label={isDark ? 'Passer en mode clair' : 'Passer en mode sombre'}
      >
        {isDark ? <Sun size={16} /> : <Moon size={16} />}
        <span>{mounted ? (isDark ? 'Mode clair' : 'Mode sombre') : '...'}</span>
      </button>
    </aside>
  )
}
