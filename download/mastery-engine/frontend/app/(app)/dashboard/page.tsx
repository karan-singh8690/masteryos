'use client'

import * as React from 'react'

import { AppLayout } from '@/components/layout/app-layout'
import { ProtectedRoute } from '@/components/layout/route-protection'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/providers/auth-provider'
import { formatRelativeTime } from '@/lib/format'

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <DashboardContent />
      </AppLayout>
    </ProtectedRoute>
  )
}

function DashboardContent() {
  const { user, isLoading } = useAuth()

  if (isLoading || !user) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    )
  }

  const profile = user.profile

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Welcome back, {profile.displayName}!
        </h1>
        <p className="text-sm text-muted-foreground">
          Here&apos;s what&apos;s happening with your learning today.
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Questions answered</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">All time</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Current streak</CardDescription>
            <CardTitle className="text-3xl">0 days</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Keep it up!</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Concepts mastered</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Across all subjects</p>
          </CardContent>
        </Card>
      </div>

      {/* Account info */}
      <Card>
        <CardHeader>
          <CardTitle>Account information</CardTitle>
          <CardDescription>Your account details</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Email</span>
            <span className="font-medium">{user.user.email}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Status</span>
            <span className="font-medium capitalize">{user.user.status.replace(/_/g, ' ')}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Email verified</span>
            <span className="font-medium">
              {user.user.emailVerifiedAt ? formatRelativeTime(user.user.emailVerifiedAt) : 'Not verified'}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">MFA enabled</span>
            <span className="font-medium">{user.user.mfaEnabled ? 'Yes' : 'No'}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Timezone</span>
            <span className="font-medium">{profile.timezone}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Member since</span>
            <span className="font-medium">{formatRelativeTime(user.user.createdAt)}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function SkeletonCard() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-16" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-3 w-20" />
      </CardContent>
    </Card>
  )
}
