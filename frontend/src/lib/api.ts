import type { Case, Entity, Evidence, Job } from '@/types'

const API_BASE = '/api/v1'
const TOKEN_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

// ---------------------------------------------------------------------------
// Token helpers — sessionStorage is the SoR. Cleared on 401 / logout.
// ---------------------------------------------------------------------------

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  return sessionStorage.getItem(TOKEN_KEY)
}

export function setAccessToken(token: string, refresh?: string): void {
  if (typeof window === 'undefined') return
  sessionStorage.setItem(TOKEN_KEY, token)
  if (refresh) sessionStorage.setItem(REFRESH_KEY, refresh)
}

export function clearAccessToken(): void {
  if (typeof window === 'undefined') return
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(REFRESH_KEY)
}

function getAuthHeader(): Record<string, string> {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function handleUnauthorized(): void {
  if (typeof window === 'undefined') return
  clearAccessToken()
  // Avoid bouncing if we're already at /login.
  if (!window.location.pathname.startsWith('/login')) {
    window.location.href = '/login'
  }
}

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface LoginResponse {
  access_token: string
  refresh_token?: string
  token_type: string
  /** When true, the client must present a TOTP code via /auth/mfa/verify. */
  mfa_required?: boolean
  /** Opaque ticket used to bind subsequent MFA verify call (when supported). */
  mfa_ticket?: string
}

export interface MeResponse {
  id: string
  username: string
  email: string
  scopes: string[]
  /** State-product capability: the user's clearance level. */
  clearance_level?: string
  is_admin?: boolean
}

export interface AuditEvent {
  id: string
  ts: string
  actor: string
  action: string
  resource: string
  prev_hash: string
  hash: string
  payload?: Record<string, unknown>
}

export interface AuditVerifyResponse {
  verified: boolean
  total_events: number
  invalid_at?: string | null
  message?: string
}

// ---------------------------------------------------------------------------
// Core fetchers
// ---------------------------------------------------------------------------

export async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
  })
  if (res.status === 401) {
    handleUnauthorized()
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
  if (res.status === 401) {
    handleUnauthorized()
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// API surface
// ---------------------------------------------------------------------------

export const api = {
  // Auth
  login: (username: string, password: string) =>
    request<LoginResponse>('POST', '/auth/login', { username, password }),
  /**
   * Verify TOTP code returned after login when mfa_required = true.
   * TODO(backend): confirm endpoint shape; currently /auth/mfa/verify with
   *                { username, code, ticket? } returning a normal LoginResponse.
   */
  verifyMfa: (payload: { username: string; code: string; ticket?: string }) =>
    request<LoginResponse>('POST', '/auth/mfa/verify', payload),
  logout: () => clearAccessToken(),
  me: () => fetcher<MeResponse>('/auth/me'),

  // Cases
  createCase: (data: Partial<Case>) => request<Case>('POST', '/cases', data),
  updateCase: (id: string, data: Partial<Case>) =>
    request<Case>('PUT', `/cases/${id}`, data),
  updateCaseStatus: (id: string, status: string) =>
    request<Case>('PATCH', `/cases/${id}/status`, { status }),
  deleteCase: (id: string) => request<void>('DELETE', `/cases/${id}`),

  // Entities
  createEntity: (data: Partial<Entity>) =>
    request<Entity>('POST', '/entities', data),
  updateEntity: (id: string, data: Partial<Entity>) =>
    request<Entity>('PUT', `/entities/${id}`, data),
  mergeEntity: (id: string, targetId: string) =>
    request<void>('POST', `/entities/${id}/merge`, {
      target_entity_id: targetId,
    }),

  // Jobs
  createJob: (data: {
    case_id: string
    job_type: string
    task_description?: string
    input_params?: Record<string, unknown>
  }) => request<Job>('POST', '/jobs', data),
  cancelJob: (id: string) => request<void>('POST', `/jobs/${id}/cancel`),

  // Evidence
  createEvidence: (data: Partial<Evidence>) =>
    request<Evidence>('POST', '/evidence', data),
  uploadEvidence: async (caseId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${API_BASE}/evidence/upload?case_id=${caseId}`, {
      method: 'POST',
      headers: getAuthHeader(),
      body: formData,
    })
    if (res.status === 401) {
      handleUnauthorized()
      throw new Error('Unauthorized')
    }
    if (!res.ok) throw new Error(await res.text())
    return res.json() as Promise<Evidence>
  },
  deleteEvidence: (id: string) => request<void>('DELETE', `/evidence/${id}`),

  // Reports
  generateReport: (data: {
    case_id: string
    report_type: string
    format: string
    entity_ids?: string[]
  }) => request<{ job_id: string }>('POST', '/reports/generate', data),

  // Audit
  /** TODO(backend): GET /audit?limit=&offset= — returns AuditEvent[] */
  listAudit: (limit = 100) =>
    fetcher<AuditEvent[]>(`/audit?limit=${limit}`),
  /** TODO(backend): GET /audit/verify — returns AuditVerifyResponse */
  verifyAudit: () => fetcher<AuditVerifyResponse>('/audit/verify'),
}
