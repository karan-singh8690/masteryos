'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/cn'
import {
  Brain,
  Sparkles,
  CalendarClock,
  LayoutDashboard,
  Code2,
  Layers,
  ArrowRight,
  Check,
  UserPlus,
  BookOpen,
  Trophy,
  type LucideIcon,
} from 'lucide-react'

interface Feature {
  icon: LucideIcon
  title: string
  desc: string
}

const FEATURES: Feature[] = [
  {
    icon: Brain,
    title: 'Adaptive Mastery',
    desc: 'Personalized question selection that targets your exact knowledge edge — never too easy, never too hard.',
  },
  {
    icon: Sparkles,
    title: 'AI Explanations',
    desc: 'Context-aware explanations generated the moment you need them, with safety guardrails and audit trails.',
  },
  {
    icon: CalendarClock,
    title: 'Spaced Repetition',
    desc: 'Scientifically-backed review scheduling that strengthens long-term retention and resists the forgetting curve.',
  },
  {
    icon: LayoutDashboard,
    title: 'Real-time Dashboard',
    desc: 'Live mastery scores, streaks, and progress analytics updated instantly across every concept you touch.',
  },
  {
    icon: Code2,
    title: 'Python Interview Prep',
    desc: 'Curated FAANG-level questions spanning data structures, algorithms, and real-world system design scenarios.',
  },
  {
    icon: Layers,
    title: 'Multi-subject Support',
    desc: 'A subject-agnostic architecture — start with Python today, expand to any domain without re-platforming.',
  },
]

interface Step {
  num: string
  icon: LucideIcon
  title: string
  desc: string
}

const STEPS: Step[] = [
  {
    num: '01',
    icon: UserPlus,
    title: 'Sign Up',
    desc: 'Create your free account and complete a quick diagnostic that maps your current knowledge across every concept.',
  },
  {
    num: '02',
    icon: BookOpen,
    title: 'Study',
    desc: 'Get an adaptive recommendation for the single highest-value learning activity available at any moment.',
  },
  {
    num: '03',
    icon: Trophy,
    title: 'Master',
    desc: 'Build durable mastery through spaced repetition and track measurable progress all the way to interview readiness.',
  },
]

interface Stat {
  value: string
  label: string
}

const STATS: Stat[] = [
  { value: '10,000+', label: 'Practice Questions' },
  { value: '50+', label: 'Core Concepts' },
  { value: '95%', label: 'Retention Rate' },
  { value: 'Real-time', label: 'Mastery Analytics' },
]

interface PricingTier {
  name: string
  price: string
  cadence: string
  description: string
  features: string[]
  cta: string
  href: string
  highlighted?: boolean
}

const PRICING: PricingTier[] = [
  {
    name: 'Free',
    price: '$0',
    cadence: '/forever',
    description: 'Everything you need to start building durable mastery.',
    features: [
      'Adaptive learning engine',
      'Mastery tracking across all concepts',
      'Daily review queue',
      'Community support',
    ],
    cta: 'Get Started Free',
    href: '/register',
  },
  {
    name: 'Pro',
    price: '$19',
    cadence: '/month',
    description: 'For serious learners preparing for high-stakes interviews.',
    features: [
      'Everything in Free',
      'Unlimited AI explanations',
      'Advanced analytics & insights',
      'Unlimited daily reviews',
      'Priority email support',
    ],
    cta: 'Start Pro Trial',
    href: '/register',
    highlighted: true,
  },
  {
    name: 'Team',
    price: '$49',
    cadence: '/seat/month',
    description: 'For cohorts, bootcamps, and engineering teams that learn together.',
    features: [
      'Everything in Pro',
      'Team analytics dashboard',
      'Shared content packs',
      'SSO & SCIM provisioning',
      'Admin & instructor controls',
    ],
    cta: 'Contact Sales',
    href: '/contact',
  },
]

export default function LandingPage() {
  return (
    <>
      {/* ============================================================
          Hero — Xbox-style dark premium showcase
         ============================================================ */}
      <section className="relative min-h-[90vh] overflow-hidden">
        {/* Dark gradient background */}
        <div className="pointer-events-none absolute inset-0 gradient-dark-hero" aria-hidden="true" />
        {/* Emerald glow */}
        <div className="pointer-events-none absolute inset-0 glow-emerald opacity-80" aria-hidden="true" />
        {/* Grid overlay */}
        <div className="pointer-events-none absolute inset-0 bg-grid opacity-40 [mask-image:radial-gradient(ellipse_60%_50%_at_50%_30%,#000_60%,transparent_100%)]" aria-hidden="true" />
        {/* Floating glow orbs */}
        <div className="pointer-events-none absolute -left-32 top-1/4 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl animate-glow-pulse" aria-hidden="true" />
        <div className="pointer-events-none absolute -right-32 bottom-1/4 h-96 w-96 rounded-full bg-teal-500/8 blur-3xl animate-glow-pulse" style={{ animationDelay: '2s' }} aria-hidden="true" />

        <div className="container relative mx-auto flex min-h-[90vh] flex-col items-center justify-center px-4 py-20 text-center">
          {/* Badge */}
          <div className="animate-fade-in-up mb-8 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-sm font-medium text-emerald-300 backdrop-blur-sm">
            <Sparkles className="h-3.5 w-3.5" />
            Now in Open Beta
            <span className="ml-1 h-1.5 w-1.5 rounded-full bg-emerald-400 animate-glow-pulse" />
          </div>

          {/* Headline */}
          <h1 className="animate-fade-in-up mx-auto max-w-5xl text-balance text-5xl font-extrabold leading-[1.05] tracking-tight sm:text-6xl md:text-7xl lg:text-8xl" style={{ animationDelay: '0.1s' }}>
            The Operating System
            <br />
            for{' '}
            <span className="gradient-emerald-text animate-gradient">Learning</span>
          </h1>

          {/* Subheadline */}
          <p className="animate-fade-in-up mx-auto mt-8 max-w-2xl text-balance text-lg text-muted-foreground md:text-xl" style={{ animationDelay: '0.2s' }}>
            Adaptive mastery tracking that determines the single highest-value learning
            activity for every user. Master Python interviews with measurable, durable mastery —
            not busywork.
          </p>

          {/* CTAs */}
          <div className="animate-fade-in-up mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row" style={{ animationDelay: '0.3s' }}>
            <Button
              size="lg"
              asChild
              className="btn-glow gradient-emerald h-14 border-0 px-8 text-base font-semibold text-white shadow-lg shadow-emerald-500/30 transition-all hover:scale-[1.03] hover:shadow-emerald-500/50"
            >
              <Link href="/register">
                Get Started Free
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            <Button
              size="lg"
              variant="outline"
              asChild
              className="glass h-14 border-border/60 px-8 text-base font-semibold backdrop-blur-sm hover:border-emerald-500/40 hover:bg-emerald-500/5"
            >
              <Link href="/docs">View Documentation</Link>
            </Button>
          </div>

          <p className="animate-fade-in-up mt-6 text-sm text-muted-foreground" style={{ animationDelay: '0.4s' }}>
            No credit card required · Free forever plan · Cancel anytime
          </p>

          {/* Stats bar */}
          <div className="animate-fade-in-up mt-16 grid w-full max-w-4xl grid-cols-2 gap-6 sm:grid-cols-4" style={{ animationDelay: '0.5s' }}>
            {STATS.map((stat, i) => (
              <div key={i} className="glass-card rounded-2xl p-5">
                <div className="gradient-emerald-text text-3xl font-extrabold md:text-4xl">{stat.value}</div>
                <div className="mt-1 text-sm text-muted-foreground">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================================
          Feature grid — glassmorphism cards
         ============================================================ */}
      <section className="relative overflow-hidden border-t border-border/40">
        <div className="pointer-events-none absolute inset-0 glow-emerald opacity-30" aria-hidden="true" />
        <div className="container relative mx-auto px-4 py-20 md:py-28">
          <div className="mx-auto mb-14 max-w-2xl text-center">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-sm font-medium text-emerald-300">
              <Sparkles className="h-3.5 w-3.5" />
              Features
            </div>
            <h2 className="text-balance text-3xl font-bold tracking-tight md:text-5xl">
              Everything you need to master{' '}
              <span className="gradient-emerald-text">Python</span>
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Six core systems that work together to turn scattered practice into measurable,
              durable mastery.
            </p>
          </div>

          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => {
              const Icon = feature.icon
              return (
                <div
                  key={feature.title}
                  className="glass-card group rounded-2xl p-6"
                >
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl gradient-emerald shadow-lg shadow-emerald-500/20 transition-transform group-hover:scale-110">
                    <Icon className="h-6 w-6 text-white" />
                  </div>
                  <h3 className="text-lg font-bold text-foreground">{feature.title}</h3>
                  <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
                    {feature.desc}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ============================================================
          How it works
         ============================================================ */}
      <section className="border-y border-border/60 bg-muted/20">
        <div className="container mx-auto px-4 py-20 md:py-28">
          <div className="mx-auto mb-14 max-w-2xl text-center">
            <Badge variant="outline" className="mb-4 border-border text-muted-foreground">
              How it works
            </Badge>
            <h2 className="text-balance text-3xl font-bold tracking-tight md:text-4xl">
              Three steps to mastery
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              From cold start to interview-ready in a single, adaptive loop.
            </p>
          </div>

          <div className="relative grid gap-8 md:grid-cols-3 md:gap-6">
            {/* Connecting line on desktop */}
            <div
              className="pointer-events-none absolute left-0 right-0 top-9 hidden h-px bg-gradient-to-r from-transparent via-emerald-500/40 to-transparent md:block"
              aria-hidden="true"
            />
            {STEPS.map((step) => {
              const Icon = step.icon
              return (
                <div key={step.num} className="relative flex flex-col items-center text-center">
                  <div className="relative z-10 mb-5 flex h-[4.5rem] w-[4.5rem] items-center justify-center rounded-2xl gradient-emerald shadow-lg shadow-emerald-500/25">
                    <Icon className="h-7 w-7 text-white" />
                  </div>
                  <span className="mb-2 text-xs font-bold uppercase tracking-widest text-emerald-500 dark:text-emerald-400">
                    Step {step.num}
                  </span>
                  <h3 className="text-xl font-semibold">{step.title}</h3>
                  <p className="mt-2 max-w-xs text-[15px] leading-relaxed text-muted-foreground">
                    {step.desc}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ============================================================
          Stats
         ============================================================ */}
      <section className="container mx-auto px-4 py-20 md:py-24">
        <div className="grid grid-cols-2 gap-6 rounded-2xl border border-border/60 bg-card/40 p-8 backdrop-blur-sm md:grid-cols-4 md:p-10">
          {STATS.map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="gradient-emerald-text text-3xl font-extrabold tracking-tight md:text-4xl">
                {stat.value}
              </div>
              <div className="mt-1.5 text-sm font-medium text-muted-foreground">
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ============================================================
          Pricing preview
         ============================================================ */}
      <section className="container mx-auto px-4 py-20 md:py-28">
        <div className="mx-auto mb-14 max-w-2xl text-center">
          <Badge variant="outline" className="mb-4 border-border text-muted-foreground">
            Pricing
          </Badge>
          <h2 className="text-balance text-3xl font-bold tracking-tight md:text-4xl">
            Simple, transparent pricing
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Start free, upgrade when you are ready. No hidden fees, ever.
          </p>
        </div>

        <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-3">
          {PRICING.map((tier) => (
            <Card
              key={tier.name}
              className={cn(
                'relative flex flex-col rounded-2xl p-7',
                tier.highlighted
                  ? 'border-emerald-500/50 bg-card shadow-xl shadow-emerald-500/10 lg:-mt-3 lg:mb-3'
                  : 'border-border/70 bg-card/60 backdrop-blur-sm',
              )}
            >
              {tier.highlighted && (
                <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 gradient-emerald border-0 px-3 py-1 text-white shadow-md">
                  Most Popular
                </Badge>
              )}
              <h3 className="text-lg font-semibold">{tier.name}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{tier.description}</p>
              <div className="mt-5 flex items-baseline gap-1">
                <span className="text-4xl font-extrabold tracking-tight">{tier.price}</span>
                <span className="text-sm font-medium text-muted-foreground">{tier.cadence}</span>
              </div>
              <ul className="mt-6 flex-1 space-y-3">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5 text-sm">
                    <Check
                      className={cn(
                        'mt-0.5 h-4 w-4 shrink-0',
                        tier.highlighted ? 'text-emerald-500' : 'text-emerald-500/80',
                      )}
                    />
                    <span className="text-foreground/90">{feature}</span>
                  </li>
                ))}
              </ul>
              <Button
                asChild
                className={cn(
                  'mt-7 w-full',
                  tier.highlighted
                    ? 'gradient-emerald border-0 text-white shadow-md shadow-emerald-500/20 hover:shadow-emerald-500/30'
                    : '',
                )}
                variant={tier.highlighted ? 'default' : 'outline'}
              >
                <Link href={tier.href}>
                  {tier.cta}
                  <ArrowRight className="ml-1.5 h-4 w-4" />
                </Link>
              </Button>
            </Card>
          ))}
        </div>
      </section>

      {/* ============================================================
          Final CTA
         ============================================================ */}
      <section className="container mx-auto px-4 pb-24 pt-4 md:pb-32">
        <div className="relative overflow-hidden rounded-3xl gradient-emerald px-6 py-16 text-center shadow-2xl shadow-emerald-500/20 md:px-12 md:py-20">
          {/* Decorative overlay */}
          <div
            className="pointer-events-none absolute inset-0 bg-grid opacity-20 [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000,transparent)]"
            aria-hidden="true"
          />
          <div className="relative">
            <h2 className="mx-auto max-w-2xl text-balance text-3xl font-bold tracking-tight text-white md:text-4xl">
              Start mastering Python today
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-balance text-lg text-white/90">
              Join our Closed Beta and be among the first to experience adaptive mastery learning
              built for serious engineers.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
              <Button
                size="lg"
                asChild
                className="h-12 border-0 bg-white px-7 text-base font-semibold text-emerald-700 shadow-lg transition-transform hover:scale-[1.02] hover:bg-white/95"
              >
                <Link href="/register">
                  Get Started Free
                  <ArrowRight className="ml-1.5 h-4 w-4" />
                </Link>
              </Button>
              <Button
                size="lg"
                variant="outline"
                asChild
                className="h-12 border-white/40 bg-transparent px-7 text-base font-semibold text-white hover:border-white/70 hover:bg-white/10 hover:text-white"
              >
                <Link href="/pricing">Compare Plans</Link>
              </Button>
            </div>
            <p className="mt-5 text-sm text-white/80">
              No credit card required · Free forever plan · Cancel anytime
            </p>
          </div>
        </div>
      </section>
    </>
  )
}
