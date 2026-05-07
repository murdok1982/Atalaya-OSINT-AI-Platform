// Classification levels — NATO / USG style banner colors.
// The session-level classification is read server-side from a cookie set by
// the backend (cookie name: ATALAYA_SESSION_CLASSIFICATION). Until the backend
// emits it, we default to UNCLASSIFIED.
// TODO(backend): emit ATALAYA_SESSION_CLASSIFICATION cookie on login response,
//               and per-case override via X-Case-Classification header.

export type ClassificationLevel =
  | 'UNCLASSIFIED'
  | 'CUI'
  | 'CONFIDENTIAL'
  | 'SECRET'
  | 'TOP_SECRET'

export const CLASSIFICATION_COOKIE = 'ATALAYA_SESSION_CLASSIFICATION'

export interface ClassificationStyle {
  /** Tailwind classes for background + text on the banner band. */
  bandClass: string
  /** Short text shown on the band. */
  label: string
  /** ARIA label / long form. */
  longLabel: string
}

const STYLES: Record<ClassificationLevel, ClassificationStyle> = {
  UNCLASSIFIED: {
    bandClass: 'bg-green-700 text-white',
    label: 'UNCLASSIFIED',
    longLabel: 'UNCLASSIFIED // Open Source Intelligence',
  },
  CUI: {
    bandClass: 'bg-blue-700 text-white',
    label: 'CUI',
    longLabel: 'CONTROLLED UNCLASSIFIED INFORMATION',
  },
  CONFIDENTIAL: {
    bandClass: 'bg-blue-900 text-white',
    label: 'CONFIDENTIAL',
    longLabel: 'CONFIDENTIAL',
  },
  SECRET: {
    bandClass: 'bg-red-700 text-white',
    label: 'SECRET',
    longLabel: 'SECRET',
  },
  TOP_SECRET: {
    bandClass: 'bg-amber-400 text-black',
    label: 'TOP SECRET',
    longLabel: 'TOP SECRET',
  },
}

export function getClassificationStyle(
  level: ClassificationLevel,
): ClassificationStyle {
  return STYLES[level] ?? STYLES.UNCLASSIFIED
}

const VALID: ReadonlySet<string> = new Set<ClassificationLevel>([
  'UNCLASSIFIED',
  'CUI',
  'CONFIDENTIAL',
  'SECRET',
  'TOP_SECRET',
])

export function normalizeClassification(
  raw: string | undefined | null,
): ClassificationLevel {
  if (!raw) return 'UNCLASSIFIED'
  const upper = raw.toUpperCase().replace(/[\s-]/g, '_')
  return VALID.has(upper) ? (upper as ClassificationLevel) : 'UNCLASSIFIED'
}
