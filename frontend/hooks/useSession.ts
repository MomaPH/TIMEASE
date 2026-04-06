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

export function useSession() {
  const [sessionId,  setSessionId]  = useState<string | null>(null)
  const [schoolData, setSchoolData] = useState<SchoolData>({})
  const [assignments, setAssignments] = useState<any[]>([])
  const [timetable,  setTimetableState] = useState<any>(null)

  // ── Initial load ─────────────────────────────────────────────────────────
  useEffect(() => {
    const stored = localStorage.getItem(SESSION_KEY)

    // Restore timetable from localStorage immediately (survives backend restart)
    if (stored) {
      const cachedTimetable = localStorage.getItem(timetableKey(stored))
      if (cachedTimetable) {
        try { setTimetableState(JSON.parse(cachedTimetable)) } catch {}
      }

      setSessionId(stored)
      getSession(stored)
        .then(data => {
          setSchoolData(data.school_data || {})
          setAssignments(data.teacher_assignments || [])
          // Backend timetable takes precedence if present
          if (data.timetable_result && Object.keys(data.timetable_result).length > 0) {
            setTimetableState(data.timetable_result)
          }
        })
        .catch(() => initSession())
    } else {
      initSession()
    }
  }, [])

  async function initSession() {
    const sid = await createSession()
    localStorage.setItem(SESSION_KEY, sid)
    setSessionId(sid)
    setSchoolData({})
    setAssignments([])
    setTimetableState(null)
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
    // Clear per-session keys
    const old = sessionId
    if (old) {
      localStorage.removeItem(timetableKey(old))
      localStorage.removeItem(`timease_messages_${old}`)
      localStorage.removeItem(`timease_aihistory_${old}`)
    }
    setSessionId(sid)
    setSchoolData({})
    setAssignments([])
    setTimetableState(null)
  }, [sessionId])

  return {
    sessionId,
    schoolData,
    assignments,
    timetable,
    setTimetable,
    updateSchoolData,
    updateAssignments,
    refreshSession,
    resetSession,
  }
}
