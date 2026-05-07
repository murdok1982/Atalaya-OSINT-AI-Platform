'use client'

import useSWR from 'swr'
import {
  fetcher,
  api,
  type AuditEvent,
  type AuditVerifyResponse,
  type MeResponse,
} from '@/lib/api'
import { formatAbsoluteTime } from '@/lib/utils'
import { ShieldCheck, ShieldAlert, RefreshCw, Lock } from 'lucide-react'
import { useState } from 'react'

// Force dynamic — audit data is per-request and must never be prerendered.
export const dynamic = 'force-dynamic'

export default function AuditPage() {
  const { data: me, isLoading: loadingMe } = useSWR<MeResponse>(
    '/auth/me',
    fetcher,
    { shouldRetryOnError: false, revalidateOnFocus: false },
  )

  const isAdmin =
    !!me?.is_admin || (me?.scopes ?? []).some((s) => s === 'admin' || s === 'audit:read')

  if (loadingMe) {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-gray-500">
        Checking authorization…
      </div>
    )
  }

  if (!me) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-sm text-gray-500">
        <Lock className="w-8 h-8 mb-2 opacity-50" />
        Sign in to access the audit trail.
      </div>
    )
  }

  if (!isAdmin) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-sm text-gray-500">
        <Lock className="w-8 h-8 mb-2 opacity-50" />
        Insufficient privileges. Audit trail is restricted to administrators.
      </div>
    )
  }

  return <AuditView />
}

function AuditView() {
  const [verifyState, setVerifyState] = useState<{
    loading: boolean
    result?: AuditVerifyResponse
    error?: string
  }>({ loading: false })

  const {
    data: events,
    error: listError,
    isLoading,
    mutate,
  } = useSWR<AuditEvent[]>('/audit?limit=200', fetcher, {
    shouldRetryOnError: false,
    revalidateOnFocus: false,
  })

  async function handleVerify() {
    setVerifyState({ loading: true })
    try {
      const res = await api.verifyAudit()
      setVerifyState({ loading: false, result: res })
    } catch (err) {
      setVerifyState({
        loading: false,
        error: err instanceof Error ? err.message : 'Verification failed',
      })
    }
  }

  // Backend may not yet expose /audit*. Be honest with the operator.
  const backendMissing =
    listError instanceof Error && /404|Not Found/i.test(listError.message)

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Audit Trail</h1>
          <p className="text-xs text-gray-500 mt-1">
            Hash-chained audit log. Each entry carries the previous entry&apos;s
            hash; tampering breaks the chain.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => mutate()}
            className="p-2 rounded-lg bg-surface border border-border hover:border-gray-400 transition-colors"
            aria-label="Refresh audit log"
          >
            <RefreshCw className="w-4 h-4 text-gray-400" />
          </button>
          <button
            onClick={handleVerify}
            disabled={verifyState.loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
          >
            <ShieldCheck className="w-4 h-4" aria-hidden />
            {verifyState.loading ? 'Verifying…' : 'Verify Chain'}
          </button>
        </div>
      </div>

      {verifyState.result && (
        <div
          className={`rounded-lg border p-4 text-sm flex items-start gap-3 ${
            verifyState.result.verified
              ? 'border-green-500/30 bg-green-500/10 text-green-300'
              : 'border-red-500/30 bg-red-500/10 text-red-300'
          }`}
        >
          {verifyState.result.verified ? (
            <ShieldCheck className="w-5 h-5 mt-0.5 shrink-0" aria-hidden />
          ) : (
            <ShieldAlert className="w-5 h-5 mt-0.5 shrink-0" aria-hidden />
          )}
          <div>
            <div className="font-semibold">
              {verifyState.result.verified
                ? 'Chain verified'
                : 'Chain integrity FAILED'}
            </div>
            <div className="text-xs opacity-80 mt-1">
              {verifyState.result.total_events} events checked.
              {verifyState.result.invalid_at &&
                ` Tamper detected at: ${verifyState.result.invalid_at}`}
              {verifyState.result.message && ` ${verifyState.result.message}`}
            </div>
          </div>
        </div>
      )}

      {verifyState.error && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4 text-sm text-yellow-300">
          Verification endpoint unavailable: {verifyState.error}
        </div>
      )}

      {backendMissing ? (
        <div className="bg-surface border border-border rounded-lg p-8 text-center">
          <Lock className="w-10 h-10 mx-auto text-gray-500 mb-3 opacity-60" />
          <p className="text-sm text-gray-300 font-medium">
            Pendiente de backend
          </p>
          <p className="text-xs text-gray-500 mt-1">
            The endpoints <span className="font-mono">/api/v1/audit</span> and{' '}
            <span className="font-mono">/api/v1/audit/verify</span> are not
            implemented yet. Once available, this view will populate
            automatically.
          </p>
        </div>
      ) : isLoading ? (
        <div className="flex items-center justify-center h-32 text-sm text-gray-500">
          Loading audit events…
        </div>
      ) : !events || events.length === 0 ? (
        <div className="text-center py-16 text-gray-500 text-sm">
          No audit events recorded yet.
        </div>
      ) : (
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-2">
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">When</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Actor</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Action</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Resource</th>
                <th className="text-left px-4 py-3 text-xs text-gray-400 font-medium">Hash</th>
              </tr>
            </thead>
            <tbody>
              {events.map((ev, i) => (
                <tr
                  key={ev.id}
                  className={`border-b border-border/50 hover:bg-surface-2 transition-colors ${
                    i % 2 !== 0 ? 'bg-surface-2/30' : ''
                  }`}
                >
                  <td className="px-4 py-3 text-xs text-gray-400 font-mono whitespace-nowrap">
                    {formatAbsoluteTime(ev.ts)}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-300">{ev.actor}</td>
                  <td className="px-4 py-3 text-xs text-blue-300 font-mono">
                    {ev.action}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-300 max-w-xs truncate">
                    {ev.resource}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">
                    {ev.hash.slice(0, 12)}…
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
