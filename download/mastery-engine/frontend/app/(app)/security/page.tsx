'use client'

import * as React from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Shield, Smartphone, Monitor, Key, Lock } from 'lucide-react'
import { toast } from 'sonner'

import { AppLayout } from '@/components/layout/app-layout'
import { ProtectedRoute } from '@/components/layout/route-protection'
import { Button } from '@/components/ui/button'
import { PasswordInput } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/forms/form'
import { useAuth } from '@/providers/auth-provider'
import { authApi, userApi, ApiError } from '@/lib/api-client'
import { queryKey } from '@/lib/query-keys'
import { changePasswordSchema, type ChangePasswordFormData } from '@/lib/validations'
import { formatRelativeTime, formatDateTime } from '@/lib/format'

export default function SecurityPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <SecurityContent />
      </AppLayout>
    </ProtectedRoute>
  )
}

function SecurityContent() {
  const { user, logout } = useAuth()
  const { data: dashboard, isLoading } = useQuery({
    queryKey: queryKey.users.security(),
    queryFn: () => userApi.security(),
  })

  const passwordForm = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    },
  })

  const changePasswordMutation = useMutation({
    mutationFn: (data: ChangePasswordFormData) =>
      authApi.changePassword(data.currentPassword, data.newPassword),
    onSuccess: () => {
      toast.success('Password changed. Please log in again.')
      logout(false)
    },
    onError: (error) => {
      if (error instanceof ApiError) {
        if (error.fieldErrors) {
          for (const [field, messages] of Object.entries(error.fieldErrors)) {
            if (messages.length > 0) {
              passwordForm.setError(field as keyof ChangePasswordFormData, {
                type: 'server',
                message: messages[0]!,
              })
            }
          }
        } else {
          toast.error(error.message)
        }
      }
    },
  })

  const onPasswordSubmit = (data: ChangePasswordFormData) => {
    changePasswordMutation.mutate(data)
  }

  if (isLoading || !dashboard || !user) {
    return (
      <div className="max-w-2xl space-y-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Security</h1>
        <p className="text-sm text-muted-foreground">Manage your account security</p>
      </div>

      {/* Security status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Security status
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <SecurityStatusRow
            label="Email verified"
            status={dashboard.emailVerified}
          />
          <SecurityStatusRow
            label="MFA enabled"
            status={dashboard.mfaEnabled}
          />
          <SecurityStatusRow
            label="Password last changed"
            status={!!dashboard.passwordLastChangedAt}
            detail={dashboard.passwordLastChangedAt ? formatRelativeTime(dashboard.passwordLastChangedAt) : 'Never'}
          />
          <SecurityStatusRow
            label="Recovery codes remaining"
            status={dashboard.recoveryCodesRemaining > 0}
            detail={`${dashboard.recoveryCodesRemaining} codes`}
          />
        </CardContent>
      </Card>

      {/* Active sessions */}
      <Card>
        <CardHeader>
          <CardTitle>Active sessions</CardTitle>
          <CardDescription>Devices currently logged into your account</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {dashboard.activeSessions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No active sessions</p>
          ) : (
            dashboard.activeSessions.map((session) => (
              <div
                key={session.id}
                className="flex items-start gap-3 rounded-md border p-3"
              >
                {session.userAgent?.includes('Mobile') ? (
                  <Smartphone className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                ) : (
                  <Monitor className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                )}
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium">{session.userAgent || 'Unknown device'}</p>
                    {session.isCurrent && <Badge variant="success">Current</Badge>}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    IP: {session.lastIp || 'Unknown'} • Last seen: {formatRelativeTime(session.lastSeenAt)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Expires: {formatDateTime(session.expiresAt)}
                  </p>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* Change password */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            Change password
          </CardTitle>
          <CardDescription>
            Changing your password will log you out of all other devices
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...passwordForm}>
            <form onSubmit={passwordForm.handleSubmit(onPasswordSubmit)} className="space-y-4" noValidate>
              <FormField
                control={passwordForm.control}
                name="currentPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Current password</FormLabel>
                    <FormControl>
                      <PasswordInput
                        placeholder="Enter current password"
                        leftIcon={<Lock className="h-4 w-4" />}
                        autoComplete="current-password"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={passwordForm.control}
                name="newPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>New password</FormLabel>
                    <FormControl>
                      <PasswordInput
                        placeholder="Enter new password"
                        leftIcon={<Lock className="h-4 w-4" />}
                        autoComplete="new-password"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={passwordForm.control}
                name="confirmPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm new password</FormLabel>
                    <FormControl>
                      <PasswordInput
                        placeholder="Re-enter new password"
                        leftIcon={<Lock className="h-4 w-4" />}
                        autoComplete="new-password"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Alert>
                <AlertDescription>
                  You will be logged out of all devices after changing your password.
                </AlertDescription>
              </Alert>

              <div className="flex justify-end">
                <Button
                  type="submit"
                  loading={changePasswordMutation.isPending}
                  disabled={changePasswordMutation.isPending}
                >
                  Change password
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  )
}

function SecurityStatusRow({
  label,
  status,
  detail,
}: {
  label: string
  status: boolean
  detail?: string
}) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <div className="flex items-center gap-2">
        {detail && <span className="text-xs text-muted-foreground">{detail}</span>}
        <Badge variant={status ? 'success' : 'destructive'}>
          {status ? 'Enabled' : 'Disabled'}
        </Badge>
      </div>
    </div>
  )
}
