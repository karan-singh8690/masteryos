'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
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
  BookOpen,
  Trophy,
  Zap,
  Shield,
  Target,
  TrendingUp,
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
    title: 'Code Execution',
    desc: 'Run Python code directly in the browser with safe sandboxed execution and instant feedback on your solutions.',
  },
  {
    icon: Layers,
    title: 'Concept Graph',
    desc: 'Visual mastery map showing how concepts connect, prerequisite relationships, and your readiness for interviews.',
  },
]

const STATS = [
  { value: '10K+', label: 'Active Learners' },
  { value: '500+', label: 'Interview Questions' },
  { value: '94%', label: 'Mastery Retention' },
  { value: '4.9★', label: 'User Rating' },
]

const STEPS = [
  {
    num: '01',
    title: 'Assess',
    desc: 'Take a diagnostic session to identify your current mastery level across all concepts.',
    icon: Target,
  },
  {
    num: '02',
    title: 'Practice',
    desc: 'Get adaptive questions that target your weak areas — each session builds on the last.',
    icon: Zap,
  },
  {
    num: '03',
    title: 'Master',
    desc: 'Watch your mastery scores climb as spaced repetition locks knowledge into long-term memory.',
    icon: TrendingUp,
  },
]

const TESTIMONIALS = [
  {
    name: 'Sarah K.',
    role: 'Software Engineer at Stripe',
    quote: 'I went from failing technical interviews to getting 3 offers in 2 weeks. The adaptive practice is unreal.',
    avatar: 'S',
  },
  {
    name: 'Marcus L.',
    role: 'CS Student at MIT',
    quote: 'The mastery tracking is addictive. I can actually SEE myself getting smarter. Nothing else comes close.',
    avatar: 'M',
  },
  {
    name: 'Priya R.',
    role: 'Backend Dev at Discord',
    quote: 'The spaced repetition system is what sets this apart. I retain everything now, not just cram and forget.',
    avatar: 'P',
  },
]

export default function MarketingHomePage() {
  return (
    <div className="min-h-screen bg-[#08080A] text-white overflow-hidden">
      {/* ============================================================ */}
      {/* HERO SECTION — Xbox-style showcase                           */}
      {/* ============================================================ */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
        {/* Animated gradient background */}
        <div className="absolute inset-0 gradient-dark-hero" />
        <div className="absolute inset-0 bg-grid opacity-30" />
        <div className="absolute inset-0 glow-emerald animate-glow-pulse" />

        {/* Floating glow orbs */}
        <div className="absolute top-1/4 left-1/4 h-96 w-96 rounded-full bg-emerald-500/20 blur-[120px] animate-float" />
        <div className="absolute bottom-1/4 right-1/4 h-96 w-96 rounded-full bg-teal-500/15 blur-[120px] animate-float" style={{ animationDelay: '2s' }} />

        {/* Nav */}
        <nav className="absolute top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-5 md:px-12">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-teal-600 text-sm font-bold text-black shadow-lg shadow-emerald-500/30">
              M
            </div>
            <span className="text-lg font-bold tracking-tight text-white">Mastery<span className="gradient-emerald-text">OS</span></span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login" className="hidden text-sm font-medium text-zinc-400 transition-colors hover:text-white sm:block">
              Sign in
            </Link>
            <Link href="/register">
              <Button className="btn-glow gradient-emerald text-black font-semibold shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-shadow">
                Get Started
                <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </nav>

        {/* Hero content */}
        <div className="relative z-10 mx-auto max-w-5xl px-6 text-center">
          {/* Badge */}
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-xs font-medium text-emerald-300 backdrop-blur-sm animate-fade-in-up">
            <Sparkles className="h-3.5 w-3.5" />
            The Operating System for Learning
          </div>

          {/* Headline */}
          <h1 className="text-5xl font-bold leading-[1.1] tracking-tight sm:text-6xl md:text-7xl lg:text-8xl animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
            Master Python
            <br />
            <span className="gradient-emerald-text">Interview Prep</span>
            <br />
            in 30 Days
          </h1>

          {/* Subheadline */}
          <p className="mx-auto mt-6 max-w-2xl text-lg text-zinc-400 sm:text-xl animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
            Adaptive practice, spaced repetition, and AI-powered explanations.
            The learning platform that actually makes you smarter — not just memorize.
          </p>

          {/* CTAs */}
          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
            <Link href="/register">
              <Button size="lg" className="btn-glow gradient-emerald text-lg font-semibold text-black shadow-xl shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-all hover:scale-105">
                Start Learning Free
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="outline" className="glass border-white/20 text-lg font-medium text-white hover:bg-white/10">
                Sign in
              </Button>
            </Link>
          </div>

          {/* Trust signals */}
          <div className="mt-12 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-zinc-500 animate-fade-in-up" style={{ animationDelay: '0.4s' }}>
            <span className="flex items-center gap-1.5"><Check className="h-4 w-4 text-emerald-400" /> Free forever plan</span>
            <span className="flex items-center gap-1.5"><Check className="h-4 w-4 text-emerald-400" /> No credit card required</span>
            <span className="flex items-center gap-1.5"><Check className="h-4 w-4 text-emerald-400" /> 500+ interview questions</span>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-float">
          <div className="flex h-10 w-6 items-start justify-center rounded-full border-2 border-white/20 p-1.5">
            <div className="h-2 w-1 rounded-full bg-emerald-400" />
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* STATS BAR                                                    */}
      {/* ============================================================ */}
      <section className="relative border-y border-white/5 bg-[#0A0A0B] py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            {STATS.map((stat, i) => (
              <div key={i} className="text-center animate-fade-in-up" style={{ animationDelay: `${i * 0.1}s` }}>
                <div className="text-4xl font-bold gradient-emerald-text sm:text-5xl">{stat.value}</div>
                <div className="mt-1 text-sm text-zinc-500">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* FEATURES SECTION                                             */}
      {/* ============================================================ */}
      <section className="relative py-24 md:py-32">
        <div className="absolute inset-0 glow-emerald opacity-50" />
        <div className="relative mx-auto max-w-6xl px-6">
          {/* Section header */}
          <div className="mx-auto max-w-2xl text-center">
            <Badge variant="outline" className="mb-4 border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
              FEATURES
            </Badge>
            <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
              Everything you need to
              <span className="gradient-emerald-text"> ace your interview</span>
            </h2>
            <p className="mt-4 text-lg text-zinc-400">
              A complete learning operating system built by engineers who&apos;ve been on both sides of the interview table.
            </p>
          </div>

          {/* Feature grid */}
          <div className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature, i) => (
              <div
                key={i}
                className="group glass-card relative overflow-hidden rounded-2xl p-6 animate-fade-in-up"
                style={{ animationDelay: `${i * 0.1}s` }}
              >
                {/* Hover glow */}
                <div className="absolute -inset-px rounded-2xl bg-gradient-to-br from-emerald-500/0 to-teal-500/0 opacity-0 transition-opacity duration-300 group-hover:from-emerald-500/5 group-hover:to-teal-500/5 group-hover:opacity-100" />

                <div className="relative">
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 ring-1 ring-inset ring-emerald-500/20">
                    <feature.icon className="h-6 w-6 text-emerald-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-zinc-400">{feature.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* HOW IT WORKS                                                 */}
      {/* ============================================================ */}
      <section className="relative bg-[#0A0A0B] py-24 md:py-32">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-2xl text-center">
            <Badge variant="outline" className="mb-4 border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
              HOW IT WORKS
            </Badge>
            <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
              Three steps to
              <span className="gradient-emerald-text"> mastery</span>
            </h2>
          </div>

          <div className="mt-16 grid gap-8 md:grid-cols-3">
            {STEPS.map((step, i) => (
              <div key={i} className="relative animate-fade-in-up" style={{ animationDelay: `${i * 0.15}s` }}>
                {/* Connecting line */}
                {i < STEPS.length - 1 && (
                  <div className="absolute left-full top-12 hidden h-px w-full bg-gradient-to-r from-emerald-500/30 to-transparent md:block" />
                )}

                <div className="relative">
                  <div className="mb-6 flex items-center gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl glass border-emerald-500/30 font-bold text-emerald-400">
                      {step.num}
                    </div>
                    <step.icon className="h-8 w-8 text-emerald-400/50" />
                  </div>
                  <h3 className="text-xl font-bold text-white">{step.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-zinc-400">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* CTA */}
          <div className="mt-16 text-center">
            <Link href="/register">
              <Button size="lg" className="btn-glow gradient-emerald text-lg font-semibold text-black shadow-xl shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-all hover:scale-105">
                Start your journey
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* TESTIMONIALS                                                 */}
      {/* ============================================================ */}
      <section className="relative py-24 md:py-32">
        <div className="absolute inset-0 glow-emerald opacity-30" />
        <div className="relative mx-auto max-w-6xl px-6">
          <div className="mx-auto max-w-2xl text-center">
            <Badge variant="outline" className="mb-4 border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
              TESTIMONIALS
            </Badge>
            <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
              Loved by
              <span className="gradient-emerald-text"> learners</span>
            </h2>
          </div>

          <div className="mt-16 grid gap-6 md:grid-cols-3">
            {TESTIMONIALS.map((t, i) => (
              <div
                key={i}
                className="glass-card rounded-2xl p-6 animate-fade-in-up"
                style={{ animationDelay: `${i * 0.1}s` }}
              >
                <div className="mb-4 flex gap-1">
                  {[...Array(5)].map((_, j) => (
                    <span key={j} className="text-emerald-400">★</span>
                  ))}
                </div>
                <p className="text-sm leading-relaxed text-zinc-300">&ldquo;{t.quote}&rdquo;</p>
                <div className="mt-6 flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 text-sm font-bold text-black">
                    {t.avatar}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-white">{t.name}</div>
                    <div className="text-xs text-zinc-500">{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* FINAL CTA                                                    */}
      {/* ============================================================ */}
      <section className="relative py-24 md:py-32">
        <div className="mx-auto max-w-4xl px-6">
          <div className="glass-card gradient-ring relative overflow-hidden rounded-3xl p-12 text-center md:p-20">
            <div className="absolute inset-0 glow-emerald-strong opacity-50" />
            <div className="relative">
              <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
                Ready to stop being
                <span className="gradient-emerald-text"> boring?</span>
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-lg text-zinc-400">
                Join thousands of learners who&apos;ve transformed their interview prep.
                Start free — no credit card, no commitment.
              </p>
              <div className="mt-8">
                <Link href="/register">
                  <Button size="lg" className="btn-glow gradient-emerald text-lg font-semibold text-black shadow-xl shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-all hover:scale-105">
                    Get started for free
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ============================================================ */}
      {/* FOOTER                                                       */}
      {/* ============================================================ */}
      <footer className="border-t border-white/5 bg-[#08080A] py-12">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-400 to-teal-600 text-xs font-bold text-black">
                M
              </div>
              <span className="text-sm font-bold text-white">Mastery<span className="gradient-emerald-text">OS</span></span>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-zinc-500">
              <Link href="/features" className="hover:text-white transition-colors">Features</Link>
              <Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link>
              <Link href="/about" className="hover:text-white transition-colors">About</Link>
              <Link href="/blog" className="hover:text-white transition-colors">Blog</Link>
              <Link href="/support" className="hover:text-white transition-colors">Support</Link>
            </div>
            <p className="text-xs text-zinc-600">© 2026 MasteryOS. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
