'use client'

import * as React from 'react'
import { Bell, Check, X, CheckCheck } from 'lucide-react'
import { toast } from 'sonner'

import {
  useNotifications,
  useMarkNotificationOpened,
  useMarkNotificationDismissed,
  useMarkAllNotificationsOpened,
} from '@/hooks/use-learner'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { Pagination } from '@/components/ui/pagination'
import { formatSmartDate } from '@/lib/format'
import { cn } from '@/lib/cn'

const PAGE_SIZE = 20

export default function NotificationsPage() {
  const [page, setPage] = React.useState(1)
  const { data, isLoading } = useNotifications({ page, pageSize: PAGE_SIZE })
  const markOpened = useMarkNotificationOpened()
  const markDismissed = useMarkNotificationDismissed()
  const markAllOpened = useMarkAllNotificationsOpened()

  const handleMarkOpened = async (id: string) => {
    try {
      await markOpened.mutateAsync(id)
    } catch {
      toast.error('Failed to mark notification')
    }
  }

  const handleDismiss = async (id: string) => {
    try {
      await markDismissed.mutateAsync(id)
    } catch {
      toast.error('Failed to dismiss notification')
    }
  }

  const handleMarkAllOpened = async () => {
    try {
      await markAllOpened.mutateAsync()
      toast.success('All notifications marked as read')
    } catch {
      toast.error('Failed to mark all notifications')
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-3xl space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      </div>
    )
  }

  const notifications = data?.items || []
  const total = data?.total || 0

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Notifications</h1>
          <p className="text-sm text-muted-foreground">{total} total</p>
        </div>
        {notifications.some((n) => n.status === 'delivered' || n.status === 'sent') && (
          <Button variant="outline" size="sm" onClick={handleMarkAllOpened} loading={markAllOpened.isPending}>
            <CheckCheck className="mr-2 h-4 w-4" />
            Mark all read
          </Button>
        )}
      </div>

      {notifications.length === 0 ? (
        <EmptyState
          icon={Bell}
          title="No notifications"
          description="You're all caught up!"
        />
      ) : (
        <>
          <ul className="space-y-2" role="list">
            {notifications.map((notification) => {
              const isUnread = notification.status === 'delivered' || notification.status === 'sent'
              return (
                <li key={notification.id}>
                  <Card
                    className={cn(
                      'transition-colors',
                      isUnread && 'border-primary/30 bg-primary/5',
                    )}
                  >
                    <CardContent className="flex items-start gap-3 p-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium">{notification.title}</p>
                          {isUnread && (
                            <span
                              className="h-2 w-2 rounded-full bg-primary"
                              aria-label="Unread"
                            />
                          )}
                        </div>
                        <p className="mt-1 text-sm text-muted-foreground">{notification.body}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {formatSmartDate(notification.created_at)}
                        </p>
                      </div>
                      <div className="flex gap-1">
                        {isUnread && (
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={() => handleMarkOpened(notification.id)}
                            aria-label="Mark as read"
                          >
                            <Check className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => handleDismiss(notification.id)}
                          aria-label="Dismiss notification"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </li>
              )
            })}
          </ul>

          {total > PAGE_SIZE && (
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              total={total}
              onPageChange={setPage}
            />
          )}
        </>
      )}
    </div>
  )
}
