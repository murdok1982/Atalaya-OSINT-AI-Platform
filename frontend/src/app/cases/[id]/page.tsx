'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import useSWR from 'swr'
import { fetcher, api } from '@/lib/api'
import type { Case, Entity, Evidence, Job, Report } from '@/types'
import { formatRelativeTime, formatAbsoluteTime, getStatusColor, getPriorityColor, getEntityTypeIcon, formatBytes, formatDuration } from '@/lib/utils'
import { ArrowLeft, Plus, RefreshCw, Download, Trash2, ExternalLink, AlertCircle, Play } from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'

const TABS = ['Overview', 'Entities', 'Evidence', 'Jobs', 'Reports', 'Timeline'] as const
type Tab = typeof TABS[number]

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [tab, setTab] = useState<Tab>('Overview')
  const [showJobDialog, setShowJobDialog] = useState(false)
  const [jobTask, setJobTask] = useState('')
  const [jobType, setJobType] = useState('COORDINATOR')
  const [launchingJob, setLaunchingJob] = useState(false)

  const { data: caseData, mutate: mutateCase } = useSWR<Case>(`/cases/${id}`, fetcher, { refreshInterval: 15000 })
  const { data: entities, mutate: mutateEntities } = useSWR<Entity[]>(tab === 'Entities' ? `/entities?case_id=${id}&limit=100` : null, fetcher)
  const { data: evidence, mutate: mutateEvidence } = useSWR<Evidence[]>(tab === 'Evidence' ? `/evidence?case_id=${id}&limit=100` : null, fetcher)
  const { data: jobs, mutate: mutateJobs } = useSWR<Job[]>((tab === 'Jobs' || tab === 'Overview') ? `/jobs?case_id=${id}&limit=50` : null, fetcher, { refreshInterval: 5000 })
  const { data: reports, mutate: mutateReports } = useSWR<Report[]>(tab === 'Reports' ? `/reports?case_id=${id}&limit=50` : null, fetcher)

  async function handleLaunchJob() {
    if (!jobTask.trim()) return
    setLaunchingJob(true)
    try {
      await api.createJob({ case_id: id, job_type: jobType, task_description: jobTask })
      toast.success('Job launched')
      setShowJobDialog(false)
      setJobTask('')
      mutateJobs()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLaunchingJob(false)
    }
  }

  async function handleDeleteEvidence(evidenceId: string) {
    if (!confirm('Delete this evidence item?')) return
    try {
      await api.deleteEvidence(evidenceId)
      toast.success('Evidence deleted')
      mutateEvidence()
    } catch {
      toast.error('Failed to delete')
    }
  }

  async function handleGenerateReport(reportType: string) {
    try {
      await api.generateReport({ case_id: id, report_type: reportType, format: 'MARKDOWN' })
      toast.success('Report generation started')
      setTab('Reports')
      mutateReports()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  if (!caseData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button onClick={() => router.push('/cases')} className="mt-0.5 p-1.5 rounded-lg hover:bg-surface-2 transition-colors text-gray-400 hover:text-white shrink-0">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold truncate">{caseData.title}</h1>
            <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${getStatusColor(caseData.status)}`}>{caseData.status}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${getPriorityColor(caseData.priority)}`}>{caseData.priority}</span>
          </div>
          {caseData.description && <p className="text-sm text-gray-400 mt-1 line-clamp-2">{caseData.description}</p>}
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            <span>Created {formatRelativeTime(caseData.created_at)}</span>
            <span>Updated {formatRelativeTime(caseData.updated_at)}</span>
            {caseData.tags.length > 0 && (
              <div className="flex gap-1">{caseData.tags.slice(0, 5).map(t => <span key={t} className="px-1.5 py-0.5 bg-surface-2 rounded text-gray-400">{t}</span>)}</div>
            )}
          </div>
        </div>
        <button
          onClick={() => setShowJobDialog(true)}
          className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors shrink-0"
        >
          <Play className="w-3.5 h-3.5" /> Run Job
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3 text-center">
        {[
          { label: 'Entities', value: caseData.entity_count },
          { label: 'Evidence', value: caseData.evidence_count },
          { label: 'Jobs', value: caseData.job_count },
        ].map(s => (
          <div key={s.label} className="bg-surface border border-border rounded-lg py-3">
            <div className="text-xl font-bold">{s.value}</div>
            <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <div className="flex gap-0 -mb-px">
          {TABS.map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === t ? 'border-blue-500 text-blue-400' : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      {tab === 'Overview' && <OverviewTab caseData={caseData} jobs={jobs ?? []} onRunJob={() => setShowJobDialog(true)} onGenerateReport={handleGenerateReport} />}
      {tab === 'Entities' && <EntitiesTab entities={entities ?? []} caseId={id} onRefresh={mutateEntities} />}
      {tab === 'Evidence' && <EvidenceTab evidence={evidence ?? []} caseId={id} onDelete={handleDeleteEvidence} onRefresh={mutateEvidence} />}
      {tab === 'Jobs' && <JobsTab jobs={jobs ?? []} onRefresh={mutateJobs} />}
      {tab === 'Reports' && <ReportsTab reports={reports ?? []} caseId={id} onGenerate={handleGenerateReport} onRefresh={mutateReports} />}
      {tab === 'Timeline' && <TimelineTab evidence={evidence ?? []} jobs={jobs ?? []} caseId={id} />}

      {/* Launch Job Dialog */}
      {showJobDialog && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-surface border border-border rounded-xl p-6 w-full max-w-lg space-y-4">
            <h2 className="font-semibold text-lg">Launch Intelligence Job</h2>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Job Type</label>
              <select
                value={jobType}
                onChange={e => setJobType(e.target.value)}
                className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="COORDINATOR">Coordinator (full pipeline)</option>
                <option value="OSINT">OSINT Agent</option>
                <option value="SOCMINT">SOCMINT Agent</option>
                <option value="ENTITY_RESOLUTION">Entity Resolution</option>
                <option value="SOURCE_VALIDATION">Source Validation</option>
                <option value="REPORT_GENERATION">Report Generation</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Task / Target *</label>
              <textarea
                value={jobTask}
                onChange={e => setJobTask(e.target.value)}
                rows={3}
                placeholder="e.g. Investigate domain example.com — find subdomains, WHOIS, cert history, and social presence"
                className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 resize-none"
              />
            </div>
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 text-xs text-yellow-400">
              Jobs will only collect publicly available information. Ensure you have authorization to investigate the target.
            </div>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowJobDialog(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">Cancel</button>
              <button
                onClick={handleLaunchJob}
                disabled={launchingJob || !jobTask.trim()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
              >
                {launchingJob ? 'Launching...' : 'Launch Job'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function OverviewTab({ caseData, jobs, onRunJob, onGenerateReport }: { caseData: Case; jobs: Job[]; onRunJob: () => void; onGenerateReport: (type: string) => void }) {
  const activeJobs = jobs.filter(j => ['RUNNING', 'PENDING', 'QUEUED'].includes(j.status))
  const recentJobs = jobs.slice(0, 4)

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-surface border border-border rounded-lg p-4 space-y-3">
          <h3 className="text-sm font-semibold text-gray-300">Case Details</h3>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-gray-500">Status</dt><dd><span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(caseData.status)}`}>{caseData.status}</span></dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Priority</dt><dd><span className={`text-xs px-2 py-0.5 rounded-full ${getPriorityColor(caseData.priority)}`}>{caseData.priority}</span></dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Classification</dt><dd className="text-gray-300">{caseData.classification}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Case ID</dt><dd className="font-mono text-xs text-gray-400">{caseData.id.slice(0, 16)}…</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Created</dt><dd className="text-gray-300">{formatAbsoluteTime(caseData.created_at)}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Last Update</dt><dd className="text-gray-300">{formatRelativeTime(caseData.updated_at)}</dd></div>
          </dl>
        </div>

        <div className="bg-surface border border-border rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-300">Running Jobs</h3>
            <span className="text-xs text-gray-500">{activeJobs.length} active</span>
          </div>
          {activeJobs.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-sm text-gray-500">No active jobs</p>
              <button onClick={onRunJob} className="mt-2 text-xs text-blue-400 hover:text-blue-300">Run a job →</button>
            </div>
          ) : (
            <div className="space-y-2">
              {activeJobs.map(j => (
                <div key={j.id} className="flex items-center justify-between p-2 bg-surface-2 rounded-lg text-xs">
                  <div>
                    <span className="font-mono text-gray-400">{j.id.slice(0, 8)}</span>
                    <span className="ml-2 text-gray-300">{j.job_type.replace(/_/g, ' ')}</span>
                  </div>
                  <span className="flex items-center gap-1 text-blue-400"><span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />{j.status}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="bg-surface border border-border rounded-lg p-4 space-y-3">
        <h3 className="text-sm font-semibold text-gray-300">Recent Activity</h3>
        {recentJobs.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">No jobs yet. <button onClick={onRunJob} className="text-blue-400">Start an investigation →</button></p>
        ) : (
          <div className="space-y-2">
            {recentJobs.map(j => (
              <div key={j.id} className="flex items-center justify-between p-3 bg-surface-2 rounded-lg text-sm">
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(j.status)}`}>{j.status}</span>
                  <span>{j.job_type.replace(/_/g, ' ')}</span>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>{j.findings_count} findings</span>
                  <span>{formatRelativeTime(j.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="bg-surface border border-border rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">Generate Report</h3>
        <div className="flex flex-wrap gap-2">
          {['EXECUTIVE_SUMMARY', 'TECHNICAL', 'TIMELINE', 'ENTITY_REPORT', 'THREAT_ASSESSMENT', 'FULL'].map(type => (
            <button key={type} onClick={() => onGenerateReport(type)} className="px-3 py-1.5 text-xs bg-surface-2 hover:bg-border border border-border rounded-lg transition-colors">
              {type.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function EntitiesTab({ entities, caseId, onRefresh }: { entities: Entity[]; caseId: string; onRefresh: () => void }) {
  const [typeFilter, setTypeFilter] = useState('ALL')
  const types = ['ALL', ...Array.from(new Set(entities.map(e => e.entity_type)))]
  const filtered = typeFilter === 'ALL' ? entities : entities.filter(e => e.entity_type === typeFilter)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex flex-wrap gap-2">
          {types.map(t => (
            <button key={t} onClick={() => setTypeFilter(t)} className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${typeFilter === t ? 'bg-blue-600 border-blue-600 text-white' : 'border-border text-gray-400 hover:border-gray-400'}`}>{t}</button>
          ))}
        </div>
        <button onClick={onRefresh} className="p-1.5 rounded-lg hover:bg-surface-2 text-gray-400"><RefreshCw className="w-3.5 h-3.5" /></button>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-500"><p>No entities found.</p></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {filtered.map(e => (
            <div key={e.id} className="bg-surface border border-border rounded-lg p-4 hover:border-blue-500/40 transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">{getEntityTypeIcon(e.entity_type)}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{e.value}</div>
                  <div className="text-xs text-gray-500">{e.entity_type}</div>
                </div>
                <div className="text-xs text-right shrink-0">
                  <div className="text-gray-400">{Math.round(e.confidence_score * 100)}%</div>
                  <div className="text-gray-600">conf.</div>
                </div>
              </div>
              {e.label && <p className="text-xs text-gray-500 mb-2 truncate">{e.label}</p>}
              <div className="flex items-center justify-between">
                {e.source && <span className="text-xs text-gray-600 truncate">{e.source}</span>}
                <span className="text-xs text-gray-500 ml-auto">{formatRelativeTime(e.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function EvidenceTab({ evidence, caseId, onDelete, onRefresh }: { evidence: Evidence[]; caseId: string; onDelete: (id: string) => void; onRefresh: () => void }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-400">{evidence.length} items</span>
        <button onClick={onRefresh} className="p-1.5 rounded-lg hover:bg-surface-2 text-gray-400"><RefreshCw className="w-3.5 h-3.5" /></button>
      </div>

      {evidence.length === 0 ? (
        <div className="text-center py-16 text-gray-500"><p>No evidence collected yet. Run an intelligence job to gather evidence.</p></div>
      ) : (
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-2">
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Type</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Title</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Source</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Hash</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Collected</th>
                <th className="text-right px-4 py-3 text-xs text-gray-400 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {evidence.map((ev, i) => (
                <tr key={ev.id} className={`border-b border-border/50 hover:bg-surface-2 transition-colors ${i % 2 !== 0 ? 'bg-surface-2/30' : ''}`}>
                  <td className="px-4 py-3">
                    <span className="text-xs px-2 py-0.5 bg-surface-2 rounded text-gray-400">{ev.evidence_type}</span>
                  </td>
                  <td className="px-4 py-3 text-sm max-w-xs truncate">{ev.title}</td>
                  <td className="px-4 py-3 text-xs text-gray-400 max-w-xs truncate">{ev.source_url || ev.source_name}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{ev.content_hash?.slice(0, 12) ?? '—'}</td>
                  <td className="px-4 py-3 text-xs text-gray-400">{formatRelativeTime(ev.collected_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {ev.source_url && (
                        <a href={ev.source_url} target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-blue-400 transition-colors">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                      <button onClick={() => onDelete(ev.id)} className="text-gray-400 hover:text-red-400 transition-colors">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function JobsTab({ jobs, onRefresh }: { jobs: Job[]; onRefresh: () => void }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-400">{jobs.length} jobs</span>
        <button onClick={onRefresh} className="p-1.5 rounded-lg hover:bg-surface-2 text-gray-400"><RefreshCw className="w-3.5 h-3.5" /></button>
      </div>
      {jobs.length === 0 ? (
        <div className="text-center py-16 text-gray-500">No jobs for this case yet.</div>
      ) : (
        <div className="space-y-2">
          {jobs.map(j => (
            <div key={j.id} className="bg-surface border border-border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-gray-400">{j.id.slice(0, 8)}</span>
                  <span className="text-sm font-medium">{j.job_type.replace(/_/g, ' ')}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(j.status)}`}>{j.status}</span>
                </div>
                <span className="text-xs text-gray-500">{formatRelativeTime(j.created_at)}</span>
              </div>
              <div className="flex items-center gap-4 text-xs text-gray-500">
                <span>{j.findings_count} findings</span>
                {j.duration_seconds != null && <span>{formatDuration(j.duration_seconds)}</span>}
                {j.error_message && <span className="text-red-400 flex items-center gap-1"><AlertCircle className="w-3 h-3" />{j.error_message.slice(0, 60)}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ReportsTab({ reports, caseId, onGenerate, onRefresh }: { reports: Report[]; caseId: string; onGenerate: (type: string) => void; onRefresh: () => void }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex flex-wrap gap-2">
          {['EXECUTIVE_SUMMARY', 'TECHNICAL', 'TIMELINE', 'ENTITY_REPORT', 'THREAT_ASSESSMENT', 'FULL'].map(type => (
            <button key={type} onClick={() => onGenerate(type)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-surface-2 hover:bg-border border border-border rounded-lg transition-colors">
              <Plus className="w-3 h-3" />{type.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
        <button onClick={onRefresh} className="p-1.5 rounded-lg hover:bg-surface-2 text-gray-400"><RefreshCw className="w-3.5 h-3.5" /></button>
      </div>
      {reports.length === 0 ? (
        <div className="text-center py-16 text-gray-500">No reports generated yet.</div>
      ) : (
        <div className="space-y-2">
          {reports.map(r => (
            <div key={r.id} className="bg-surface border border-border rounded-lg p-4 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium">{r.title}</span>
                  <span className="text-xs px-2 py-0.5 bg-surface-2 rounded text-gray-400">{r.report_type}</span>
                  <span className="text-xs px-2 py-0.5 bg-surface-2 rounded text-gray-400">{r.format}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(r.status)}`}>{r.status}</span>
                </div>
                <span className="text-xs text-gray-500">{formatRelativeTime(r.created_at)}</span>
              </div>
              {r.status === 'COMPLETED' && r.file_path && (
                <a
                  href={`/api/v1/reports/${r.id}/download`}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-surface-2 hover:bg-border border border-border rounded-lg transition-colors"
                >
                  <Download className="w-3.5 h-3.5" /> Download
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function TimelineTab({ evidence, jobs, caseId }: { evidence: Evidence[]; jobs: Job[]; caseId: string }) {
  const events = [
    ...evidence.map(ev => ({ id: ev.id, time: ev.collected_at, label: ev.title, type: 'evidence', sub: ev.evidence_type })),
    ...jobs.map(j => ({ id: j.id, time: j.created_at, label: j.job_type.replace(/_/g, ' '), type: 'job', sub: j.status })),
  ].sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())

  if (events.length === 0) {
    return <div className="text-center py-16 text-gray-500">No timeline data yet. Run jobs to collect evidence.</div>
  }

  return (
    <div className="space-y-1">
      {events.map((ev, i) => (
        <div key={ev.id} className="flex gap-4 items-start py-2">
          <div className="shrink-0 text-right w-36 text-xs text-gray-500 pt-0.5">{formatAbsoluteTime(ev.time)}</div>
          <div className="shrink-0 flex flex-col items-center">
            <div className={`w-2.5 h-2.5 rounded-full mt-1 ${ev.type === 'evidence' ? 'bg-blue-400' : 'bg-purple-400'}`} />
            {i < events.length - 1 && <div className="w-px flex-1 bg-border mt-1 min-h-[1.5rem]" />}
          </div>
          <div className="flex-1 pb-2">
            <span className="text-sm">{ev.label}</span>
            <div className="flex gap-2 mt-0.5">
              <span className={`text-xs px-1.5 py-0.5 rounded ${ev.type === 'evidence' ? 'bg-blue-500/20 text-blue-400' : 'bg-purple-500/20 text-purple-400'}`}>{ev.type}</span>
              <span className="text-xs text-gray-500">{ev.sub}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
