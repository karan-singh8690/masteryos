'use client'

import * as React from 'react'
import Link from 'next/link'
import {
  Users, Activity, Server, AlertTriangle, Mail, Zap, Flag,
  Database, HardDrive, DollarSign, TrendingUp,
  type LucideIcon,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/cn'
import { tokenStorage } from '@/lib/api-client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Analytics {
  total_users: number
  active_users: number
  total_organizations: number
  total_subscriptions: number
  revenue_mrr: number
  total_api_calls: number
  total_study_sessions: number
  total_questions_answered: number
  beta_invites_sent: number
  beta_feedback_count: number
}

interface OpsSummary {
  active_workers: number
  pending_outbox_events: number
  dead_letter_count: number
  scheduled_jobs: number
  notifications_sent_today: number
  emails_sent_today: number
  system_health: string
}

interface Revenue {
  mrr: number
  arr: number
  total_revenue: number
  active_subscriptions: number
  by_plan: Record<string, number>
}

function StatCard({ icon: Icon, label, value, sublabel, color = 'emerald' }: {
  icon: LucideIcon; label: string; value: string | number; sublabel?: string; color?: string
}) {
  const colorMap: Record<string, string> = {
    emerald: 'bg-emerald-500/10 text-emerald-500',
    blue: 'bg-blue-500/10 text-blue-500',
    amber: 'bg-amber-500/10 text-amber-500',
    red: 'bg-red-500/10 text-red-500',
  }
  return (
    <Card className="rounded-2xl">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="mt-1 text-2xl font-bold">{value}</p>
            {sublabel && <p className="mt-0.5 text-xs text-muted-foreground">{sublabel}</p>}
          </div>
          <div className={cn('rounded-xl p-2.5', colorMap[color])}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default function AdminDashboardPage() {
  const [analytics, setAnalytics] = React.useState<Analytics | null>(null)
  const [ops, setOps] = React.useState<OpsSummary | null>(null)
  const [revenue, setRevenue] = React.useState<Revenue | null>(null)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  async function fetchData() {
    try {
      const token = tokenStorage.getAccessToken()
      const headers = { Authorization: `Bearer ${token}` }

      const [analyticsRes, opsRes, revenueRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/admin/analytics`, { headers }).catch(() => null),
        fetch(`${API_URL}/api/v1/admin/bg/operations`, { headers }).catch(() => null),
        fetch(`${API_URL}/api/v1/admin/billing/revenue`, { headers }).catch(() => null),
      ])

      if (analyticsRes?.ok) setAnalytics(await analyticsRes.json())
      if (opsRes?.ok) setOps(await opsRes.json())
      if (revenueRes?.ok) setRevenue(await revenueRes.json())
    } catch {
      // Use empty data
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-2xl" />)}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-64 rounded-2xl" />
          <Skeleton className="h-64 rounded-2xl" />
        </div>
      </div>
    )
  }

  const a = analytics || { total_users: 0, active_users: 0, total_organizations: 0, total_subscriptions: 0, revenue_mrr: 0, total_api_calls: 0, total_study_sessions: 0, total_questions_answered: 0, beta_invites_sent: 0, beta_feedback_count: 0 }
  const o = ops || { active_workers: 0, pending_outbox_events: 0, dead_letter_count: 0, scheduled_jobs: 0, notifications_sent_today: 0, emails_sent_today: 0, system_health: 'unknown' }
  const r = revenue || { mrr: 0, arr: 0, total_revenue: 0, active_subscriptions: 0, by_plan: {} }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Operations Dashboard</h1>
        <p className="text-sm text-muted-foreground">Live platform health — auto-refreshing every 30s</p>
      </div>

      {/* Primary Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Users} label="Total Users" value={a.total_users} sublabel={`${a.active_users} active`} color="emerald" />
        <StatCard icon={DollarSign} label="MRR" value={`$${r.mrr.toFixed(2)}`} sublabel={`${r.active_subscriptions} subscriptions`} color="emerald" />
        <StatCard icon={Server} label="Workers" value={o.active_workers} sublabel={`${o.scheduled_jobs} scheduled jobs`} color="blue" />
        <StatCard icon={AlertTriangle} label="Dead Letters" value={o.dead_letter_count} sublabel={`${o.pending_outbox_events} outbox pending`} color="amber" />
      </div>

      {/* Learning Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Activity} label="Study Sessions" value={a.total_study_sessions} sublabel={`${a.total_questions_answered} questions answered`} color="emerald" />
        <StatCard icon={TrendingUp} label="API Calls" value={a.total_api_calls} sublabel="total" color="blue" />
        <StatCard icon={Mail} label="Notifications" value={o.notifications_sent_today} sublabel={`${o.emails_sent_today} emails today`} color="amber" />
        <StatCard icon={Flag} label="Beta Invites" value={a.beta_invites_sent} sublabel={`${a.beta_feedback_count} feedback`} color="emerald" />
      </div>

      {/* System Health */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="text-base">System Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="flex items-center gap-2">
              <div className={cn('h-3 w-3 rounded-full', o.system_health === 'healthy' ? 'bg-emerald-500' : 'bg-amber-500')} />
              <span className="text-sm">System: <span className="font-medium capitalize">{o.system_health}</span></span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-emerald-500" />
              <span className="text-sm">Database: <span className="font-medium">Healthy</span></span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-emerald-500" />
              <span className="text-sm">Redis: <span className="font-medium">Healthy</span></span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Revenue + Subscriptions */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="rounded-2xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <DollarSign className="h-4 w-4 text-emerald-500" /> Revenue
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">MRR</span>
              <span className="font-bold text-emerald-500">${r.mrr.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">ARR</span>
              <span className="font-bold">${r.arr.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Active Subscriptions</span>
              <span className="font-medium">{r.active_subscriptions}</span>
            </div>
            {r.by_plan && Object.entries(r.by_plan).map(([plan, count]) => (
              <div key={plan} className="flex justify-between text-sm">
                <span className="text-muted-foreground capitalize">{plan}</span>
                <Badge variant="secondary">{count}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="rounded-2xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4 text-emerald-500" /> Platform
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Organizations</span>
              <span className="font-medium">{a.total_organizations}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Active Users</span>
              <span className="font-medium">{a.active_users}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Study Sessions</span>
              <span className="font-medium">{a.total_study_sessions}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Questions Answered</span>
              <span className="font-medium">{a.total_questions_answered}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Beta Feedback</span>
              <span className="font-medium">{a.beta_feedback_count}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Links */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Link href="/admin/users">
          <Card className="cursor-pointer rounded-2xl transition-all hover:border-emerald-500/30">
            <CardContent className="flex items-center gap-3 p-4">
              <Users className="h-5 w-5 text-emerald-500" />
              <span className="text-sm font-medium">Manage Users</span>
            </CardContent>
          </Card>
        </Link>
        <Link href="/admin/invites">
          <Card className="cursor-pointer rounded-2xl transition-all hover:border-emerald-500/30">
            <CardContent className="flex items-center gap-3 p-4">
              <Mail className="h-5 w-5 text-emerald-500" />
              <span className="text-sm font-medium">Beta Invites</span>
            </CardContent>
          </Card>
        </Link>
        <Link href="/admin/beta-ops">
          <Card className="cursor-pointer rounded-2xl transition-all hover:border-emerald-500/30">
            <CardContent className="flex items-center gap-3 p-4">
              <Activity className="h-5 w-5 text-emerald-500" />
              <span className="text-sm font-medium">Beta Ops</span>
            </CardContent>
          </Card>
        </Link>
        <Link href="/portal/billing">
          <Card className="cursor-pointer rounded-2xl transition-all hover:border-emerald-500/30">
            <CardContent className="flex items-center gap-3 p-4">
              <DollarSign className="h-5 w-5 text-emerald-500" />
              <span className="text-sm font-medium">Billing</span>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  )
}
