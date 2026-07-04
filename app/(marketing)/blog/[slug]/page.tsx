'use client'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Calendar, Clock, User, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function BlogPostPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto max-w-3xl">
        <Button variant="ghost" asChild className="mb-6">
          <Link href="/blog"><ArrowLeft className="mr-2 h-4 w-4" /> Back to Blog</Link>
        </Button>
        <Badge variant="secondary" className="mb-4">Engineering</Badge>
        <h1 className="text-3xl font-extrabold tracking-tight md:text-4xl">
          Building an Adaptive Learning Engine
        </h1>
        <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1"><User className="h-4 w-4" /> Engineering Team</span>
          <span className="flex items-center gap-1"><Calendar className="h-4 w-4" /> 2026-07-01</span>
          <span className="flex items-center gap-1"><Clock className="h-4 w-4" /> 8 min read</span>
        </div>
        <div className="mt-8 space-y-6 text-lg leading-relaxed text-muted-foreground">
          <p>
            When we started building MasteryOS, we had one core question: how do you determine
            the single highest-value learning activity for each user at any given moment?
          </p>
          <p>
            Most learning platforms use a simple approach: linear progression through a
            curriculum. But this ignores the fact that learners come with different backgrounds,
            different goals, and different rates of forgetting.
          </p>
          <h2 className="text-2xl font-bold text-foreground">The mastery score</h2>
          <p>
            Our first insight was that we needed a way to measure durable mastery — not just
            completion. We developed a mastery score that combines memory (recent performance)
            with durable mastery (long-term understanding), weighted by evidence count and
            confidence intervals.
          </p>
          <pre className="rounded-lg bg-muted p-4"><code className="text-sm font-mono">
{`mastery_score = memory_score * 0.3 + durable_mastery * 0.7
confidence_interval = 1.0 / sqrt(evidence_count)`}
          </code></pre>
          <h2 className="text-2xl font-bold text-foreground">The recommendation engine</h2>
          <p>
            With mastery scores in hand, the recommendation engine considers three factors:
            current mastery level, concept dependencies, and review urgency. The result is
            a ranked list of the highest-value activities for the learner right now.
          </p>
          <p>
            We deliberately made the algorithm deterministic first, with AI as an optional
            enhancement layer. This ensures reproducibility and prevents the "black box"
            problem that plagues many AI-first platforms.
          </p>
        </div>
        <Card className="mt-12">
          <CardContent className="pt-6">
            <h3 className="mb-2 font-semibold">About the author</h3>
            <p className="text-sm text-muted-foreground">
              The Engineering Team builds the core platform — from the adaptive learning engine
              to the real-time WebSocket layer. We are hiring!
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
