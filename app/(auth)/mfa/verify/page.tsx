'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
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
import { authApi, ApiError } from '@/lib/api-client'
import { mfaVerifySchema, type MfaVerifyFormData } from '@/lib/validations'
import { ROUTES } from '@/lib/constants'
import { toast } from 'sonner'

export default function MfaVerifyPage() {
  const router = useRouter()
  const [error, setError] = React.useState<string | null>(null)

  const form = useForm<MfaVerifyFormData>({
    resolver: zodResolver(mfaVerifySchema),
    defaultValues: { code: '' },
  })

  const onSubmit = async (data: MfaVerifyFormData) => {
    setError(null)
    try {
      await authApi.mfaVerify(data.code, 'sensitive_action')
      toast.success('MFA code verified!')
      router.push(ROUTES.DASHBOARD)
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
        <Link href={ROUTES.RECOVERY_CODES} className="text-primary hover:underline">
          Use a recovery code instead
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
