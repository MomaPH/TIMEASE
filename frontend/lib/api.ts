const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || ''

function networkErrorMessage(): string {
  if (API_BASE) {
    return `Erreur reseau: impossible de joindre l'API (${API_BASE}). Verifiez que l'URL est correcte et que le backend est lance.`
  }
  return "Erreur reseau: impossible de joindre l'API via /api (proxy frontend). Verifiez que backend et frontend sont bien demarres."
}

function buildApiUrl(path: string): string {
  if (API_BASE) {
    return `${API_BASE.replace(/\/$/, '')}${path}`
  }
  return path
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(buildApiUrl(path), init)
  } catch {
    throw new Error(networkErrorMessage())
  }
}

async function readErrorDetail(res: Response): Promise<string | null> {
  const contentType = res.headers.get('content-type') || ''

  try {
    if (contentType.includes('application/json')) {
      const body = await res.json()
      if (typeof body?.detail === 'string' && body.detail.trim()) {
        return body.detail
      }
    }

    const text = (await res.text()).trim()
    if (text) return text
  } catch {
    // Ignore parse errors and fallback to status code.
  }

  return null
}

async function ensureOk(res: Response, fallback: string): Promise<void> {
  if (res.ok) return

  const detail = await readErrorDetail(res)
  if (detail) {
    throw new Error(`${fallback}: ${detail}`)
  }
  throw new Error(`${fallback}: HTTP ${res.status}`)
}

export async function createSession(): Promise<string> {
  const res = await request('/api/session', { method: 'POST' })
  await ensureOk(res, 'Creation de session echouee')
  const data = await res.json()
  if (!data?.session_id) {
    throw new Error('Reponse API invalide: session_id manquant.')
  }
  return data.session_id
}

export async function getSession(sid: string) {
  const res = await request(`/api/session/${sid}`)
  await ensureOk(res, 'Lecture de session echouee')
  return res.json()
}


export async function uploadFile(sid: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  const res = await request(`/api/session/${sid}/upload`, { method: 'POST', body: form })
  await ensureOk(res, 'Upload echoue')
  return res.json()
}

export async function updateSchoolData(sid: string, data: any) {
  const res = await request(`/api/session/${sid}/school_data`, {
    method:  'PUT',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(data),
  })
  await ensureOk(res, 'Mise a jour des donnees ecole echouee')
  return res.json()
}

export async function updateAssignments(sid: string, assignments: any[]) {
  const res = await request(`/api/session/${sid}/assignments`, {
    method:  'PUT',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ assignments }),
  })
  await ensureOk(res, 'Mise a jour des affectations echouee')
  return res.json()
}

export async function solve(sid: string) {
  const res = await request(`/api/session/${sid}/solve`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ timeout: 120 }),
  })
  await ensureOk(res, 'Generation echouee')
  return res.json()
}

export async function restoreSession(
  sid: string,
  payload: { school_data?: any; teacher_assignments?: any[]; timetable_result?: any },
) {
  const res = await request(`/api/session/${sid}/restore`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(payload),
  })
  await ensureOk(res, 'Restauration de session echouee')
  return res.json()
}

export async function exportFile(sid: string, format: string) {
  const res = await request(`/api/session/${sid}/export/${format}`)
  await ensureOk(res, 'Export echoue')
  return res.blob()
}
