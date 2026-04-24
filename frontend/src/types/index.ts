export type CaseStatus = 'OPEN' | 'ACTIVE' | 'CLOSED' | 'ARCHIVED'
export type CasePriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type EntityType =
  | 'PERSON' | 'ORGANIZATION' | 'DOMAIN' | 'EMAIL' | 'PHONE'
  | 'IP' | 'ASN' | 'HANDLE' | 'CHANNEL' | 'URL' | 'DOCUMENT'
  | 'IMAGE' | 'LOCATION' | 'ALIAS'
export type JobStatus = 'PENDING' | 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
export type JobType =
  | 'OSINT_RESEARCH' | 'SOCMINT' | 'ENTITY_RESOLUTION'
  | 'DOMAIN_INVESTIGATION' | 'REPORT_GENERATION' | 'CUSTOM'
export type EvidenceType =
  | 'URL' | 'FILE' | 'SCREENSHOT' | 'TEXT' | 'METADATA'
  | 'API_RESPONSE' | 'DNS_RECORD' | 'WHOIS' | 'CERTIFICATE'
  | 'SOCIAL_POST' | 'DOCUMENT'

export interface Case {
  id: string
  title: string
  description: string
  status: CaseStatus
  priority: CasePriority
  tags: string[]
  operator_id: string
  scope_notes: string
  classification: string
  created_at: string
  updated_at: string
  entity_count: number
  evidence_count: number
  job_count: number
}

export interface Entity {
  id: string
  case_id: string
  entity_type: string
  value: string
  label: string | null
  display_name: string
  source: string | null
  attributes: Record<string, unknown>
  confidence_score: number
  is_target: boolean
  tags: string[]
  notes: string
  merged_into_id: string | null
  created_at: string
  updated_at: string
}

export interface Evidence {
  id: string
  case_id: string
  entity_id: string | null
  title: string
  description: string
  evidence_type: string
  source_url: string | null
  source_name: string | null
  content_hash: string | null
  content_text: string | null
  file_size_bytes: number | null
  collected_at: string
  collected_by: string
  confidence_score: number
  tags: string[]
  is_sensitive: boolean
  created_at: string
}

export interface Job {
  id: string
  case_id: string
  job_type: JobType
  status: JobStatus
  arq_job_id: string | null
  created_by: string
  result_summary: string | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
  findings_count: number
  input_params: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface Report {
  id: string
  case_id: string
  job_id: string | null
  title: string
  summary: string
  report_type: string
  format: string
  status: string
  file_path: string | null
  content: string | null
  generated_by: string
  word_count: number
  entity_ids: string[]
  created_at: string
}

export interface LLMProviderInfo {
  name: string
  enabled: boolean
  is_default: boolean
  default_model: string
  requires_key: boolean
}

export interface SystemHealth {
  status: 'ok' | 'degraded' | 'down'
  db: boolean
  redis: boolean
  version: string
  uptime_seconds: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}
