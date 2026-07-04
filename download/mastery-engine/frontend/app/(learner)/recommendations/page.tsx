'use client'

import * as React from 'react'
import { Lightbulb, Check, X } from 'lucide-react'
import { toast } from 'sonner'

import { useRecommendations, useAcceptRecommendation, useDismissRecommendation } from '@/hooks/use-learner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { formatRelativeTime } from '@/lib/format'

export default function RecommendationsPage() {
  const { data: recommendations, isLoading } = useRecommendations()
  const acceptMutation = useAcceptRecommendation()
  const dismissMutation = useDismissRecommendation()

  const handleAccept = async (id: string) => {
    try {
      await acceptMutation.mutateAsync(id)
      toast.success('Recommendation accepted!')
    } catch {
      toast.error('Failed to accept recommendation')
    }
  }

  const handleDismiss = async (id: string) => {
    try {
      await dismissMutation.mutateAsync(id)
      toast.success('Recommendation dismissed')
    } catch {
      toast.error('Failed to dismiss recommendation')
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-3xl space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Recommendations</h1>
        <p className="text-sm text-muted-foreground">Personalized suggestions to improve your mastery</p>
      </div>

      {!recommendations || recommendations.length === 0 ? (
        <EmptyState
          icon={Lightbulb}
          title="No recommendations"
          description="We don't have any recommendations for you right now. Keep studying!"
        />
      ) : (
        <ul className="space-y-3" role="list">
          {recommendations.map((rec) => (
            <li key={rec.id}>
              <Card hover>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <Lightbulb className="h-4 w-4 text-primary" aria-hidden="true" />
                        <Badge variant="outline" className="text-xs capitalize">
                          {rec.recommendation_type.replace(/_/g, ' ')}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {formatRelativeTime(rec.created_at)}
                        </span>
                      </div>
                      <p className="text-sm">{rec.reason}</p>
                      {rec.concept_name && (
                        <p className="text-xs text-muted-foreground">
                          Concept: {rec.concept_name}
                        </p>
                      )}
                    </div>
                    <div className="flex gap-1">
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => handleAccept(rec.id)}
                        aria-label="Accept recommendation"
                        disabled={acceptMutation.isPending}
                      >
                        <Check className="h-4 w-4 text-success" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => handleDismiss(rec.id)}
                        aria-label="Dismiss recommendation"
                        disabled={dismissMutation.isPending}
                      >
                        <X className="h-4 w-4 text-muted-foreground" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
