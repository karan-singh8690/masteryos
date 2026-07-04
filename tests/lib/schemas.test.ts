import { describe, it, expect } from 'vitest'

import {
  loginSchema,
  registerSchema,
  forgotPasswordSchema,
  resetPasswordSchema,
  changePasswordSchema,
  verifyEmailSchema,
  mfaVerifySchema,
  mfaEnableSchema,
  mfaDisableSchema,
  mfaRecoverySchema,
  updateProfileSchema,
  emailSchema,
  passwordSchema,
  strongPasswordSchema,
  displayNameSchema,
  calculatePasswordStrength,
} from '@/lib/validations'

describe('Schema exports', () => {
  it('all schemas are defined', () => {
    expect(loginSchema).toBeDefined()
    expect(registerSchema).toBeDefined()
    expect(forgotPasswordSchema).toBeDefined()
    expect(resetPasswordSchema).toBeDefined()
    expect(changePasswordSchema).toBeDefined()
    expect(verifyEmailSchema).toBeDefined()
    expect(mfaVerifySchema).toBeDefined()
    expect(mfaEnableSchema).toBeDefined()
    expect(mfaDisableSchema).toBeDefined()
    expect(mfaRecoverySchema).toBeDefined()
    expect(updateProfileSchema).toBeDefined()
    expect(emailSchema).toBeDefined()
    expect(passwordSchema).toBeDefined()
    expect(strongPasswordSchema).toBeDefined()
    expect(displayNameSchema).toBeDefined()
    expect(calculatePasswordStrength).toBeDefined()
  })
})

describe('mfaDisableSchema', () => {
  it('requires password', () => {
    expect(mfaDisableSchema.safeParse({ password: '' }).success).toBe(false)
    expect(mfaDisableSchema.safeParse({ password: 'pass' }).success).toBe(true)
  })
})

describe('mfaRecoverySchema', () => {
  it('requires recovery code', () => {
    expect(mfaRecoverySchema.safeParse({ recoveryCode: '' }).success).toBe(false)
  })

  it('uppercases the code', () => {
    const result = mfaRecoverySchema.safeParse({ recoveryCode: 'abcd-1234' })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.recoveryCode).toBe('ABCD-1234')
    }
  })
})

describe('updateProfileSchema', () => {
  it('requires display name', () => {
    expect(
      updateProfileSchema.safeParse({
        displayName: '',
        timezone: 'UTC',
        locale: 'en-US',
      }).success,
    ).toBe(false)
  })

  it('requires timezone', () => {
    expect(
      updateProfileSchema.safeParse({
        displayName: 'Test',
        timezone: '',
        locale: 'en-US',
      }).success,
    ).toBe(false)
  })

  it('accepts valid profile', () => {
    expect(
      updateProfileSchema.safeParse({
        displayName: 'Test User',
        timezone: 'America/New_York',
        locale: 'en-US',
      }).success,
    ).toBe(true)
  })
})

describe('displayNameSchema', () => {
  it('accepts valid name', () => {
    expect(displayNameSchema.safeParse('John Doe').success).toBe(true)
  })

  it('rejects empty', () => {
    expect(displayNameSchema.safeParse('').success).toBe(false)
  })

  it('rejects too long', () => {
    expect(displayNameSchema.safeParse('a'.repeat(101)).success).toBe(false)
  })

  it('trims whitespace', () => {
    const result = displayNameSchema.safeParse('  John  ')
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data).toBe('John')
    }
  })
})

describe('calculatePasswordStrength edge cases', () => {
  it('returns 0 for empty', () => {
    expect(calculatePasswordStrength('').score).toBe(0)
  })

  it('returns weak for only lowercase', () => {
    expect(calculatePasswordStrength('abcdefghijkl').score).toBeLessThanOrEqual(2)
  })

  it('returns higher for mixed case + numbers', () => {
    expect(
      calculatePasswordStrength('Abcdefghij123').score,
    ).toBeGreaterThanOrEqual(2)
  })

  it('returns strong for complex password', () => {
    expect(
      calculatePasswordStrength('MyStr0ng!P@ssw0rd#2024').score,
    ).toBe(4)
  })

  it('includes color + percentage in result', () => {
    const result = calculatePasswordStrength('test')
    expect(result).toHaveProperty('color')
    expect(result).toHaveProperty('percentage')
    expect(result).toHaveProperty('label')
    expect(typeof result.percentage).toBe('number')
  })
})
