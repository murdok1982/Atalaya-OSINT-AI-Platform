'use client'

import { usePathname } from 'next/navigation'
import useSWR from 'swr'
import { fetcher, type MeResponse } from '@/lib/api'
import { ShieldCheck } from 'lucide-react'
import { normalizeClassification, getClassificationStyle } from '@/lib/classification'

const routeLabels: Record<string, string> = {
  '/': 'Dashboard',
  '/cases': 'Cases',
  '/entities': 'Entities',
  '/jobs': 'Job Queue',
  '/reports': 'Reports',
  '/audit': 'Audit Trail',
  '/settings': 'Settings',
}

export default function Header() {
  const pathname = usePathname()
  const label =
    Object.entries(routeLabels).find(([key]) =>
      key === '/' ? pathname === '/' : pathname.startsWith(key) && key !== '/',
    )?.[1] ?? 'Atalaya'

  // Best-effort: if /auth/me fails (e.g. unauthenticated on /login), fail
  // silently — don't break the layout chrome.
  const { data: me } = useSWR<MeResponse>('/auth/me', fetcher, {
    shouldRetryOnError: false,
    revalidateOnFocus: false,
  })

  const clearance = normalizeClassification(me?.clearance_level)
  const clearanceStyle = getClassificationStyle(clearance)

  return (
    <header className="h-14 border-b border-border bg-surface flex items-center px-6 shrink-0">
      <h1 className="font-semibold text-sm text-gray-200">{label}</h1>
      <div className="ml-auto flex items-center gap-3">
        {me ? (
          <div
            className="flex items-center gap-2"
            aria-label={`Signed in as ${me.username}`}
          >
            <span className="text-xs text-gray-400 font-mono">{me.username}</span>
            <span
              className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${clearanceStyle.bandClass}`}
              title={`Clearance: ${clearanceStyle.longLabel}`}
            >
              <ShieldCheck className="w-3 h-3" aria-hidden />
              {clearanceStyle.label}
            </span>
          </div>
        ) : (
          <span className="text-xs text-gray-500 font-mono">unauthenticated</span>
        )}
      </div>
    </header>
  )
}
