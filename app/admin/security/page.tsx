'use client'

import * as React from 'react'
import { AlertTriangle, Shield, Activity, CheckCircle } from 'lucide-react'
import { toast } from 'sonner'

import { useSecurityDashboard, useSecurityIncidents, useResolveSecurityIncident } from '@/hooks/use-admin'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { formatRelativeTime } from '@/lib/format'
import { Progress } from '@/components/ui/progress'

export default function SecurityPage() {
  const { data: dashboard, isLoading } = useSecurityDashboard()
  const { data: incidents } = useSecurityIncidents()
  const resolveMutation = useResolveSecurityIncident()

  if (isLoading) return <div className="space-y-6"><Skeleton className="h-8 w-48" /><div className="grid gap-4 sm:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}</div></div>

  return (
    <div className="max-w-4xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Security Center</h1><p className="text-sm text-muted-foreground">Monitor security incidents and threats</p></div>

      {dashboard && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Unresolved Incidents</CardTitle><p className="text-2xl font-bold text-destructive">{dashboard.unresolved_incidents}</p></CardHeader></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Critical Incidents</CardTitle><p className="text-2xl font-bold text-destructive">{dashboard.critical_incidents}</p></CardHeader></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Failed Logins (24h)</CardTitle><p className="text-2xl font-bold">{dashboard.failed_logins_24h}</p></CardHeader></Card>
          <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">MFA Adoption</CardTitle><p className="text-2xl font-bold">{Math.round(dashboard.mfa_adoption_rate * 100)}%</p></CardHeader></Card>
        </div>
      )}

      {dashboard && (
        <Card><CardHeader><CardTitle className="text-base">Security Overview</CardTitle></CardHeader>
          <CardContent><div className="grid gap-4 sm:grid-cols-3">
            <div><p className="text-xs text-muted-foreground">Suspicious Sessions</p><p className="text-lg font-bold">{dashboard.suspicious_sessions}</p></div>
            <div><p className="text-xs text-muted-foreground">Password Resets (24h)</p><p className="text-lg font-bold">{dashboard.password_resets_24h}</p></div>
            <div><p className="text-xs text-muted-foreground">Rate Limit Violations</p><p className="text-lg font-bold">{dashboard.rate_limit_violations_24h}</p></div>
          </div></CardContent>
        </Card>
      )}

      <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><AlertTriangle className="h-4 w-4" />Recent Incidents</CardTitle></CardHeader>
        <CardContent>
          {!incidents || incidents.length === 0 ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground"><CheckCircle className="h-4 w-4 text-success" />No security incidents</div>
          ) : (
            <div className="space-y-2">{incidents.slice(0, 10).map((inc) => (
              <div key={inc.id} className="flex items-start justify-between rounded-lg border p-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2"><Badge variant={inc.severity === 'critical' ? 'destructive' : inc.severity === 'warning' ? 'warning' : 'secondary'} className="text-xs capitalize">{inc.severity}</Badge><Badge variant="outline" className="text-xs">{inc.incident_type}</Badge></div>
                  <p className="mt-1 text-sm">{inc.description}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{inc.ip_address} • {formatRelativeTime(inc.created_at)}</p>
                </div>
                {!inc.resolved_at && <Button size="sm" variant="ghost" onClick={() => resolveMutation.mutateAsync({ id: inc.id }).then(() => toast.success('Incident resolved')).catch(() => toast.error('Failed'))} loading={resolveMutation.isPending}>Resolve</Button>}
              </div>
            ))}</div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
