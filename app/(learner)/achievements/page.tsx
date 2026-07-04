'use client'

import * as React from 'react'
import { Trophy, Lock } from 'lucide-react'

import { useAchievements } from '@/hooks/use-learner'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/cn'
import { formatRelativeTime } from '@/lib/format'

const CATEGORY_LABELS: Record<string, string> = {
  learning: 'Learning',
  streak: 'Streaks',
  mastery: 'Mastery',
  social: 'Social',
  special: 'Special',
}

export default function AchievementsPage() {
  const { data: achievements, isLoading } = useAchievements()

  if (isLoading) {
    return (
      <div className="max-w-4xl space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      </div>
    )
  }

  if (!achievements || achievements.length === 0) {
    return (
      <div className="max-w-2xl">
        <EmptyState
          icon={Trophy}
          title="No achievements yet"
          description="Start studying to unlock achievements!"
        />
      </div>
    )
  }

  const unlocked = achievements.filter((a) => a.is_unlocked)
  const locked = achievements.filter((a) => !a.is_unlocked)

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Achievements</h1>
        <p className="text-sm text-muted-foreground">
          {unlocked.length} of {achievements.length} unlocked
        </p>
      </div>

      {/* Unlocked achievements */}
      {unlocked.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Unlocked ({unlocked.length})
          </h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3" role="list">
            {unlocked.map((achievement) => (
              <Card key={achievement.id} hover className="border-success/30" role="listitem">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-success/10 text-2xl">
                      {achievement.icon || '🏆'}
                    </div>
                    <div className="flex-1">
                      <h3 className="text-sm font-semibold">{achievement.name}</h3>
                      <p className="text-xs text-muted-foreground">{achievement.description}</p>
                      {achievement.unlocked_at && (
                        <p className="mt-1 text-xs text-success">
                          Unlocked {formatRelativeTime(achievement.unlocked_at)}
                        </p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Locked achievements */}
      {locked.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Locked ({locked.length})
          </h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3" role="list">
            {locked.map((achievement) => {
              const percentage = achievement.target > 0
                ? (achievement.progress / achievement.target) * 100
                : 0
              return (
                <Card key={achievement.id} className="opacity-70" role="listitem">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted text-2xl grayscale">
                        <Lock className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-sm font-semibold">{achievement.name}</h3>
                        <p className="text-xs text-muted-foreground">{achievement.description}</p>
                        <div className="mt-2 space-y-1">
                          <div className="flex justify-between text-xs text-muted-foreground">
                            <span>{achievement.progress} / {achievement.target}</span>
                            <span>{Math.round(percentage)}%</span>
                          </div>
                          <Progress value={percentage} className="h-1.5" />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
