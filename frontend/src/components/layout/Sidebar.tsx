'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, FolderOpen, Network, Activity,
  FileText, Settings, LogOut, Hexagon, ScrollText,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { clearAccessToken } from '@/lib/api'

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/cases', label: 'Cases', icon: FolderOpen },
  { href: '/entities', label: 'Entities', icon: Network },
  { href: '/jobs', label: 'Jobs', icon: Activity },
  { href: '/reports', label: 'Reports', icon: FileText },
  { href: '/audit', label: 'Audit', icon: ScrollText },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-56 bg-surface border-r border-border flex flex-col shrink-0">
      {/* Logo */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Hexagon className="w-6 h-6 text-blue-400" strokeWidth={1.5} />
          <span className="font-bold text-lg tracking-tight">Atalaya</span>
        </div>
        <p className="text-xs text-gray-500 mt-0.5">OSINT Platform</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== '/' && pathname.startsWith(href))
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                active
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-surface-2',
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Bottom */}
      <div className="p-3 border-t border-border space-y-1">
        <Link
          href="/settings"
          className={cn(
            'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
            pathname === '/settings'
              ? 'bg-blue-600/20 text-blue-400'
              : 'text-gray-400 hover:text-gray-200 hover:bg-surface-2',
          )}
        >
          <Settings className="w-4 h-4" />
          Settings
        </Link>
        <button
          onClick={() => {
            clearAccessToken()
            window.location.href = '/login'
          }}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-400 hover:text-red-400 hover:bg-red-400/10 transition-colors w-full text-left"
          aria-label="Sign out"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </div>
    </aside>
  )
}
