import Link from 'next/link'
import {
  BookOpen,
  Code2,
  Terminal,
  Server,
  Shield,
  Brain,
  FileText,
  Wrench,
  ArrowRight,
  type LucideIcon,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface DocSection {
  icon: LucideIcon
  title: string
  desc: string
  href: string
  tag?: string
}

const SECTIONS: DocSection[] = [
  {
    icon: BookOpen,
    title: 'Getting Started',
    desc: 'Quick start guide, installation steps, and a high-level architecture overview.',
    href: '/docs/getting-started',
    tag: 'New',
  },
  {
    icon: Code2,
    title: 'REST API',
    desc: 'Complete REST API reference with request examples and response schemas.',
    href: '/docs/rest-api',
  },
  {
    icon: Terminal,
    title: 'CLI',
    desc: 'Command-line tool for managing MasteryOS resources and deployments.',
    href: '/docs/cli',
  },
  {
    icon: Server,
    title: 'SDKs',
    desc: 'Official SDKs for Python, JavaScript, Go, Java, and C#.',
    href: '/docs/sdks',
  },
  {
    icon: Shield,
    title: 'Security',
    desc: 'Authentication, RBAC, audit logging, and compliance controls.',
    href: '/docs/security',
  },
  {
    icon: Brain,
    title: 'AI Platform',
    desc: 'Provider-agnostic AI with safety controls and cost guardrails.',
    href: '/docs/ai',
    tag: 'Popular',
  },
  {
    icon: FileText,
    title: 'Changelog',
    desc: 'Version history, release notes, and breaking change migrations.',
    href: '/changelog',
  },
  {
    icon: Wrench,
    title: 'Troubleshooting',
    desc: 'Common issues, error diagnostics, and known solutions.',
    href: '/docs/troubleshooting',
  },
]

export default function DocsPage() {
  return (
    <div className="space-y-12">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-emerald-500/[0.08] via-transparent to-transparent p-8 sm:p-12">
        <div
          className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-emerald-500/10 blur-3xl"
          aria-hidden="true"
        />
        <div className="relative">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
            Documentation
          </span>
          <h1 className="mt-4 text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl">
            Documentation
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground">
            Everything you need to build with MasteryOS — from quick start guides to deep
            platform references.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/docs/getting-started"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 transition-all hover:from-emerald-600 hover:to-emerald-700"
            >
              Get started
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
            <Link
              href="/docs/rest-api"
              className="inline-flex items-center gap-2 rounded-xl border border-border/60 bg-background px-5 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-muted"
            >
              <Code2 className="h-4 w-4 text-emerald-500" aria-hidden="true" />
              Browse the API
            </Link>
          </div>
        </div>
      </section>

      {/* Category grid */}
      <section>
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Browse by category</h2>
          <span className="text-xs text-muted-foreground">{SECTIONS.length} sections</span>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {SECTIONS.map((section) => {
            const Icon = section.icon
            return (
              <Link
                key={section.title}
                href={section.href}
                className="group block focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded-2xl"
              >
                <Card className="h-full rounded-2xl border-border/60 transition-all duration-200 hover:-translate-y-0.5 hover:border-emerald-500/40 hover:shadow-lg hover:shadow-emerald-500/[0.06]">
                  <CardHeader className="p-5">
                    <div className="mb-3 flex items-center justify-between">
                      <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-500 transition-colors group-hover:bg-emerald-500/20">
                        <Icon className="h-5 w-5" aria-hidden="true" />
                      </span>
                      {section.tag && (
                        <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                          {section.tag}
                        </span>
                      )}
                    </div>
                    <CardTitle className="flex items-center gap-1.5 text-base">
                      {section.title}
                      <ArrowRight
                        className="h-3.5 w-3.5 -translate-x-1 text-emerald-500 opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100"
                        aria-hidden="true"
                      />
                    </CardTitle>
                    <CardDescription className="mt-1.5 leading-relaxed">
                      {section.desc}
                    </CardDescription>
                  </CardHeader>
                </Card>
              </Link>
            )
          })}
        </div>
      </section>

      {/* Footer help band */}
      <section className="rounded-2xl border border-border/60 bg-muted/30 p-6 sm:p-8">
        <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h3 className="text-base font-semibold text-foreground">Can’t find what you’re looking for?</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Our engineering team is here to help you ship faster.
            </p>
          </div>
          <Link
            href="/docs/troubleshooting"
            className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-border/60 bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:border-emerald-500/40 hover:text-emerald-600 dark:hover:text-emerald-400"
          >
            <Wrench className="h-4 w-4 text-emerald-500" aria-hidden="true" />
            Visit troubleshooting
          </Link>
        </div>
      </section>
    </div>
  )
}
