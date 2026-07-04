'use client'

import * as React from 'react'
import { Mail, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'

import { useEmailDelivery, useRetryEmail } from '@/hooks/use-admin'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { formatSmartDate } from '@/lib/format'

export default function AdminEmailPage() {
  const [statusFilter, setStatusFilter] = React.useState<string>('all')
  const { data: emails, isLoading } = useEmailDelivery({ status: statusFilter !== 'all' ? statusFilter : undefined })
  const retryMutation = useRetryEmail()

  return (
    <div className="max-w-4xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Email Operations</h1><p className="text-sm text-muted-foreground">Monitor email delivery and retries</p></div>
      <Select value={statusFilter} onValueChange={setStatusFilter}><SelectTrigger className="w-40"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All Status</SelectItem><SelectItem value="sent">Sent</SelectItem><SelectItem value="delivered">Delivered</SelectItem><SelectItem value="failed">Failed</SelectItem><SelectItem value="bounced">Bounced</SelectItem><SelectItem value="deferred">Deferred</SelectItem></SelectContent></Select>
      {isLoading ? <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}</div> : (
        !emails || emails.length === 0 ? <p className="text-sm text-muted-foreground">No emails found</p> : (
          <div className="space-y-2">
            {emails.map((e) => (
              <Card key={e.id} hover><CardContent className="flex items-center justify-between p-4">
                <div className="flex-1"><div className="flex items-center gap-2"><Mail className="h-4 w-4 text-muted-foreground" aria-hidden="true" /><p className="text-sm font-medium">{e.subject}</p></div><p className="mt-1 text-xs text-muted-foreground">To: {e.to_address} • Template: {e.template_name} • {formatSmartDate(e.created_at)}</p>{e.error_message && <p className="mt-1 text-xs text-destructive">{e.error_message}</p>}{e.bounce_type && <p className="mt-1 text-xs text-warning">Bounce: {e.bounce_type}</p>}</div>
                <div className="flex items-center gap-2">
                  <Badge variant={e.status === 'delivered' ? 'success' : e.status === 'failed' || e.status === 'bounced' ? 'destructive' : 'secondary'} className="text-xs capitalize">{e.status}</Badge>
                  {(e.status === 'failed' || e.status === 'deferred') && <Button size="sm" variant="ghost" onClick={() => retryMutation.mutateAsync(e.id).then(() => toast.success('Retrying')).catch(() => toast.error('Failed'))} loading={retryMutation.isPending} aria-label="Retry email"><RefreshCw className="h-4 w-4" /></Button>}
                </div>
              </CardContent></Card>
            ))}
          </div>
        )
      )}
    </div>
  )
}
