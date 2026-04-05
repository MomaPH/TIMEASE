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
