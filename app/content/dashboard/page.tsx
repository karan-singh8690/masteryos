'use client'

import * as React from 'react'
import Link from 'next/link'
import {
  BookOpen, FileCode, Clock, CheckCircle2, AlertCircle,
  Package, TrendingUp, BarChart3, ArrowRight,
} from 'lucide-react'

import { useContentDashboard } from '@/hooks/use-content'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { formatRelativeTime } from '@/lib/format'

export default function ContentDashboardPage() {
  const { data: dashboard, isLoading, isError, refetch } = useContentDashboard()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    )
  }

  if (isError) {
    return <ErrorState onRetry={() => refetch()} />
  }

  if (!dashboard) {
    return <EmptyState title="No content yet" description="Create your first subject to get started." />
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Content Dashboard</h1>
        <p className="text-sm text-muted-foreground">Manage your curriculum content</p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={BookOpen}
          label="Subjects"
          value={dashboard.subjects.length}
          href="/content/subjects"
        />
        <StatCard
          icon={FileCode}
          label="Draft templates"
          value={dashboard.draft_templates}
          href="/content/templates"
        />
        <StatCard
          icon={CheckCircle2}
          label="Published templates"
          value={dashboard.published_templates}
        />
        <StatCard
          icon={Clock}
          label="Pending reviews"
          value={dashboard.pending_reviews}
        />
      </div>

      {/* Coverage stats */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BarChart3 className="h-4 w-4" aria-hidden="true" />
            Coverage statistics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            <CoverageStat
              label="Concept coverage"
              current={dashboard.coverage_stats.concepts_with_templates}
              total={dashboard.coverage_stats.total_concepts}
            />
            <CoverageStat
              label="Explanation coverage"
              current={dashboard.coverage_stats.concepts_with_explanations}
              total={dashboard.coverage_stats.total_concepts}
            />
            <CoverageStat
              label="Misconception coverage"
              current={dashboard.coverage_stats.concepts_with_misconceptions}
              total={dashboard.coverage_stats.total_concepts}
            />
          </div>
        </CardContent>
      </Card>

      {/* Recently edited + Publishing queue */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Recently edited */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recently edited</CardTitle>
          </CardHeader>
          <CardContent>
            {dashboard.recently_edited.length === 0 ? (
              <p className="text-sm text-muted-foreground">No recent edits</p>
            ) : (
              <ul className="space-y-2" role="list">
                {dashboard.recently_edited.slice(0, 5).map((item) => (
                  <li key={item.id} className="flex items-center justify-between text-sm">
                    <div>
                      <span className="font-medium">{item.name}</span>
                      <span className="ml-2 text-xs text-muted-foreground capitalize">{item.type}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">{formatRelativeTime(item.updated_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Publishing queue */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Package className="h-4 w-4" aria-hidden="true" />
              Publishing queue
            </CardTitle>
          </CardHeader>
          <CardContent>
            {dashboard.publishing_queue.length === 0 ? (
              <p className="text-sm text-muted-foreground">No items in queue</p>
            ) : (
              <ul className="space-y-2" role="list">
                {dashboard.publishing_queue.slice(0, 5).map((item) => (
                  <li key={item.id} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      {item.ready_to_publish ? (
                        <CheckCircle2 className="h-3 w-3 text-success" aria-hidden="true" />
                      ) : (
                        <AlertCircle className="h-3 w-3 text-warning" aria-hidden="true" />
                      )}
                      <span className="font-medium">{item.name}</span>
                    </div>
                    <Badge variant={item.ready_to_publish ? 'success' : 'warning'} className="text-xs">
                      {item.ready_to_publish ? 'Ready' : `${item.validation_issues.length} issues`}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Template quality metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <TrendingUp className="h-4 w-4" aria-hidden="true" />
            Template quality metrics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-xs text-muted-foreground">Avg discrimination</p>
              <p className="text-lg font-bold">{dashboard.template_quality_metrics.avg_discrimination.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Avg difficulty</p>
              <p className="text-lg font-bold capitalize">{dashboard.template_quality_metrics.avg_difficulty}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total hints</p>
              <p className="text-lg font-bold">{dashboard.template_quality_metrics.total_hints}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-2">
        <Button asChild variant="default">
          <Link href="/content/subjects/create">
            <BookOpen className="mr-2 h-4 w-4" />
            Create subject
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/content/templates/create">
            <FileCode className="mr-2 h-4 w-4" />
            Create template
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/content/analytics">
            <BarChart3 className="mr-2 h-4 w-4" />
            View analytics
          </Link>
        </Button>
      </div>
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  href,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: number
  href?: string
}) {
  const content = (
    <Card hover={!!href}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardDescription>{label}</CardDescription>
          <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        </div>
        <CardTitle className="text-3xl">{value}</CardTitle>
      </CardHeader>
      {href && (
        <CardContent>
          <span className="flex items-center gap-1 text-xs text-primary">
            View <ArrowRight className="h-3 w-3" aria-hidden="true" />
          </span>
        </CardContent>
      )}
    </Card>
  )
  return href ? <Link href={href}>{content}</Link> : content
}

function CoverageStat({ label, current, total }: { label: string; current: number; total: number }) {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-bold">
        {current} / {total} <span className="text-sm text-muted-foreground">({percentage}%)</span>
      </p>
      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary transition-all"
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={percentage}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  )
}
