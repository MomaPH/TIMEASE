const BASE = 'http://localhost:8000'

export async function createSession(): Promise<string> {
  const res = await fetch(`${BASE}/api/session`, { method: 'POST' })
  const data = await res.json()
  return data.session_id
}

export async function getSession(sid: string) {
  const res = await fetch(`${BASE}/api/session/${sid}`)
  return res.json()
}

export async function sendChat(sid: string, message: string, fileContent?: string) {
  const res = await fetch(`${BASE}/api/session/${sid}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, file_content: fileContent }),
  })
  return res.json()
}

export async function uploadFile(sid: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/api/session/${sid}/upload`, { method: 'POST', body: form })
  return res.json()
}

export async function mergeData(sid: string, type: string, data: any) {
  const res = await fetch(`${BASE}/api/session/${sid}/merge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, data }),
  })
  return res.json()
}

export async function solve(sid: string) {
  const res = await fetch(`${BASE}/api/session/${sid}/solve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ timeout: 120 }),
  })
  return res.json()
}

export async function exportFile(sid: string, format: string) {
  const res = await fetch(`${BASE}/api/session/${sid}/export/${format}`)
  return res.blob()
}
