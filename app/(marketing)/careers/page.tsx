'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { MapPin, Briefcase } from 'lucide-react'

const POSITIONS = [
  { title: 'Senior Backend Engineer (Python/FastAPI)', location: 'Remote', type: 'Full-time', dept: 'Engineering' },
  { title: 'Frontend Engineer (React/Next.js)', location: 'Remote', type: 'Full-time', dept: 'Engineering' },
  { title: 'AI/ML Engineer', location: 'Remote', type: 'Full-time', dept: 'AI' },
  { title: 'DevOps/SRE Engineer', location: 'Remote', type: 'Full-time', dept: 'Infrastructure' },
  { title: 'Product Designer', location: 'Remote', type: 'Full-time', dept: 'Design' },
  { title: 'Content Author (Python)', location: 'Remote', type: 'Contract', dept: 'Content' },
]

const BENEFITS = ['Competitive salary + equity', 'Remote-first culture', 'Flexible hours', 'Health/dental/vision', 'Unlimited PTO', 'Learning budget', 'Conference budget', 'Home office stipend']

export default function CareersPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto mb-16 max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">Careers</h1>
        <p className="mt-4 text-lg text-muted-foreground">Join us in building the future of learning.</p>
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {BENEFITS.map((b) => (
          <Card key={b}><CardContent className="pt-6 text-center text-sm font-medium">{b}</CardContent></Card>
        ))}
      </div>
      <div className="mt-16">
        <h2 className="mb-6 text-2xl font-bold">Open positions</h2>
        <div className="space-y-4">
          {POSITIONS.map((pos) => (
            <Card key={pos.title}>
              <CardContent className="flex flex-col items-start justify-between gap-4 pt-6 sm:flex-row sm:items-center">
                <div>
                  <h3 className="font-semibold">{pos.title}</h3>
                  <div className="mt-1 flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1"><Briefcase className="h-4 w-4" /> {pos.dept}</span>
                    <span className="flex items-center gap-1"><MapPin className="h-4 w-4" /> {pos.location}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="secondary">{pos.type}</Badge>
                  <Button variant="outline" size="sm">Apply</Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
