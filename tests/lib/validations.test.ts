import { describe, it, expect } from 'vitest'

import {
  emailSchema,
  passwordSchema,
  strongPasswordSchema,
  loginSchema,
  registerSchema,
  forgotPasswordSchema,
  resetPasswordSchema,
  changePasswordSchema,
  mfaVerifySchema,
} from '@/lib/validations'

describe('emailSchema', () => {
  it('accepts valid email', () => {
    const result = emailSchema.safeParse('user@example.com')
    expect(result.success).toBe(true)
  })

  it('rejects empty string', () => {
    const result = emailSchema.safeParse('')
    expect(result.success).toBe(false)
  })

  it('rejects invalid email', () => {
    expect(emailSchema.safeParse('not-an-email').success).toBe(false)
    expect(emailSchema.safeParse('user@').success).toBe(false)
    expect(emailSchema.safeParse('@example.com').success).toBe(false)
  })

  it('lowercases the email', () => {
    const result = emailSchema.safeParse('USER@EXAMPLE.COM')
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data).toBe('user@example.com')
    }
  })
})

describe('passwordSchema', () => {
  it('accepts password with min length', () => {
    const result = passwordSchema.safeParse('a'.repeat(12))
    expect(result.success).toBe(true)
  })

  it('rejects short password', () => {
    expect(passwordSchema.safeParse('short').success).toBe(false)
  })
})

describe('strongPasswordSchema', () => {
  it('requires lowercase', () => {
    expect(strongPasswordSchema.safeParse('AAAAAAA123!').success).toBe(false)
  })

  it('requires uppercase', () => {
    expect(strongPasswordSchema.safeParse('aaaaaaa123!').success).toBe(false)
  })

  it('requires number', () => {
    expect(strongPasswordSchema.safeParse('aaaaaaaaAA!').success).toBe(false)
  })

  it('requires special character', () => {
    expect(strongPasswordSchema.safeParse('aaaaaaaaAA1').success).toBe(false)
  })

  it('accepts strong password', () => {
    expect(strongPasswordSchema.safeParse('StrongPass123!').success).toBe(true)
  })
})

describe('loginSchema', () => {
  it('accepts valid login', () => {
    const result = loginSchema.safeParse({
      email: 'user@example.com',
      password: 'password',
    })
    expect(result.success).toBe(true)
  })

  it('requires email', () => {
    expect(loginSchema.safeParse({ password: 'pw' }).success).toBe(false)
  })

  it('requires password', () => {
    expect(loginSchema.safeParse({ email: 'user@example.com' }).success).toBe(false)
  })

  it('validates MFA code format', () => {
    expect(
      loginSchema.safeParse({
        email: 'user@example.com',
        password: 'pw',
        mfaCode: '12345', // 5 digits — invalid
      }).success,
    ).toBe(false)

    expect(
      loginSchema.safeParse({
        email: 'user@example.com',
        password: 'pw',
        mfaCode: '123456', // 6 digits — valid
      }).success,
    ).toBe(true)
  })
})

describe('registerSchema', () => {
  const validData = {
    email: 'user@example.com',
    password: 'StrongPass123!',
    confirmPassword: 'StrongPass123!',
    displayName: 'Test User',
    acceptTerms: true,
  }

  it('accepts valid registration', () => {
    expect(registerSchema.safeParse(validData).success).toBe(true)
  })

  it('requires matching passwords', () => {
    expect(
      registerSchema.safeParse({
        ...validData,
        confirmPassword: 'Different123!',
      }).success,
    ).toBe(false)
  })

  it('requires accepting terms', () => {
    expect(
      registerSchema.safeParse({
        ...validData,
        acceptTerms: false,
      }).success,
    ).toBe(false)
  })

  it('requires display name', () => {
    expect(
      registerSchema.safeParse({
        ...validData,
        displayName: '',
      }).success,
    ).toBe(false)
  })
})

describe('forgotPasswordSchema', () => {
  it('accepts valid email', () => {
    expect(forgotPasswordSchema.safeParse({ email: 'user@example.com' }).success).toBe(true)
  })

  it('requires email', () => {
    expect(forgotPasswordSchema.safeParse({ email: '' }).success).toBe(false)
  })
})

describe('resetPasswordSchema', () => {
  it('accepts valid reset', () => {
    expect(
      resetPasswordSchema.safeParse({
        token: 'abc',
        password: 'StrongPass123!',
        confirmPassword: 'StrongPass123!',
      }).success,
    ).toBe(true)
  })

  it('requires matching passwords', () => {
    expect(
      resetPasswordSchema.safeParse({
        token: 'abc',
        password: 'StrongPass123!',
        confirmPassword: 'Different123!',
      }).success,
    ).toBe(false)
  })
})

describe('changePasswordSchema', () => {
  it('accepts valid change', () => {
    expect(
      changePasswordSchema.safeParse({
        currentPassword: 'OldPass123!',
        newPassword: 'NewPass123!',
        confirmPassword: 'NewPass123!',
      }).success,
    ).toBe(true)
  })

  it('rejects same current + new password', () => {
    expect(
      changePasswordSchema.safeParse({
        currentPassword: 'SamePass123!',
        newPassword: 'SamePass123!',
        confirmPassword: 'SamePass123!',
      }).success,
    ).toBe(false)
  })
})

describe('mfaVerifySchema', () => {
  it('accepts 6-digit code', () => {
    expect(mfaVerifySchema.safeParse({ code: '123456' }).success).toBe(true)
  })

  it('rejects non-6-digit code', () => {
    expect(mfaVerifySchema.safeParse({ code: '12345' }).success).toBe(false)
    expect(mfaVerifySchema.safeParse({ code: '1234567' }).success).toBe(false)
    expect(mfaVerifySchema.safeParse({ code: 'abcdef' }).success).toBe(false)
  })

  it('requires code', () => {
    expect(mfaVerifySchema.safeParse({ code: '' }).success).toBe(false)
  })
})
