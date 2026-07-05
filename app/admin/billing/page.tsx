'use client'

import * as React from 'react'
import { DollarSign, TrendingUp, CreditCard, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { tokenStorage } from '@/lib/api-client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Revenue {
  mrr: number
  arr: number
  total_revenue: number
  active_subscriptions: number
  churned_this_month: number
  new_this_month: number
  by_plan: Record<string, number>
}

interface Subscription {
  id: string
  user_id: string
  plan_slug: string
  status: string
  current_period_end: string | null
  created_at: string
}

export default function AdminBillingPage() {
  const [revenue, setRevenue] = React.useState<Revenue | null>(null)
  const [subs, setSubs] = React.useState<Subscription[]>([])
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => { fetchData() }, [])

  async function fetchData() {
    try {
      const token = tokenStorage.getAccessToken()
      const headers = { Authorization: `Bearer ${token}` }

      const [revRes, subsRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/admin/billing/revenue`, { headers }).catch(() => null),
        fetch(`${API_URL}/api/v1/admin/billing/subscriptions`, { headers }).catch(() => null),
      ])

      if (revRes?.ok) setRevenue(await revRes.json())
      if (subsRes?.ok) {
        const data = await subsRes.json()
        setSubs(data.items || data || [])
      }
    } catch { /* empty */ }
    finally { setLoading(false) }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
      </div>
    )
  }

  const r = revenue || { mrr: 0, arr: 0, total_revenue: 0, active_subscriptions: 0, churned_this_month: 0, new_this_month: 0, by_plan: {} }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Billing & Revenue</h1>
        <p className="text-sm text-muted-foreground">Platform revenue and subscription management</p>
      </div>

      {/* Revenue Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="rounded-2xl border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 to-transparent">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Monthly Recurring Revenue</p>
                <p className="mt-1 text-3xl font-bold text-emerald-500">${r.mrr.toFixed(2)}</p>
              </div>
              <DollarSign className="h-8 w-8 text-emerald-500/50" />
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-2xl">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Annual Recurring Revenue</p>
                <p className="mt-1 text-3xl font-bold">${r.arr.toFixed(2)}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-blue-500/50" />
            </div>
          </CardContent>
        </Card>
        <Card className="rounded-2xl">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Active Subscriptions</p>
                <p className="mt-1 text-3xl font-bold">{r.active_subscriptions}</p>
              </div>
              <CreditCard className="h-8 w-8 text-amber-500/50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Plan Breakdown */}
      <Card className="rounded-2xl">
        <CardHeader><CardTitle className="text-base">Subscriptions by Plan</CardTitle></CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-3">
            {Object.entries(r.by_plan || {}).map(([plan, count]) => (
              <div key={plan} className="flex items-center justify-between rounded-lg border p-3">
                <span className="capitalize font-medium">{plan}</span>
                <Badge variant="secondary">{count} users</Badge>
              </div>
            ))}
            {Object.keys(r.by_plan || {}).length === 0 && (
              <p className="text-sm text-muted-foreground">No subscriptions yet</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Recent Subscriptions */}
      <Card className="rounded-2xl">
        <CardHeader><CardTitle className="text-base">Recent Subscriptions</CardTitle></CardHeader>
        <CardContent>
          {subs.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No subscriptions yet</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="p-3 font-medium">Plan</th>
                    <th className="p-3 font-medium">Status</th>
                    <th className="p-3 font-medium">Period End</th>
                    <th className="p-3 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {subs.map((sub) => (
                    <tr key={sub.id} className="border-b">
                      <td className="p-3"><Badge variant="secondary" className="capitalize">{sub.plan_slug}</Badge></td>
                      <td className="p-3"><Badge variant={sub.status === 'active' ? 'success' : 'destructive'} className="text-xs capitalize">{sub.status}</Badge></td>
                      <td className="p-3 text-muted-foreground">{sub.current_period_end ? new Date(sub.current_period_end).toLocaleDateString() : '—'}</td>
                      <td className="p-3 text-muted-foreground">{new Date(sub.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
