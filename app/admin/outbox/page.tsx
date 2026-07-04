'use client'

import * as React from 'react'
import { FileText, RefreshCw, Clock } from 'lucide-react'
import { toast } from 'sonner'

import { useOutboxEvents, useOutboxStats, useReplayOutboxEvent } from '@/hooks/use-admin'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { formatRelativeTime } from '@/lib/format'

export default function OutboxPage() {
  const [statusFilter, setStatusFilter] = React.useState<string>('all')
  const { data: events, isLoading } = useOutboxEvents({ status: statusFilter !== 'all' ? statusFilter : undefined })
  const { data: stats } = useOutboxStats()
  const replayMutation = useReplayOutboxEvent()

  return (
    <div className="max-w-4xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Outbox Console</h1><p className="text-sm text-muted-foreground">Inspect and replay domain events</p></div>

      {stats && (
        <div className="grid gap-4 sm:grid-cols-4">
          <Card><CardContent className="pt-6"><p className="text-xs text-muted-foreground">Pending</p><p className="text-2xl font-bold">{stats.pending}</p></CardContent></Card>
          <Card><CardContent className="pt-6"><p className="text-xs text-muted-foreground">In Progress</p><p className="text-2xl font-bold">{stats.leased_in_progress}</p></CardContent></Card>
          <Card><CardContent className="pt-6"><p className="text-xs text-muted-foreground">Dispatched</p><p className="text-2xl font-bold">{stats.dispatched}</p></CardContent></Card>
          <Card><CardContent className="pt-6"><p className="text-xs text-muted-foreground">Dead Lettered</p><p className="text-2xl font-bold text-destructive">{stats.dead_lettered}</p></CardContent></Card>
        </div>
      )}

      <Select value={statusFilter} onValueChange={setStatusFilter}>
        <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
        <SelectContent><SelectItem value="all">All Status</SelectItem><SelectItem value="pending">Pending</SelectItem><SelectItem value="dispatched">Dispatched</SelectItem><SelectItem value="dead_lettered">Dead Lettered</SelectItem></SelectContent>
      </Select>

      {isLoading ? <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}</div> : (
        !events || events.length === 0 ? <p className="text-sm text-muted-foreground">No events found</p> : (
          <div className="space-y-2">
            {events.map((e) => (
              <Card key={e.id} hover>
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2"><FileText className="h-4 w-4 text-muted-foreground" aria-hidden="true" /><p className="text-sm font-medium font-mono">{e.event_type}</p></div>
                    <p className="mt-1 text-xs text-muted-foreground">ID: {e.id} • Created {formatRelativeTime(e.created_at)}</p>
                    {e.last_dispatch_error && <p className="mt-1 text-xs text-destructive">Error: {e.last_dispatch_error.slice(0, 100)}</p>}
                    {e.next_retry_at && <p className="mt-1 text-xs text-warning"><Clock className="mr-1 inline h-3 w-3" />Retry at {formatRelativeTime(e.next_retry_at)}</p>}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={e.status === 'dispatched' ? 'success' : e.status === 'dead_lettered' ? 'destructive' : 'warning'} className="text-xs capitalize">{e.status}</Badge>
                    {e.status === 'pending' && <Badge variant="outline" className="text-xs">Attempt {e.dispatch_attempt_count}</Badge>}
                    {(e.status === 'pending' || e.status === 'dead_lettered') && (
                      <Button size="sm" variant="ghost" onClick={() => replayMutation.mutateAsync(e.id).then(() => toast.success('Event replayed')).catch(() => toast.error('Failed'))} loading={replayMutation.isPending} aria-label="Replay event">
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )
      )}
    </div>
  )
}
