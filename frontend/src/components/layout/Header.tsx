'use client'

import { usePathname } from 'next/navigation'

const routeLabels: Record<string, string> = {
  '/': 'Dashboard',
  '/cases': 'Cases',
  '/entities': 'Entities',
  '/jobs': 'Job Queue',
  '/reports': 'Reports',
  '/settings': 'Settings',
}

export default function Header() {
  const pathname = usePathname()
  const label = Object.entries(routeLabels).find(([key]) =>
    key === '/' ? pathname === '/' : pathname.startsWith(key) && key !== '/'
  )?.[1] ?? 'Atalaya'

  return (
    <header className="h-14 border-b border-border bg-surface flex items-center px-6 shrink-0">
      <h1 className="font-semibold text-sm text-gray-200">{label}</h1>
      <div className="ml-auto flex items-center gap-3">
        <span className="text-xs text-gray-500 font-mono">localhost:3000</span>
      </div>
    </header>
  )
}
