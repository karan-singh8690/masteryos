'use client'

import { Clock, Play, Pause, CheckCircle, XCircle } from 'lucide-react'
import { toast } from 'sonner'

import { useScheduledJobs, useRunJob, usePauseJob, useResumeJob } from '@/hooks/use-admin'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { formatRelativeTime, formatDateTime } from '@/lib/format'

export default function SchedulerPage() {
  const { data: jobs, isLoading } = useScheduledJobs()
  const runMutation = useRunJob()
  const pauseMutation = usePauseJob()
  const resumeMutation = useResumeJob()

  return (
    <div className="max-w-4xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Scheduler</h1><p className="text-sm text-muted-foreground">Manage recurring background jobs</p></div>

      {isLoading ? <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}</div> : (
        !jobs || jobs.length === 0 ? <p className="text-sm text-muted-foreground">No scheduled jobs</p> : (
          <div className="space-y-2">
            {jobs.map((job) => (
              <Card key={job.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2"><Clock className="h-4 w-4 text-muted-foreground" aria-hidden="true" /><p className="text-sm font-medium">{job.name}</p><Badge variant={job.status === 'active' ? 'success' : job.status === 'paused' ? 'warning' : 'secondary'} className="text-xs capitalize">{job.status}</Badge></div>
                      {job.description && <p className="mt-1 text-xs text-muted-foreground">{job.description}</p>}
                      <p className="mt-1 text-xs text-muted-foreground">Handler: {job.handler_name} • Schedule: {job.schedule_type} ({job.schedule_expr})</p>
                      <div className="mt-1 flex gap-4 text-xs text-muted-foreground">
                        <span>Runs: {job.run_count}</span><span>Failures: {job.failure_count}</span>
                        {job.last_run_at && <span>Last run: {formatRelativeTime(job.last_run_at)}</span>}
                        {job.last_run_status === 'success' ? <span className="text-success"><CheckCircle className="mr-1 inline h-3 w-3" />Success</span> : job.last_run_status === 'failed' ? <span className="text-destructive"><XCircle className="mr-1 inline h-3 w-3" />Failed</span> : null}
                      </div>
                      {job.last_run_error && <p className="mt-1 text-xs text-destructive">Error: {job.last_run_error.slice(0, 100)}</p>}
                      <p className="mt-1 text-xs text-primary">Next: {formatDateTime(job.next_run_at)}</p>
                    </div>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => runMutation.mutateAsync(job.name).then(() => toast.success('Job triggered')).catch(() => toast.error('Failed'))} loading={runMutation.isPending} aria-label="Run job now"><Play className="h-4 w-4" /></Button>
                      {job.status === 'active' ? (
                        <Button size="sm" variant="ghost" onClick={() => pauseMutation.mutateAsync(job.id).then(() => toast.success('Paused')).catch(() => toast.error('Failed'))} loading={pauseMutation.isPending} aria-label="Pause job"><Pause className="h-4 w-4" /></Button>
                      ) : job.status === 'paused' ? (
                        <Button size="sm" variant="ghost" onClick={() => resumeMutation.mutateAsync(job.id).then(() => toast.success('Resumed')).catch(() => toast.error('Failed'))} loading={resumeMutation.isPending} aria-label="Resume job"><Play className="h-4 w-4" /></Button>
                      ) : null}
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
