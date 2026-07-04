'use client'

import * as React from 'react'
import { Mail } from 'lucide-react'

import { useAdminNotifications } from '@/hooks/use-admin'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { formatSmartDate } from '@/lib/format'

export default function AdminNotificationsPage() {
  const [statusFilter, setStatusFilter] = React.useState<string>('all')
  const { data: notifications, isLoading } = useAdminNotifications({ status: statusFilter !== 'all' ? statusFilter : undefined })

  return (
    <div className="max-w-4xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Notification Operations</h1><p className="text-sm text-muted-foreground">Monitor notification delivery</p></div>
      <Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className="w-40"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All Status</SelectItem><SelectItem value="queued">Queued</SelectItem><SelectItem value="sent">Sent</SelectItem><SelectItem value="delivered">Delivered</SelectItem><SelectItem value="failed">Failed</SelectItem></SelectContent></Select>
      {isLoading ? <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}</div> : (
        !notifications || notifications.length === 0 ? <p className="text-sm text-muted-foreground">No notifications found</p> : (
          <div className="space-y-2">
            {notifications.map((n) => (
              <Card key={n.id} hover><CardContent className="flex items-center justify-between p-4">
                <div className="flex-1"><div className="flex items-center gap-2"><Mail className="h-4 w-4 text-muted-foreground" aria-hidden="true" /><p className="text-sm font-medium">{n.title}</p></div><p className="mt-1 text-xs text-muted-foreground">{n.notification_type} • {n.channel} • {formatSmartDate(n.created_at)}</p></div>
                <Badge variant={n.status === 'delivered' ? 'success' : n.status === 'failed' ? 'destructive' : n.status === 'sent' ? 'secondary' : 'warning'} className="text-xs capitalize">{n.status}</Badge>
              </CardContent></Card>
            ))}
          </div>
        )
      )}
    </div>
  )
}
