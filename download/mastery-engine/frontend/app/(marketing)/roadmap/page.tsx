'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ThumbsUp, CheckCircle2, Clock, Lightbulb } from 'lucide-react'

const COLUMNS = [
  { key: 'planned', title: 'Planned', icon: Lightbulb, items: [
    { title: 'Multi-subject support', desc: 'Expand beyond Python to JavaScript, Go, Rust, and SQL.', votes: 142 },
    { title: 'Mobile app (iOS/Android)', desc: 'Native mobile apps with offline support.', votes: 98 },
    { title: 'Team study rooms', desc: 'Real-time collaborative study sessions.', votes: 67 },
  ]},
  { key: 'in_progress', title: 'In Progress', icon: Clock, items: [
    { title: 'AI Coach', desc: 'Personalized AI study coach with daily plans.', votes: 189 },
    { title: 'Code execution sandbox', desc: 'Run Python code in-browser during practice.', votes: 134 },
    { title: 'Interview simulator', desc: 'Mock interviews with AI interviewer.', votes: 112 },
  ]},
  { key: 'shipped', title: 'Shipped', icon: CheckCircle2, items: [
    { title: 'Adaptive learning engine v1', desc: 'Deterministic recommendation algorithm.', votes: 256 },
    { title: 'Mastery tracking', desc: 'Durable mastery scores with confidence intervals.', votes: 201 },
    { title: 'Spaced repetition', desc: 'Adaptive review scheduling.', votes: 178 },
    { title: 'Closed Beta platform', desc: 'Invite system, feedback, analytics.', votes: 156 },
  ]},
  { key: 'consideration', title: 'Under Consideration', icon: Lightbulb, items: [
    { title: 'GitHub integration', desc: 'Import code from repos for practice.', votes: 45 },
    { title: 'Video explanations', desc: 'Short video clips for key concepts.', votes: 38 },
  ]},
]

export default function RoadmapPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto mb-16 max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">Product Roadmap</h1>
        <p className="mt-4 text-lg text-muted-foreground">
          See what we are building next. Vote on features you want.
        </p>
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {COLUMNS.map((col) => {
          const Icon = col.icon
          return (
            <div key={col.key}>
              <div className="mb-4 flex items-center gap-2">
                <Icon className="h-5 w-5 text-blue-600" />
                <h2 className="font-semibold">{col.title}</h2>
                <Badge variant="secondary">{col.items.length}</Badge>
              </div>
              <div className="space-y-3">
                {col.items.map((item) => (
                  <Card key={item.title}>
                    <CardContent className="pt-4">
                      <h3 className="text-sm font-semibold">{item.title}</h3>
                      <p className="mt-1 text-xs text-muted-foreground">{item.desc}</p>
                      <div className="mt-3 flex items-center justify-between">
                        <Button variant="ghost" size="sm" className="h-7 px-2 text-xs">
                          <ThumbsUp className="mr-1 h-3 w-3" /> {item.votes}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
