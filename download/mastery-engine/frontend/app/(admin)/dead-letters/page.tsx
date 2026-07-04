'use client'

import { AlertTriangle, RefreshCw, Check } from 'lucide-react'
import { toast } from 'sonner'

import { useDeadLetters, useRetryDeadLetter, useResolveDeadLetter } from '@/hooks/use-admin'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { formatRelativeTime } from '@/lib/format'

export default function DeadLettersPage() {
  const { data: letters, isLoading } = useDeadLetters({ resolved: false })
  const retryMutation = useRetryDeadLetter()
  const resolveMutation = useResolveDeadLetter()

  return (
    <div className="max-w-4xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Dead Letters</h1><p className="text-sm text-muted-foreground">Events that exhausted all retries</p></div>

      {isLoading ? <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}</div> : (
        !letters || letters.length === 0 ? (
          <div className="rounded-lg border p-8 text-center"><Check className="mx-auto h-8 w-8 text-success" aria-hidden="true" /><p className="mt-2 text-sm text-muted-foreground">No unresolved dead letters</p></div>
        ) : (
          <div className="space-y-2">
            {letters.map((dl) => (
              <Card key={dl.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-destructive" aria-hidden="true" /><p className="text-sm font-medium font-mono">{dl.event_type}</p><Badge variant={dl.severity === 'critical' ? 'destructive' : 'warning'} className="text-xs capitalize">{dl.severity}</Badge></div>
                      <p className="mt-2 text-xs text-destructive">{dl.error_message}</p>
                      <p className="mt-1 text-xs text-muted-foreground">Type: {dl.error_type} • Retries: {dl.retry_count} • Created {formatRelativeTime(dl.created_at)}</p>
                    </div>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => retryMutation.mutateAsync(dl.id).then(() => toast.success('Retrying')).catch(() => toast.error('Failed'))} loading={retryMutation.isPending}><RefreshCw className="h-4 w-4" /></Button>
                      <Button size="sm" variant="ghost" onClick={() => resolveMutation.mutateAsync({ id: dl.id }).then(() => toast.success('Resolved')).catch(() => toast.error('Failed'))} loading={resolveMutation.isPending}><Check className="h-4 w-4 text-success" /></Button>
                    </div>
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
