'use client'

import * as React from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { AppLayout } from '@/components/layout/app-layout'
import { ProtectedRoute } from '@/components/layout/route-protection'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '@/components/forms/form'
import { useAuth } from '@/providers/auth-provider'
import { userApi, ApiError } from '@/lib/api-client'
import { queryKey } from '@/lib/query-keys'
import { updateProfileSchema, type UpdateProfileFormData } from '@/lib/validations'

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <ProfileContent />
      </AppLayout>
    </ProtectedRoute>
  )
}

function ProfileContent() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const form = useForm<UpdateProfileFormData>({
    resolver: zodResolver(updateProfileSchema),
    defaultValues: {
      displayName: user?.profile.displayName || '',
      timezone: user?.profile.timezone || 'UTC',
      locale: user?.profile.locale || 'en-US',
      avatarUrl: user?.profile.avatarUrl || '',
    },
  })

  const mutation = useMutation({
    mutationFn: (data: UpdateProfileFormData) =>
      userApi.updateProfile({
        displayName: data.displayName,
        timezone: data.timezone,
        locale: data.locale,
        avatarUrl: data.avatarUrl || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKey.users.me() })
      toast.success('Profile updated successfully')
    },
    onError: (error) => {
      if (error instanceof ApiError) {
        toast.error(error.message)
      } else {
        toast.error('Failed to update profile')
      }
    },
  })

  const onSubmit = (data: UpdateProfileFormData) => {
    mutation.mutate(data)
  }

  if (!user) return null

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
        <p className="text-sm text-muted-foreground">Manage your profile information</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile information</CardTitle>
          <CardDescription>Update your display name, timezone, and avatar</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <FormField
                control={form.control}
                name="displayName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Display name</FormLabel>
                    <FormControl>
                      <Input placeholder="Your name" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="timezone"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Timezone</FormLabel>
                      <FormControl>
                        <Input placeholder="UTC" {...field} />
                      </FormControl>
                      <FormDescription>Your IANA timezone (e.g., America/New_York)</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="locale"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Locale</FormLabel>
                      <FormControl>
                        <Input placeholder="en-US" {...field} />
                      </FormControl>
                      <FormDescription>Your BCP 47 locale tag</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="avatarUrl"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Avatar URL</FormLabel>
                    <FormControl>
                      <Input placeholder="https://..." {...field} />
                    </FormControl>
                    <FormDescription>Link to your profile picture</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => form.reset()}
                  disabled={mutation.isPending}
                >
                  Reset
                </Button>
                <Button type="submit" loading={mutation.isPending} disabled={mutation.isPending}>
                  Save changes
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  )
}
