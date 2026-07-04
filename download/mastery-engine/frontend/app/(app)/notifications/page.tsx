'use client'

import { Bell, Check } from 'lucide-react'

import { AppLayout } from '@/components/layout/app-layout'
import { ProtectedRoute } from '@/components/layout/route-protection'
import { EmptyState } from '@/components/ui/empty-state'

export default function NotificationsPage() {
  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="max-w-2xl space-y-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Notifications</h1>
            <p className="text-sm text-muted-foreground">Your recent notifications</p>
          </div>
          <EmptyState
            icon={Bell}
            title="No notifications yet"
            description="When you have notifications, they'll appear here."
          />
        </div>
      </AppLayout>
    </ProtectedRoute>
  )
}
