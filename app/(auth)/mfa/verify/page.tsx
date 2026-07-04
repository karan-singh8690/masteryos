'use client'

import * as React from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Shield } from 'lucide-react'

import { AuthLayout } from '@/components/layout/auth-layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/forms/form'
import { authApi, ApiError, tokenStorage } from '@/lib/api-client'
import { mfaVerifySchema, type MfaVerifyFormData } from '@/lib/validations'
import { ROUTES } from '@/lib/constants'
import { useAuth } from '@/providers/auth-provider'
import { toast } from 'sonner'

export default function MfaVerifyPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { setUser } = useAuth()
  const [error, setError] = React.useState<string | null>(null)

  // Get MFA session token + redirect from URL (set by login page)
  const mfaSessionToken = searchParams.get('mfa_session_token') || ''
  const redirect = searchParams.get('redirect') || ROUTES.DASHBOARD
  const isLoginChallenge = !!mfaSessionToken

  const form = useForm<MfaVerifyFormData>({
    resolver: zodResolver(mfaVerifySchema),
    defaultValues: { code: '' },
  })

  const onSubmit = async (data: MfaVerifyFormData) => {
    setError(null)
    try {
      if (isLoginChallenge) {
        // Login MFA challenge: re-POST /auth/login with mfa_code + mfa_session_token
        const response = await authApi.login({
          email: '', // not needed — mfa_session_token identifies the session
          password: '',
          mfa_session_token: mfaSessionToken,
          mfa_code: data.code,
        } as any)

        tokenStorage.setAccessToken(response.access_token)
        if (response.refresh_token) {
          tokenStorage.setRefreshToken(response.refresh_token)
        }
        document.cookie = 'mastery-authenticated=true; path=/; SameSite=Strict'

        // Fetch user role for middleware
        try {
          const me = await authApi.me()
          if (me.roles?.length) {
            document.cookie = `mastery-role=${me.roles[0]}; path=/; SameSite=Strict`
            setUser(me)
          } else {
            setUser(response.user)
          }
        } catch {
          setUser(response.user)
        }

        toast.success('MFA verified! Welcome back.')
        router.push(redirect)
      } else {
        // Sensitive action MFA (user already authenticated) — use /auth/mfa/verify
        await authApi.mfaVerify(data.code, 'sensitive_action')
        toast.success('MFA code verified!')
        router.push(ROUTES.DASHBOARD)
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Invalid or expired code. Please try again.')
      }
    }
  }

  return (
    <AuthLayout
      title="MFA verification"
      description="Enter the 6-digit code from your authenticator app"
      footer={
        isLoginChallenge ? (
          <Link href={ROUTES.RECOVERY_CODES + '?mfa_session_token=' + mfaSessionToken} className="text-primary hover:underline">
            Use a recovery code instead
          </Link>
        ) : (
          <Link href={ROUTES.RECOVERY_CODES} className="text-primary hover:underline">
            Use a recovery code instead
          </Link>
        )
      }
    >
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="flex justify-center">
            <div className="rounded-full bg-primary/10 p-4">
              <Shield className="h-8 w-8 text-primary" aria-hidden="true" />
            </div>
          </div>

          <FormField
            control={form.control}
            name="code"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="sr-only">MFA Code</FormLabel>
                <FormControl>
                  <Input
                    placeholder="000000"
                    maxLength={6}
                    inputMode="numeric"
                    pattern="[0-9]*"
                    autoComplete="one-time-code"
                    autoFocus
                    aria-required="true"
                    className="text-center text-2xl tracking-[0.5em]"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button
            type="submit"
            className="w-full"
            loading={form.formState.isSubmitting}
            disabled={form.formState.isSubmitting}
          >
            Verify
          </Button>
        </form>
      </Form>
    </AuthLayout>
  )
}
