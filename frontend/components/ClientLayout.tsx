'use client'
import { useState } from 'react'
import { Menu } from 'lucide-react'
import Sidebar from './Sidebar'
import { ToastProvider } from './Toast'

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <ToastProvider>
      {/* ── Mobile top bar (hidden on md+) ─────────────────────────────── */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-30 h-14 bg-white dark:bg-gray-950 border-b border-gray-200 dark:border-gray-800 flex items-center px-4 gap-3">
        <button
          onClick={() => setMobileOpen(true)}
          className="p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          aria-label="Ouvrir le menu"
        >
          <Menu size={20} />
        </button>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-teal-600 text-white flex items-center justify-center text-xs font-bold select-none">
            T
          </div>
          <span className="font-semibold text-gray-900 dark:text-white text-base">TIMEASE</span>
        </div>
      </div>

      {/* ── Mobile backdrop ─────────────────────────────────────────────── */}
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/40 animate-fade-in-fast"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <Sidebar mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />

      {/* ── Page content ────────────────────────────────────────────────── */}
      <main className="md:ml-60 min-h-screen pt-14 md:pt-0 p-4 sm:p-6 md:p-8">
        {children}
      </main>
    </ToastProvider>
  )
}
