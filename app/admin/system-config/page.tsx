'use client'

import * as React from 'react'
import { Settings, Mail, Database, Zap, Server, Shield, ToggleLeft, ToggleRight } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { tokenStorage } from '@/lib/api-client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function SystemConfigPage() {
  const [config, setConfig] = React.useState<any>(null)
  const [smtp, setSmtp] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [maintenance, setMaintenance] = React.useState(false)

  React.useEffect(() => {
    fetchConfig()
  }, [])

  async function fetchConfig() {
    try {
      const token = tokenStorage.getAccessToken()
      const headers = { Authorization: `Bearer ${token}` }

      const [configRes, smtpRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/admin/system-config`, { headers }).catch(() => null),
        fetch(`${API_URL}/api/v1/admin/ops/smtp-status`, { headers }).catch(() => null),
      ])

      if (configRes?.ok) setConfig(await configRes.json())
      if (smtpRes?.ok) setSmtp(await smtpRes.json())
    } catch {
      // Use defaults
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center py-20"><div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-500/20 border-t-emerald-500" /></div>
  }

  // Defensive access — use optional chaining and fallbacks
  const emailConfig = config?.email || {}
  const queueConfig = config?.queue || {}
  const limitsConfig = config?.limits || {}

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">System Configuration</h1>
        <p className="text-sm text-muted-foreground">View and manage platform settings</p>
      </div>

      {/* Environment */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Server className="h-5 w-5 text-emerald-500" />Environment</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">App Environment</span><Badge variant="secondary" className="capitalize">{config?.app_env || 'production'}</Badge></div>
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">Closed Beta</span><Badge variant={config?.closed_beta_enabled ? 'success' : 'secondary'} className="text-xs">{config?.closed_beta_enabled ? 'Enabled' : 'Disabled'}</Badge></div>
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">Max Beta Users</span><span className="font-medium">{config?.max_beta_users || 20}</span></div>
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">Docs Enabled</span><Badge variant={config?.enable_docs ? 'success' : 'secondary'} className="text-xs">{config?.enable_docs ? 'Yes' : 'No'}</Badge></div>
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">AI Enabled</span><Badge variant={config?.ai_enabled ? 'success' : 'secondary'} className="text-xs">{config?.ai_enabled ? 'Yes' : 'No'}</Badge></div>
        </CardContent>
      </Card>

      {/* SMTP / Email */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Mail className="h-5 w-5 text-emerald-500" />SMTP Configuration</CardTitle>
          <CardDescription>Email delivery settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">Configured</span><Badge variant={smtp?.configured ? 'success' : 'destructive'} className="text-xs">{smtp?.configured ? 'Yes' : 'No'}</Badge></div>
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">Host</span><span className="font-medium">{smtp?.host || 'Not set'}</span></div>
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">Port</span><span className="font-medium">{smtp?.port || '—'}</span></div>
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">Username</span><span className="font-medium">{smtp?.username || 'Not set'}</span></div>
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">From Email</span><span className="font-medium">{smtp?.from_email || 'Not set'}</span></div>
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">TLS</span><Badge variant={smtp?.use_tls ? 'success' : 'secondary'} className="text-xs">{smtp?.use_tls ? 'Enabled' : 'Disabled'}</Badge></div>
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">Password Set</span><Badge variant={smtp?.has_password ? 'success' : 'destructive'} className="text-xs">{smtp?.has_password ? 'Yes' : 'No'}</Badge></div>
        </CardContent>
      </Card>

      {/* Beta Feature Flags */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Shield className="h-5 w-5 text-emerald-500" />Beta Feature Flags</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {config?.beta_flags && Object.entries(config.beta_flags).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between">
              <span className="text-sm capitalize">{key.replace(/_/g, ' ')}</span>
              <Badge variant={value ? 'success' : 'secondary'} className="text-xs">{value ? 'Enabled' : 'Disabled'}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Maintenance Mode */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {maintenance ? <ToggleRight className="h-5 w-5 text-amber-500" /> : <ToggleLeft className="h-5 w-5 text-muted-foreground" />}
            Maintenance Mode
          </CardTitle>
          <CardDescription>Toggle to put the platform in maintenance mode</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <Switch
              id="maintenance"
              checked={maintenance}
              onCheckedChange={async (checked) => {
                setMaintenance(checked)
                try {
                  const token = tokenStorage.getAccessToken()
                  await fetch(`${API_URL}/api/v1/admin/system-config/maintenance?enabled=${checked}`, {
                    method: 'POST',
                    headers: { Authorization: `Bearer ${token}` },
                  })
                } catch {
                  // Non-fatal
                }
              }}
            />
            <Label htmlFor="maintenance">{maintenance ? 'Maintenance mode ON' : 'Platform operational'}</Label>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
