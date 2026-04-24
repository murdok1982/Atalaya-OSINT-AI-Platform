import type { Case, Entity, Evidence, Job, Report } from '@/types'

const API_BASE = '/api/v1'

function getAuthHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {}
  const token = sessionStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
  })
  if (res.status === 401) {
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  // Auth
  login: (username: string, password: string) =>
    request<{ access_token: string; refresh_token: string; token_type: string }>(
      'POST', '/auth/login', { username, password }
    ),
  logout: () => {
    sessionStorage.removeItem('access_token')
    sessionStorage.removeItem('refresh_token')
  },
  me: () => fetcher<{ id: string; username: string; email: string; scopes: string[] }>('/auth/me'),

  // Cases
  createCase: (data: Partial<Case>) => request<Case>('POST', '/cases', data),
  updateCase: (id: string, data: Partial<Case>) => request<Case>('PUT', `/cases/${id}`, data),
  updateCaseStatus: (id: string, status: string) =>
    request<Case>('PATCH', `/cases/${id}/status`, { status }),
  deleteCase: (id: string) => request<void>('DELETE', `/cases/${id}`),

  // Entities
  createEntity: (data: Partial<Entity>) => request<Entity>('POST', '/entities', data),
  updateEntity: (id: string, data: Partial<Entity>) => request<Entity>('PUT', `/entities/${id}`, data),
  mergeEntity: (id: string, targetId: string) =>
    request<void>('POST', `/entities/${id}/merge`, { target_entity_id: targetId }),

  // Jobs
  createJob: (data: { case_id: string; job_type: string; task_description?: string; input_params?: Record<string, unknown> }) =>
    request<Job>('POST', '/jobs', data),
  cancelJob: (id: string) => request<void>('POST', `/jobs/${id}/cancel`),

  // Evidence
  createEvidence: (data: Partial<Evidence>) => request<Evidence>('POST', '/evidence', data),
  uploadEvidence: async (caseId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${API_BASE}/evidence/upload?case_id=${caseId}`, {
      method: 'POST',
      headers: getAuthHeader(),
      body: formData,
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json() as Promise<Evidence>
  },

  // Reports
  generateReport: (data: {
    case_id: string
    report_type: string
    format: string
    entity_ids?: string[]
  }) => request<{ job_id: string }>('POST', '/reports/generate', data),
}
