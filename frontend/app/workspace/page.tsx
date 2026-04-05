'use client'
import { useState, useEffect, useRef } from 'react'
import { Paperclip, Send, Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import ChatMessage from '@/components/ChatMessage'
import QuickReplies from '@/components/QuickReplies'
import DataPanel from '@/components/DataPanel'
import { useSession } from '@/hooks/useSession'
import { useToast } from '@/components/Toast'
import { sendChat, uploadFile, mergeData, solve } from '@/lib/api'
import type { ChatMessage as ChatMessageType, ToolCall } from '@/lib/types'

const WELCOME: ChatMessageType = {
  role: 'ai',
  content:
    "Bienvenue sur TIMEASE ! Je suis votre assistant pour créer l'emploi du temps. On commence ? Comment s'appelle votre école ?",
  quickReplies: ["Mon école s'appelle...", 'Voici mon fichier Excel', "J'ai besoin d'aide"],
}

// ── Skeleton placeholders while session initialises ──────────────────────────
function SkeletonPanel() {
  return (
    <div className="flex flex-col gap-3 p-5 animate-pulse">
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
      <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded w-full mt-1" />
      {[...Array(4)].map((_, i) => (
        <div key={i} className="h-10 bg-gray-100 dark:bg-gray-800 rounded-lg" />
      ))}
    </div>
  )
}

export default function WorkspacePage() {
  const router        = useRouter()
  const { toast }     = useToast()
  const { sessionId, schoolData, assignments, refreshSession } = useSession()

  const [messages, setMessages]           = useState<ChatMessageType[]>([WELCOME])
  const [input, setInput]                 = useState('')
  const [isLoading, setIsLoading]         = useState(false)
  const [pendingToolCalls, setPendingToolCalls] = useState<ToolCall[]>([])
  const [isSolving, setIsSolving]         = useState(false)

  const scrollRef = useRef<HTMLDivElement>(null)
  const fileRef   = useRef<HTMLInputElement>(null)

  // Auto-scroll to newest message
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  // Latest AI message quick replies shown at bottom as chips
  const lastAiReplies =
    [...messages].reverse().find(m => m.role === 'ai')?.quickReplies ?? []

  // ── Helpers ────────────────────────────────────────────────────────────────
  function appendAiResponse(res: any) {
    if (res.tool_calls?.length) {
      const summary = JSON.stringify(
        Object.fromEntries(res.tool_calls.map((tc: ToolCall) => [tc.name, tc.data])),
        null,
        2,
      )
      setPendingToolCalls(res.tool_calls)
      setMessages(prev => [
        ...prev,
        { role: 'confirm', content: summary, toolCalls: res.tool_calls },
      ])
    } else {
      setMessages(prev => [
        ...prev,
        {
          role: 'ai',
          content:      res.message ?? res.message_fr ?? '',
          quickReplies: res.quick_replies ?? [],
        },
      ])
    }
  }

  function addError(text: string) {
    setMessages(prev => [...prev, { role: 'ai', content: text }])
  }

  // ── Send message ───────────────────────────────────────────────────────────
  async function send(text?: string) {
    const msg = (text ?? input).trim()
    if (!msg || isLoading || !sessionId) return

    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setInput('')
    setIsLoading(true)

    try {
      const res = await sendChat(sessionId, msg)
      appendAiResponse(res)
    } catch {
      toast('Connexion au serveur perdue', 'error')
      addError('Impossible de contacter le serveur. Vérifiez que le backend est lancé.')
    } finally {
      setIsLoading(false)
    }
  }

  // ── File upload ────────────────────────────────────────────────────────────
  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !sessionId) return
    e.target.value = ''

    setMessages(prev => [...prev, { role: 'user', content: `📎 ${file.name}` }])
    setIsLoading(true)

    try {
      const res = await uploadFile(sessionId, file)

      if (res.type === 'direct_import') {
        const d      = res.school_data ?? {}
        const parts  = ['Fichier importé !']
        if (d.teachers?.length)  parts.push(`${d.teachers.length} enseignant(s)`)
        if (d.classes?.length)   parts.push(`${d.classes.length} classe(s)`)
        if (d.rooms?.length)     parts.push(`${d.rooms.length} salle(s)`)
        if (d.curriculum?.length) parts.push(`${d.curriculum.length} entrée(s) de programme`)

        setMessages(prev => [
          ...prev,
          {
            role: 'ai',
            content: parts.join(' · '),
            quickReplies: ['Parfait !', 'Modifier les données', 'Générer maintenant'],
          },
        ])
        toast('Fichier importé avec succès')
        refreshSession()
      } else if (res.type === 'text_extract') {
        const chatRes = await sendChat(sessionId, 'Analyse ce fichier', res.content)
        appendAiResponse(chatRes)
        toast('Fichier importé avec succès')
      } else {
        addError("Format de fichier non reconnu.")
      }
    } catch {
      toast('Erreur lors de l\'upload', 'error')
      addError('Impossible de traiter ce fichier.')
    } finally {
      setIsLoading(false)
    }
  }

  // ── Confirm tool calls ─────────────────────────────────────────────────────
  async function handleConfirm() {
    if (!sessionId || !pendingToolCalls.length) return

    try {
      for (const tc of pendingToolCalls) {
        await mergeData(sessionId, tc.name, tc.data)
      }
      setPendingToolCalls([])
      setMessages(prev => [
        ...prev,
        {
          role: 'ai',
          content: 'Données enregistrées !',
          quickReplies: ['Ajouter des enseignants', 'Configurer les classes', 'Continuer'],
        },
      ])
      toast('Données enregistrées')
      refreshSession()
    } catch {
      toast('Erreur lors de la sauvegarde', 'error')
    }
  }

  function handleReject() {
    setPendingToolCalls([])
    setMessages(prev => [
      ...prev,
      { role: 'ai', content: "D'accord, corrigez-moi.", quickReplies: [] },
    ])
  }

  // ── Generate timetable ─────────────────────────────────────────────────────
  async function handleGenerate() {
    if (!sessionId || isSolving) return
    setIsSolving(true)
    setMessages(prev => [
      ...prev,
      { role: 'ai', content: 'Résolution en cours… Cela peut prendre quelques secondes.' },
    ])

    try {
      const res = await solve(sessionId)
      if (res.status === 'OPTIMAL' || res.status === 'FEASIBLE') {
        toast('Emploi du temps généré !')
        router.push('/results')
      } else {
        const reason = res.status ?? 'erreur inconnue'
        addError(`Impossible de générer l'emploi du temps (${reason}). Vérifiez vos contraintes.`)
        toast(`Échec de la résolution : ${reason}`, 'error')
      }
    } catch {
      toast('Connexion au serveur perdue', 'error')
      addError('Erreur de connexion lors de la génération.')
    } finally {
      setIsSolving(false)
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <div className="mb-4 flex-shrink-0">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Espace de travail</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          Configurez les données de votre école via le chat
        </p>
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* ── Chat column (60%) ── */}
        <div className="flex flex-col flex-[3] min-w-0 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm overflow-hidden">

          {/* Message area */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-5 py-5">
            {messages.map((msg, i) => (
              <ChatMessage
                key={i}
                message={msg}
                onConfirm={msg.role === 'confirm' ? handleConfirm : undefined}
                onReject={msg.role  === 'confirm' ? handleReject  : undefined}
              />
            ))}

            {/* Typing indicator */}
            {isLoading && (
              <div className="flex justify-start mb-3 animate-fade-in">
                <div className="bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-2xl rounded-tl-sm flex gap-1.5 items-center">
                  {[0, 150, 300].map(delay => (
                    <span
                      key={delay}
                      className="w-1.5 h-1.5 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce"
                      style={{ animationDelay: `${delay}ms` }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Bottom quick-reply chips */}
          {lastAiReplies.length > 0 && !isLoading && (
            <div className="px-4 sm:px-5 pb-2 pt-1 flex flex-wrap gap-2">
              <QuickReplies replies={lastAiReplies} onSelect={send} />
            </div>
          )}

          {/* Input bar */}
          <div className="flex items-center gap-2 px-3 sm:px-4 py-3 border-t border-gray-200 dark:border-gray-800">
            <button
              onClick={() => fileRef.current?.click()}
              title="Envoyer un fichier (.xlsx, .xls, .csv, .docx, .txt, .pdf)"
              className="text-gray-400 hover:text-teal-600 dark:hover:text-teal-400 flex-shrink-0 transition-colors p-1"
              disabled={isLoading}
            >
              <Paperclip size={18} />
            </button>
            <input
              type="file"
              ref={fileRef}
              className="hidden"
              accept=".xlsx,.xls,.csv,.docx,.txt,.pdf"
              onChange={handleUpload}
            />
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
              placeholder="Décrivez votre école ou envoyez un fichier..."
              disabled={isLoading}
              className="flex-1 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 disabled:opacity-60 transition-opacity"
            />
            <button
              onClick={() => send()}
              disabled={isLoading || !input.trim()}
              className="p-2 rounded-lg bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-50 transition-colors flex-shrink-0"
            >
              {isLoading
                ? <Loader2 size={16} className="animate-spin" />
                : <Send size={16} />
              }
            </button>
          </div>
        </div>

        {/* ── Data panel (40%) — hidden on mobile, shown md+ ── */}
        <div className="hidden md:flex flex-[2] bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm overflow-hidden flex-col">
          {!sessionId
            ? <SkeletonPanel />
            : (
              <div className="p-5 flex-1 flex flex-col overflow-hidden">
                <DataPanel
                  data={schoolData}
                  assignments={assignments}
                  onGenerate={handleGenerate}
                  isSolving={isSolving}
                />
              </div>
            )
          }
        </div>
      </div>
    </div>
  )
}
