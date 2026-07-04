'use client'

import * as React from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Lock, ArrowLeft } from 'lucide-react'

import { AuthLayout } from '@/components/layout/auth-layout'
import { Button } from '@/components/ui/button'
import { PasswordInput } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/forms/form'
import { PasswordStrengthMeter } from '@/components/forms/password-strength-meter'
import { authApi, ApiError } from '@/lib/api-client'
import { resetPasswordSchema, type ResetPasswordFormData } from '@/lib/validations'
import { ROUTES } from '@/lib/constants'
import { toast } from 'sonner'

export default function ResetPasswordPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token') || ''
  const [error, setError] = React.useState<string | null>(null)
  const [password, setPassword] = React.useState('')

  const form = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      token,
      password: '',
      confirmPassword: '',
    },
  })

  React.useEffect(() => {
    if (!token) {
      setError('Reset token is missing. Please request a new reset link.')
    }
  }, [token])

  const onSubmit = async (data: ResetPasswordFormData) => {
    setError(null)
    try {
      await authApi.resetPassword(data.token, data.password)
      toast.success('Password reset successfully!')
      router.push(ROUTES.LOGIN)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('An unexpected error occurred. Please try again.')
      }
    }
  }

  return (
    <AuthLayout
      title="Reset your password"
      description="Enter your new password"
      footer={
        <Link href={ROUTES.LOGIN} className="inline-flex items-center gap-1 text-primary hover:underline">
          <ArrowLeft className="h-3 w-3" /> Back to login
        </Link>
      }
    >
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>New password</FormLabel>
                <FormControl>
                  <PasswordInput
                    placeholder="Enter new password"
                    leftIcon={<Lock className="h-4 w-4" />}
                    autoComplete="new-password"
                    aria-required="true"
                    {...field}
                    onChange={(e) => {
                      field.onChange(e)
                      setPassword(e.target.value)
                    }}
                  />
                </FormControl>
                <FormMessage />
                <PasswordStrengthMeter password={password} />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="confirmPassword"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Confirm new password</FormLabel>
                <FormControl>
                  <PasswordInput
                    placeholder="Re-enter new password"
                    leftIcon={<Lock className="h-4 w-4" />}
                    autoComplete="new-password"
                    aria-required="true"
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
            disabled={form.formState.isSubmitting || !token}
          >
            Reset password
          </Button>
        </form>
      </Form>
    </AuthLayout>
  )
}
