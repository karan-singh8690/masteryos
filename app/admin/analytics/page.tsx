'use client'

import { BarChart3, TrendingUp, Users, Activity, Server, Mail } from 'lucide-react'

import { usePlatformAnalytics } from '@/hooks/use-admin'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { ActivityBarChart, TrendChart } from '@/components/charts'

export default function AdminAnalyticsPage() {
  const { data: analytics, isLoading } = usePlatformAnalytics()

  if (isLoading) return <div className="space-y-6"><Skeleton className="h-8 w-48" /><div className="grid gap-4 md:grid-cols-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-48 w-full" />)}</div></div>
  if (!analytics) return null

  // Defensive: backend may return flat fields instead of nested arrays/objects.
  // Use optional chaining + fallbacks everywhere.
  const userGrowth = analytics.user_growth ?? []
  const learningActivity = analytics.learning_activity ?? []
  const workerThroughput = analytics.worker_throughput ?? []
  const emailMetrics = analytics.email_metrics ?? { sent: 0, failed: 0, bounced: 0 }
  const notificationMetrics = analytics.notification_metrics ?? { queued: 0, delivered: 0, failed: 0 }
  const systemUtilization = analytics.system_utilization ?? {
    cpu_usage: 0, memory_usage: 0, disk_usage: 0, db_connections: 0, redis_connections: 0,
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Platform Analytics</h1><p className="text-sm text-muted-foreground">Platform-wide metrics and trends</p></div>

      {/* Summary stats from flat backend fields */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card><CardContent className="pt-6"><div className="text-2xl font-bold">{(analytics as any).total_users ?? 0}</div><p className="text-xs text-muted-foreground">Total Users</p></CardContent></Card>
        <Card><CardContent className="pt-6"><div className="text-2xl font-bold">{(analytics as any).active_users ?? 0}</div><p className="text-xs text-muted-foreground">Active Users</p></CardContent></Card>
        <Card><CardContent className="pt-6"><div className="text-2xl font-bold">{(analytics as any).total_study_sessions ?? 0}</div><p className="text-xs text-muted-foreground">Study Sessions</p></CardContent></Card>
        <Card><CardContent className="pt-6"><div className="text-2xl font-bold">{(analytics as any).total_questions_answered ?? 0}</div><p className="text-xs text-muted-foreground">Questions Answered</p></CardContent></Card>
      </div>

      {userGrowth.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Users className="h-4 w-4" />User Growth</CardTitle><CardDescription>New users per day</CardDescription></CardHeader>
            <CardContent><TrendChart data={userGrowth.map(u => ({ date: u.date, value: u.new_users }))} title="New Users" height={180} /></CardContent>
          </Card>
          <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Activity className="h-4 w-4" />Learning Activity</CardTitle><CardDescription>Questions answered per day</CardDescription></CardHeader>
            <CardContent><ActivityBarChart data={learningActivity.map(a => ({ label: a.date.slice(5), value: a.questions_answered }))} title="" height={180} /></CardContent>
          </Card>
        </div>
      )}

      {workerThroughput.length > 0 && (
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Server className="h-4 w-4" />Worker Throughput</CardTitle><CardDescription>Events processed per day</CardDescription></CardHeader>
          <CardContent><ActivityBarChart data={workerThroughput.map(w => ({ label: w.date.slice(5), value: w.events_processed }))} title="" height={200} /></CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card><CardHeader><CardTitle className="text-base">Email Metrics</CardTitle></CardHeader>
          <CardContent><div className="grid grid-cols-3 gap-4"><div><p className="text-xs text-muted-foreground">Sent</p><p className="text-lg font-bold">{emailMetrics.sent}</p></div><div><p className="text-xs text-muted-foreground">Failed</p><p className="text-lg font-bold text-destructive">{emailMetrics.failed}</p></div><div><p className="text-xs text-muted-foreground">Bounced</p><p className="text-lg font-bold text-warning">{emailMetrics.bounced}</p></div></div></CardContent>
        </Card>
        <Card><CardHeader><CardTitle className="text-base">Notification Metrics</CardTitle></CardHeader>
          <CardContent><div className="grid grid-cols-3 gap-4"><div><p className="text-xs text-muted-foreground">Queued</p><p className="text-lg font-bold">{notificationMetrics.queued}</p></div><div><p className="text-xs text-muted-foreground">Delivered</p><p className="text-lg font-bold text-success">{notificationMetrics.delivered}</p></div><div><p className="text-xs text-muted-foreground">Failed</p><p className="text-lg font-bold text-destructive">{notificationMetrics.failed}</p></div></div></CardContent>
        </Card>
      </div>

      <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><TrendingUp className="h-4 w-4" />System Utilization</CardTitle></CardHeader>
        <CardContent><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div><p className="text-xs text-muted-foreground">CPU</p><p className="text-lg font-bold">{systemUtilization.cpu_usage}%</p></div>
          <div><p className="text-xs text-muted-foreground">Memory</p><p className="text-lg font-bold">{systemUtilization.memory_usage}%</p></div>
          <div><p className="text-xs text-muted-foreground">Disk</p><p className="text-lg font-bold">{systemUtilization.disk_usage}%</p></div>
          <div><p className="text-xs text-muted-foreground">DB Conns</p><p className="text-lg font-bold">{systemUtilization.db_connections}</p></div>
          <div><p className="text-xs text-muted-foreground">Redis Conns</p><p className="text-lg font-bold">{systemUtilization.redis_connections}</p></div>
        </div></CardContent>
      </Card>
    </div>
  )
}
