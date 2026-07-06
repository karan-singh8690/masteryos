/**
 * Zod validation schemas for authentication forms.
 *
 * These schemas complement (not replace) server-side validation.
 * They provide immediate client-side feedback for common errors.
 */

import { z } from 'zod'

import { PASSWORD_MIN_LENGTH } from '@/lib/constants'

// ============================================================
// Email
// ============================================================

export const emailSchema = z
  .string()
  .min(1, 'Email is required')
  .email('Please enter a valid email address')
  .max(255, 'Email is too long')
  .transform((v) => v.trim().toLowerCase())

// ============================================================
// Password
// ============================================================

export const passwordSchema = z
  .string()
  .min(PASSWORD_MIN_LENGTH, `Password must be at least ${PASSWORD_MIN_LENGTH} characters`)
  .max(128, 'Password is too long (max 128 characters)')

export const strongPasswordSchema = passwordSchema
  .refine((v) => /[a-z]/.test(v), 'Password must contain a lowercase letter')
  .refine((v) => /[A-Z]/.test(v), 'Password must contain an uppercase letter')
  .refine((v) => /[0-9]/.test(v), 'Password must contain a number')
  .refine(
    (v) => /[^a-zA-Z0-9]/.test(v),
    'Password must contain a special character',
  )

// ============================================================
// Display name
// ============================================================

export const displayNameSchema = z
  .string()
  .min(1, 'Display name is required')
  .max(100, 'Display name is too long (max 100 characters)')
  .transform((v) => v.trim())

// ============================================================
// Login
// ============================================================

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, 'Password is required'),
  mfaCode: z
    .string()
    .optional()
    .refine((v) => !v || /^\d{6}$/.test(v), 'MFA code must be 6 digits'),
  recoveryCode: z.string().optional(),
})

export type LoginFormData = z.infer<typeof loginSchema>

// ============================================================
// Register
// ============================================================

export const registerSchema = z
  .object({
    email: emailSchema,
    password: strongPasswordSchema,
    confirmPassword: z.string().min(1, 'Please confirm your password'),
    displayName: displayNameSchema,
    timezone: z.string().default('UTC'),
    locale: z.string().default('en-US'),
    acceptTerms: z.boolean().refine((v) => v === true, 'You must accept the terms'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

export type RegisterFormData = z.infer<typeof registerSchema>

// ============================================================
// Forgot Password
// ============================================================

export const forgotPasswordSchema = z.object({
  email: emailSchema,
})

export type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>

// ============================================================
// Reset Password
// ============================================================

export const resetPasswordSchema = z
  .object({
    token: z.string().min(1, 'Reset token is required'),
    password: strongPasswordSchema,
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

export type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>

// ============================================================
// Change Password
// ============================================================

export const changePasswordSchema = z
  .object({
    currentPassword: z.string().min(1, 'Current password is required'),
    newPassword: strongPasswordSchema,
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })
  .refine((data) => data.currentPassword !== data.newPassword, {
    message: 'New password must be different from current password',
    path: ['newPassword'],
  })

export type ChangePasswordFormData = z.infer<typeof changePasswordSchema>

// ============================================================
// Verify Email
// ============================================================

export const verifyEmailSchema = z.object({
  token: z.string().min(1, 'Verification token is required'),
})

export type VerifyEmailFormData = z.infer<typeof verifyEmailSchema>

// ============================================================
// MFA
// ============================================================

export const mfaVerifySchema = z.object({
  code: z
    .string()
    .min(1, 'Code is required')
    .refine((v) => /^\d{6}$/.test(v), 'Code must be 6 digits'),
})

export type MfaVerifyFormData = z.infer<typeof mfaVerifySchema>

export const mfaEnableSchema = z.object({
  totpCode: z
    .string()
    .min(1, 'Code is required')
    .refine((v) => /^\d{6}$/.test(v), 'Code must be 6 digits'),
})

export type MfaEnableFormData = z.infer<typeof mfaEnableSchema>

export const mfaDisableSchema = z.object({
  password: z.string().min(1, 'Password is required'),
})

export type MfaDisableFormData = z.infer<typeof mfaDisableSchema>

export const mfaRecoverySchema = z.object({
  recoveryCode: z
    .string()
    .min(1, 'Recovery code is required')
    .transform((v) => v.trim().toUpperCase()),
})

export type MfaRecoveryFormData = z.infer<typeof mfaRecoverySchema>

// ============================================================
// Profile
// ============================================================

export const updateProfileSchema = z.object({
  displayName: displayNameSchema,
  timezone: z.string().min(1, 'Timezone is required'),
  locale: z.string().min(1, 'Locale is required'),
  avatarUrl: z.string().url('Invalid URL').optional().or(z.literal('')),
})

export type UpdateProfileFormData = z.infer<typeof updateProfileSchema>

// ============================================================
// Password strength calculator
// ============================================================

export interface PasswordStrength {
  score: 0 | 1 | 2 | 3 | 4
  label: 'Very Weak' | 'Weak' | 'Fair' | 'Good' | 'Strong'
  percentage: number
  color: string
}

export function calculatePasswordStrength(password: string): PasswordStrength {
  if (!password) {
    return { score: 0, label: 'Very Weak', percentage: 0, color: 'bg-destructive' }
  }

  let score = 0
  const checks = [
    password.length >= PASSWORD_MIN_LENGTH,
    /[a-z]/.test(password),
    /[A-Z]/.test(password),
    /[0-9]/.test(password),
    /[^a-zA-Z0-9]/.test(password),
    password.length >= 16,
  ]

  score = checks.filter(Boolean).length

  if (score <= 1) {
    return { score: 1, label: 'Weak', percentage: 20, color: 'bg-destructive' }
  }
  if (score <= 2) {
    return { score: 2, label: 'Fair', percentage: 40, color: 'bg-warning' }
  }
  if (score <= 3) {
    return { score: 3, label: 'Good', percentage: 60, color: 'bg-yellow-500' }
  }
  if (score <= 4) {
    return { score: 3, label: 'Good', percentage: 80, color: 'bg-success' }
  }
  return { score: 4, label: 'Strong', percentage: 100, color: 'bg-success' }
}
