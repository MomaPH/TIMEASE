'use client'
import { useState, useEffect, useRef, useCallback, Suspense } from 'react'
import { Bot, MessageSquare, LayoutDashboard, RotateCcw, CheckCircle, XCircle, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'
import ChatMessage from '@/components/ChatMessage'
import ChatInput from '@/components/ChatInput'
import AgentActionPill from '@/components/AgentActionPill'
import StepIndicator from '@/components/StepIndicator'
import StepPanel from '@/components/StepPanel'
import FileImportModal from '@/components/FileImportModal'
import { useSession } from '@/hooks/useSession'
import { useToast } from '@/components/Toast'
import { sendChatStream, uploadFile, solve, applyPending } from '@/lib/api'
import type { ChatMessage as ChatMessageType, PendingChange, SchoolData } from '@/lib/types'

// ── Thinking words (cycling while AI is loading) ──────────────────────────────
const THINKING_WORDS = [
  'Réflexion', 'Inspiration', 'Analyse', 'Curiosité', 'Élaboration',
  'Imagination', 'Perspicacité', 'Contemplation', 'Créativité', 'Ingéniosité',
  'Illumination', 'Discernement', 'Intuition', 'Précision', 'Sagacité',
  'Concentration', 'Synthèse', 'Clairvoyance', 'Perspicacité', 'Équilibre',
]

function ThinkingWord() {
  const [idx, setIdx] = useState(() => Math.floor(Math.random() * THINKING_WORDS.length))
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const interval = setInterval(() => {
      setVisible(false)
      setTimeout(() => {
        setIdx(i => (i + 1) % THINKING_WORDS.length)
        setVisible(true)
      }, 300)
    }, 1800)
    return () => clearInterval(interval)
  }, [])

  return (
    <span
      className="text-sm text-teal-600 dark:text-teal-400 font-medium italic transition-opacity duration-300"
      style={{ opacity: visible ? 1 : 0 }}
    >
      {THINKING_WORDS[idx]}…
    </span>
  )
}

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

function WorkspaceContent() {
  const router       = useRouter()
  const searchParams = useSearchParams()
  const { toast }    = useToast()

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
  const [messages,         setMessages]         = useState<ChatMessageType[]>([WELCOME])
  const [aiHistory,        setAiHistory]        = useState<any[]>([])
  const [input,            setInput]            = useState('')
  const [isLoading,        setIsLoading]        = useState(false)
  const [isSolving,        setIsSolving]        = useState(false)
  const [pendingChanges,   setPendingChanges]   = useState<PendingChange[]>([])
  const [activeTool,       setActiveTool]       = useState<string | null>(null)
  const [isStreamInterrupted, setIsStreamInterrupted] = useState(false)
  const [expandedPreviews, setExpandedPreviews] = useState<Set<number>>(new Set())
  const transientIdRef = useRef<string | null>(null)
  const streamAbortRef = useRef<AbortController | null>(null)

  // ── Import modal ──────────────────────────────────────────────────────────
  const [importModal, setImportModal] = useState<{ open: boolean; data?: any }>({ open: false })

  const scrollRef = useRef<HTMLDivElement>(null)

  // ── Restore messages + history; honour ?step= param ─────────────────────
  useEffect(() => {
    if (!sessionId) return
    const storedMsgs = localStorage.getItem(msgs_key(sessionId))
    const storedHist = localStorage.getItem(hist_key(sessionId))
    if (storedMsgs) { try { setMessages(JSON.parse(storedMsgs)) } catch {} }
    if (storedHist)  { try { setAiHistory(JSON.parse(storedHist)) } catch {} }
    const stepParam = searchParams.get('step')
    if (stepParam !== null) {
      const idx = parseInt(stepParam, 10)
      if (!isNaN(idx) && idx >= 0 && idx <= 8) setCurrentStep(idx)
    }
  }, [sessionId]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Auto-scroll with smooth behavior ──────────────────────────────────────
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      })
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

  // ── Transient (fugace) message helpers ────────────────────────────────────
  // A transient message is a temporary placeholder that gets replaced in-place
  // by the actual result, so it never accumulates in the history.
  function addTransientMessage(content: string): string {
    const id = `t_${Date.now()}`
    transientIdRef.current = id
    setMessages(prev => [...prev, { role: 'ai' as const, content, _transientId: id } as any])
    return id
  }

  function replaceTransientMessage(id: string, msg: ChatMessageType) {
    transientIdRef.current = null
    setMessages(prev => {
      const next = prev.map(m => (m as any)._transientId === id ? msg : m)
      if (sessionId) localStorage.setItem(msgs_key(sessionId), JSON.stringify(next))
      return next
    })
  }

  function removeTransientMessage(id: string) {
    transientIdRef.current = null
    setMessages(prev => prev.filter(m => (m as any)._transientId !== id))
  }

  // ── Streaming send helper ─────────────────────────────────────────────────
  async function _streamSend(msg: string, fileContent?: string) {
    streamAbortRef.current?.abort()
    const controller = new AbortController()
    streamAbortRef.current = controller
    setIsStreamInterrupted(false)

    // Append a placeholder AI message that we'll fill in as tokens arrive
    const streamingId = Date.now().toString()
    setMessages(prev => {
      const next = [...prev, { role: 'ai' as const, content: '', _streamingId: streamingId } as any]
      if (sessionId) localStorage.setItem(msgs_key(sessionId), JSON.stringify(next))
      return next
    })

    const removeStreamingMsg = () => {
      setMessages(prev => {
        const next = prev.filter(m => (m as any)._streamingId !== streamingId)
        if (sessionId) localStorage.setItem(msgs_key(sessionId), JSON.stringify(next))
        return next
      })
    }

    let res: Awaited<ReturnType<typeof sendChatStream>>
    try {
      res = await sendChatStream(
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
        // onToolStart: show active tool pill
        (name) => setActiveTool(name),
        controller.signal,
      )
    } catch (err) {
      removeStreamingMsg()
      setActiveTool(null)
      if (err instanceof DOMException && err.name === 'AbortError') {
        setIsStreamInterrupted(true)
        return
      }
      throw err
    } finally {
      if (streamAbortRef.current === controller) {
        streamAbortRef.current = null
      }
    }

    // Clear tool pill when streaming completes
    setActiveTool(null)

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

    if (res.pending_changes?.length) {
      setPendingChanges(res.pending_changes)
      setExpandedPreviews(new Set())
    }
    if (res.data_saved)                  await refreshSession()
    if (typeof res.set_step === 'number') setCurrentStep(res.set_step)
    if (res.trigger_generation)          handleGenerate()
  }

  // ── Staging: apply or reject pending AI changes ───────────────────────────
  async function handleApply() {
    if (!sessionId || !pendingChanges.length) return
    const count = pendingChanges.length
    try {
      await applyPending(sessionId, true)
      setPendingChanges([])
      await refreshSession()   // await so form is populated before message appears
      addMessage({ role: 'ai', content: `✅ **${count} modification(s) appliquée(s).** Les données ont été enregistrées.` })
    } catch {
      toast('Erreur lors de l\'application des modifications', 'error')
    }
  }

  async function handleReject() {
    if (!sessionId || !pendingChanges.length) return
    try {
      await applyPending(sessionId, false)
      setPendingChanges([])
      addMessage({ role: 'ai', content: '↩️ Modifications refusées. Aucune donnée n\'a été modifiée.' })
    } catch {
      toast('Erreur lors de l\'annulation', 'error')
    }
  }

  function togglePreview(idx: number) {
    setExpandedPreviews(prev => {
      const next = new Set(prev)
      next.has(idx) ? next.delete(idx) : next.add(idx)
      return next
    })
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

  // ── Direct data edits (from StepPanel forms) ──────────────────────────────
  async function handleUpdateSchoolData(newData: SchoolData) {
    await updateSchoolData(newData)
  }

  async function handleUpdateAssignments(newAssignments: any[]) {
    await updateAssignments(newAssignments)
  }

  function handleStopStreaming() {
    if (!streamAbortRef.current) return
    streamAbortRef.current.abort()
    setIsLoading(false)
    setActiveTool(null)
    toast('Génération interrompue')
    addMessage({ role: 'system', content: 'Génération interrompue.' })
  }

  // ── Generate timetable ────────────────────────────────────────────────────
  async function handleGenerate() {
    if (!sessionId || isSolving) return
    setIsSolving(true)
    setCurrentStep(8)

    // Fugace "en cours" message — replaced in-place by the result
    const tid = addTransientMessage(
      '⚙️ **Génération en cours…**\n\nLe solveur analyse vos contraintes. Cela peut prendre quelques secondes.',
    )

    try {
      const res = await solve(sessionId)

      if (res.status === 'OPTIMAL' || res.status === 'FEASIBLE' || res.status === 'PARTIAL') {
        setTimetable(res)
        toast('Emploi du temps généré !')

        const partial = res.status === 'PARTIAL'
        // Filter entries with no subject to avoid "B" phantom artifacts
        const unscheduled: any[] = (res.unscheduled ?? []).filter((u: any) => u.subject)
        let partialDetail = ''
        if (unscheduled.length > 0) {
          const lines = unscheduled.slice(0, 5).map((u: any) => {
            const id = [u.school_class, u.subject].filter(Boolean).join(' · ')
            return `- **${id}**${u.reason ? ` — ${u.reason}` : ''}`
          })
          if (unscheduled.length > 5) lines.push(`- _…et ${unscheduled.length - 5} autres_`)
          partialDetail = '\n\n**Sessions non planifiées :**\n' + lines.join('\n')
        }

        replaceTransientMessage(tid, {
          role:    'ai',
          content: partial
            ? `⚠️ **Emploi du temps partiellement généré** — ${res.assignments?.length ?? 0} sessions placées, ${unscheduled.length} non planifiée(s).${partialDetail}`
            : `✅ **${res.assignments?.length ?? 0} sessions planifiées.**`,
        })

        if (!partial) {
          setTimeout(() => router.push('/results'), 1200)
        }
      } else {
        const summary = res.conflict_summary || res.message || 'Aucune solution trouvée.'
        replaceTransientMessage(tid, {
          role:    'ai',
          content: `❌ **Génération impossible**\n\n${summary}`,
        })
        toast('Impossible de générer l\'emploi du temps', 'error')
        return
      }
    } catch {
      removeTransientMessage(tid)
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
              <span className="text-xs text-gray-400 dark:text-gray-500">· claude-sonnet</span>
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
                isLastMessage={i === messages.length - 1}
                onRegenerate={i === messages.length - 1 && msg.role === 'ai' ? () => {
                  // Remove last AI message and resend previous user message
                  if (i > 0 && messages[i - 1].role === 'user') {
                    setMessages(prev => prev.slice(0, -1))
                    send(messages[i - 1].content)
                  }
                } : undefined}
                onEdit={msg.role === 'user' ? () => {
                  // Populate input with message content for editing
                  setInput(msg.content)
                  // Remove this message and all subsequent messages
                  setMessages(prev => prev.slice(0, i))
                } : undefined}
              />
            ))}

            {isStreamInterrupted && (
              <div className="mb-2 flex justify-center">
                <span className="text-[11px] text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 px-2 py-1 rounded-full">
                  Réponse interrompue. Vous pouvez reformuler ou relancer.
                </span>
              </div>
            )}

            {/* Active tool pill */}
            {activeTool && (
              <AgentActionPill toolName={activeTool} />
            )}

            {/* Thinking indicator — only before first streaming token arrives */}
            {isLoading && !messages.some(m => (m as any)._streamingId !== undefined) && (
              <div className="flex justify-start mb-3 animate-fade-in">
                <div className="w-7 h-7 rounded-full bg-teal-100 dark:bg-teal-900/40 flex items-center justify-center mr-2 mt-0.5 flex-shrink-0">
                  <Bot size={14} className="text-teal-600 dark:text-teal-400" />
                </div>
                <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm">
                  <ThinkingWord />
                </div>
              </div>
            )}

            {/* ── Staging card ── */}
            {pendingChanges.length > 0 && (
              <div className="mb-3 animate-fade-in">
                <div className="rounded-2xl border-2 border-amber-300 dark:border-amber-600 bg-amber-50 dark:bg-amber-950/30 overflow-hidden shadow-sm">
                  <div className="px-4 py-3 flex items-center gap-2 border-b border-amber-200 dark:border-amber-700">
                    <div className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
                    <span className="text-sm font-semibold text-amber-800 dark:text-amber-300">
                      Révision requise — {pendingChanges.length} modification{pendingChanges.length > 1 ? 's' : ''} en attente
                    </span>
                  </div>

                  <div className="divide-y divide-amber-100 dark:divide-amber-900">
                    {pendingChanges.map((change, idx) => (
                      <div key={idx} className="px-4 py-2.5">
                        <button
                          onClick={() => togglePreview(idx)}
                          className="w-full flex items-center justify-between text-left gap-2 group"
                        >
                          <span className="text-sm font-medium text-amber-900 dark:text-amber-200">
                            {change.label}
                          </span>
                          {expandedPreviews.has(idx)
                            ? <ChevronUp size={14} className="text-amber-500 flex-shrink-0" />
                            : <ChevronDown size={14} className="text-amber-500 flex-shrink-0" />
                          }
                        </button>
                        {expandedPreviews.has(idx) && (
                          <div className="mt-2 text-xs text-amber-800 dark:text-amber-300 overflow-x-auto">
                            <table className="w-full border-collapse min-w-max">
                              {(() => {
                                const rows = change.preview.split('\n').map((row, ri) => {
                                  const cells = row.split('|').filter((_, ci) => ci > 0 && ci < row.split('|').length - 1)
                                  if (!cells.length || row.match(/^[\s|:-]+$/)) return null
                                  return { ri, cells }
                                }).filter(Boolean) as { ri: number; cells: string[] }[]
                                const [header, ...body] = rows
                                return (
                                  <>
                                    {header && (
                                      <thead>
                                        <tr className="border-b border-amber-300 dark:border-amber-700">
                                          {header.cells.map((cell, ci) => (
                                            <th key={ci} className="px-2 py-1 text-left whitespace-nowrap font-semibold">{cell.trim()}</th>
                                          ))}
                                        </tr>
                                      </thead>
                                    )}
                                    <tbody>
                                      {body.map(({ ri, cells }) => (
                                        <tr key={ri} className="border-b border-amber-100 dark:border-amber-900/50 last:border-0">
                                          {cells.map((cell, ci) => (
                                            <td key={ci} className="px-2 py-1 text-left whitespace-nowrap">{cell.trim()}</td>
                                          ))}
                                        </tr>
                                      ))}
                                    </tbody>
                                  </>
                                )
                              })()}
                            </table>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  <div className="px-4 py-3 flex gap-2 border-t border-amber-200 dark:border-amber-700 bg-amber-50/80 dark:bg-amber-950/20">
                    <button
                      onClick={handleApply}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-xl transition-colors"
                    >
                      <CheckCircle size={14} /> Appliquer
                    </button>
                    <button
                      onClick={handleReject}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                    >
                      <XCircle size={14} /> Refuser
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input bar */}
          {pendingChanges.length > 0 && (
            <div className="px-4 py-1.5 text-xs text-center text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/20 border-t border-gray-100 dark:border-gray-800">
              Révisez les modifications ci-dessus avant de continuer
            </div>
          )}
          <ChatInput
            value={input}
            onChange={setInput}
            onSend={() => send()}
            onStop={handleStopStreaming}
            onFileUpload={async (file) => {
              if (!sessionId) return

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
            }}
            isLoading={isLoading}
            isStreaming={messages.some(m => (m as any)._streamingId !== undefined)}
            disabled={pendingChanges.length > 0}
            placeholder={
              pendingChanges.length > 0
                ? 'Révisez les modifications avant de continuer…'
                : sessionId ? 'Message…' : 'Chargement…'
            }
            sessionId={sessionId}
          />
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
              onAskAI={(errorContext) => {
                // Send error context to AI chat
                send(errorContext)
                // Switch to chat view on mobile
                if (window.innerWidth < 768) {
                  setMobileView('chat')
                }
              }}
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

// Wrap with Suspense for useSearchParams
export default function WorkspacePage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-screen bg-gray-50 dark:bg-gray-900">
        <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
      </div>
    }>
      <WorkspaceContent />
    </Suspense>
  )
}
