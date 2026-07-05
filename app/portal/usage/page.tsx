'use client'

import { BarChart3, Clock, FileCode, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function UsagePage() {
  const stats = [
    { label: 'API Calls This Month', value: '12,847', limit: '50,000', icon: FileCode },
    { label: 'Study Hours', value: '127h', limit: 'Unlimited', icon: Clock },
    { label: 'Questions Answered', value: '1,432', limit: 'Unlimited', icon: TrendingUp },
    { label: 'Avg Daily Streak', value: '14 days', limit: '—', icon: BarChart3 },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Usage</h1>
        <p className="text-muted-foreground">Track your API usage and learning activity.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardDescription>{stat.label}</CardDescription>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <CardTitle className="text-2xl">{stat.value}</CardTitle>
                {stat.limit !== '—' && (
                  <CardDescription>Limit: {stat.limit}</CardDescription>
                )}
              </CardHeader>
            </Card>
          )
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>API Usage (Last 30 Days)</CardTitle>
          <CardDescription>Daily API call count</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex h-40 items-end gap-1">
            {Array.from({ length: 30 }).map((_, i) => (
              <div
                key={i}
                className="flex-1 rounded-t bg-primary/20"
                style={{ height: `${20 + Math.random() * 80}%` }}
              />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
