'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { fetcher, api } from '@/lib/api'
import type { Report, Case } from '@/types'
import { formatRelativeTime, getStatusColor } from '@/lib/utils'
import { FileText, Download, Plus, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

const REPORT_TYPES = ['EXECUTIVE_SUMMARY', 'TECHNICAL', 'TIMELINE', 'ENTITY_REPORT', 'THREAT_ASSESSMENT', 'FULL']

export default function ReportsPage() {
  const [showNew, setShowNew] = useState(false)
  const [selectedCase, setSelectedCase] = useState('')
  const [reportType, setReportType] = useState('EXECUTIVE_SUMMARY')
  const [format, setFormat] = useState('MARKDOWN')
  const [generating, setGenerating] = useState(false)

  const { data: reports, mutate } = useSWR<Report[]>('/reports?limit=50', fetcher, { refreshInterval: 10000 })
  const { data: cases } = useSWR<Case[]>('/cases?limit=100', fetcher)

  async function handleGenerate() {
    if (!selectedCase) return
    setGenerating(true)
    try {
      await api.generateReport({ case_id: selectedCase, report_type: reportType, format })
      toast.success('Report generation started')
      setShowNew(false)
      setSelectedCase('')
      mutate()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setGenerating(false)
    }
  }

  const grouped = reports?.reduce<Record<string, Report[]>>((acc, r) => {
    const key = r.case_id ?? 'unknown'
    acc[key] = [...(acc[key] ?? []), r]
    return acc
  }, {}) ?? {}

  const caseMap = Object.fromEntries((cases ?? []).map(c => [c.id, c]))

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Reports</h1>
        <div className="flex items-center gap-2">
          <button onClick={() => mutate()} className="p-2 rounded-lg bg-surface border border-border hover:border-gray-400 transition-colors">
            <RefreshCw className="w-4 h-4 text-gray-400" />
          </button>
          <button
            onClick={() => setShowNew(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" /> Generate Report
          </button>
        </div>
      </div>

      {/* New report dialog */}
      {showNew && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-surface border border-border rounded-xl p-6 w-full max-w-md space-y-4">
            <h2 className="font-semibold text-lg">Generate Report</h2>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Case *</label>
              <select
                value={selectedCase}
                onChange={e => setSelectedCase(e.target.value)}
                className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="">Select a case...</option>
                {cases?.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Report Type</label>
              <select
                value={reportType}
                onChange={e => setReportType(e.target.value)}
                className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              >
                {REPORT_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1 block">Format</label>
              <select
                value={format}
                onChange={e => setFormat(e.target.value)}
                className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="MARKDOWN">Markdown</option>
                <option value="JSON">JSON</option>
                <option value="PDF">PDF</option>
              </select>
            </div>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowNew(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">Cancel</button>
              <button
                onClick={handleGenerate}
                disabled={generating || !selectedCase}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
              >
                {generating ? 'Generating...' : 'Generate'}
              </button>
            </div>
          </div>
        </div>
      )}

      {reports?.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No reports yet. Generate your first report.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped).map(([caseId, caseReports]) => (
            <div key={caseId}>
              <div className="flex items-center gap-2 mb-3">
                <h2 className="text-sm font-semibold text-gray-300">
                  {caseMap[caseId]?.title ?? 'Unknown Case'}
                </h2>
                <span className="text-xs text-gray-500">({caseReports.length})</span>
              </div>
              <div className="bg-surface border border-border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-surface-2">
                      <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Title</th>
                      <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Type</th>
                      <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Format</th>
                      <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Status</th>
                      <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Created</th>
                      <th className="text-right px-4 py-3 text-xs text-gray-400 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {caseReports.map((r, i) => (
                      <tr key={r.id} className={`border-b border-border/50 hover:bg-surface-2 transition-colors ${i % 2 !== 0 ? 'bg-surface-2/30' : ''}`}>
                        <td className="px-4 py-3 text-sm max-w-xs truncate">{r.title}</td>
                        <td className="px-4 py-3 text-xs text-gray-400">{r.report_type.replace(/_/g, ' ')}</td>
                        <td className="px-4 py-3">
                          <span className="text-xs px-2 py-0.5 bg-surface-2 rounded text-gray-400">{r.format}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(r.status)}`}>{r.status}</span>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-400">{formatRelativeTime(r.created_at)}</td>
                        <td className="px-4 py-3 text-right">
                          {r.status === 'COMPLETED' && r.file_path && (
                            <a
                              href={`/api/v1/reports/${r.id}/download`}
                              className="flex items-center gap-1.5 ml-auto w-fit text-xs text-gray-400 hover:text-blue-400 transition-colors"
                            >
                              <Download className="w-3.5 h-3.5" /> Download
                            </a>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
