'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Target, Users, Zap, Heart } from 'lucide-react'

const VALUES = [
  { icon: Target, title: 'Mastery over memorization', desc: 'We measure durable understanding, not time spent or questions completed.' },
  { icon: Users, title: 'Learner-first', desc: 'Every decision starts with "does this help the learner?"' },
  { icon: Zap, title: 'Adaptive by default', desc: 'No two learners are the same. Our platform adapts to each one.' },
  { icon: Heart, title: 'Open and honest', desc: 'We share our roadmap, changelog, and metrics publicly.' },
]

const TIMELINE = [
  { year: '2025', title: 'Inception', desc: 'Started as a research project on adaptive learning algorithms.' },
  { year: '2026', title: 'Closed Beta', desc: 'Launched with 20 invited users for Python interview preparation.' },
  { year: '2026', title: 'Public Beta', desc: 'Opening the platform to 100+ users with expanded content.' },
  { year: '2027', title: 'General Availability', desc: 'Full public launch with multi-subject support.' },
]

export default function AboutPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto mb-16 max-w-3xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">About MasteryOS</h1>
        <p className="mt-4 text-lg text-muted-foreground">
          We are building the operating system for learning — a platform that determines
          the single highest-value learning activity for every user based on measurable mastery.
        </p>
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {VALUES.map((v) => {
          const Icon = v.icon
          return (
            <Card key={v.title}>
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/10">
                  <Icon className="h-5 w-5 text-blue-600" />
                </div>
                <CardTitle className="text-lg">{v.title}</CardTitle>
              </CardHeader>
              <CardContent><p className="text-sm text-muted-foreground">{v.desc}</p></CardContent>
            </Card>
          )
        })}
      </div>
      <div className="mx-auto mt-20 max-w-3xl">
        <h2 className="mb-8 text-2xl font-bold">Our journey</h2>
        <div className="space-y-8">
          {TIMELINE.map((item) => (
            <div key={item.year + item.title} className="flex gap-6">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-purple-600 text-sm font-bold text-white">
                {item.year}
              </div>
              <div>
                <h3 className="text-lg font-semibold">{item.title}</h3>
                <p className="mt-1 text-muted-foreground">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
