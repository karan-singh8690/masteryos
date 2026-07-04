'use client'

import * as React from 'react'
import { Settings, Wrench } from 'lucide-react'
import { toast } from 'sonner'

import { useSystemConfig, useSetMaintenanceMode } from '@/hooks/use-admin'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function SystemConfigPage() {
  const { data: config, isLoading } = useSystemConfig()
  const maintenanceMutation = useSetMaintenanceMode()
  const [maintenance, setMaintenance] = React.useState(false)

  React.useEffect(() => { if (config) setMaintenance(config.maintenance_mode) }, [config])

  const handleMaintenanceToggle = async (enabled: boolean) => {
    setMaintenance(enabled)
    try { await maintenanceMutation.mutateAsync(enabled); toast.success(enabled ? 'Maintenance mode enabled' : 'Maintenance mode disabled') } catch { setMaintenance(!enabled); toast.error('Failed') }
  }

  if (isLoading) return <div className="space-y-6"><Skeleton className="h-8 w-48" /><Skeleton className="h-48 w-full" /></div>
  if (!config) return null

  return (
    <div className="max-w-3xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">System Configuration</h1><p className="text-sm text-muted-foreground">Platform settings and configuration</p></div>

      {maintenance && <Alert variant="warning"><Wrench className="h-4 w-4" /><AlertDescription>Maintenance mode is ENABLED. Users will see the maintenance page.</AlertDescription></Alert>}

      <Card><CardHeader><CardTitle className="text-base">Maintenance Mode</CardTitle><CardDescription>Toggle to show users the maintenance page</CardDescription></CardHeader>
        <CardContent><div className="flex items-center justify-between"><div><Label htmlFor="maintenance">Enable maintenance mode</Label><p className="text-xs text-muted-foreground">Blocks all non-admin access</p></div><Switch id="maintenance" checked={maintenance} onCheckedChange={handleMaintenanceToggle} disabled={maintenanceMutation.isPending} /></div></CardContent>
      </Card>

      <Card><CardHeader><CardTitle className="text-base">Email Settings</CardTitle></CardHeader>
        <CardContent><div className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-muted-foreground">From Address</span><span className="font-medium">{config.email.from_address}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Rate Limit</span><span className="font-medium">{config.email.rate_limit_per_minute}/min</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Retry Enabled</span><Badge variant={config.email.retry_enabled ? 'success' : 'secondary'} className="text-xs">{config.email.retry_enabled ? 'Yes' : 'No'}</Badge></div>
        </div></CardContent>
      </Card>

      <Card><CardHeader><CardTitle className="text-base">Queue Settings</CardTitle></CardHeader>
        <CardContent><div className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-muted-foreground">Batch Size</span><span className="font-medium">{config.queue.batch_size}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Visibility Timeout</span><span className="font-medium">{config.queue.visibility_timeout_seconds}s</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Max Retries</span><span className="font-medium">{config.queue.max_retries}</span></div>
        </div></CardContent>
      </Card>

      <Card><CardHeader><CardTitle className="text-base">Limits</CardTitle></CardHeader>
        <CardContent><div className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-muted-foreground">Max Sessions/User</span><span className="font-medium">{config.limits.max_sessions_per_user}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Max Enrollments/User</span><span className="font-medium">{config.limits.max_enrollments_per_user}</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Rate Limit/min</span><span className="font-medium">{config.limits.rate_limit_per_minute}</span></div>
        </div></CardContent>
      </Card>
    </div>
  )
}
