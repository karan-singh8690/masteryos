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

  return (
    <div className="max-w-4xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Platform Analytics</h1><p className="text-sm text-muted-foreground">Platform-wide metrics and trends</p></div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Users className="h-4 w-4" />User Growth</CardTitle><CardDescription>New users per day</CardDescription></CardHeader>
          <CardContent><TrendChart data={analytics.user_growth.map(u => ({ date: u.date, value: u.new_users }))} title="New Users" height={180} /></CardContent>
        </Card>
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Activity className="h-4 w-4" />Learning Activity</CardTitle><CardDescription>Questions answered per day</CardDescription></CardHeader>
          <CardContent><ActivityBarChart data={analytics.learning_activity.map(a => ({ label: a.date.slice(5), value: a.questions_answered }))} title="" height={180} /></CardContent>
        </Card>
      </div>

      <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Server className="h-4 w-4" />Worker Throughput</CardTitle><CardDescription>Events processed per day</CardDescription></CardHeader>
        <CardContent><ActivityBarChart data={analytics.worker_throughput.map(w => ({ label: w.date.slice(5), value: w.events_processed }))} title="" height={200} /></CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card><CardHeader><CardTitle className="text-base">Email Metrics</CardTitle></CardHeader>
          <CardContent><div className="grid grid-cols-3 gap-4"><div><p className="text-xs text-muted-foreground">Sent</p><p className="text-lg font-bold">{analytics.email_metrics.sent}</p></div><div><p className="text-xs text-muted-foreground">Failed</p><p className="text-lg font-bold text-destructive">{analytics.email_metrics.failed}</p></div><div><p className="text-xs text-muted-foreground">Bounced</p><p className="text-lg font-bold text-warning">{analytics.email_metrics.bounced}</p></div></div></CardContent>
        </Card>
        <Card><CardHeader><CardTitle className="text-base">Notification Metrics</CardTitle></CardHeader>
          <CardContent><div className="grid grid-cols-3 gap-4"><div><p className="text-xs text-muted-foreground">Queued</p><p className="text-lg font-bold">{analytics.notification_metrics.queued}</p></div><div><p className="text-xs text-muted-foreground">Delivered</p><p className="text-lg font-bold text-success">{analytics.notification_metrics.delivered}</p></div><div><p className="text-xs text-muted-foreground">Failed</p><p className="text-lg font-bold text-destructive">{analytics.notification_metrics.failed}</p></div></div></CardContent>
        </Card>
      </div>

      <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><TrendingUp className="h-4 w-4" />System Utilization</CardTitle></CardHeader>
        <CardContent><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div><p className="text-xs text-muted-foreground">CPU</p><p className="text-lg font-bold">{analytics.system_utilization.cpu_usage}%</p></div>
          <div><p className="text-xs text-muted-foreground">Memory</p><p className="text-lg font-bold">{analytics.system_utilization.memory_usage}%</p></div>
          <div><p className="text-xs text-muted-foreground">Disk</p><p className="text-lg font-bold">{analytics.system_utilization.disk_usage}%</p></div>
          <div><p className="text-xs text-muted-foreground">DB Conns</p><p className="text-lg font-bold">{analytics.system_utilization.db_connections}</p></div>
          <div><p className="text-xs text-muted-foreground">Redis Conns</p><p className="text-lg font-bold">{analytics.system_utilization.redis_connections}</p></div>
        </div></CardContent>
      </Card>
    </div>
  )
}
