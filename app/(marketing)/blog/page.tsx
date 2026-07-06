'use client'

import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Calendar, Clock, User, ArrowRight, Sparkles, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/cn'

const POSTS = [
  {
    slug: 'building-adaptive-learning-engine',
    title: 'Building an Adaptive Learning Engine',
    excerpt: 'How we designed a deterministic recommendation algorithm that picks the single highest-value question for each learner — no ML required.',
    category: 'Engineering',
    date: 'July 1, 2026',
    author: 'Engineering Team',
    readTime: '8 min',
    featured: true,
  },
  {
    slug: 'mastery-vs-memory',
    title: 'Mastery vs Memory: Why Completion Is Not Enough',
    excerpt: 'The difference between finishing a course and actually mastering the material — and how we measure it.',
    category: 'Learning Science',
    date: 'June 28, 2026',
    author: 'Product Team',
    readTime: '6 min',
  },
  {
    slug: 'ai-explanations-safety',
    title: 'AI Explanations: Safety First, Always',
    excerpt: 'Our approach to AI-generated content: safety validation, human review, and deterministic fallbacks.',
    category: 'AI',
    date: 'June 25, 2026',
    author: 'AI Team',
    readTime: '7 min',
  },
  {
    slug: 'securing-masteryos',
    title: 'Securing MasteryOS: Our Security Architecture',
    excerpt: 'Argon2id, RS256 JWT, MFA, RBAC, audit logging — a deep dive into our security stack.',
    category: 'Security',
    date: 'June 22, 2026',
    author: 'Security Team',
    readTime: '10 min',
  },
  {
    slug: 'why-we-built-masteryos',
    title: 'Why We Built MasteryOS',
    excerpt: 'The origin story: from a research project to a Closed Beta platform for Python interview prep.',
    category: 'Product',
    date: 'June 20, 2026',
    author: 'Founders',
    readTime: '5 min',
  },
  {
    slug: 'spaced-repetition-algorithm',
    title: 'Inside Our Spaced Repetition Algorithm',
    excerpt: 'The math behind adaptive review scheduling — intervals, priorities, and mastery trajectories.',
    category: 'Learning Science',
    date: 'June 12, 2026',
    author: 'Product Team',
    readTime: '8 min',
  },
]

const CATEGORIES = [
  { label: 'All', active: true },
  { label: 'Engineering', active: false },
  { label: 'AI', active: false },
  { label: 'Learning Science', active: false },
  { label: 'Security', active: false },
  { label: 'Product', active: false },
]

const CATEGORY_COLORS: Record<string, string> = {
  'Engineering': 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  'AI': 'text-purple-400 bg-purple-500/10 border-purple-500/30',
  'Learning Science': 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  'Security': 'text-red-400 bg-red-500/10 border-red-500/30',
  'Product': 'text-amber-400 bg-amber-500/10 border-amber-500/30',
}

export default function BlogPage() {
  const featuredPost = POSTS.find((p) => p.featured)
  const otherPosts = POSTS.filter((p) => !p.featured)

  return (
    <div className="min-h-screen bg-[#08080A] text-white">
      {/* Background glow */}
      <div className="pointer-events-none fixed inset-0 glow-emerald opacity-20" />

      <div className="relative container mx-auto px-4 py-20">
        {/* Hero */}
        <div className="mx-auto mb-16 max-w-2xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-xs font-medium text-emerald-300 backdrop-blur-sm">
            <Sparkles className="h-3.5 w-3.5" />
            Insights & Updates
          </div>
          <h1 className="text-5xl font-bold tracking-tight">
            The{' '}
            <span className="gradient-emerald-text">Blog</span>
          </h1>
          <p className="mt-4 text-lg text-zinc-400">
            Insights from the team building MasteryOS. Engineering deep-dives, learning science, and product updates.
          </p>
        </div>

        {/* Featured post */}
        {featuredPost && (
          <div className="mx-auto mb-12 max-w-4xl">
            <Link href={`/blog/${featuredPost.slug}`}>
              <Card className="glass-card group cursor-pointer overflow-hidden">
                <div className="grid md:grid-cols-2">
                  {/* Visual side */}
                  <div className="relative min-h-[240px] overflow-hidden bg-gradient-to-br from-emerald-600/20 via-teal-700/10 to-emerald-900/20">
                    <div className="absolute inset-0 bg-grid opacity-30" />
                    <div className="absolute inset-0 glow-emerald opacity-50" />
                    <div className="relative flex h-full items-center justify-center p-8">
                      <div className="text-center">
                        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-600 shadow-lg shadow-emerald-500/30">
                          <TrendingUp className="h-8 w-8 text-black" />
                        </div>
                        <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                          Featured
                        </Badge>
                      </div>
                    </div>
                  </div>
                  {/* Content side */}
                  <CardContent className="flex flex-col justify-center p-6 md:p-8">
                    <Badge variant="outline" className={cn('mb-3 w-fit border', CATEGORY_COLORS[featuredPost.category])}>
                      {featuredPost.category}
                    </Badge>
                    <h2 className="text-2xl font-bold leading-tight text-white transition-colors group-hover:text-emerald-400">
                      {featuredPost.title}
                    </h2>
                    <p className="mt-3 text-sm leading-relaxed text-zinc-400">
                      {featuredPost.excerpt}
                    </p>
                    <div className="mt-6 flex items-center gap-4 text-xs text-zinc-500">
                      <span className="flex items-center gap-1"><User className="h-3 w-3" /> {featuredPost.author}</span>
                      <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> {featuredPost.date}</span>
                      <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {featuredPost.readTime}</span>
                    </div>
                    <div className="mt-4 flex items-center gap-1 text-sm font-medium text-emerald-400 transition-transform group-hover:translate-x-1">
                      Read article <ArrowRight className="h-4 w-4" />
                    </div>
                  </CardContent>
                </div>
              </Card>
            </Link>
          </div>
        )}

        {/* Category filter */}
        <div className="mx-auto mb-10 max-w-4xl">
          <div className="flex flex-wrap justify-center gap-2">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.label}
                className={cn(
                  'rounded-full border px-4 py-1.5 text-sm font-medium transition-all',
                  cat.active
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                    : 'border-white/10 bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white'
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* Post grid */}
        <div className="mx-auto grid max-w-5xl gap-6 md:grid-cols-2 lg:grid-cols-3">
          {otherPosts.map((post, i) => (
            <Link key={post.slug} href={`/blog/${post.slug}`}>
              <Card
                className="glass-card group h-full cursor-pointer animate-fade-in-up"
                style={{ animationDelay: `${i * 0.1}s` }}
              >
                <CardContent className="flex h-full flex-col p-6">
                  {/* Category badge */}
                  <Badge variant="outline" className={cn('mb-4 w-fit border', CATEGORY_COLORS[post.category])}>
                    {post.category}
                  </Badge>

                  {/* Title */}
                  <h3 className="text-lg font-bold leading-tight text-white transition-colors group-hover:text-emerald-400">
                    {post.title}
                  </h3>

                  {/* Excerpt */}
                  <p className="mt-2 flex-1 text-sm leading-relaxed text-zinc-400">
                    {post.excerpt}
                  </p>

                  {/* Meta */}
                  <div className="mt-5 flex items-center gap-3 text-xs text-zinc-600">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {post.date}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {post.readTime}
                    </span>
                  </div>

                  {/* Read more */}
                  <div className="mt-4 flex items-center gap-1 text-sm font-medium text-emerald-400 transition-transform group-hover:translate-x-1">
                    Read more <ArrowRight className="h-3.5 w-3.5" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {/* Newsletter CTA */}
        <div className="mx-auto mt-20 max-w-2xl">
          <Card className="glass-card gradient-ring relative overflow-hidden p-8 text-center">
            <div className="absolute inset-0 glow-emerald-strong opacity-30" />
            <div className="relative">
              <Sparkles className="mx-auto h-10 w-10 text-emerald-400" />
              <h3 className="mt-4 text-2xl font-bold text-white">
                Never miss an{' '}
                <span className="gradient-emerald-text">update</span>
              </h3>
              <p className="mt-2 text-sm text-zinc-400">
                Get the latest engineering insights and product updates delivered to your inbox.
              </p>
              <div className="mx-auto mt-6 flex max-w-sm gap-2">
                <input
                  type="email"
                  placeholder="you@example.com"
                  className="h-10 flex-1 rounded-lg border border-white/10 bg-white/5 px-3 text-sm text-white placeholder:text-zinc-600 focus:border-emerald-500/40 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                />
                <button className="btn-glow rounded-lg gradient-emerald px-4 py-2 text-sm font-semibold text-black shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50">
                  Subscribe
                </button>
              </div>
              <p className="mt-3 text-xs text-zinc-600">No spam. Unsubscribe anytime.</p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
