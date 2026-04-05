import type { Metadata } from 'next'
import './globals.css'
import ClientLayout from '@/components/ClientLayout'

export const metadata: Metadata = {
  title: 'TIMEASE — Générateur d\'emploi du temps',
  description: 'Générateur d\'emplois du temps pour écoles privées francophones.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body className="bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 antialiased">
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  )
}
