'use client'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Calendar, Clock, User, ArrowLeft, ArrowRight, Share2, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/cn'

const CATEGORY_COLORS: Record<string, string> = {
  'Engineering': 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  'AI': 'text-purple-400 bg-purple-500/10 border-purple-500/30',
  'Learning Science': 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  'Security': 'text-red-400 bg-red-500/10 border-red-500/30',
  'Product': 'text-amber-400 bg-amber-500/10 border-amber-500/30',
}

export default function BlogPostPage() {
  return (
    <div className="min-h-screen bg-[#08080A] text-white">
      {/* Background glow */}
      <div className="pointer-events-none fixed inset-0 glow-emerald opacity-20" />

      <div className="relative container mx-auto px-4 py-20">
        <div className="mx-auto max-w-3xl">
          {/* Back link */}
          <Link href="/blog" className="mb-8 inline-flex items-center gap-2 text-sm text-zinc-400 transition-colors hover:text-emerald-400">
            <ArrowLeft className="h-4 w-4" />
            Back to Blog
          </Link>

          {/* Article header */}
          <div className="mb-8">
            <Badge variant="outline" className={cn('mb-4 border', CATEGORY_COLORS['Engineering'])}>
              Engineering
            </Badge>
            <h1 className="text-4xl font-bold leading-tight tracking-tight md:text-5xl">
              Building an{' '}
              <span className="gradient-emerald-text">Adaptive Learning Engine</span>
            </h1>
            <div className="mt-6 flex flex-wrap items-center gap-4 text-sm text-zinc-500">
              <span className="flex items-center gap-1.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 text-xs font-bold text-black">
                  E
                </div>
                Engineering Team
              </span>
              <span className="flex items-center gap-1"><Calendar className="h-4 w-4" /> July 1, 2026</span>
              <span className="flex items-center gap-1"><Clock className="h-4 w-4" /> 8 min read</span>
            </div>
          </div>

          {/* Hero image / gradient banner */}
          <div className="relative mb-10 h-64 overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-600/20 via-teal-700/10 to-emerald-900/20">
            <div className="absolute inset-0 bg-grid opacity-30" />
            <div className="absolute inset-0 glow-emerald opacity-50" />
            <div className="relative flex h-full items-center justify-center">
              <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-emerald-400 to-teal-600 shadow-2xl shadow-emerald-500/30">
                <Sparkles className="h-10 w-10 text-black" />
              </div>
            </div>
          </div>

          {/* Article content */}
          <div className="space-y-6 text-lg leading-relaxed text-zinc-300">
            <p className="text-xl text-zinc-200">
              When we started building MasteryOS, we had one core question: how do you determine
              the single highest-value learning activity for each user at any given moment?
            </p>
            <p>
              Most learning platforms use a simple approach: linear progression through a
              curriculum. Finish chapter 1, move to chapter 2. But this ignores everything we
              know about how learning actually works. People forget things. They have different
              strengths and weaknesses. They need review at different intervals.
            </p>

            <h2 className="pt-4 text-2xl font-bold text-white">The Problem with Linear Learning</h2>
            <p>
              Traditional courses treat all learners the same. Everyone sees the same content in
              the same order, regardless of their existing knowledge. This is efficient for the
              platform but terrible for the learner. If you already know Python lists, why are
              you spending 20 minutes on a chapter about them?
            </p>
            <p>
              We wanted something different: a system that knows what you know, what you
              don&apos;t, and what you&apos;re about to forget — and uses that knowledge to pick
              the perfect next question.
            </p>

            <h2 className="pt-4 text-2xl font-bold text-white">The Mastery Score</h2>
            <p>
              At the heart of our engine is the mastery score — a 0 to 1 value representing your
              durable understanding of a concept. It combines two signals:
            </p>
            <ul className="space-y-2 pl-6">
              <li className="list-disc text-zinc-300">
                <strong className="text-white">Memory score</strong> — recent performance, decays over time
              </li>
              <li className="list-disc text-zinc-300">
                <strong className="text-white">Durable mastery</strong> — long-term evidence from all attempts
              </li>
            </ul>
            <p>
              The memory score captures &ldquo;can you answer this right now?&rdquo; while durable
              mastery captures &ldquo;have you deeply understood this?&rdquo; Together, they give
              us a nuanced picture of your knowledge state.
            </p>

            <h2 className="pt-4 text-2xl font-bold text-white">The Queue Generator</h2>
            <p>
              When you start a study session, our DeterministicQueueGenerator builds a personalized
              queue of questions. It considers:
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                { label: 'Due reviews', weight: '35%', desc: 'Spaced repetition scheduling' },
                { label: 'Weak concepts', weight: '30%', desc: 'Where mastery is low' },
                { label: 'New concepts', weight: '20%', desc: 'Topics you haven\'t seen' },
                { label: 'Goal urgency', weight: '15%', desc: 'Aligned with your learning goal' },
              ].map((item, i) => (
                <div key={i} className="glass-card rounded-xl p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white">{item.label}</span>
                    <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                      {item.weight}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-zinc-500">{item.desc}</p>
                </div>
              ))}
            </div>

            <h2 className="pt-4 text-2xl font-bold text-white">No ML Required</h2>
            <p>
              Here&apos;s the surprising part: our engine is entirely deterministic. No machine
              learning models, no neural networks, no black boxes. Given the same inputs, it
              always produces the same output. This makes it:
            </p>
            <ul className="space-y-2 pl-6">
              <li className="list-disc text-zinc-300"><strong className="text-white">Reproducible</strong> — you can verify exactly why a question was selected</li>
              <li className="list-disc text-zinc-300"><strong className="text-white">Fast</strong> — no model inference latency</li>
              <li className="list-disc text-zinc-300"><strong className="text-white">Explainable</strong> — every recommendation has a clear reason</li>
              <li className="list-disc text-zinc-300"><strong className="text-white">Reliable</strong> — no model drift or training data bias</li>
            </ul>

            <h2 className="pt-4 text-2xl font-bold text-white">What&apos;s Next</h2>
            <p>
              We&apos;re working on adding concept prerequisite graphs (so we don&apos;t ask you
              about binary trees before arrays), adaptive difficulty adjustment, and ML-assisted
              distractor generation. But the core engine — the deterministic mastery tracker —
              will always be explainable and verifiable.
            </p>
            <p>
              Because at the end of the day, you deserve to know why the platform is asking you
              what it&apos;s asking. And we deserve to be able to explain it.
            </p>
          </div>

          {/* Share + Author */}
          <div className="mt-12 flex items-center justify-between border-t border-white/10 pt-8">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 text-sm font-bold text-black">
                E
              </div>
              <div>
                <div className="text-sm font-semibold text-white">Engineering Team</div>
                <div className="text-xs text-zinc-500">MasteryOS</div>
              </div>
            </div>
            <Button variant="outline" size="sm" className="border-white/15 bg-white/5 text-white hover:bg-white/10">
              <Share2 className="mr-2 h-4 w-4" />
              Share
            </Button>
          </div>

          {/* CTA */}
          <Card className="glass-card gradient-ring relative mt-12 overflow-hidden p-8 text-center">
            <div className="absolute inset-0 glow-emerald-strong opacity-30" />
            <div className="relative">
              <h3 className="text-2xl font-bold text-white">
                Ready to try it{' '}
                <span className="gradient-emerald-text">yourself?</span>
              </h3>
              <p className="mt-2 text-sm text-zinc-400">
                Start your mastery journey today. Free forever, no credit card required.
              </p>
              <Link href="/register">
                <Button className="btn-glow mt-6 gradient-emerald font-semibold text-black shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50">
                  Get Started Free
                  <ArrowRight className="ml-1 h-4 w-4" />
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
