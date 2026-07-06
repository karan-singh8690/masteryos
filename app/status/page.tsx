'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CheckCircle2, AlertCircle, XCircle, Clock, Activity, Server, Database, Zap, Bell, Mail, Brain, Wifi } from 'lucide-react'
import { cn } from '@/lib/cn'

const SERVICES = [
  { name: 'API', icon: Server, status: 'operational', uptime90d: 99.98 },
  { name: 'Database', icon: Database, status: 'operational', uptime90d: 100.0 },
  { name: 'Redis Cache', icon: Zap, status: 'operational', uptime90d: 99.99 },
  { name: 'WebSocket', icon: Wifi, status: 'operational', uptime90d: 99.9 },
  { name: 'Notifications', icon: Bell, status: 'operational', uptime90d: 99.97 },
  { name: 'Email Delivery', icon: Mail, status: 'degraded', uptime90d: 98.5 },
  { name: 'AI Engine', icon: Brain, status: 'operational', uptime90d: 99.8 },
  { name: 'Background Workers', icon: Activity, status: 'operational', uptime90d: 99.95 },
]

const STATUS_CONFIG = {
  operational: {
    icon: CheckCircle2,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    dot: 'bg-emerald-500',
    label: 'Operational',
    labelClass: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  },
  degraded: {
    icon: AlertCircle,
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    dot: 'bg-amber-500',
    label: 'Degraded',
    labelClass: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  },
  down: {
    icon: XCircle,
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    dot: 'bg-red-500',
    label: 'Down',
    labelClass: 'text-red-400 bg-red-500/10 border-red-500/30',
  },
}

const INCIDENTS = [
  { date: '2026-07-02', title: 'Email delivery delays', status: 'monitoring', desc: 'Some verification emails delayed by up to 5 minutes. Investigating SMTP provider. All other services unaffected.' },
]

const MAINTENANCE = [
  { date: '2026-07-10', title: 'Database maintenance', desc: 'Scheduled PostgreSQL vacuum + index rebuild. Expected downtime: 5 minutes during off-peak hours.' },
]

// Generate 90 days of uptime history (mock data — mostly green)
const UPTIME_HISTORY = Array.from({ length: 90 }, (_, i) => {
  // Days 87 and 88 are degraded (email issue), rest operational
  if (i === 87 || i === 88) return 'degraded'
  return 'operational'
})

export default function StatusPage() {
  const allOperational = SERVICES.every((s) => s.status === 'operational')
  const operationalCount = SERVICES.filter((s) => s.status === 'operational').length
  const avgUptime = (SERVICES.reduce((sum, s) => sum + s.uptime90d, 0) / SERVICES.length).toFixed(2)

  return (
    <div className="min-h-screen bg-[#08080A] text-white">
      {/* Background glow */}
      <div className="pointer-events-none fixed inset-0 glow-emerald opacity-20" />

      <div className="relative container mx-auto px-4 py-20">
        {/* Hero */}
        <div className="mx-auto mb-16 max-w-2xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-xs font-medium text-emerald-300 backdrop-blur-sm">
            <Activity className="h-3.5 w-3.5" />
            Real-time Status
          </div>
          <h1 className="text-5xl font-bold tracking-tight">
            System{' '}
            <span className="gradient-emerald-text">Status</span>
          </h1>
          <p className="mt-4 text-lg text-zinc-400">
            Monitor the health of all MasteryOS services in real-time.
          </p>

          {/* Overall status banner */}
          <div className={cn(
            'mt-8 inline-flex items-center gap-3 rounded-2xl border px-8 py-4 backdrop-blur-sm',
            allOperational
              ? 'border-emerald-500/30 bg-emerald-500/10'
              : 'border-amber-500/30 bg-amber-500/10'
          )}>
            {allOperational ? (
              <CheckCircle2 className="h-7 w-7 text-emerald-400" />
            ) : (
              <AlertCircle className="h-7 w-7 text-amber-400" />
            )}
            <div className="text-left">
              <div className={cn('text-xl font-bold', allOperational ? 'text-emerald-400' : 'text-amber-400')}>
                {allOperational ? 'All Systems Operational' : 'Partial Service Degradation'}
              </div>
              <div className="text-sm text-zinc-400">
                {operationalCount}/{SERVICES.length} services operational · {avgUptime}% avg uptime
              </div>
            </div>
          </div>
        </div>

        {/* 90-day uptime bar */}
        <div className="mx-auto mb-12 max-w-3xl">
          <Card className="glass-card p-6">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-medium text-zinc-300">90-day uptime history</h3>
              <div className="flex items-center gap-4 text-xs text-zinc-500">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  Operational
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-amber-500" />
                  Degraded
                </span>
              </div>
            </div>
            {/* Uptime bars */}
            <div className="flex gap-0.5">
              {UPTIME_HISTORY.map((day, i) => (
                <div
                  key={i}
                  className={cn(
                    'h-10 flex-1 rounded-sm transition-all hover:scale-y-110',
                    day === 'operational' ? 'bg-emerald-500/70 hover:bg-emerald-400' : 'bg-amber-500/70 hover:bg-amber-400'
                  )}
                  title={`Day ${i + 1}: ${day}`}
                />
              ))}
            </div>
            <div className="mt-2 flex justify-between text-xs text-zinc-600">
              <span>90 days ago</span>
              <span>Today</span>
            </div>
          </Card>
        </div>

        {/* Service status cards */}
        <div className="mx-auto max-w-3xl space-y-3">
          {SERVICES.map((service, i) => {
            const config = STATUS_CONFIG[service.status as keyof typeof STATUS_CONFIG]
            const Icon = service.icon
            return (
              <Card
                key={service.name}
                className="glass-card animate-fade-in-up"
                style={{ animationDelay: `${i * 0.05}s` }}
              >
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      'flex h-10 w-10 items-center justify-center rounded-xl ring-1 ring-inset',
                      config.bg,
                      config.border,
                    )}>
                      <Icon className={cn('h-5 w-5', config.color)} />
                    </div>
                    <div>
                      <div className="font-semibold text-white">{service.name}</div>
                      <div className="text-xs text-zinc-500">{service.uptime90d}% uptime (90d)</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {/* Mini uptime sparkline (last 14 days) */}
                    <div className="hidden gap-0.5 sm:flex">
                      {UPTIME_HISTORY.slice(-14).map((day, j) => (
                        <div
                          key={j}
                          className={cn(
                            'h-6 w-1 rounded-sm',
                            day === 'operational' ? 'bg-emerald-500/60' : 'bg-amber-500/60'
                          )}
                        />
                      ))}
                    </div>
                    {/* Status badge */}
                    <div className={cn(
                      'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium',
                      config.labelClass,
                    )}>
                      <span className={cn('h-1.5 w-1.5 rounded-full', config.dot)} />
                      {config.label}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Active Incidents */}
        {INCIDENTS.length > 0 && (
          <div className="mx-auto mt-16 max-w-3xl">
            <h2 className="mb-4 text-2xl font-bold text-white">Active Incidents</h2>
            {INCIDENTS.map((inc) => (
              <Card key={inc.title} className="glass-card border-amber-500/20">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="h-2 w-2 animate-pulse rounded-full bg-amber-500" />
                        <h3 className="font-semibold text-white">{inc.title}</h3>
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-zinc-400">{inc.desc}</p>
                      <p className="mt-2 text-xs text-zinc-600">{inc.date}</p>
                    </div>
                    <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-400 capitalize">
                      {inc.status}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Scheduled Maintenance */}
        {MAINTENANCE.length > 0 && (
          <div className="mx-auto mt-12 max-w-3xl">
            <h2 className="mb-4 text-2xl font-bold text-white">Scheduled Maintenance</h2>
            {MAINTENANCE.map((m) => (
              <Card key={m.title} className="glass-card">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-zinc-500" />
                        <h3 className="font-semibold text-white">{m.title}</h3>
                      </div>
                      <p className="mt-2 text-sm leading-relaxed text-zinc-400">{m.desc}</p>
                    </div>
                    <Badge variant="outline" className="border-white/15 bg-white/5 text-zinc-300">
                      <Clock className="mr-1 h-3 w-3" />
                      {m.date}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Footer note */}
        <div className="mx-auto mt-16 max-w-3xl text-center">
          <p className="text-sm text-zinc-500">
            Status data updates every 60 seconds. Last updated: {new Date().toLocaleString()}
          </p>
          <p className="mt-2 text-xs text-zinc-600">
            Need help? Visit our{' '}
            <a href="/support" className="text-emerald-400 hover:text-emerald-300 transition-colors">Support Center</a>
          </p>
        </div>
      </div>
    </div>
  )
}
