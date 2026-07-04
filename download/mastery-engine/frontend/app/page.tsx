import Link from 'next/link'
import { ArrowRight, BookOpen, Trophy, Calendar, Zap } from 'lucide-react'

import { PublicLayout } from '@/components/layout/public-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { APP_NAME, ROUTES } from '@/lib/constants'

const FEATURES = [
  {
    icon: BookOpen,
    title: 'Adaptive learning',
    description: 'Our engine determines the single highest-value learning activity for you.',
  },
  {
    icon: Trophy,
    title: 'Mastery tracking',
    description: 'Track your mastery score across concepts with evidence-based scoring.',
  },
  {
    icon: Calendar,
    title: 'Spaced repetition',
    description: 'Smart review scheduling ensures concepts stick long-term.',
  },
  {
    icon: Zap,
    title: 'Real-time feedback',
    description: 'Get instant feedback on your answers with detailed explanations.',
  },
]

export default function HomePage() {
  return (
    <PublicLayout>
      {/* Hero section */}
      <section className="container flex flex-col items-center gap-6 py-20 text-center md:py-32">
        <div className="inline-flex items-center gap-2 rounded-full border bg-muted/50 px-4 py-1.5 text-sm text-muted-foreground">
          <span className="flex h-2 w-2 rounded-full bg-success" />
          Adaptive Learning OS
        </div>
        <h1 className="text-balance text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
          Master concepts,{' '}
          <span className="bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
            not just memorize
          </span>
        </h1>
        <p className="max-w-2xl text-balance text-lg text-muted-foreground">
          {APP_NAME} determines the single highest-value learning activity for every user
          based on measurable mastery.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Button asChild size="lg" rightIcon={<ArrowRight className="h-4 w-4" />}>
            <Link href={ROUTES.REGISTER}>Get started free</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href={ROUTES.LOGIN}>Sign in</Link>
          </Button>
        </div>
      </section>

      {/* Features section */}
      <section className="container py-16">
        <div className="mb-12 text-center">
          <h2 className="text-3xl font-bold tracking-tight">Why Mastery Engine?</h2>
          <p className="mt-2 text-muted-foreground">Built for serious learners</p>
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((feature) => {
            const Icon = feature.icon
            return (
              <Card key={feature.title} hover>
                <CardHeader>
                  <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
                  </div>
                  <CardTitle className="text-base">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{feature.description}</CardDescription>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </section>

      {/* CTA section */}
      <section className="container py-16">
        <Card className="overflow-hidden">
          <CardContent className="flex flex-col items-center gap-6 p-8 text-center md:p-12">
            <h2 className="text-2xl font-bold tracking-tight md:text-3xl">
              Ready to start your mastery journey?
            </h2>
            <p className="max-w-xl text-muted-foreground">
              Join learners using {APP_NAME} to master Python interview prep and beyond.
            </p>
            <Button asChild size="lg" rightIcon={<ArrowRight className="h-4 w-4" />}>
              <Link href={ROUTES.REGISTER}>Create your free account</Link>
            </Button>
          </CardContent>
        </Card>
      </section>
    </PublicLayout>
  )
}
