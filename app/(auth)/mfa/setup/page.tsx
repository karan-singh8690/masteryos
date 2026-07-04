'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Shield, Copy, Download, Check } from 'lucide-react'

import { AuthLayout } from '@/components/layout/auth-layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/forms/form'
import { authApi, ApiError } from '@/lib/api-client'
import { mfaEnableSchema, type MfaEnableFormData } from '@/lib/validations'
import { ROUTES } from '@/lib/constants'
import { toast } from 'sonner'

export default function MfaSetupPage() {
  const router = useRouter()
  const [setup, setSetup] = React.useState<{
    secret: string
    qrCodeUri: string
    recoveryCodes: string[]
  } | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [copiedCode, setCopiedCode] = React.useState<string | null>(null)
  const [enabled, setEnabled] = React.useState(false)

  const form = useForm<MfaEnableFormData>({
    resolver: zodResolver(mfaEnableSchema),
    defaultValues: { totpCode: '' },
  })

  // Fetch MFA setup on mount
  React.useEffect(() => {
    const fetchSetup = async () => {
      try {
        const result = await authApi.mfaSetup()
        setSetup(result)
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message)
        }
      }
    }
    fetchSetup()
  }, [])

  const onSubmit = async (data: MfaEnableFormData) => {
    if (!setup) return
    setError(null)
    try {
      await authApi.mfaEnable(data.totpCode, setup.secret)
      setEnabled(true)
      toast.success('MFA enabled successfully!')
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to enable MFA. Please try again.')
      }
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedCode(text)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const downloadRecoveryCodes = () => {
    if (!setup) return
    const content = `Mastery Engine — Recovery Codes\n\n${setup.recoveryCodes.join('\n')}\n\nKeep these codes safe. Each can be used once.`
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'mastery-engine-recovery-codes.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (enabled) {
    return (
      <AuthLayout title="MFA enabled!" description="Your account is now protected with MFA.">
        <div className="space-y-4 text-center">
          <Check className="mx-auto h-16 w-16 text-success" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">
            Make sure you&apos;ve saved your recovery codes in a safe place.
          </p>
          <Button className="w-full" asChild>
            <Link href={ROUTES.DASHBOARD}>Continue to dashboard</Link>
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Set up MFA" description="Protect your account with two-factor authentication">
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!setup ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Step 1: Scan QR code */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">1</span>
                Scan QR code
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.).
              </p>
              <div className="flex justify-center rounded-lg border bg-white p-4">
                {/* The QR URI is otpauth:// — in production, render as a QR image */}
                <div className="flex h-48 w-48 items-center justify-center rounded bg-muted text-center text-xs text-muted-foreground">
                  QR Code
                  <br />
                  (Render in production)
                </div>
              </div>
              <details className="text-xs">
                <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                  Can&apos;t scan? Enter manually
                </summary>
                <div className="mt-2 flex items-center gap-2">
                  <code className="flex-1 rounded bg-muted p-2 font-mono text-xs break-all">
                    {setup.secret}
                  </code>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => copyToClipboard(setup.secret)}
                    aria-label="Copy secret"
                  >
                    {copiedCode === setup.secret ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </details>
            </CardContent>
          </Card>

          {/* Step 2: Enter code */}
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="totpCode"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Enter the 6-digit code</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="123456"
                        maxLength={6}
                        inputMode="numeric"
                        pattern="[0-9]*"
                        autoComplete="one-time-code"
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
                Verify and enable MFA
              </Button>
            </form>
          </Form>

          {/* Step 3: Save recovery codes */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">2</span>
                Save recovery codes
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Alert>
                <Shield className="h-4 w-4" />
                <AlertDescription>
                  Save these codes in a safe place. Each can be used once to access your account if you lose your authenticator device.
                </AlertDescription>
              </Alert>
              <div className="grid grid-cols-2 gap-2 rounded-lg border bg-muted/50 p-4 font-mono text-sm">
                {setup.recoveryCodes.map((code) => (
                  <div key={code} className="text-center">
                    {code}
                  </div>
                ))}
              </div>
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={downloadRecoveryCodes}
                leftIcon={<Download className="h-4 w-4" />}
              >
                Download recovery codes
              </Button>
            </CardContent>
          </Card>

          <div className="text-center">
            <Link href={ROUTES.DASHBOARD} className="text-sm text-muted-foreground hover:text-foreground">
              Skip for now
            </Link>
          </div>
        </div>
      )}
    </AuthLayout>
  )
}
