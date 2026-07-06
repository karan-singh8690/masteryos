'use client'

import * as React from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { User, Mail, Globe, Clock, Save, RotateCcw, Crown, Check } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
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
import { GradientAvatar } from '@/components/ui/avatar'

export default function ProfilePage() {
  return <ProfileContent />
}

function ProfileContent() {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const form = useForm<UpdateProfileFormData>({
    resolver: zodResolver(updateProfileSchema),
    defaultValues: {
      displayName: user?.profile?.display_name || '',
      timezone: user?.profile?.timezone || 'UTC',
      locale: user?.profile?.locale || 'en-US',
      avatarUrl: user?.profile?.avatar_url || '',
    },
  })

  const mutation = useMutation({
    mutationFn: (data: UpdateProfileFormData) =>
      userApi.updateProfile({
        display_name: data.displayName,
        timezone: data.timezone,
        locale: data.locale,
        avatar_url: data.avatarUrl || undefined,
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

  const email = user.user?.email || ''
  const displayName = user.profile?.display_name || 'User'
  const role = user.roles?.[0] || 'learner'
  const status = user.user?.status || 'active'

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <GradientAvatar email={email} name={displayName} size="xl" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{displayName}</h1>
          <div className="mt-1 flex items-center gap-2">
            <Badge variant="secondary" className="capitalize">{role}</Badge>
            <Badge variant="outline" className="text-emerald-500 border-emerald-500/30">
              <Check className="mr-1 h-3 w-3" /> {status}
            </Badge>
          </div>
        </div>
      </div>

      {/* Profile Card */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5 text-emerald-500" />
            Profile Information
          </CardTitle>
          <CardDescription>Update your display name, timezone, and avatar</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5" noValidate>
              {/* Display Name */}
              <FormField
                control={form.control}
                name="displayName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Display Name</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input placeholder="Your name" className="pl-9" {...field} />
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Timezone + Locale */}
              <div className="grid gap-5 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="timezone"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" /> Timezone
                      </FormLabel>
                      <FormControl>
                        <Input placeholder="UTC" {...field} />
                      </FormControl>
                      <FormDescription>e.g., America/New_York</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="locale"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="flex items-center gap-1.5">
                        <Globe className="h-3.5 w-3.5" /> Language
                      </FormLabel>
                      <FormControl>
                        <Input placeholder="en-US" {...field} />
                      </FormControl>
                      <FormDescription>Your language preference</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* Avatar URL */}
              <FormField
                control={form.control}
                name="avatarUrl"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Avatar URL (optional)</FormLabel>
                    <FormControl>
                      <Input placeholder="https://example.com/avatar.png" {...field} />
                    </FormControl>
                    <FormDescription>Leave empty to use auto-generated gradient avatar</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Actions */}
              <div className="flex items-center justify-between border-t pt-4">
                <p className="text-xs text-muted-foreground">
                  Changes are visible immediately after saving.
                </p>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => form.reset()}
                    disabled={mutation.isPending}
                    className="gap-1.5"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Reset
                  </Button>
                  <Button type="submit" loading={mutation.isPending} disabled={mutation.isPending} className="gap-1.5">
                    <Save className="h-3.5 w-3.5" />
                    Save Changes
                  </Button>
                </div>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>

      {/* Account Info Card */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-emerald-500" />
            Account Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Email</span>
            <span className="text-sm font-medium">{email}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Account Type</span>
            <Badge variant="secondary" className="capitalize">{role}</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 capitalize">{status}</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Upgrade Card */}
      <Card className="rounded-2xl border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 to-transparent">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Crown className="h-5 w-5 text-emerald-500" />
            Upgrade to Pro
          </CardTitle>
          <CardDescription>Unlock unlimited study sessions, AI explanations, and advanced analytics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 mb-4">
            {[
              'Unlimited study sessions',
              'AI-powered explanations',
              'Advanced analytics',
              'Priority support',
            ].map((feature) => (
              <div key={feature} className="flex items-center gap-2 text-sm">
                <Check className="h-4 w-4 text-emerald-500" />
                {feature}
              </div>
            ))}
          </div>
          <a href="/portal/billing" className="block">
            <Button className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 text-white hover:from-emerald-600 hover:to-teal-600">
              <Crown className="mr-2 h-4 w-4" />
              Upgrade Now
            </Button>
          </a>
        </CardContent>
      </Card>
    </div>
  )
}
