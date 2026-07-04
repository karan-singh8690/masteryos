'use client'

import * as React from 'react'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Mail, ArrowLeft } from 'lucide-react'

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
import { forgotPasswordSchema, type ForgotPasswordFormData } from '@/lib/validations'
import { ROUTES } from '@/lib/constants'
import { toast } from 'sonner'

export default function ForgotPasswordPage() {
  const [submitted, setSubmitted] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  const form = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  })

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setError(null)
    try {
      await authApi.forgotPassword(data.email)
      setSubmitted(true)
      toast.success('Reset link sent (if account exists)')
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('An unexpected error occurred. Please try again.')
      }
    }
  }

  if (submitted) {
    return (
      <AuthLayout
        title="Check your email"
        description="If an account exists with that email, a reset link has been sent."
        footer={
          <Link href={ROUTES.LOGIN} className="inline-flex items-center gap-1 text-primary hover:underline">
            <ArrowLeft className="h-3 w-3" /> Back to login
          </Link>
        }
      >
        <Alert>
          <Mail className="h-4 w-4" />
          <AlertDescription>
            We&apos;ve sent a password reset link to your email address. The link expires in 15 minutes.
          </AlertDescription>
        </Alert>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Forgot password?"
      description="Enter your email and we'll send you a reset link"
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

          <Button
            type="submit"
            className="w-full"
            loading={form.formState.isSubmitting}
            disabled={form.formState.isSubmitting}
          >
            Send reset link
          </Button>
        </form>
      </Form>
    </AuthLayout>
  )
}
