'use client'
import { useState, useEffect } from 'react'
import { createSession, getSession } from '@/lib/api'

export function useSession() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [schoolData, setSchoolData] = useState<any>({})
  const [assignments, setAssignments] = useState<any[]>([])
  const [timetable, setTimetable] = useState<any>(null)

  useEffect(() => {
    const stored = localStorage.getItem('timease_session')
    if (stored) {
      setSessionId(stored)
      getSession(stored)
        .then(data => {
          setSchoolData(data.school_data || {})
          setAssignments(data.teacher_assignments || [])
          setTimetable(data.timetable_result || null)
        })
        .catch(() => initSession())
    } else {
      initSession()
    }
  }, [])

  async function initSession() {
    const sid = await createSession()
    localStorage.setItem('timease_session', sid)
    setSessionId(sid)
  }

  function refreshSession() {
    if (!sessionId) return
    getSession(sessionId).then(data => {
      setSchoolData(data.school_data || {})
      setAssignments(data.teacher_assignments || [])
      setTimetable(data.timetable_result || null)
    })
  }

  return { sessionId, schoolData, assignments, timetable, refreshSession }
}
