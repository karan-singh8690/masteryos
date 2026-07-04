'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { KeyRound } from 'lucide-react'

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
import { mfaRecoverySchema, type MfaRecoveryFormData } from '@/lib/validations'
import { ROUTES } from '@/lib/constants'
import { toast } from 'sonner'

export default function RecoveryCodesPage() {
  const router = useRouter()
  const [error, setError] = React.useState<string | null>(null)

  const form = useForm<MfaRecoveryFormData>({
    resolver: zodResolver(mfaRecoverySchema),
    defaultValues: { recoveryCode: '' },
  })

  const onSubmit = async (data: MfaRecoveryFormData) => {
    setError(null)
    try {
      const response = await authApi.mfaRecovery(data.recoveryCode)
      toast.success(response.message || 'Recovery code used successfully')
      router.push(ROUTES.DASHBOARD)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Invalid recovery code. Please try again.')
      }
    }
  }

  return (
    <AuthLayout
      title="Use recovery code"
      description="Enter one of your recovery codes to access your account"
      footer={
        <Link href={ROUTES.MFA_VERIFY} className="text-primary hover:underline">
          Use MFA code instead
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
              <KeyRound className="h-8 w-8 text-primary" aria-hidden="true" />
            </div>
          </div>

          <FormField
            control={form.control}
            name="recoveryCode"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Recovery code</FormLabel>
                <FormControl>
                  <Input
                    placeholder="XXXX-XXXX-XXXX-XXXX"
                    autoFocus
                    aria-required="true"
                    className="text-center font-mono uppercase"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <Alert>
            <AlertDescription>
              Each recovery code can only be used once. After using a code, it becomes invalid.
            </AlertDescription>
          </Alert>

          <Button
            type="submit"
            className="w-full"
            loading={form.formState.isSubmitting}
            disabled={form.formState.isSubmitting}
          >
            Use recovery code
          </Button>
        </form>
      </Form>
    </AuthLayout>
  )
}
