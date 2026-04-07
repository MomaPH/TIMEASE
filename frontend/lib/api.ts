import type { PendingChange } from './types'

const BASE = 'http://localhost:8000'

export async function createSession(): Promise<string> {
  const res = await fetch(`${BASE}/api/session`, { method: 'POST' })
  const data = await res.json()
  return data.session_id
}

export async function getSession(sid: string) {
  const res = await fetch(`${BASE}/api/session/${sid}`)
  if (!res.ok) throw new Error('Session not found')
  return res.json()
}

export async function sendChat(
  sid: string,
  message: string,
  fileContent?: string,
  aiHistory?: any[],
) {
  const res = await fetch(`${BASE}/api/session/${sid}/chat`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ message, file_content: fileContent, ai_history: aiHistory }),
  })
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`)
  return res.json()
}

export async function sendChatStream(
  sid: string,
  message: string,
  fileContent: string | undefined,
  aiHistory: any[],
  onDelta: (text: string) => void,
  onToolStart: (name: string) => void,
  signal?: AbortSignal,
): Promise<{
  data_saved: boolean
  trigger_generation: boolean
  options: { label: string; value: string }[]
  set_step: number | null
  saved_types: string[]
  ai_history: any[]
  pending_changes: PendingChange[] | undefined
}> {
  const res = await fetch(`${BASE}/api/session/${sid}/chat/stream`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ message, file_content: fileContent, ai_history: aiHistory }),
    signal,
  })
  if (!res.ok) throw new Error(`Chat stream failed: ${res.status}`)
  if (!res.body)  throw new Error('No response body')

  const reader  = res.body.getReader()
  const decoder = new TextDecoder()
  let   buf     = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop() ?? ''  // keep incomplete last line
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const json = line.slice(6).trim()
      if (!json) continue
      try {
        const evt = JSON.parse(json)
        if (evt.type === 'delta')      onDelta(evt.text ?? '')
        if (evt.type === 'tool_start') onToolStart(evt.name ?? '')
        if (evt.type === 'done')       return evt
      } catch { /* ignore malformed */ }
    }
  }
  // Process any buffered final line that didn't end with newline
  if (buf.startsWith('data: ')) {
    const json = buf.slice(6).trim()
    if (json) {
      try {
        const evt = JSON.parse(json)
        if (evt.type === 'done') return evt
      } catch { /* ignore */ }
    }
  }
  throw new Error('Stream ended without done event')
}

export async function uploadFile(sid: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/api/session/${sid}/upload`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  return res.json()
}

export async function updateSchoolData(sid: string, data: any) {
  const res = await fetch(`${BASE}/api/session/${sid}/school_data`, {
    method:  'PUT',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`Update failed: ${res.status}`)
  return res.json()
}

export async function updateAssignments(sid: string, assignments: any[]) {
  const res = await fetch(`${BASE}/api/session/${sid}/assignments`, {
    method:  'PUT',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ assignments }),
  })
  if (!res.ok) throw new Error(`Update failed: ${res.status}`)
  return res.json()
}

export async function solve(sid: string) {
  const res = await fetch(`${BASE}/api/session/${sid}/solve`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ timeout: 120 }),
  })
  if (!res.ok) throw new Error(`Solve failed: ${res.status}`)
  return res.json()
}

export async function restoreSession(
  sid: string,
  payload: { school_data?: any; teacher_assignments?: any[]; timetable_result?: any },
) {
  const res = await fetch(`${BASE}/api/session/${sid}/restore`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Restore failed: ${res.status}`)
  return res.json()
}

export async function exportFile(sid: string, format: string) {
  const res = await fetch(`${BASE}/api/session/${sid}/export/${format}`)
  if (!res.ok) throw new Error(`Export failed: ${res.status}`)
  return res.blob()
}

export async function applyPending(sid: string, apply: boolean) {
  const res = await fetch(`${BASE}/api/session/${sid}/apply_pending`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ apply }),
  })
  if (!res.ok) throw new Error(`Apply pending failed: ${res.status}`)
  return res.json() as Promise<{ ok: boolean; applied: number }>
}

export async function generateCollabLinks(sid: string) {
  const res = await fetch(`${BASE}/api/session/${sid}/collab/generate`, { method: 'POST' })
  if (!res.ok) throw new Error(`Collab generate failed: ${res.status}`)
  return res.json() as Promise<{ links: { teacher: string; token: string; status: string }[] }>
}
