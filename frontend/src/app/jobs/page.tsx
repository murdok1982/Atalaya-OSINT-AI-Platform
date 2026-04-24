'use client'

import useSWR from 'swr'
import { fetcher, api } from '@/lib/api'
import type { Job } from '@/types'
import { formatRelativeTime, formatDuration, getStatusColor } from '@/lib/utils'
import { RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

function JobStatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${getStatusColor(status)}`}>
      {status === 'RUNNING' && <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />}
      {status}
    </span>
  )
}

export default function JobsPage() {
  const { data: jobs, mutate } = useSWR<Job[]>('/jobs?limit=50', fetcher, { refreshInterval: 5000 })

  async function handleCancel(jobId: string) {
    try {
      await api.cancelJob(jobId)
      toast.success('Job cancelled')
      mutate()
    } catch (e: any) {
      toast.error(e.message)
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Job Queue</h1>
        <button onClick={() => mutate()} className="p-2 rounded-lg bg-surface border border-border hover:border-gray-400 transition-colors">
          <RefreshCw className="w-4 h-4 text-gray-400" />
        </button>
      </div>

      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-2">
              <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">ID</th>
              <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Type</th>
              <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Status</th>
              <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Findings</th>
              <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Duration</th>
              <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Created</th>
              <th className="text-right px-4 py-3 text-xs text-gray-400 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {jobs?.map((j, i) => (
              <tr key={j.id} className={`border-b border-border/50 hover:bg-surface-2 transition-colors ${i % 2 === 0 ? '' : 'bg-surface-2/30'}`}>
                <td className="px-4 py-3 font-mono text-xs text-gray-400">{j.id.slice(0, 8)}</td>
                <td className="px-4 py-3 text-xs">{j.job_type.replace(/_/g, ' ')}</td>
                <td className="px-4 py-3"><JobStatusBadge status={j.status} /></td>
                <td className="px-4 py-3 text-xs">{j.findings_count}</td>
                <td className="px-4 py-3 text-xs text-gray-400">{formatDuration(j.duration_seconds)}</td>
                <td className="px-4 py-3 text-xs text-gray-400">{formatRelativeTime(j.created_at)}</td>
                <td className="px-4 py-3 text-right">
                  {['PENDING', 'QUEUED', 'RUNNING'].includes(j.status) && (
                    <button
                      onClick={() => handleCancel(j.id)}
                      className="text-xs text-red-400 hover:text-red-300 transition-colors"
                    >
                      Cancel
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {jobs?.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-gray-500 text-sm">No jobs yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
