import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { formatDistanceToNow, format } from 'date-fns'
import { es } from 'date-fns/locale'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatRelativeTime(dateStr: string): string {
  try {
    return formatDistanceToNow(new Date(dateStr), { addSuffix: true })
  } catch {
    return dateStr
  }
}

export function formatAbsoluteTime(dateStr: string): string {
  try {
    return format(new Date(dateStr), 'yyyy-MM-dd HH:mm')
  } catch {
    return dateStr
  }
}

export function getPriorityColor(priority: string): string {
  const colors: Record<string, string> = {
    CRITICAL: 'text-red-400 bg-red-400/10 border-red-400/30',
    HIGH: 'text-orange-400 bg-orange-400/10 border-orange-400/30',
    MEDIUM: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30',
    LOW: 'text-green-400 bg-green-400/10 border-green-400/30',
  }
  return colors[priority] ?? 'text-gray-400 bg-gray-400/10 border-gray-400/30'
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    OPEN: 'text-blue-400 bg-blue-400/10',
    ACTIVE: 'text-green-400 bg-green-400/10',
    CLOSED: 'text-gray-400 bg-gray-400/10',
    ARCHIVED: 'text-gray-500 bg-gray-500/10',
    RUNNING: 'text-blue-400 bg-blue-400/10',
    COMPLETED: 'text-green-400 bg-green-400/10',
    FAILED: 'text-red-400 bg-red-400/10',
    PENDING: 'text-gray-400 bg-gray-400/10',
    QUEUED: 'text-yellow-400 bg-yellow-400/10',
    CANCELLED: 'text-gray-500 bg-gray-500/10',
  }
  return colors[status] ?? 'text-gray-400 bg-gray-400/10'
}

export function getEntityTypeIcon(entityType: string): string {
  const icons: Record<string, string> = {
    PERSON: '👤', ORGANIZATION: '🏢', DOMAIN: '🌐', EMAIL: '📧',
    PHONE: '📱', IP: '🖥️', IP_ADDRESS: '🖥️', ASN: '🔌', HANDLE: '@',
    CHANNEL: '📢', URL: '🔗', DOCUMENT: '📄', IMAGE: '🖼️',
    LOCATION: '📍', ALIAS: '🔀', USERNAME: '@',
    HASH: '#', CRYPTOCURRENCY_ADDRESS: '₿',
    VULNERABILITY: '⚠️', MALWARE: '🦠', TOOL: '🔧', OTHER: '❔',
  }
  return icons[entityType] ?? '❓'
}

export function truncateHash(hash: string, chars = 8): string {
  return hash.length > chars ? `${hash.slice(0, chars)}...` : hash
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

export function formatDuration(seconds: number | null): string {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const min = Math.floor(seconds / 60)
  const sec = Math.round(seconds % 60)
  return `${min}m ${sec}s`
}
