'use client'

import * as React from 'react'
import { BarChart3, TrendingUp, Target, FileCode, Clock, AlertCircle } from 'lucide-react'

import { useContentAnalytics } from '@/hooks/use-content'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { ActivityBarChart, TrendChart } from '@/components/charts'

export default function ContentAnalyticsPage() {
  const { data: analytics, isLoading, isError } = useContentAnalytics()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      </div>
    )
  }

  if (isError || !analytics) {
    return (
      <EmptyState
        icon={BarChart3}
        title="Analytics not available"
        description="Analytics data couldn't be loaded."
      />
    )
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Content analytics</h1>
        <p className="text-sm text-muted-foreground">Insights into your content performance</p>
      </div>

      {/* Coverage stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Concept coverage</CardDescription>
            <CardTitle className="text-3xl">{Math.round(analytics.coverage.concept_coverage * 100)}%</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Explanation coverage</CardDescription>
            <CardTitle className="text-3xl">{Math.round(analytics.coverage.explanation_coverage * 100)}%</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Misconception coverage</CardDescription>
            <CardTitle className="text-3xl">{Math.round(analytics.coverage.misconception_coverage * 100)}%</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Content quality */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-4 w-4" aria-hidden="true" />
            Content quality
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-4">
            <div>
              <p className="text-xs text-muted-foreground">Avg discrimination</p>
              <p className="text-lg font-bold">{analytics.content_quality.avg_discrimination.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Avg difficulty</p>
              <p className="text-lg font-bold capitalize">{analytics.content_quality.avg_difficulty}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Missing explanations</p>
              <p className="text-lg font-bold text-warning">{analytics.content_quality.missing_explanations}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Missing hints</p>
              <p className="text-lg font-bold text-warning">{analytics.content_quality.missing_hints}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Publishing velocity */}
      {analytics.publishing_velocity.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-4 w-4" aria-hidden="true" />
              Publishing velocity
            </CardTitle>
            <CardDescription>Templates published over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ActivityBarChart
              data={analytics.publishing_velocity.map(p => ({
                label: new Date(p.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
                value: p.published,
              }))}
              title=""
              height={200}
            />
          </CardContent>
        </Card>
      )}

      {/* Difficulty distribution */}
      {analytics.difficulty_distribution.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Target className="h-4 w-4" aria-hidden="true" />
              Difficulty distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {analytics.difficulty_distribution.map((d) => {
                const max = Math.max(...analytics.difficulty_distribution.map((x) => x.count))
                const percentage = max > 0 ? (d.count / max) * 100 : 0
                return (
                  <div key={d.difficulty} className="flex items-center gap-3">
                    <span className="w-24 text-sm capitalize">{d.difficulty}</span>
                    <div className="flex-1">
                      <div className="h-6 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{ width: `${percentage}%` }}
                          role="progressbar"
                          aria-valuenow={d.count}
                          aria-valuemin={0}
                          aria-valuemax={max}
                        />
                      </div>
                    </div>
                    <span className="w-8 text-right text-sm font-medium">{d.count}</span>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Question type distribution */}
      {analytics.question_distribution.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileCode className="h-4 w-4" aria-hidden="true" />
              Question type distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {analytics.question_distribution.map((q) => (
                <Badge key={q.question_type} variant="secondary" className="text-sm">
                  {q.question_type.replace(/_/g, ' ')}: {q.count}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Template usage */}
      {analytics.template_usage.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <BarChart3 className="h-4 w-4" aria-hidden="true" />
              Top templates by usage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2" role="list">
              {analytics.template_usage.slice(0, 10).map((t) => (
                <li key={t.template_id} className="flex items-center justify-between text-sm">
                  <span className="font-medium">{t.template_code}</span>
                  <span className="text-muted-foreground">{t.usage_count} uses</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
