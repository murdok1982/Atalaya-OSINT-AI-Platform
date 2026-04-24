'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { fetcher, api } from '@/lib/api'
import type { Case } from '@/types'
import { formatRelativeTime, getStatusColor, getPriorityColor } from '@/lib/utils'
import { Plus, FolderOpen } from 'lucide-react'
import Link from 'next/link'
import { toast } from 'sonner'

const STATUS_OPTIONS = ['ALL', 'OPEN', 'ACTIVE', 'CLOSED', 'ARCHIVED']
const PRIORITY_OPTIONS = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

export default function CasesPage() {
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [priorityFilter, setPriorityFilter] = useState('ALL')
  const [showNew, setShowNew] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [creating, setCreating] = useState(false)

  const params = new URLSearchParams({ limit: '100' })
  if (statusFilter !== 'ALL') params.set('status', statusFilter)
  if (priorityFilter !== 'ALL') params.set('priority', priorityFilter)

  const { data: cases, mutate } = useSWR<Case[]>(`/cases?${params}`, fetcher, { refreshInterval: 15000 })

  async function handleCreate() {
    if (!newTitle.trim()) return
    setCreating(true)
    try {
      await api.createCase({ title: newTitle, description: newDesc })
      toast.success('Case created')
      setShowNew(false)
      setNewTitle('')
      setNewDesc('')
      mutate()
    } catch (e: any) {
      toast.error(`Failed: ${e.message}`)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Cases</h1>
        <button
          onClick={() => setShowNew(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" /> New Case
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {STATUS_OPTIONS.map(s => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${statusFilter === s ? 'bg-blue-600 border-blue-600 text-white' : 'border-border text-gray-400 hover:border-gray-400'}`}
          >
            {s}
          </button>
        ))}
        <div className="w-px bg-border mx-1" />
        {PRIORITY_OPTIONS.map(p => (
          <button
            key={p}
            onClick={() => setPriorityFilter(p)}
            className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${priorityFilter === p ? 'bg-blue-600 border-blue-600 text-white' : 'border-border text-gray-400 hover:border-gray-400'}`}
          >
            {p}
          </button>
        ))}
      </div>

      {/* New case modal */}
      {showNew && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-surface border border-border rounded-xl p-6 w-full max-w-md space-y-4">
            <h2 className="font-semibold text-lg">New Investigation</h2>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Title *</label>
              <input
                value={newTitle}
                onChange={e => setNewTitle(e.target.value)}
                placeholder="Investigation title..."
                className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Description</label>
              <textarea
                value={newDesc}
                onChange={e => setNewDesc(e.target.value)}
                rows={3}
                placeholder="Scope, objectives, authorization notes..."
                className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 resize-none"
              />
            </div>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowNew(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">Cancel</button>
              <button
                onClick={handleCreate}
                disabled={creating || !newTitle.trim()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
              >
                {creating ? 'Creating...' : 'Create Case'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cases grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {cases?.map(c => (
          <Link key={c.id} href={`/cases/${c.id}`} className="block bg-surface border border-border rounded-lg p-4 hover:border-blue-500/50 transition-colors group">
            <div className={`h-0.5 w-8 rounded mb-3 ${c.priority === 'CRITICAL' ? 'bg-red-500' : c.priority === 'HIGH' ? 'bg-orange-500' : c.priority === 'MEDIUM' ? 'bg-yellow-500' : 'bg-green-500'}`} />
            <div className="flex items-start justify-between gap-2 mb-2">
              <h3 className="font-medium text-sm group-hover:text-blue-300 transition-colors">{c.title}</h3>
              <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full ${getStatusColor(c.status)}`}>{c.status}</span>
            </div>
            {c.description && <p className="text-xs text-gray-500 line-clamp-2 mb-3">{c.description}</p>}
            <div className="flex items-center justify-between text-xs text-gray-500">
              <div className="flex gap-3">
                <span>E:{c.entity_count}</span>
                <span>Ev:{c.evidence_count}</span>
                <span>J:{c.job_count}</span>
              </div>
              <span>{formatRelativeTime(c.updated_at)}</span>
            </div>
            {c.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {c.tags.slice(0, 3).map(t => (
                  <span key={t} className="text-xs px-1.5 py-0.5 bg-surface-2 rounded text-gray-400">{t}</span>
                ))}
              </div>
            )}
          </Link>
        ))}
        {cases?.length === 0 && (
          <div className="col-span-3 text-center py-16 text-gray-500">
            <FolderOpen className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No cases found. Create your first investigation.</p>
          </div>
        )}
      </div>
    </div>
  )
}
