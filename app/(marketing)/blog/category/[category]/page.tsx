'use client'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Calendar, Clock, User, ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { useParams } from 'next/navigation'

const POSTS = [
  { slug: 'building-adaptive-learning-engine', title: 'Building an Adaptive Learning Engine', excerpt: 'How we designed a deterministic recommendation algorithm.', category: 'Engineering', date: '2026-07-01', author: 'Engineering Team', readTime: '8 min' },
  { slug: 'mastery-vs-memory', title: 'Mastery vs Memory', excerpt: 'The difference between finishing a course and mastering the material.', category: 'Learning Science', date: '2026-06-28', author: 'Product Team', readTime: '6 min' },
  { slug: 'ai-explanations-safety', title: 'AI Explanations: Safety First', excerpt: 'Our approach to AI-generated content safety.', category: 'AI', date: '2026-06-25', author: 'AI Team', readTime: '7 min' },
]

export default function BlogCategoryPage() {
  const params = useParams()
  const category = decodeURIComponent(params.category as string)
  const filtered = POSTS.filter((p) => p.category.toLowerCase() === category.toLowerCase())
  return (
    <div className="container mx-auto px-4 py-20">
      <Button variant="ghost" asChild className="mb-6">
        <Link href="/blog"><ArrowLeft className="mr-2 h-4 w-4" /> Back to Blog</Link>
      </Button>
      <h1 className="mb-8 text-4xl font-extrabold tracking-tight capitalize">{category}</h1>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {filtered.length > 0 ? filtered.map((post) => (
          <Card key={post.slug} className="cursor-pointer hover:shadow-lg">
            <CardContent className="pt-6">
              <Badge variant="secondary" className="mb-3">{post.category}</Badge>
              <h2 className="text-lg font-bold">{post.title}</h2>
              <p className="mt-2 text-sm text-muted-foreground">{post.excerpt}</p>
              <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1"><User className="h-3 w-3" /> {post.author}</span>
                <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> {post.date}</span>
                <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {post.readTime}</span>
              </div>
            </CardContent>
          </Card>
        )) : <p className="text-muted-foreground">No posts in this category yet. Check back soon!</p>}
      </div>
    </div>
  )
}
