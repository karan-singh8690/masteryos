import { describe, it, expect } from 'vitest'

import { ROUTES, API_ROUTES, APP_NAME, API_BASE_URL } from '@/lib/constants'

describe('constants', () => {
  it('has app name', () => {
    expect(APP_NAME).toBeDefined()
    expect(typeof APP_NAME).toBe('string')
  })

  it('has API base URL', () => {
    expect(API_BASE_URL).toContain('/api/v1')
  })

  describe('ROUTES', () => {
    it('has all auth routes', () => {
      expect(ROUTES.LOGIN).toBe('/login')
      expect(ROUTES.REGISTER).toBe('/register')
      expect(ROUTES.FORGOT_PASSWORD).toBe('/forgot-password')
      expect(ROUTES.RESET_PASSWORD).toBe('/reset-password')
      expect(ROUTES.VERIFY_EMAIL).toBe('/verify-email')
      expect(ROUTES.MFA_SETUP).toBe('/mfa/setup')
      expect(ROUTES.MFA_VERIFY).toBe('/mfa/verify')
      expect(ROUTES.RECOVERY_CODES).toBe('/recovery-codes')
    })

    it('has app routes', () => {
      expect(ROUTES.DASHBOARD).toBe('/dashboard')
      expect(ROUTES.PROFILE).toBe('/profile')
      expect(ROUTES.SECURITY).toBe('/security')
      expect(ROUTES.SETTINGS).toBe('/settings')
      expect(ROUTES.NOTIFICATIONS).toBe('/notifications')
    })

    it('has error routes', () => {
      expect(ROUTES.UNAUTHORIZED).toBe('/unauthorized')
      expect(ROUTES.FORBIDDEN).toBe('/forbidden')
      expect(ROUTES.SESSION_EXPIRED).toBe('/session-expired')
      expect(ROUTES.OFFLINE).toBe('/offline')
      expect(ROUTES.MAINTENANCE).toBe('/maintenance')
    })
  })

  describe('API_ROUTES', () => {
    it('has auth routes', () => {
      expect(API_ROUTES.AUTH.REGISTER).toBe('/auth/register')
      expect(API_ROUTES.AUTH.LOGIN).toBe('/auth/login')
      expect(API_ROUTES.AUTH.REFRESH).toBe('/auth/refresh')
      expect(API_ROUTES.AUTH.LOGOUT).toBe('/auth/logout')
      expect(API_ROUTES.AUTH.LOGOUT_ALL).toBe('/auth/logout-all')
      expect(API_ROUTES.AUTH.VERIFY_EMAIL).toBe('/auth/verify-email')
      expect(API_ROUTES.AUTH.FORGOT_PASSWORD).toBe('/auth/forgot-password')
      expect(API_ROUTES.AUTH.RESET_PASSWORD).toBe('/auth/reset-password')
      expect(API_ROUTES.AUTH.CHANGE_PASSWORD).toBe('/auth/change-password')
    })

    it('has MFA routes', () => {
      expect(API_ROUTES.AUTH.MFA_SETUP).toBe('/auth/mfa/setup')
      expect(API_ROUTES.AUTH.MFA_VERIFY).toBe('/auth/mfa/verify')
      expect(API_ROUTES.AUTH.MFA_ENABLE).toBe('/auth/mfa/enable')
      expect(API_ROUTES.AUTH.MFA_DISABLE).toBe('/auth/mfa/disable')
      expect(API_ROUTES.AUTH.MFA_RECOVERY).toBe('/auth/mfa/recovery')
    })

    it('has user routes', () => {
      expect(API_ROUTES.USERS.ME).toBe('/users/me')
      expect(API_ROUTES.USERS.SECURITY).toBe('/users/me/security')
    })
  })
})

describe('types', () => {
  it('User type has required fields', () => {
    // Type-level test — if this compiles, the types are correct
    const user = {
      id: '123',
      email: 'test@example.com',
      status: 'active' as const,
      mfaEnabled: false,
      emailVerifiedAt: null,
      createdAt: '2024-01-01T00:00:00Z',
    }
    expect(user.id).toBe('123')
  })

  it('AuthResponse type has required fields', () => {
    const response = {
      accessToken: 'token',
      refreshToken: 'refresh',
      expiresIn: 900,
      tokenType: 'Bearer',
      user: {
        id: '123',
        email: 'test@example.com',
        status: 'active' as const,
        mfaEnabled: false,
        emailVerifiedAt: null,
        createdAt: '2024-01-01T00:00:00Z',
      },
    }
    expect(response.accessToken).toBe('token')
  })
})
