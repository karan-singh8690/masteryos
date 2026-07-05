'use client'

import * as React from 'react'
import {
  Settings, Mail, Database, Zap, Server, Shield, ToggleLeft, ToggleRight,
  Loader2, Check, Users, Rocket, Lock, Globe,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { tokenStorage } from '@/lib/api-client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const BETA_MODES = [
  {
    value: 'off',
    label: 'Production',
    description: 'Anyone can register freely. No beta banner, no feedback loop.',
    icon: Globe,
    color: 'emerald',
  },
  {
    value: 'open',
    label: 'Open Beta',
    description: 'Anyone can register freely. Shows beta banner + feedback widget. No invite required.',
    icon: Rocket,
    color: 'amber',
  },
  {
    value: 'closed',
    label: 'Closed Beta',
    description: 'Invite token required. Capped at max_beta_users (default 20).',
    icon: Lock,
    color: 'rose',
  },
] as const

export default function SystemConfigPage() {
  const [config, setConfig] = React.useState<any>(null)
  const [smtp, setSmtp] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [maintenance, setMaintenance] = React.useState(false)
  const [betaModeSaving, setBetaModeSaving] = React.useState(false)
  const [pendingBetaMode, setPendingBetaMode] = React.useState<string | null>(null)

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

  async function saveBetaMode(mode: string) {
    setBetaModeSaving(true)
    setPendingBetaMode(mode)
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/admin/system-config`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ beta_mode: mode }),
      })
      if (res.ok) {
        toast.success(`Beta mode set to "${mode}"`)
        // Refresh config to reflect the change
        await fetchConfig()
      } else {
        const err = await res.json().catch(() => ({}))
        toast.error(err.detail || 'Failed to update beta mode')
      }
    } catch {
      toast.error('Network error')
    } finally {
      setBetaModeSaving(false)
      setPendingBetaMode(null)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center py-20"><div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-500/20 border-t-emerald-500" /></div>
  }

  const currentBetaMode = config?.beta_mode || 'off'

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">System Configuration</h1>
        <p className="text-sm text-muted-foreground">View and manage platform settings</p>
      </div>

      {/* Beta Mode */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Rocket className="h-5 w-5 text-emerald-500" />
            Beta Mode
          </CardTitle>
          <CardDescription>
            Controls who can register. Changes are effective immediately but ephemeral —
            set the <code className="rounded bg-muted px-1 py-0.5 text-xs">BETA_MODE</code> env var
            in Railway for persistence across restarts.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            {BETA_MODES.map((mode) => {
              const Icon = mode.icon
              const isSelected = currentBetaMode === mode.value
              const isPending = pendingBetaMode === mode.value
              return (
                <button
                  key={mode.value}
                  type="button"
                  onClick={() => !isSelected && !betaModeSaving && saveBetaMode(mode.value)}
                  disabled={betaModeSaving}
                  className={`
                    group relative flex flex-col items-start gap-2 rounded-xl border p-4 text-left transition-all
                    ${isSelected
                      ? 'border-emerald-500 bg-emerald-500/5 ring-1 ring-emerald-500/20'
                      : 'border-border hover:border-emerald-500/40 hover:bg-muted/30'
                    }
                    ${betaModeSaving && !isPending ? 'opacity-60' : ''}
                  `}
                  aria-pressed={isSelected}
                >
                  <div className="flex w-full items-center justify-between">
                    <Icon className={`h-5 w-5 ${isSelected ? 'text-emerald-500' : 'text-muted-foreground'}`} />
                    {isSelected && <Check className="h-4 w-4 text-emerald-500" />}
                    {isPending && <Loader2 className="h-4 w-4 animate-spin text-emerald-500" />}
                  </div>
                  <div className="font-semibold text-sm">{mode.label}</div>
                  <div className="text-xs text-muted-foreground leading-relaxed">
                    {mode.description}
                  </div>
                </button>
              )
            })}
          </div>

          {currentBetaMode === 'closed' && (
            <div className="rounded-md border border-amber-500/20 bg-amber-500/5 p-3 text-sm">
              <div className="flex items-center gap-2 font-medium text-amber-700 dark:text-amber-400">
                <Lock className="h-4 w-4" />
                Closed beta active
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                New users need an invite token. Max users: {config?.max_beta_users || 20}.
                Manage invites from <a href="/admin/invites" className="text-emerald-600 underline">Beta Invites</a>.
              </div>
            </div>
          )}
          {currentBetaMode === 'open' && (
            <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-3 text-sm">
              <div className="flex items-center gap-2 font-medium text-emerald-700 dark:text-emerald-400">
                <Rocket className="h-4 w-4" />
                Open beta active
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                Anyone can register at <a href="/register" className="text-emerald-600 underline">/register</a> without an invite.
                Beta banner + feedback widget will be visible to all users.
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Environment */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Server className="h-5 w-5 text-emerald-500" />Environment</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">App Environment</span><Badge variant="secondary" className="capitalize">{config?.app_env || 'production'}</Badge></div>
          <div className="flex justify-between"><span className="text-sm text-muted-foreground">Beta Mode</span><Badge variant={currentBetaMode === 'off' ? 'secondary' : 'success'} className="text-xs capitalize">{currentBetaMode}</Badge></div>
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
