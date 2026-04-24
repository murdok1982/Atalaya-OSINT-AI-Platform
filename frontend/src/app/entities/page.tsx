'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import type { Entity, Case } from '@/types'
import { formatRelativeTime, getEntityTypeIcon } from '@/lib/utils'
import { Network, Search, RefreshCw } from 'lucide-react'
import Link from 'next/link'

const ENTITY_TYPES = ['ALL', 'DOMAIN', 'IP_ADDRESS', 'EMAIL', 'PERSON', 'ORGANIZATION', 'URL', 'PHONE', 'USERNAME', 'HASH', 'CRYPTOCURRENCY_ADDRESS', 'VULNERABILITY', 'MALWARE', 'TOOL', 'OTHER']

export default function EntitiesPage() {
  const [typeFilter, setTypeFilter] = useState('ALL')
  const [search, setSearch] = useState('')

  const params = new URLSearchParams({ limit: '200' })
  if (typeFilter !== 'ALL') params.set('entity_type', typeFilter)
  if (search.trim()) params.set('search', search.trim())

  const { data: entities, mutate } = useSWR<Entity[]>(`/entities?${params}`, fetcher, { refreshInterval: 30000 })
  const { data: cases } = useSWR<Case[]>('/cases?limit=100', fetcher)

  const caseMap = Object.fromEntries((cases ?? []).map(c => [c.id, c]))

  const entityCounts = ENTITY_TYPES.slice(1).reduce<Record<string, number>>((acc, type) => {
    acc[type] = entities?.filter(e => e.entity_type === type).length ?? 0
    return acc
  }, {})

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Entities</h1>
        <button onClick={() => mutate()} className="p-2 rounded-lg bg-surface border border-border hover:border-gray-400 transition-colors">
          <RefreshCw className="w-4 h-4 text-gray-400" />
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search entities by value, label, or source..."
          className="w-full bg-surface border border-border rounded-lg pl-9 pr-4 py-2.5 text-sm focus:outline-none focus:border-blue-500"
        />
      </div>

      {/* Type filters */}
      <div className="flex flex-wrap gap-2">
        {ENTITY_TYPES.map(t => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
              typeFilter === t ? 'bg-blue-600 border-blue-600 text-white' : 'border-border text-gray-400 hover:border-gray-400'
            }`}
          >
            {t !== 'ALL' && <span>{getEntityTypeIcon(t)}</span>}
            {t}
            {t !== 'ALL' && entityCounts[t] > 0 && <span className="opacity-70">({entityCounts[t]})</span>}
          </button>
        ))}
      </div>

      {/* Entities grid */}
      {entities?.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <Network className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No entities found.</p>
        </div>
      ) : (
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-2">
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Type</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Value</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Label</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Case</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Confidence</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Source</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Added</th>
              </tr>
            </thead>
            <tbody>
              {entities?.map((e, i) => (
                <tr key={e.id} className={`border-b border-border/50 hover:bg-surface-2 transition-colors ${i % 2 !== 0 ? 'bg-surface-2/30' : ''}`}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <span>{getEntityTypeIcon(e.entity_type)}</span>
                      <span className="text-xs text-gray-400">{e.entity_type}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs max-w-xs truncate">{e.value}</td>
                  <td className="px-4 py-3 text-xs text-gray-400 max-w-xs truncate">{e.label || '—'}</td>
                  <td className="px-4 py-3">
                    {e.case_id && caseMap[e.case_id] ? (
                      <Link href={`/cases/${e.case_id}`} className="text-xs text-blue-400 hover:text-blue-300 truncate block max-w-xs">
                        {caseMap[e.case_id].title}
                      </Link>
                    ) : (
                      <span className="text-xs text-gray-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-surface-2 rounded-full h-1.5">
                        <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${e.confidence_score * 100}%` }} />
                      </div>
                      <span className="text-xs text-gray-400">{Math.round(e.confidence_score * 100)}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">{e.source || '—'}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{formatRelativeTime(e.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
