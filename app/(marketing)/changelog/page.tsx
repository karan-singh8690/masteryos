'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Check, Wrench, AlertTriangle, Sparkles, Rocket, Zap, Shield, Brain, Trophy, Palette } from 'lucide-react'
import { cn } from '@/lib/cn'

const RELEASES = [
  {
    version: 'v1.2.0',
    date: 'July 6, 2026',
    type: 'minor',
    title: 'Premium Dark Redesign + Full Study Flow',
    features: [
      { icon: Palette, text: 'Complete dark premium redesign — glassmorphism, emerald gradients, glow effects across all pages' },
      { icon: Rocket, text: 'Full study session flow: start → answer questions → see explanations → finish → view summary' },
      { icon: Brain, text: 'Adaptive queue generates real Python interview questions from seeded content' },
      { icon: Trophy, text: 'Mastery tracking with concept names (not UUIDs), weak/strong concept display' },
      { icon: Shield, text: 'Answer scoring fixed — correct answers now properly marked as correct' },
      { icon: Zap, text: 'Abandon session + End session endpoints added' },
      { icon: Sparkles, text: 'Premium UI components: glass cards, gradient buttons, emerald switches, dark inputs' },
    ],
    fixes: [
      'Fixed 409 on answered questions (adaptive queue now returns only unanswered)',
      'Fixed choice_id vs choice key mismatch in answer scoring',
      'Fixed auth provider race condition (redirect to login on every navigation)',
      'Fixed UUID not JSON serializable in outbox events',
      'Fixed adaptive queue NoneType error (list(goals) when goals is None)',
      'Fixed parameter_seed exceeding int32 range',
      'Fixed duplicate navigation on landing page + profile/settings pages',
      'Fixed session summary 404 (added GET /study-sessions/{id}/summary endpoint)',
      'Fixed WebSocket 403 (was creating new JWT key manager per connection)',
    ],
    breaking: [],
  },
  {
    version: 'v1.1.0',
    date: 'July 5, 2026',
    type: 'minor',
    title: 'Open Beta + Admin Tools',
    features: [
      { icon: Sparkles, text: 'Open Beta mode — anyone can register freely without invite tokens' },
      { icon: Shield, text: 'Three-state beta mode: off / closed / open (admin-togglable from System Config)' },
      { icon: Brain, text: 'Beta banner dynamically reflects current beta mode' },
      { icon: Trophy, text: 'Admin users page with MFA badges, role management, GDPR anonymize' },
    ],
    fixes: [
      'Fixed admin pages crashing with .map() on undefined',
      'Added security dashboard + incidents endpoints',
      'Fixed admin Email/Audit/Analytics page crashes',
    ],
    breaking: [],
  },
  {
    version: 'v1.0.1',
    date: 'July 3, 2026',
    type: 'patch',
    title: 'Production Deployment Fixes',
    features: [],
    fixes: [
      'Auto-seed Python interview content on backend startup',
      'Auto-create default algorithm version for answer scoring',
      'Fixed WebSocket authentication (TokenClaims.user_id vs claims.get)',
      'Fixed CORS parsing for Railway deployment',
      'Fixed CSRF exemption for WebSocket paths',
      'Auto-verify email on registration (skip SMTP for beta)',
      'First-admin bypass for closed beta registration',
    ],
    breaking: [],
  },
  {
    version: 'v1.0.0',
    date: 'June 15, 2026',
    type: 'major',
    title: 'Initial Public Release',
    features: [
      { icon: Shield, text: 'Argon2id + RS256 JWT + MFA authentication' },
      { icon: Brain, text: 'Adaptive mastery engine with spaced repetition' },
      { icon: Trophy, text: 'RBAC with 6 roles and 30+ permissions' },
      { icon: Zap, text: 'Background processing (outbox, scheduler, notifications, email)' },
      { icon: Sparkles, text: 'AI platform with provider abstraction' },
      { icon: Rocket, text: 'Content authoring portal with template builder' },
      { icon: Shield, text: 'Admin portal with operations dashboard' },
      { icon: Zap, text: 'WebSocket real-time updates' },
      { icon: Brain, text: 'Offline support with optimistic UI' },
      { icon: Shield, text: 'Comprehensive monitoring (Prometheus + Grafana + Sentry)' },
    ],
    fixes: [],
    breaking: ['Initial public release'],
  },
]

const TYPE_CONFIG: Record<string, { color: string; bg: string; border: string; icon: typeof Sparkles }> = {
  major: { color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/30', icon: Rocket },
  minor: { color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', icon: Sparkles },
  patch: { color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30', icon: Wrench },
  hotfix: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/30', icon: AlertTriangle },
  beta: { color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30', icon: Zap },
}

export default function ChangelogPage() {
  return (
    <div className="min-h-screen bg-[#08080A] text-white">
      {/* Background glow */}
      <div className="pointer-events-none fixed inset-0 glow-emerald opacity-20" />

      <div className="relative container mx-auto px-4 py-20">
        {/* Hero */}
        <div className="mx-auto mb-16 max-w-2xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-xs font-medium text-emerald-300 backdrop-blur-sm">
            <Rocket className="h-3.5 w-3.5" />
            Product Updates
          </div>
          <h1 className="text-5xl font-bold tracking-tight">
            <span className="gradient-emerald-text">Changelog</span>
          </h1>
          <p className="mt-4 text-lg text-zinc-400">
            What&apos;s new in MasteryOS. We ship improvements every week.
          </p>
        </div>

        {/* Timeline */}
        <div className="mx-auto max-w-3xl">
          <div className="relative space-y-8 before:absolute before:left-[19px] before:top-2 before:h-full before:w-px before:bg-gradient-to-b before:from-emerald-500/40 before:via-white/10 before:to-transparent">
            {RELEASES.map((rel, i) => {
              const typeConfig = TYPE_CONFIG[rel.type] ?? TYPE_CONFIG.minor!
              const TypeIcon = typeConfig.icon
              return (
                <div key={rel.version} className="relative pl-12 animate-fade-in-up" style={{ animationDelay: `${i * 0.1}s` }}>
                  {/* Timeline dot */}
                  <div className={cn(
                    'absolute left-0 top-1 flex h-10 w-10 items-center justify-center rounded-full ring-4 ring-[#08080A]',
                    typeConfig.bg,
                    'border',
                    typeConfig.border,
                  )}>
                    <TypeIcon className={cn('h-5 w-5', typeConfig.color)} />
                  </div>

                  {/* Release card */}
                  <Card className="glass-card">
                    <CardContent className="pt-6">
                      {/* Header */}
                      <div className="mb-4 flex flex-wrap items-center gap-3">
                        <h2 className="text-2xl font-bold text-white">{rel.version}</h2>
                        <Badge variant="outline" className={cn('border', typeConfig.border, typeConfig.bg, typeConfig.color, 'capitalize')}>
                          {rel.type}
                        </Badge>
                        <span className="text-sm text-zinc-500">{rel.date}</span>
                      </div>
                      <p className="mb-4 text-sm font-medium text-zinc-300">{rel.title}</p>

                      {/* Features */}
                      {rel.features.length > 0 && (
                        <div className="mb-4">
                          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-emerald-400">
                            <Check className="h-4 w-4" />
                            New Features
                          </h3>
                          <ul className="space-y-2.5">
                            {rel.features.map((f, j) => {
                              const FeatureIcon = f.icon
                              return (
                                <li key={j} className="flex items-start gap-3">
                                  <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 ring-1 ring-inset ring-emerald-500/20">
                                    <FeatureIcon className="h-3.5 w-3.5 text-emerald-400" />
                                  </div>
                                  <span className="text-sm leading-relaxed text-zinc-300">{f.text}</span>
                                </li>
                              )
                            })}
                          </ul>
                        </div>
                      )}

                      {/* Fixes */}
                      {rel.fixes.length > 0 && (
                        <div className="mb-4">
                          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-blue-400">
                            <Wrench className="h-4 w-4" />
                            Bug Fixes
                          </h3>
                          <ul className="space-y-1.5">
                            {rel.fixes.map((f, j) => (
                              <li key={j} className="flex items-start gap-2 text-sm text-zinc-400">
                                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-blue-400" />
                                {f}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Breaking changes */}
                      {rel.breaking.length > 0 && (
                        <div>
                          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-red-400">
                            <AlertTriangle className="h-4 w-4" />
                            Breaking Changes
                          </h3>
                          <ul className="space-y-1.5">
                            {rel.breaking.map((f, j) => (
                              <li key={j} className="flex items-start gap-2 text-sm text-zinc-400">
                                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-red-400" />
                                {f}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              )
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="mx-auto mt-16 max-w-3xl text-center">
          <Card className="glass-card p-6">
            <p className="text-sm text-zinc-400">
              Want to suggest a feature or report a bug?{' '}
              <a href="/support" className="font-medium text-emerald-400 hover:text-emerald-300 transition-colors">
                Visit our Support Center
              </a>
            </p>
          </Card>
        </div>
      </div>
    </div>
  )
}
