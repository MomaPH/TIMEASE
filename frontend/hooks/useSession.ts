'use client'
import { useState, useEffect, useCallback } from 'react'
import {
  createSession,
  getSession,
  updateSchoolData as apiUpdateSchoolData,
  updateAssignments as apiUpdateAssignments,
} from '@/lib/api'
import type { SchoolData } from '@/lib/types'

const SESSION_KEY  = 'timease_session'
const timetableKey = (sid: string) => `timease_timetable_${sid}`

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  return fallback
}

export function useSession() {
  const [sessionId,  setSessionId]  = useState<string | null>(null)
  const [schoolData, setSchoolData] = useState<SchoolData>({})
  const [assignments, setAssignments] = useState<any[]>([])
  const [timetable,  setTimetableState] = useState<any>(null)
  const [sessionError, setSessionError] = useState<string | null>(null)

  // ── Initial load ─────────────────────────────────────────────────────────
  useEffect(() => {
    let mounted = true

    async function bootstrapSession() {
      const stored = localStorage.getItem(SESSION_KEY)

      // Restore timetable from localStorage immediately (survives backend restart)
      if (stored) {
        const cachedTimetable = localStorage.getItem(timetableKey(stored))
        if (cachedTimetable) {
          try { setTimetableState(JSON.parse(cachedTimetable)) } catch {}
        }

        setSessionId(stored)

        try {
          const data = await getSession(stored)
          if (!mounted) return

          setSchoolData(data.school_data || {})
          setAssignments(data.teacher_assignments || [])
          // Backend timetable takes precedence if present
          if (data.timetable_result && Object.keys(data.timetable_result).length > 0) {
            setTimetableState(data.timetable_result)
          }
          setSessionError(null)
          return
        } catch {
          // Fall through to create a new session.
        }
      }

      try {
        await initSession()
      } catch (error) {
        if (!mounted) return
        setSessionError(getErrorMessage(error, 'Impossible d\'initialiser une session.'))
      }
    }

    void bootstrapSession()

    return () => {
      mounted = false
    }
  }, [])

  async function initSession() {
    const sid = await createSession()
    localStorage.setItem(SESSION_KEY, sid)
    setSessionId(sid)
    setSchoolData({})
    setAssignments([])
    setTimetableState(null)
    setSessionError(null)
  }

  // ── Mutations ─────────────────────────────────────────────────────────────
  const updateSchoolData = useCallback(async (newData: SchoolData) => {
    setSchoolData(newData)
    const sid = localStorage.getItem(SESSION_KEY)
    if (sid) {
      try { await apiUpdateSchoolData(sid, newData) } catch {}
    }
  }, [])

  const updateAssignments = useCallback(async (newAssignments: any[]) => {
    setAssignments(newAssignments)
    const sid = localStorage.getItem(SESSION_KEY)
    if (sid) {
      try { await apiUpdateAssignments(sid, newAssignments) } catch {}
    }
  }, [])

  const setTimetable = useCallback((t: any) => {
    setTimetableState(t)
    const sid = sessionId || localStorage.getItem(SESSION_KEY)
    if (sid && t) {
      localStorage.setItem(timetableKey(sid), JSON.stringify(t))
    }
  }, [sessionId])

  const refreshSession = useCallback((): Promise<void> => {
    const sid = sessionId || localStorage.getItem(SESSION_KEY)
    if (!sid) return Promise.resolve()
    return getSession(sid)
      .then(data => {
        setSchoolData(data.school_data || {})
        setAssignments(data.teacher_assignments || [])
      })
      .catch(() => {})
  }, [sessionId])

  const resetSession = useCallback(async () => {
    const sid = await createSession()
    localStorage.setItem(SESSION_KEY, sid)
    // Clear per-session timetable key
    const old = sessionId
    if (old) {
      localStorage.removeItem(timetableKey(old))
    }
    setSessionId(sid)
    setSchoolData({})
    setAssignments([])
    setTimetableState(null)
    setSessionError(null)
  }, [sessionId])

  return {
    sessionId,
    schoolData,
    assignments,
    timetable,
    sessionError,
    setTimetable,
    updateSchoolData,
    updateAssignments,
    refreshSession,
    resetSession,
  }
}
