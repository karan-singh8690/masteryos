/**
 * Gradient avatar utilities — deterministic gradient classes for avatars.
 *
 * Given a seed (typically a user id or email), returns a Tailwind gradient
 * class string that can be applied to an avatar fallback. The same seed will
 * always map to the same gradient, providing consistent per-user colors
 * without storing any state.
 */

// Emerald / teal forward palette, with a few complementary hues for variety.
// All gradients use 500–700 stops to ensure strong contrast with white text.
const AVATAR_GRADIENTS = [
  'from-emerald-500 to-teal-600',
  'from-teal-500 to-emerald-600',
  'from-green-500 to-emerald-600',
  'from-cyan-500 to-emerald-600',
  'from-emerald-500 to-cyan-600',
  'from-emerald-600 to-green-700',
  'from-teal-500 to-cyan-600',
  'from-lime-500 to-emerald-600',
] as const

/**
 * Hash a string into a stable positive integer.
 */
function hashSeed(seed: string): number {
  let hash = 0
  for (let i = 0; i < seed.length; i++) {
    hash = (hash << 5) - hash + seed.charCodeAt(i)
    hash |= 0 // Convert to 32-bit integer
  }
  return Math.abs(hash)
}

/**
 * Returns the Tailwind gradient class pair (e.g. "from-emerald-500 to-teal-600")
 * for a given seed string.
 */
export function getAvatarGradient(seed: string): string {
  if (!seed) return AVATAR_GRADIENTS[0]!
  return AVATAR_GRADIENTS[hashSeed(seed) % AVATAR_GRADIENTS.length]!
}

/**
 * Returns the full Tailwind class string for a gradient avatar background.
 * Apply this to an element that also has `bg-gradient-to-br text-white`.
 */
export function getGradientAvatarClasses(seed: string): string {
  return `bg-gradient-to-br ${getAvatarGradient(seed)} text-white`
}

/* ============================================================
   Auto-generated gradient avatars (email-based)
   ============================================================ */

/** A CSS `linear-gradient` string plus a human-readable label. */
export interface AvatarGradient {
  /** Full CSS background-image value, e.g. `linear-gradient(135deg, #10B981, #34D399)`. */
  gradient: string
  /** Short semantic name, useful for debugging / alt text. */
  label: string
}

/** Ten pre-defined gradient pairs covering a broad, accessible palette. */
const EMAIL_GRADIENTS: AvatarGradient[] = [
  { gradient: 'linear-gradient(135deg, #10B981, #34D399)', label: 'emerald-to-teal' },
  { gradient: 'linear-gradient(135deg, #8B5CF6, #A855F7)', label: 'violet-to-purple' },
  { gradient: 'linear-gradient(135deg, #3B82F6, #06B6D4)', label: 'blue-to-cyan' },
  { gradient: 'linear-gradient(135deg, #F97316, #EF4444)', label: 'orange-to-red' },
  { gradient: 'linear-gradient(135deg, #EC4899, #F43F5E)', label: 'pink-to-rose' },
  { gradient: 'linear-gradient(135deg, #F59E0B, #EAB308)', label: 'amber-to-yellow' },
  { gradient: 'linear-gradient(135deg, #6366F1, #3B82F6)', label: 'indigo-to-blue' },
  { gradient: 'linear-gradient(135deg, #14B8A6, #06B6D4)', label: 'teal-to-cyan' },
  { gradient: 'linear-gradient(135deg, #D946EF, #EC4899)', label: 'fuchsia-to-pink' },
  { gradient: 'linear-gradient(135deg, #84CC16, #22C55E)', label: 'lime-to-green' },
]

/**
 * Deterministic 32-bit hash (djb2 variant) for a string.
 * Returns a non-negative integer.
 */
function hashString(input: string): number {
  let hash = 5381
  for (let i = 0; i < input.length; i++) {
    hash = (hash << 5) + hash + input.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}

/**
 * Derive up to two uppercase initials from an email's local part.
 * Splits on common separators (`.`, `_`, `-`, `+`) and takes the first
 * letter of the first two segments, falling back to the first 1–2 chars.
 */
function initialsFromEmail(email: string): string {
  const localPart = email.split('@')[0] ?? ''
  const segments = localPart.split(/[._\-+]/).filter(Boolean)

  if (segments.length >= 2) {
    const first = segments[0]!.charAt(0)
    const second = segments[1]!.charAt(0)
    return (first + second).toUpperCase()
  }

  const trimmed = localPart.trim()
  if (trimmed.length >= 2) return trimmed.slice(0, 2).toUpperCase()
  if (trimmed.length === 1) return trimmed.toUpperCase()
  return '?'
}

export interface GeneratedAvatar {
  initials: string
  gradient: string
  label: string
}

/**
 * Generate a deterministic gradient + initials pair from an email address.
 *
 * The same email always maps to the same gradient, so avatars are stable
 * across renders without persisting any state.
 *
 * @example
 * const { initials, gradient } = generateAvatar('jane.doe@example.com')
 * // → { initials: 'JD', gradient: 'linear-gradient(135deg, #10B981, #34D399)', ... }
 */
export function generateAvatar(email: string): GeneratedAvatar {
  const normalized = (email || '').trim().toLowerCase()
  const index = normalized.length > 0 ? hashString(normalized) % EMAIL_GRADIENTS.length : 0
  const { gradient, label } = EMAIL_GRADIENTS[index]!
  const initials = initialsFromEmail(normalized)
  return { initials, gradient, label }
}
