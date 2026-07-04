'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Calendar, Clock, User } from 'lucide-react'

const POSTS = [
  { slug: 'building-adaptive-learning-engine', title: 'Building an Adaptive Learning Engine', excerpt: 'How we designed a deterministic recommendation algorithm that picks the single highest-value question for each learner.', category: 'Engineering', date: '2026-07-01', author: 'Engineering Team', readTime: '8 min' },
  { slug: 'mastery-vs-memory', title: 'Mastery vs Memory: Why Completion Is Not Enough', excerpt: 'The difference between finishing a course and actually mastering the material — and how we measure it.', category: 'Learning Science', date: '2026-06-28', author: 'Product Team', readTime: '6 min' },
  { slug: 'ai-explanations-safety', title: 'AI Explanations: Safety First, Always', excerpt: 'Our approach to AI-generated content: safety validation, human review, and deterministic fallbacks.', category: 'AI', date: '2026-06-25', author: 'AI Team', readTime: '7 min' },
  { slug: 'securing-masteryos', title: 'Securing MasteryOS: Our Security Architecture', excerpt: 'Argon2id, RS256 JWT, MFA, RBAC, audit logging — a deep dive into our security stack.', category: 'Security', date: '2026-06-22', author: 'Security Team', readTime: '10 min' },
  { slug: 'why-we-built-masteryos', title: 'Why We Built MasteryOS', excerpt: 'The origin story: from a research project to a Closed Beta platform.', category: 'Product', date: '2026-06-20', author: 'Founders', readTime: '5 min' },
  { slug: 'clean-architecture-fastapi', title: 'Clean Architecture with FastAPI: A Practical Guide', excerpt: 'How we structured a 40,000-line FastAPI backend using Clean Architecture + DDD.', category: 'Architecture', date: '2026-06-18', author: 'Engineering Team', readTime: '12 min' },
  { slug: 'scaling-postgresql-learning-platform', title: 'Scaling PostgreSQL for a Learning Platform', excerpt: 'Schema design, indexing strategy, and query optimization for 57+ tables across 10 schemas.', category: 'Performance', date: '2026-06-15', author: 'Engineering Team', readTime: '9 min' },
  { slug: 'spaced-repetition-algorithm', title: 'Inside Our Spaced Repetition Algorithm', excerpt: 'The math behind adaptive review scheduling — intervals, priorities, and mastery trajectories.', category: 'Learning Science', date: '2026-06-12', author: 'Product Team', readTime: '8 min' },
  { slug: 'monitoring-masteryos', title: 'Monitoring MasteryOS: Prometheus, Grafana, and Beyond', excerpt: 'Our observability stack: metrics, logs, traces, and alerts for a production learning platform.', category: 'Engineering', date: '2026-06-10', author: 'DevOps Team', readTime: '7 min' },
]

const CATEGORIES = ['All', 'Engineering', 'AI', 'Learning Science', 'Security', 'Product', 'Architecture', 'Performance']

export default function BlogPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto mb-12 max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">Blog</h1>
        <p className="mt-4 text-lg text-muted-foreground">Insights from the team building MasteryOS.</p>
      </div>
      <div className="mb-8 flex flex-wrap justify-center gap-2">
        {CATEGORIES.map((cat) => (
          <Badge key={cat} variant={cat === 'All' ? 'default' : 'secondary'} className="cursor-pointer">{cat}</Badge>
        ))}
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {POSTS.map((post) => (
          <Card key={post.slug} className="cursor-pointer transition-shadow hover:shadow-lg">
            <CardContent className="pt-6">
              <Badge variant="secondary" className="mb-3">{post.category}</Badge>
              <h2 className="text-lg font-bold leading-tight">{post.title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{post.excerpt}</p>
              <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1"><User className="h-3 w-3" /> {post.author}</span>
                <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> {post.date}</span>
                <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {post.readTime}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
