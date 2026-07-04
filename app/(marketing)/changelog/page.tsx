'use client'
import { Badge } from '@/components/ui/badge'
import { Check, Wrench, AlertTriangle } from 'lucide-react'

const RELEASES = [
  { version: 'v1.1.0', date: '2026-07-15', type: 'minor', features: ['Beta Operations Dashboard with 17 KPIs', 'Registration funnel analytics', 'User Success Center with 8 at-risk signals', 'Experiment platform with statistical significance testing', 'Release management with canary/staged rollout'], fixes: ['Fixed invite email dispatch not being wired', 'Fixed backup script Redis auth issue', 'Fixed Grafana dashboard provisioning format'], breaking: [] },
  { version: 'v1.0.1', date: '2026-07-03', type: 'patch', features: [], fixes: ['Fixed PostgreSQL SSL cert mounting in production', 'Fixed Nginx SSL cert provisioning script', 'Installed curl in Docker images for healthchecks', 'Resolved database init script ordering', 'Wired Prometheus exporters + Alertmanager', 'Completed SMTP configuration in Settings class', 'Enforced admin RBAC on beta endpoints', 'Fixed CSP headers for Next.js compatibility'], breaking: [] },
  { version: 'v1.0.0', date: '2026-06-15', type: 'major', features: ['Closed Beta system with invite management', 'Argon2id + RS256 JWT + MFA authentication', 'RBAC with 6 roles and 30+ permissions', 'Background processing (outbox, scheduler, notifications, email)', 'AI platform with provider abstraction (Ollama, OpenAI, Gemini, Anthropic)', 'Content authoring portal with template builder', 'Admin portal with operations dashboard', 'WebSocket real-time updates', 'Offline support with optimistic UI', 'Comprehensive monitoring (Prometheus + Grafana + Sentry)'], fixes: [], breaking: ['Initial public release'] },
]

const TYPE_COLORS: Record<string, string> = {
  major: 'bg-purple-600', minor: 'bg-blue-600', patch: 'bg-teal-600', hotfix: 'bg-red-600', beta: 'bg-amber-600',
}

export default function ChangelogPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto mb-16 max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">Changelog</h1>
        <p className="mt-4 text-lg text-muted-foreground">What is new in MasteryOS.</p>
      </div>
      <div className="mx-auto max-w-3xl space-y-12">
        {RELEASES.map((rel) => (
          <div key={rel.version} className="relative border-l-2 border-border pl-8">
            <div className="absolute -left-[9px] top-0 h-4 w-4 rounded-full border-2 border-background bg-blue-600" />
            <div className="mb-4 flex items-center gap-3">
              <h2 className="text-2xl font-bold">{rel.version}</h2>
              <Badge className={TYPE_COLORS[rel.type]}>{rel.type}</Badge>
              <span className="text-sm text-muted-foreground">{rel.date}</span>
            </div>
            {rel.features.length > 0 && (
              <div className="mb-4">
                <h3 className="mb-2 flex items-center gap-2 font-semibold text-teal-600"><Check className="h-4 w-4" /> New Features</h3>
                <ul className="space-y-1">{rel.features.map((f) => <li key={f} className="text-sm text-muted-foreground">{f}</li>)}</ul>
              </div>
            )}
            {rel.fixes.length > 0 && (
              <div className="mb-4">
                <h3 className="mb-2 flex items-center gap-2 font-semibold text-blue-600"><Wrench className="h-4 w-4" /> Bug Fixes</h3>
                <ul className="space-y-1">{rel.fixes.map((f) => <li key={f} className="text-sm text-muted-foreground">{f}</li>)}</ul>
              </div>
            )}
            {rel.breaking.length > 0 && (
              <div>
                <h3 className="mb-2 flex items-center gap-2 font-semibold text-red-600"><AlertTriangle className="h-4 w-4" /> Breaking Changes</h3>
                <ul className="space-y-1">{rel.breaking.map((f) => <li key={f} className="text-sm text-muted-foreground">{f}</li>)}</ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
