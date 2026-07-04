'use client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Brain, TrendingUp, Calendar, Sparkles, Zap, BarChart3, Check } from 'lucide-react'

const FEATURES = [
  { icon: Brain, title: 'Adaptive Learning Engine', desc: 'Our recommendation engine analyzes your mastery scores, learning history, and concept dependencies to serve the single highest-value question at any moment. No wasted time on concepts you already know.', points: ['Deterministic algorithm with AI enhancement', 'Concept dependency graph', 'Difficulty-adaptive question selection', 'Intent-based sessions (drill, diagnostic, review)'] },
  { icon: TrendingUp, title: 'Mastery Tracking', desc: 'Durable mastery scores measure real understanding, not just completion. Our algorithm tracks evidence count, confidence intervals, and concept state (unseen → novice → developing → proficient → mastered).', points: ['Evidence-based scoring', 'Confidence intervals per concept', 'Concept state machine', 'Algorithm versioning for reproducibility'] },
  { icon: Calendar, title: 'Spaced Repetition', desc: 'Scientifically-backed review scheduling using the spacing effect. Reviews are scheduled based on your mastery trajectory, with intervals that expand on success and contract on failure.', points: ['Adaptive review intervals', 'Priority-based scheduling', 'Streak tracking', 'Review effectiveness analytics'] },
  { icon: Sparkles, title: 'AI Explanations', desc: 'Context-aware explanations powered by AI when you need them most. Optional AI layer enhances the deterministic engine without replacing it.', points: ['Provider-agnostic (Ollama, OpenAI, Gemini, Anthropic)', 'Safety-validated outputs', 'Human review pipeline', 'Cost controls and rate limiting'] },
  { icon: Zap, title: 'Real-time Feedback', desc: 'Instant feedback on every answer with misconception tracking. Know not just whether you got it right, but why you got it wrong.', points: ['Misconception tagging', 'Partial credit for near-misses', 'Hint system with tiered disclosure', 'WebSocket-based real-time updates'] },
  { icon: BarChart3, title: 'Progress Analytics', desc: 'Detailed insights into your learning velocity, concept mastery distribution, and interview readiness trend. Know exactly where you stand.', points: ['Mastery growth over time', 'Weak/strong concept identification', 'Interview readiness score', 'Cohort comparison'] },
]

export default function FeaturesPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto mb-16 max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">Features</h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Six core features that work together to accelerate your learning.
        </p>
      </div>
      <div className="space-y-16">
        {FEATURES.map((feature, i) => {
          const Icon = feature.icon
          return (
            <div key={feature.title} className={`grid gap-8 md:grid-cols-2 ${i % 2 === 1 ? 'md:[&>*:first-child]:order-2' : ''}`}>
              <div>
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600/10">
                  <Icon className="h-6 w-6 text-blue-600" />
                </div>
                <h2 className="text-2xl font-bold">{feature.title}</h2>
                <p className="mt-3 text-muted-foreground">{feature.desc}</p>
              </div>
              <Card>
                <CardContent className="pt-6">
                  <ul className="space-y-3">
                    {feature.points.map((point) => (
                      <li key={point} className="flex items-start gap-2">
                        <Check className="mt-0.5 h-5 w-5 shrink-0 text-teal-500" />
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </div>
          )
        })}
      </div>
    </div>
  )
}
