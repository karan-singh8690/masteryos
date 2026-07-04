'use client'

import { Server, Power, AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'

import { useAdminWorkers, useWorkerMetrics, useRequestWorkerShutdown } from '@/hooks/use-admin'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { formatRelativeTime } from '@/lib/format'
import { cn } from '@/lib/cn'

export default function WorkersPage() {
  const { data: workers, isLoading } = useAdminWorkers()
  const { data: metrics } = useWorkerMetrics()
  const shutdownMutation = useRequestWorkerShutdown()

  return (
    <div className="max-w-4xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Worker Console</h1><p className="text-sm text-muted-foreground">Monitor and control background workers</p></div>

      {metrics && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Active Workers</CardTitle><p className="text-2xl font-bold">{metrics.workers.active}</p></CardHeader></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Dead Workers</CardTitle><p className="text-2xl font-bold text-destructive">{metrics.workers.dead}</p></CardHeader></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Jobs Processed</CardTitle><p className="text-2xl font-bold">{metrics.workers.total_processed}</p></CardHeader></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Jobs Failed</CardTitle><p className="text-2xl font-bold">{metrics.workers.total_failed}</p></CardHeader></Card>
        </div>
      )}

      {isLoading ? <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}</div> : (
        !workers || workers.length === 0 ? <p className="text-sm text-muted-foreground">No workers registered</p> : (
          <div className="space-y-2">
            {workers.map((w) => (
              <Card key={w.worker_id} className={cn(w.is_stale && 'border-destructive/50')}>
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2"><Server className="h-4 w-4 text-muted-foreground" aria-hidden="true" /><p className="text-sm font-medium font-mono">{w.worker_id}</p><Badge variant="outline" className="text-xs">{w.worker_type}</Badge></div>
                    <p className="mt-1 text-xs text-muted-foreground">{w.hostname} • PID {w.process_id} • Last seen {w.last_seen_at ? formatRelativeTime(w.last_seen_at) : 'never'}</p>
                    {w.current_job && <p className="mt-1 text-xs text-primary">Current: {w.current_job}</p>}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={w.status === 'running' ? 'success' : w.status === 'crashed' ? 'destructive' : w.status === 'draining' ? 'warning' : 'secondary'} className="capitalize">{w.status}</Badge>
                    {w.is_stale && <Badge variant="destructive" className="text-xs"><AlertTriangle className="mr-1 h-3 w-3" />Stale</Badge>}
                    <span className="text-xs text-muted-foreground">{w.jobs_processed} processed</span>
                    {(w.status === 'running' || w.status === 'starting') && (
                      <Button size="sm" variant="ghost" onClick={() => shutdownMutation.mutateAsync(w.worker_id).then(() => toast.success('Shutdown requested')).catch(() => toast.error('Failed'))} loading={shutdownMutation.isPending}>
                        <Power className="h-4 w-4" />
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
