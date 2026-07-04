'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Brain, TrendingUp, Calendar, Sparkles, Zap, BarChart3,
  ArrowRight, Check, ChevronDown,
} from 'lucide-react'

const FEATURES = [
  { icon: Brain, title: 'Adaptive Learning', desc: 'Personalized question selection based on your mastery level and learning history.' },
  { icon: TrendingUp, title: 'Mastery Tracking', desc: 'Durable mastery scores that measure real understanding, not just memory.' },
  { icon: Calendar, title: 'Spaced Repetition', desc: 'Scientifically-backed review scheduling that strengthens long-term retention.' },
  { icon: Sparkles, title: 'AI Explanations', desc: 'Context-aware explanations powered by AI when you need them most.' },
  { icon: Zap, title: 'Real-time Feedback', desc: 'Instant feedback on every answer with misconception tracking.' },
  { icon: BarChart3, title: 'Progress Analytics', desc: 'Detailed insights into your learning velocity and concept mastery.' },
]

const STEPS = [
  { num: '01', title: 'Assess', desc: 'Start with a diagnostic session that maps your current knowledge across all concepts.' },
  { num: '02', title: 'Learn', desc: 'Get adaptive recommendations for the highest-value learning activity at any moment.' },
  { num: '03', title: 'Master', desc: 'Build durable mastery through spaced repetition and track your progress to interview readiness.' },
]

const FAQS = [
  { q: 'What is MasteryOS?', a: 'MasteryOS is an adaptive learning platform that determines the single highest-value learning activity for every user based on measurable mastery. Our first subject is Python interview preparation.' },
  { q: 'How is this different from other learning platforms?', a: 'Unlike platforms that track completion or time spent, MasteryOS measures durable mastery — your actual understanding of each concept. Our adaptive engine uses this to recommend exactly what to study next.' },
  { q: 'Is there a free tier?', a: 'Yes! The Free plan includes access to all Python interview prep content, adaptive learning, and mastery tracking. Pro and Team plans add AI explanations, advanced analytics, and team features.' },
  { q: 'Do I need to know Python already?', a: 'No. MasteryOS adapts to your level — whether you are a beginner learning variables for the first time or an expert preparing for FAANG interviews.' },
  { q: 'Is my data secure?', a: 'We use Argon2id password hashing, RS256 JWT authentication, MFA support, and full audit logging. All data is encrypted at rest and in transit. We are GDPR compliant.' },
]

export default function LandingPage() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden border-b">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 via-purple-600/10 to-teal-500/10" />
        <div className="container relative mx-auto px-4 py-20 text-center md:py-32">
          <Badge variant="secondary" className="mb-6">
            <Sparkles className="mr-1 h-3 w-3" /> Now in Closed Beta
          </Badge>
          <h1 className="mx-auto max-w-4xl text-4xl font-extrabold tracking-tight sm:text-5xl md:text-6xl">
            The Operating System for{' '}
            <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-teal-500 bg-clip-text text-transparent">
              Learning
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground md:text-xl">
            Adaptive mastery tracking that determines the single highest-value learning
            activity for every user. Master Python interviews with measurable, durable mastery.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Button size="lg" asChild>
              <Link href="/register">
                Get Started Free <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/docs">View Documentation</Link>
            </Button>
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            No credit card required · Free forever plan · Cancel anytime
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="container mx-auto px-4 py-20">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
            Everything you need to master Python
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Six core features that work together to accelerate your learning.
          </p>
        </div>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => {
            const Icon = feature.icon
            return (
              <Card key={feature.title}>
                <CardHeader>
                  <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/10">
                    <Icon className="h-5 w-5 text-blue-600" />
                  </div>
                  <CardTitle>{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-base">{feature.desc}</CardDescription>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </section>

      {/* How it works */}
      <section className="border-y bg-muted/30">
        <div className="container mx-auto px-4 py-20">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">How it works</h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Three steps to mastery.
            </p>
          </div>
          <div className="grid gap-8 md:grid-cols-3">
            {STEPS.map((step) => (
              <div key={step.num} className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-purple-600 text-xl font-bold text-white">
                  {step.num}
                </div>
                <h3 className="text-xl font-semibold">{step.title}</h3>
                <p className="mt-2 text-muted-foreground">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="container mx-auto px-4 py-20">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Frequently asked questions</h2>
        </div>
        <div className="mx-auto max-w-3xl space-y-4">
          {FAQS.map((faq) => (
            <details key={faq.q} className="group rounded-lg border p-4">
              <summary className="flex cursor-pointer items-center justify-between font-semibold">
                {faq.q}
                <ChevronDown className="h-5 w-5 text-muted-foreground transition-transform group-open:rotate-180" />
              </summary>
              <p className="mt-3 text-muted-foreground">{faq.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t bg-gradient-to-br from-blue-600 to-purple-600 py-20 text-white">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
            Start mastering Python today
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-blue-100">
            Join our Closed Beta and be among the first to experience adaptive mastery learning.
          </p>
          <Button size="lg" variant="secondary" asChild className="mt-8">
            <Link href="/register">
              Get Started Free <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </section>
    </>
  )
}
