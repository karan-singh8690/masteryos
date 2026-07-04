'use client'

import * as React from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Mail, Lock, User as UserIcon } from 'lucide-react'

import { AuthLayout } from '@/components/layout/auth-layout'
import { Button } from '@/components/ui/button'
import { Input, PasswordInput } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
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
import { authApi, ApiError, tokenStorage } from '@/lib/api-client'
import { registerSchema, type RegisterFormData } from '@/lib/validations'
import { ROUTES } from '@/lib/constants'
import { useAuth } from '@/providers/auth-provider'
import { toast } from 'sonner'

export default function RegisterPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { setUser } = useAuth()
  const [error, setError] = React.useState<string | null>(null)
  const [password, setPassword] = React.useState('')

  const redirect = searchParams.get('redirect') || ROUTES.DASHBOARD

  const form = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: '',
      password: '',
      confirmPassword: '',
      displayName: '',
      acceptTerms: false,
    },
  })

  const onSubmit = async (data: RegisterFormData) => {
    setError(null)
    try {
      const response = await authApi.register({
        email: data.email,
        password: data.password,
        displayName: data.displayName,
      })
      tokenStorage.setAccessToken(response.accessToken)
      if (response.refreshToken) {
        tokenStorage.setRefreshToken(response.refreshToken)
      }
      setUser(response.user)
      toast.success('Account created! Please verify your email.')
      router.push(ROUTES.VERIFY_EMAIL)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === 'EMAIL_ALREADY_REGISTERED') {
          setError('An account with this email already exists.')
        } else if (err.fieldErrors) {
          for (const [field, messages] of Object.entries(err.fieldErrors)) {
            if (messages.length > 0) {
              form.setError(field as keyof RegisterFormData, {
                type: 'server',
                message: messages[0]!,
              })
            }
          }
        } else {
          setError(err.message)
        }
      } else {
        setError('An unexpected error occurred. Please try again.')
      }
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      description="Start your mastery journey today"
      footer={
        <>
          Already have an account?{' '}
          <Link href={ROUTES.LOGIN} className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
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
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <Input
                    type="email"
                    placeholder="you@example.com"
                    leftIcon={<Mail className="h-4 w-4" />}
                    autoComplete="email"
                    autoFocus
                    aria-required="true"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="displayName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Display name</FormLabel>
                <FormControl>
                  <Input
                    placeholder="Your name"
                    leftIcon={<UserIcon className="h-4 w-4" />}
                    autoComplete="name"
                    aria-required="true"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Password</FormLabel>
                <FormControl>
                  <PasswordInput
                    placeholder="Create a strong password"
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
                <FormLabel>Confirm password</FormLabel>
                <FormControl>
                  <PasswordInput
                    placeholder="Re-enter your password"
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

          <FormField
            control={form.control}
            name="acceptTerms"
            render={({ field }) => (
              <FormItem>
                <div className="flex items-start gap-2">
                  <Checkbox
                    id="acceptTerms"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                  <label htmlFor="acceptTerms" className="text-sm text-muted-foreground">
                    I agree to the{' '}
                    <Link href="/terms" className="text-primary hover:underline">
                      Terms of Service
                    </Link>{' '}
                    and{' '}
                    <Link href="/privacy" className="text-primary hover:underline">
                      Privacy Policy
                    </Link>
                  </label>
                </div>
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
            Create account
          </Button>
        </form>
      </Form>
    </AuthLayout>
  )
}
