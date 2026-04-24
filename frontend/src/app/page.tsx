'use client'

import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import type { Case, Job, SystemHealth } from '@/types'
import { formatRelativeTime, getStatusColor, getPriorityColor, formatDuration } from '@/lib/utils'
import { FolderOpen, Activity, Network, Shield, AlertCircle, CheckCircle2, Circle, Cpu } from 'lucide-react'
import Link from 'next/link'

function StatCard({ label, value, icon: Icon, color = 'text-blue-400' }: { label: string; value: number | string; icon: any; color?: string }) {
  return (
    <div className="bg-surface rounded-lg border border-border p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-400">{label}</span>
        <Icon className={`w-4 h-4 ${color}`} />
      </div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  )
}

function HealthDot({ ok }: { ok: boolean }) {
  return <span className={`inline-block w-2 h-2 rounded-full ${ok ? 'bg-green-400' : 'bg-red-400'}`} />
}

export default function DashboardPage() {
  const { data: health } = useSWR<SystemHealth>('/health', fetcher, { refreshInterval: 30000 })
  const { data: cases } = useSWR<Case[]>('/cases?status=ACTIVE&limit=5', fetcher, { refreshInterval: 15000 })
  const { data: allCases } = useSWR<Case[]>('/cases?limit=100', fetcher)
  const { data: jobs } = useSWR<Job[]>('/jobs?limit=5', fetcher, { refreshInterval: 5000 })
  const { data: runningJobs } = useSWR<Job[]>('/jobs?status=RUNNING&limit=10', fetcher, { refreshInterval: 5000 })

  const totalActive = allCases?.filter(c => c.status === 'ACTIVE' || c.status === 'OPEN').length ?? 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Atalaya Operations Center</h1>
          <p className="text-sm text-gray-400 mt-1">Open Intelligence Platform</p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          {health ? (
            <div className="flex items-center gap-2 bg-surface border border-border rounded-lg px-3 py-2">
              <HealthDot ok={health.status === 'ok'} />
              <span className="text-gray-300">DB</span>
              <HealthDot ok={health.db} />
              <span className="text-gray-300">Redis</span>
              <HealthDot ok={health.redis} />
              <span className="text-gray-500 text-xs">v{health.version}</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 bg-surface border border-border rounded-lg px-3 py-2">
              <Circle className="w-3 h-3 text-yellow-400 animate-pulse" />
              <span className="text-gray-400">Connecting...</span>
            </div>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Active Cases" value={totalActive} icon={FolderOpen} color="text-blue-400" />
        <StatCard label="Running Jobs" value={runningJobs?.length ?? 0} icon={Activity} color="text-yellow-400" />
        <StatCard label="Total Jobs Today" value={jobs?.length ?? 0} icon={Cpu} color="text-purple-400" />
        <StatCard label="System Status" value={health?.status === 'ok' ? 'Healthy' : 'Degraded'} icon={Shield} color={health?.status === 'ok' ? 'text-green-400' : 'text-red-400'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Cases */}
        <div className="bg-surface rounded-lg border border-border p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Active Cases</h2>
            <Link href="/cases" className="text-xs text-blue-400 hover:text-blue-300">View all →</Link>
          </div>
          <div className="space-y-3">
            {cases?.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-4">No active cases. <Link href="/cases" className="text-blue-400">Create one →</Link></p>
            )}
            {cases?.map(c => (
              <Link key={c.id} href={`/cases/${c.id}`} className="block p-3 rounded-lg bg-surface-2 hover:bg-border transition-colors">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm truncate">{c.title}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(c.status)}`}>{c.status}</span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                  <span>Entities: {c.entity_count}</span>
                  <span>Evidence: {c.evidence_count}</span>
                  <span>{formatRelativeTime(c.updated_at)}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Recent Jobs */}
        <div className="bg-surface rounded-lg border border-border p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Recent Jobs</h2>
            <Link href="/jobs" className="text-xs text-blue-400 hover:text-blue-300">View all →</Link>
          </div>
          <div className="space-y-3">
            {jobs?.length === 0 && (
              <p className="text-sm text-gray-500 text-center py-4">No jobs yet.</p>
            )}
            {jobs?.map(j => (
              <div key={j.id} className="p-3 rounded-lg bg-surface-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400 font-mono">{j.id.slice(0, 8)}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(j.status)}`}>
                    {j.status === 'RUNNING' ? '🔄 ' : ''}{j.status}
                  </span>
                </div>
                <div className="text-sm mt-1">{j.job_type.replace('_', ' ')}</div>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                  <span>Findings: {j.findings_count}</span>
                  {j.duration_seconds && <span>Duration: {formatDuration(j.duration_seconds)}</span>}
                  <span>{formatRelativeTime(j.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-surface rounded-lg border border-border p-5">
        <h2 className="font-semibold mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <Link href="/cases" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors">
            + New Case
          </Link>
          <Link href="/jobs" className="px-4 py-2 bg-surface-2 hover:bg-border border border-border rounded-lg text-sm font-medium transition-colors">
            View Job Queue
          </Link>
          <Link href="/reports" className="px-4 py-2 bg-surface-2 hover:bg-border border border-border rounded-lg text-sm font-medium transition-colors">
            Reports Library
          </Link>
          <Link href="/settings" className="px-4 py-2 bg-surface-2 hover:bg-border border border-border rounded-lg text-sm font-medium transition-colors">
            Configure LLM Providers
          </Link>
        </div>
      </div>
    </div>
  )
}
