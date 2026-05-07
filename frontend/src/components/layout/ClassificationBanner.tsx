import { cookies } from 'next/headers'
import {
  CLASSIFICATION_COOKIE,
  getClassificationStyle,
  normalizeClassification,
  type ClassificationLevel,
} from '@/lib/classification'

interface ClassificationBannerProps {
  position: 'top' | 'bottom'
  /** Optional explicit override (e.g. case-detail pages). */
  level?: ClassificationLevel
}

/**
 * Server component that renders a NATO/USG-style classification band.
 * Reads ATALAYA_SESSION_CLASSIFICATION cookie; defaults to UNCLASSIFIED.
 */
export default function ClassificationBanner({
  position,
  level,
}: ClassificationBannerProps) {
  const cookieStore = cookies()
  const fromCookie = cookieStore.get(CLASSIFICATION_COOKIE)?.value
  const resolved: ClassificationLevel =
    level ?? normalizeClassification(fromCookie)
  const style = getClassificationStyle(resolved)

  return (
    <div
      role="status"
      aria-label={`Classification: ${style.longLabel}`}
      className={`${style.bandClass} flex items-center justify-center px-3 py-1 text-xs font-bold uppercase tracking-widest select-none ${
        position === 'top' ? 'border-b border-black/30' : 'border-t border-black/30'
      }`}
    >
      <span aria-hidden className="mx-2 hidden sm:inline">{'//'}</span>
      <span>{style.longLabel}</span>
      <span aria-hidden className="mx-2 hidden sm:inline">{'//'}</span>
    </div>
  )
}
