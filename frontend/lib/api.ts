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

export type SolveMode = 'fast' | 'balanced' | 'complete'
export type SolveJobStatus = 'queued' | 'running' | 'done' | 'failed' | 'timeout' | 'cancelled'

export type SnapshotRecord = {
  id: string
  name: string
  created_at: number
  school_data: any
  teacher_assignments: any[]
}

export type JobRecord = {
  id: string
  snapshot_id: string
  status: SolveJobStatus
  mode: SolveMode
  created_at: number
  started_at?: number | null
  finished_at?: number | null
  result?: any
  estimate?: any
  request_id?: string
  report?: {
    outcome: 'success' | 'failed' | 'partial'
    reason_code: string
    reason_message: string
    summary: string
    diagnostics?: Record<string, any>
  } | null
}

export async function createSnapshot(
  sid: string,
  payload?: { name?: string; school_data?: any; teacher_assignments?: any[] },
) {
  const res = await request(`/api/session/${sid}/snapshots`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload ?? {}),
  })
  await ensureOk(res, 'Creation de version echouee')
  return res.json()
}

export async function renameSnapshot(sid: string, snapshotId: string, name: string) {
  const res = await request(`/api/session/${sid}/snapshots/${snapshotId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  await ensureOk(res, 'Renommage de version echoue')
  return res.json()
}

export async function deleteSnapshot(sid: string, snapshotId: string): Promise<{ ok: boolean; deleted_jobs: number }> {
  const res = await request(`/api/session/${sid}/snapshots/${snapshotId}`, { method: 'DELETE' })
  await ensureOk(res, 'Suppression de version echouee')
  return res.json()
}

export async function listSnapshots(sid: string): Promise<{ snapshots: SnapshotRecord[] }> {
  const res = await request(`/api/session/${sid}/snapshots`)
  await ensureOk(res, 'Lecture des versions echouee')
  return res.json()
}

export async function duplicateSnapshot(sid: string, snapshotId: string) {
  const res = await request(`/api/session/${sid}/snapshots/${snapshotId}/duplicate`, {
    method: 'POST',
  })
  await ensureOk(res, 'Duplication de version echouee')
  return res.json()
}

export async function createSolveJob(
  sid: string,
  payload: { snapshot_id: string; mode?: SolveMode; timeout?: number; request_id?: string },
): Promise<{ job: JobRecord }> {
  const res = await request(`/api/session/${sid}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  await ensureOk(res, 'Creation du job echouee')
  return res.json()
}

export async function listSolveJobs(sid: string): Promise<{ jobs: JobRecord[] }> {
  const res = await request(`/api/session/${sid}/jobs`)
  await ensureOk(res, 'Lecture des jobs echouee')
  return res.json()
}

export async function cancelSolveJob(sid: string, jobId: string): Promise<{ job: JobRecord }> {
  const res = await request(`/api/session/${sid}/jobs/${jobId}/cancel`, { method: 'POST' })
  await ensureOk(res, 'Arret du job echoue')
  return res.json()
}

export async function deleteSolveJob(sid: string, jobId: string): Promise<{ ok: boolean }> {
  const res = await request(`/api/session/${sid}/jobs/${jobId}`, { method: 'DELETE' })
  await ensureOk(res, 'Suppression du job echouee')
  return res.json()
}

export async function getSolveEstimate(sid: string) {
  const res = await request(`/api/session/${sid}/solve-estimate`)
  await ensureOk(res, 'Estimation de generation echouee')
  return res.json()
}

export async function exportFile(sid: string, format: string) {
  const res = await request(`/api/session/${sid}/export/${format}`)
  await ensureOk(res, 'Export echoue')
  return res.blob()
}
