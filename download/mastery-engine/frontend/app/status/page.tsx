'use client'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CheckCircle2, AlertCircle, XCircle, Clock } from 'lucide-react'

const SERVICES = [
  { name: 'API', status: 'operational', uptime90d: 99.98 },
  { name: 'Workers', status: 'operational', uptime90d: 99.95 },
  { name: 'Database', status: 'operational', uptime90d: 100.0 },
  { name: 'Redis', status: 'operational', uptime90d: 99.99 },
  { name: 'WebSocket', status: 'operational', uptime90d: 99.9 },
  { name: 'Notifications', status: 'operational', uptime90d: 99.97 },
  { name: 'Email', status: 'degraded', uptime90d: 98.5 },
  { name: 'AI', status: 'operational', uptime90d: 99.8 },
]

const STATUS_CONFIG = {
  operational: { icon: CheckCircle2, color: 'text-teal-500', bg: 'bg-teal-500', label: 'Operational' },
  degraded: { icon: AlertCircle, color: 'text-amber-500', bg: 'bg-amber-500', label: 'Degraded' },
  down: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500', label: 'Down' },
}

const INCIDENTS = [
  { date: '2026-07-02', title: 'Email delivery delays', status: 'monitoring', desc: 'Some verification emails delayed by up to 5 minutes. Investigating SMTP provider.' },
]

const MAINTENANCE = [
  { date: '2026-07-10', title: 'Database maintenance', desc: 'Scheduled PostgreSQL vacuum + index rebuild. Expected downtime: 5 minutes.' },
]

export default function StatusPage() {
  const allOperational = SERVICES.every((s) => s.status === 'operational')
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto mb-12 max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">System Status</h1>
        <div className={`mt-4 inline-flex items-center gap-2 rounded-full px-6 py-2 text-lg font-semibold ${allOperational ? 'bg-teal-500/10 text-teal-600' : 'bg-amber-500/10 text-amber-600'}`}>
          {allOperational ? <><CheckCircle2 className="h-5 w-5" /> All Systems Operational</> : <><AlertCircle className="h-5 w-5" /> Partial Service Degradation</>}
        </div>
      </div>
      <div className="mx-auto max-w-3xl space-y-4">
        {SERVICES.map((service) => {
          const config = STATUS_CONFIG[service.status as keyof typeof STATUS_CONFIG]
          const Icon = config.icon
          return (
            <Card key={service.name}>
              <CardContent className="flex items-center justify-between pt-6">
                <div className="flex items-center gap-3">
                  <Icon className={`h-5 w-5 ${config.color}`} />
                  <span className="font-semibold">{service.name}</span>
                </div>
                <div className="flex items-center gap-6">
                  <div className="hidden sm:flex gap-0.5">
                    {Array.from({ length: 90 }).map((_, i) => (
                      <div key={i} className={`h-8 w-1 rounded-sm ${i < 88 ? 'bg-teal-500' : service.status === 'operational' ? 'bg-teal-500' : 'bg-amber-500'}`} />
                    ))}
                  </div>
                  <div className="text-right">
                    <Badge variant="secondary" className={config.color}>{config.label}</Badge>
                    <p className="mt-1 text-xs text-muted-foreground">{service.uptime90d}% uptime</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
      {INCIDENTS.length > 0 && (
        <div className="mx-auto mt-12 max-w-3xl">
          <h2 className="mb-4 text-2xl font-bold">Active Incidents</h2>
          {INCIDENTS.map((inc) => (
            <Card key={inc.title}><CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">{inc.title}</h3>
                <Badge variant="secondary" className="text-amber-600">{inc.status}</Badge>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{inc.desc}</p>
              <p className="mt-2 text-xs text-muted-foreground">{inc.date}</p>
            </CardContent></Card>
          ))}
        </div>
      )}
      {MAINTENANCE.length > 0 && (
        <div className="mx-auto mt-12 max-w-3xl">
          <h2 className="mb-4 text-2xl font-bold">Scheduled Maintenance</h2>
          {MAINTENANCE.map((m) => (
            <Card key={m.title}><CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">{m.title}</h3>
                <Badge variant="secondary"><Clock className="mr-1 h-3 w-3" /> {m.date}</Badge>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{m.desc}</p>
            </CardContent></Card>
          ))}
        </div>
      )}
    </div>
  )
}
