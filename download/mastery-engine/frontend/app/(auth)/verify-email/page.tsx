'use client'

import * as React from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Mail, CheckCircle2, ArrowLeft } from 'lucide-react'

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
import { authApi, ApiError } from '@/lib/api-client'
import { verifyEmailSchema, type VerifyEmailFormData } from '@/lib/validations'
import { ROUTES } from '@/lib/constants'
import { useAuth } from '@/providers/auth-provider'
import { toast } from 'sonner'

export default function VerifyEmailPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const tokenFromUrl = searchParams.get('token') || ''
  const { refresh } = useAuth()
  const [verified, setVerified] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [email, setEmail] = React.useState('')

  const form = useForm<VerifyEmailFormData>({
    resolver: zodResolver(verifyEmailSchema),
    defaultValues: { token: tokenFromUrl },
  })

  // Auto-submit if token is in URL
  React.useEffect(() => {
    if (tokenFromUrl) {
      form.handleSubmit(onSubmit)()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tokenFromUrl])

  const onSubmit = async (data: VerifyEmailFormData) => {
    setError(null)
    try {
      await authApi.verifyEmail(data.token)
      setVerified(true)
      refresh()
      toast.success('Email verified successfully!')
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('An unexpected error occurred. Please try again.')
      }
    }
  }

  const handleResend = async () => {
    if (!email) {
      setError('Please enter your email address.')
      return
    }
    try {
      await authApi.resendVerification(email)
      toast.success('Verification email sent (if account exists)')
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      }
    }
  }

  if (verified) {
    return (
      <AuthLayout
        title="Email verified!"
        description="Your email has been successfully verified."
      >
        <div className="space-y-4 text-center">
          <CheckCircle2 className="mx-auto h-16 w-16 text-success" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">
            You can now access all features of Mastery Engine.
          </p>
          <Button className="w-full" asChild>
            <Link href={ROUTES.DASHBOARD}>Go to dashboard</Link>
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Verify your email"
      description="Enter the verification token sent to your email"
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
            name="token"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Verification token</FormLabel>
                <FormControl>
                  <Input
                    placeholder="Enter token from your email"
                    autoFocus
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
            disabled={form.formState.isSubmitting}
          >
            Verify email
          </Button>
        </form>
      </Form>

      <div className="mt-6 space-y-4 border-t pt-4">
        <p className="text-center text-sm text-muted-foreground">
          Didn&apos;t receive an email?
        </p>
        <div className="flex gap-2">
          <Input
            type="email"
            placeholder="Enter your email"
            leftIcon={<Mail className="h-4 w-4" />}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-label="Email for resend"
          />
          <Button type="button" variant="outline" onClick={handleResend}>
            Resend
          </Button>
        </div>
      </div>
    </AuthLayout>
  )
}
