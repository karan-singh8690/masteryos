'use client'

import * as React from 'react'
import { FileText, Download, Search } from 'lucide-react'

import { useAuditLogs } from '@/hooks/use-admin'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDateTime } from '@/lib/format'
import { useDebounce } from '@/hooks/use-debounce'

export default function AuditLogsPage() {
  const [search, setSearch] = React.useState('')
  const [actionFilter, setActionFilter] = React.useState<string>('all')
  const debouncedSearch = useDebounce(search, 300)
  const { data: logs, isLoading } = useAuditLogs({
    action: actionFilter !== 'all' ? actionFilter : undefined,
    correlation_id: debouncedSearch || undefined,
  })

  return (
    <div className="max-w-5xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Audit Logs</h1><p className="text-sm text-muted-foreground">Searchable audit trail</p></div>

      <div className="flex gap-2">
        <div className="relative flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" /><Input placeholder="Search by correlation ID..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-10" aria-label="Search audit logs" /></div>
        <Select value={actionFilter} onValueChange={setActionFilter}><SelectTrigger className="w-48"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All Actions</SelectItem><SelectItem value="LOGIN_SUCCESS">Login Success</SelectItem><SelectItem value="LOGIN_FAILURE">Login Failure</SelectItem><SelectItem value="LOGOUT">Logout</SelectItem><SelectItem value="PASSWORD_CHANGED">Password Changed</SelectItem><SelectItem value="MFA_ENABLED">MFA Enabled</SelectItem><SelectItem value="USER_REGISTERED">User Registered</SelectItem><SelectItem value="SECURITY_INCIDENT">Security Incident</SelectItem></SelectContent></Select>
        <Button variant="outline"><Download className="mr-2 h-4 w-4" />Export</Button>
      </div>

      {isLoading ? <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}</div> : (
        !logs || logs.length === 0 ? <p className="text-sm text-muted-foreground">No audit logs found</p> : (
          <div className="space-y-1">
            {logs.map((log) => (
              <Card key={log.id} hover><CardContent className="flex items-center justify-between p-3">
                <div className="flex items-center gap-3">
                  <FileText className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                  <div><div className="flex items-center gap-2"><Badge variant={log.success ? 'success' : 'destructive'} className="text-xs">{log.action}</Badge>{log.user_email && <span className="text-xs text-muted-foreground">{log.user_email}</span>}</div>{log.ip_address && <p className="mt-0.5 text-xs text-muted-foreground">IP: {log.ip_address}</p>}</div>
                </div>
                <div className="text-right"><p className="text-xs text-muted-foreground">{formatDateTime(log.created_at)}</p>{log.correlation_id && <p className="text-xs font-mono text-muted-foreground">{log.correlation_id.slice(0, 8)}...</p>}</div>
              </CardContent></Card>
            ))}
          </div>
        )
      )}
    </div>
  )
}
