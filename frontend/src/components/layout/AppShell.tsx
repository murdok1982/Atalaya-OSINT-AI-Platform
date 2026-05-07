'use client'

import { usePathname } from 'next/navigation'
import Sidebar from './Sidebar'
import Header from './Header'

/**
 * AppShell hides the sidebar/header chrome on routes that should render
 * fullscreen (login). Everything inside the shell is client-side because
 * Sidebar/Header read pathname.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isAuthRoute = pathname?.startsWith('/login') ?? false

  if (isAuthRoute) {
    return <main className="flex-1 overflow-y-auto">{children}</main>
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}
