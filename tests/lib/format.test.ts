import { describe, it, expect } from 'vitest'

import {
  formatDate,
  formatDateTime,
  formatRelativeTime,
  formatSmartDate,
  formatNumber,
  formatPercent,
  formatDuration,
  truncate,
  capitalize,
  toTitleCase,
  normalizeEmail,
  getInitials,
  maskEmail,
  formatBytes,
} from '@/lib/format'

describe('format utilities', () => {
  describe('formatDate', () => {
    it('formats with default pattern', () => {
      expect(formatDate('2024-01-15T10:00:00Z')).toMatch(/Jan.*15.*2024/)
    })

    it('formats with custom pattern', () => {
      expect(formatDate('2024-01-15T10:00:00Z', 'yyyy-MM-dd')).toBe('2024-01-15')
    })

    it('handles Date object', () => {
      expect(formatDate(new Date('2024-01-15T10:00:00Z'))).toMatch(/2024/)
    })

    it('returns dash for null', () => {
      expect(formatDate(null)).toBe('—')
    })

    it('returns dash for undefined', () => {
      expect(formatDate(undefined)).toBe('—')
    })

    it('returns dash for invalid date', () => {
      expect(formatDate('invalid')).toBe('—')
    })
  })

  describe('formatDateTime', () => {
    it('formats date + time', () => {
      const result = formatDateTime('2024-01-15T10:00:00Z')
      expect(result).toMatch(/Jan.*15.*2024/)
      expect(result).toMatch(/\d{1,2}:\d{2}/)
    })
  })

  describe('formatRelativeTime', () => {
    it('shows "ago" for past dates', () => {
      const past = new Date(Date.now() - 3600 * 1000).toISOString()
      expect(formatRelativeTime(past)).toMatch(/ago/i)
    })

    it('returns dash for null', () => {
      expect(formatRelativeTime(null)).toBe('—')
    })

    it('returns dash for invalid', () => {
      expect(formatRelativeTime('invalid')).toBe('—')
    })
  })

  describe('formatSmartDate', () => {
    it('returns dash for null', () => {
      expect(formatSmartDate(null)).toBe('—')
    })

    it('returns dash for invalid', () => {
      expect(formatSmartDate('invalid')).toBe('—')
    })

    it('formats today with time', () => {
      const now = new Date().toISOString()
      const result = formatSmartDate(now)
      expect(result).toMatch(/today/i)
    })
  })

  describe('formatNumber', () => {
    it('formats small numbers', () => {
      expect(formatNumber(42)).toBe('42')
    })

    it('formats thousands', () => {
      expect(formatNumber(1234567)).toMatch(/1,234,567/)
    })
  })

  describe('formatPercent', () => {
    it('formats with 0 decimals', () => {
      expect(formatPercent(85.567)).toBe('86%')
    })

    it('formats with decimals', () => {
      expect(formatPercent(85.567, 2)).toBe('85.57%')
    })
  })

  describe('formatDuration', () => {
    it('formats seconds', () => {
      expect(formatDuration(45)).toBe('45s')
    })

    it('formats minutes', () => {
      expect(formatDuration(125)).toBe('2m 5s')
    })

    it('formats hours', () => {
      expect(formatDuration(3725)).toBe('1h 2m')
    })
  })

  describe('truncate', () => {
    it('does not truncate short strings', () => {
      expect(truncate('hello', 10)).toBe('hello')
    })

    it('truncates long strings', () => {
      expect(truncate('hello world', 8)).toBe('hello w…')
    })

    it('handles exact length', () => {
      expect(truncate('hello', 5)).toBe('hello')
    })
  })

  describe('capitalize', () => {
    it('capitalizes first letter', () => {
      expect(capitalize('hello')).toBe('Hello')
    })

    it('handles empty string', () => {
      expect(capitalize('')).toBe('')
    })

    it('handles already capitalized', () => {
      expect(capitalize('Hello')).toBe('Hello')
    })
  })

  describe('toTitleCase', () => {
    it('converts snake_case', () => {
      expect(toTitleCase('hello_world_foo')).toBe('Hello World Foo')
    })

    it('converts kebab-case', () => {
      expect(toTitleCase('hello-world-foo')).toBe('Hello World Foo')
    })

    it('converts mixed case', () => {
      expect(toTitleCase('HELLO_WORLD')).toBe('Hello World')
    })
  })

  describe('normalizeEmail', () => {
    it('lowercases email', () => {
      expect(normalizeEmail('USER@EXAMPLE.COM')).toBe('user@example.com')
    })

    it('trims whitespace', () => {
      expect(normalizeEmail('  user@example.com  ')).toBe('user@example.com')
    })
  })

  describe('getInitials', () => {
    it('returns initials for two-word name', () => {
      expect(getInitials('John Doe')).toBe('JD')
    })

    it('returns single initial for one-word name', () => {
      expect(getInitials('John')).toBe('J')
    })

    it('handles multiple words', () => {
      expect(getInitials('John Middle Doe')).toBe('JD')
    })

    it('handles extra whitespace', () => {
      expect(getInitials('  John   Doe  ')).toBe('JD')
    })

    it('returns ? for empty', () => {
      expect(getInitials('')).toBe('?')
    })

    it('returns ? for whitespace only', () => {
      expect(getInitials('   ')).toBe('?')
    })
  })

  describe('maskEmail', () => {
    it('masks long local part', () => {
      expect(maskEmail('alice@example.com')).toBe('al***@example.com')
    })

    it('masks short local part', () => {
      expect(maskEmail('ab@example.com')).toBe('a***@example.com')
    })

    it('handles single char local part', () => {
      expect(maskEmail('a@example.com')).toBe('a***@example.com')
    })

    it('returns input if no @', () => {
      expect(maskEmail('notanemail')).toBe('notanemail')
    })
  })

  describe('formatBytes', () => {
    it('formats 0 bytes', () => {
      expect(formatBytes(0)).toBe('0 B')
    })

    it('formats bytes', () => {
      expect(formatBytes(500)).toBe('500 B')
    })

    it('formats KB', () => {
      expect(formatBytes(1024)).toBe('1 KB')
    })

    it('formats MB', () => {
      expect(formatBytes(1024 * 1024)).toBe('1 MB')
    })

    it('formats GB', () => {
      expect(formatBytes(1024 * 1024 * 1024)).toBe('1 GB')
    })

    it('supports decimal places', () => {
      expect(formatBytes(1536, 2)).toBe('1.5 KB')
    })
  })
})
