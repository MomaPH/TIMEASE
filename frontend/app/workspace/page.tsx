'use client'
import { useState, useEffect, useRef, useCallback } from 'react'
import { Paperclip, Send, Loader2, Bot, MessageSquare, LayoutDashboard, RotateCcw } from 'lucide-react'
import { useRouter } from 'next/navigation'
import ChatMessage from '@/components/ChatMessage'
import StepIndicator from '@/components/StepIndicator'
import StepPanel from '@/components/StepPanel'
import FileImportModal from '@/components/FileImportModal'
import { useSession } from '@/hooks/useSession'
import { useToast } from '@/components/Toast'
import { sendChatStream, uploadFile, solve } from '@/lib/api'
import type { ChatMessage as ChatMessageType, SchoolData } from '@/lib/types'

// ── Constants ─────────────────────────────────────────────────────────────────

const WELCOME: ChatMessageType = {
  role: 'ai',
  content:
    "Bonjour ! Je suis TIMEASE, votre assistant pour créer des emplois du temps scolaires.\n\n" +
    "Je peux vous guider étape par étape, analyser vos fichiers Excel ou répondre à toutes vos questions. " +
    "Pour commencer : **quel est le nom de votre école ?**",
}

const msgs_key  = (sid: string) => `timease_messages_${sid}`
const hist_key  = (sid: string) => `timease_aihistory_${sid}`

// ── Workspace page ────────────────────────────────────────────────────────────

export default function WorkspacePage() {
  const router = useRouter()
  const { toast } = useToast()

  const {
    sessionId,
    schoolData,
    assignments,
    setTimetable,
    updateSchoolData,
    updateAssignments,
    refreshSession,
    resetSession,
  } = useSession()

  // ── Step state ────────────────────────────────────────────────────────────
  const [currentStep, setCurrentStep] = useState(0)
  const [mobileView, setMobileView]   = useState<'chat' | 'form'>('chat')

  // ── Chat state ────────────────────────────────────────────────────────────
  const [messages,   setMessages]   = useState<ChatMessageType[]>([WELCOME])
  const [aiHistory,  setAiHistory]  = useState<any[]>([])
  const [input,      setInput]      = useState('')
  const [isLoading,  setIsLoading]  = useState(false)
  const [isSolving,  setIsSolving]  = useState(false)

  // ── Import modal ──────────────────────────────────────────────────────────
  const [importModal, setImportModal] = useState<{ open: boolean; data?: any }>({ open: false })

  const scrollRef = useRef<HTMLDivElement>(null)
  const fileRef   = useRef<HTMLInputElement>(null)

  // ── Restore messages and history from localStorage once sessionId is known
  useEffect(() => {
    if (!sessionId) return
    const storedMsgs = localStorage.getItem(msgs_key(sessionId))
    const storedHist = localStorage.getItem(hist_key(sessionId))
    if (storedMsgs) {
      try { setMessages(JSON.parse(storedMsgs)) } catch {}
    }
    if (storedHist) {
      try { setAiHistory(JSON.parse(storedHist)) } catch {}
    }
  }, [sessionId])

  // ── Auto-scroll ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isLoading])

  // ── Message helpers ───────────────────────────────────────────────────────
  const addMessage = useCallback((msg: ChatMessageType) => {
    setMessages(prev => {
      const next = [...prev, msg]
      if (sessionId) localStorage.setItem(msgs_key(sessionId), JSON.stringify(next))
      return next
    })
  }, [sessionId])

  const saveHistory = useCallback((history: any[]) => {
    setAiHistory(history)
    if (sessionId) localStorage.setItem(hist_key(sessionId), JSON.stringify(history))
  }, [sessionId])

  // ── Streaming send helper ─────────────────────────────────────────────────
  async function _streamSend(msg: string, fileContent?: string) {
    // Append a placeholder AI message that we'll fill in as tokens arrive
    const streamingId = Date.now().toString()
    setMessages(prev => {
      const next = [...prev, { role: 'ai' as const, content: '', _streamingId: streamingId } as any]
      if (sessionId) localStorage.setItem(msgs_key(sessionId), JSON.stringify(next))
      return next
    })

    const res = await sendChatStream(
      sessionId!,
      msg,
      fileContent,
      aiHistory,
      // onDelta: append text to the streaming message
      (text) => {
        setMessages(prev => {
          const next = prev.map(m =>
            (m as any)._streamingId === streamingId
              ? { ...m, content: m.content + text }
              : m,
          )
          if (sessionId) localStorage.setItem(msgs_key(sessionId), JSON.stringify(next))
          return next
        })
      },
      // onToolStart: no UI change needed
      (_name) => {},
    )

    // Finalize the streaming message with metadata
    saveHistory(res.ai_history || [])
    setMessages(prev => {
      const next = prev.map(m => {
        if ((m as any)._streamingId !== streamingId) return m
        const { _streamingId: _, ...rest } = m as any
        return {
          ...rest,
          dataSaved:  res.data_saved,
          savedTypes: res.saved_types,
          options:    res.options?.length ? res.options : undefined,
        }
      })
      if (sessionId) localStorage.setItem(msgs_key(sessionId), JSON.stringify(next))
      return next
    })

    if (res.data_saved)              refreshSession()
    if (typeof res.set_step === 'number') setCurrentStep(res.set_step)
    if (res.trigger_generation)      handleGenerate()
  }

  // ── Send message ──────────────────────────────────────────────────────────
  async function send(text?: string) {
    const msg = (text ?? input).trim()
    if (!msg || isLoading || !sessionId) return

    addMessage({ role: 'user', content: msg })
    setInput('')
    setIsLoading(true)

    try {
      await _streamSend(msg)
    } catch {
      addMessage({ role: 'ai', content: 'Impossible de contacter le serveur. Vérifiez que le backend est lancé.' })
      toast('Connexion au serveur perdue', 'error')
    } finally {
      setIsLoading(false)
    }
  }

  // ── File upload ───────────────────────────────────────────────────────────
  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !sessionId) return
    e.target.value = ''

    addMessage({ role: 'user', content: `📎 ${file.name}` })
    setIsLoading(true)

    try {
      const res = await uploadFile(sessionId, file)

      if (res.type === 'direct_import') {
        refreshSession()
        setImportModal({ open: true, data: res })
        toast('Fichier importé avec succès')
      } else if (res.type === 'text_extract') {
        // Send extracted text to AI for processing via streaming
        await _streamSend('Analyse ce fichier et enregistre les données.', res.content)
        toast('Fichier traité par l\'assistant')
      } else {
        addMessage({ role: 'ai', content: 'Je n\'ai pas pu lire ce fichier. Essayez un autre format (xlsx, pdf, docx, csv, txt).' })
      }
    } catch {
      addMessage({ role: 'ai', content: 'Erreur lors du traitement du fichier.' })
      toast('Erreur lors de l\'upload', 'error')
    } finally {
      setIsLoading(false)
    }
  }

  // ── Direct data edits (from StepPanel forms) ──────────────────────────────
  async function handleUpdateSchoolData(newData: SchoolData) {
    await updateSchoolData(newData)
  }

  async function handleUpdateAssignments(newAssignments: any[]) {
    await updateAssignments(newAssignments)
  }

  // ── Generate timetable ────────────────────────────────────────────────────
  async function handleGenerate() {
    if (!sessionId || isSolving) return
    setIsSolving(true)
    setCurrentStep(8)

    addMessage({
      role:    'ai',
      content: '⚙️ **Génération en cours…**\n\nLe solveur analyse vos contraintes. Cela peut prendre quelques secondes.',
    })

    try {
      const res = await solve(sessionId)

      if (res.status === 'OPTIMAL' || res.status === 'FEASIBLE' || res.status === 'PARTIAL') {
        setTimetable(res)
        toast('Emploi du temps généré !')

        const partial = res.status === 'PARTIAL'
        addMessage({
          role:    'ai',
          content: partial
            ? `✅ **Emploi du temps partiellement généré** (${res.assignments?.length ?? 0} sessions placées).\n\nCertaines sessions n'ont pas pu être planifiées. Consultez les résultats pour les détails.`
            : `✅ **Emploi du temps généré avec succès !** (${res.assignments?.length ?? 0} sessions planifiées)\n\nRedirection vers les résultats…`,
        })

        setTimeout(() => router.push('/results'), 1200)
      } else {
        const summary = res.conflict_summary || res.message || 'Aucune solution trouvée.'
        addMessage({
          role:    'ai',
          content: `❌ **Génération impossible**\n\n${summary}\n\n---\nCorrigez les problèmes ci-dessus et relancez la génération.`,
        })
        toast('Impossible de générer l\'emploi du temps', 'error')
      }
    } catch {
      addMessage({ role: 'ai', content: '❌ Erreur de connexion lors de la génération.' })
      toast('Erreur de connexion', 'error')
    } finally {
      setIsSolving(false)
    }
  }

  // ── Reset session ─────────────────────────────────────────────────────────
  async function handleReset() {
    if (!confirm('Réinitialiser la session ? Toutes les données seront perdues.')) return
    await resetSession()
    setMessages([WELCOME])
    setAiHistory([])
    setCurrentStep(0)
    toast('Session réinitialisée')
  }

  // ── Next step ─────────────────────────────────────────────────────────────
  function handleNext() {
    setCurrentStep(s => Math.min(s + 1, 8))
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 0px)' }}>

      {/* ── Mobile top bar ── */}
      <div className="md:hidden flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex-shrink-0">
        <h1 className="font-semibold text-sm text-gray-800 dark:text-gray-200">Espace de travail</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setMobileView('chat')}
            className={`flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg transition-colors ${mobileView === 'chat' ? 'bg-teal-600 text-white' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}`}
          >
            <MessageSquare size={13} /> Chat
          </button>
          <button
            onClick={() => setMobileView('form')}
            className={`flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg transition-colors ${mobileView === 'form' ? 'bg-teal-600 text-white' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}`}
          >
            <LayoutDashboard size={13} /> Données
          </button>
        </div>
      </div>

      {/* ── Main content ── */}
      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* ── Chat column ── */}
        <div className={`flex flex-col bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 ${mobileView === 'form' ? 'hidden md:flex' : 'flex'} w-full md:w-[55%]`}>

          {/* Desktop chat header */}
          <div className="hidden md:flex items-center justify-between px-5 py-3 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-teal-100 dark:bg-teal-900/40 flex items-center justify-center">
                <Bot size={14} className="text-teal-600 dark:text-teal-400" />
              </div>
              <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">TIMEASE Assistant</span>
              <span className="text-xs text-gray-400 dark:text-gray-500">· claude-haiku</span>
            </div>
            <button
              onClick={handleReset}
              title="Nouvelle session"
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <RotateCcw size={13} /> Réinitialiser
            </button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 sm:px-5 py-4">
            {messages.map((msg, i) => (
              <ChatMessage
                key={i}
                message={msg}
                onOptionSelect={(value) => send(value)}
              />
            ))}

            {/* Typing indicator */}
            {isLoading && (
              <div className="flex justify-start mb-3 animate-fade-in">
                <div className="w-7 h-7 rounded-full bg-teal-100 dark:bg-teal-900/40 flex items-center justify-center mr-2 mt-0.5 flex-shrink-0">
                  <Bot size={14} className="text-teal-600 dark:text-teal-400" />
                </div>
                <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-2xl rounded-tl-sm flex gap-1.5 items-center shadow-sm">
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

          {/* Input bar */}
          <div className="flex items-center gap-2 px-3 sm:px-4 py-3 border-t border-gray-100 dark:border-gray-800 flex-shrink-0">
            <button
              onClick={() => fileRef.current?.click()}
              title="Envoyer un fichier"
              disabled={isLoading || !sessionId}
              className="text-gray-400 hover:text-teal-600 dark:hover:text-teal-400 flex-shrink-0 transition-colors p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50"
            >
              <Paperclip size={17} />
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
              placeholder={sessionId ? 'Message…' : 'Chargement…'}
              disabled={isLoading || !sessionId}
              className="flex-1 px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:bg-white dark:focus:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 disabled:opacity-60 transition-all"
            />
            <button
              onClick={() => send()}
              disabled={isLoading || !input.trim() || !sessionId}
              className="p-2 rounded-xl bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-40 transition-colors flex-shrink-0"
            >
              {isLoading
                ? <Loader2 size={16} className="animate-spin" />
                : <Send size={16} />
              }
            </button>
          </div>
        </div>

        {/* ── Right panel: Step indicator + form ── */}
        <div className={`flex flex-col bg-gray-50 dark:bg-gray-900/50 ${mobileView === 'chat' ? 'hidden md:flex' : 'flex'} w-full md:w-[45%]`}>
          <StepIndicator
            currentStep={currentStep}
            schoolData={schoolData}
            assignments={assignments}
            onStepClick={setCurrentStep}
          />
          <div className="flex-1 min-h-0">
            <StepPanel
              step={currentStep}
              schoolData={schoolData}
              assignments={assignments}
              onUpdateSchoolData={handleUpdateSchoolData}
              onUpdateAssignments={handleUpdateAssignments}
              onNext={handleNext}
              onGenerate={handleGenerate}
              isSolving={isSolving}
            />
          </div>
        </div>
      </div>

      {/* ── File import modal ── */}
      {importModal.open && importModal.data && (
        <FileImportModal
          data={importModal.data}
          onClose={() => setImportModal({ open: false })}
          onContinue={(stepIdx) => {
            setCurrentStep(stepIdx)
            setMobileView('form')
          }}
        />
      )}
    </div>
  )
}
