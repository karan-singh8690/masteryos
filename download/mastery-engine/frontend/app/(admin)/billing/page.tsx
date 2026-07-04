'use client'

import { CreditCard, DollarSign, TrendingUp, Users } from 'lucide-react'

import { useBillingPlans, useBillingSubscriptions, useBillingInvoices, useBillingRevenue } from '@/hooks/use-admin'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDateTime } from '@/lib/format'
import { ActivityBarChart } from '@/components/charts'

export default function BillingPage() {
  const { data: plans, isLoading: plansLoading } = useBillingPlans()
  const { data: subscriptions } = useBillingSubscriptions()
  const { data: invoices } = useBillingInvoices()
  const { data: revenue } = useBillingRevenue()

  return (
    <div className="max-w-4xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Billing Administration</h1><p className="text-sm text-muted-foreground">Manage plans, subscriptions, and revenue</p></div>

      {revenue && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card><CardHeader className="pb-2"><CardDescription>Total Revenue</CardDescription><CardTitle className="text-2xl">${revenue.total_revenue.toLocaleString()}</CardTitle></CardHeader></Card>
          <Card><CardHeader className="pb-2"><CardDescription>Monthly Revenue</CardDescription><CardTitle className="text-2xl">${revenue.monthly_revenue.toLocaleString()}</CardTitle></CardHeader></Card>
          <Card><CardHeader className="pb-2"><CardDescription>Active Subscriptions</CardDescription><CardTitle className="text-2xl">{revenue.active_subscriptions}</CardTitle></CardHeader></Card>
          <Card><CardHeader className="pb-2"><CardDescription>Churn Rate</CardDescription><CardTitle className="text-2xl">{(revenue.churn_rate * 100).toFixed(1)}%</CardTitle></CardHeader></Card>
        </div>
      )}

      {revenue && revenue.revenue_trend.length > 0 && (
        <Card><CardHeader><CardTitle className="text-base">Revenue Trend</CardTitle></CardHeader>
          <CardContent><ActivityBarChart data={revenue.revenue_trend.map(r => ({ label: r.date.slice(5), value: r.revenue }))} title="" height={200} /></CardContent>
        </Card>
      )}

      <Card><CardHeader><CardTitle className="text-base">Plans</CardTitle></CardHeader>
        <CardContent>
          {plansLoading ? <Skeleton className="h-32 w-full" /> : (
            <div className="space-y-2">{plans?.map((plan) => (
              <div key={plan.id} className="flex items-center justify-between rounded-lg border p-3">
                <div><p className="text-sm font-medium">{plan.name}</p><p className="text-xs text-muted-foreground">{plan.code}</p></div>
                <div className="flex items-center gap-2"><span className="text-sm font-bold">${plan.price_monthly}/mo</span><Badge variant={plan.status === 'active' ? 'success' : 'secondary'} className="text-xs capitalize">{plan.status}</Badge></div>
              </div>
            ))}</div>
          )}
        </CardContent>
      </Card>

      <Card><CardHeader><CardTitle className="text-base">Recent Subscriptions</CardTitle></CardHeader>
        <CardContent>
          {!subscriptions || subscriptions.length === 0 ? <p className="text-sm text-muted-foreground">No subscriptions</p> : (
            <div className="space-y-2">{subscriptions.slice(0, 5).map((sub) => (
              <div key={sub.id} className="flex items-center justify-between text-sm">
                <span>{sub.plan_name}</span>
                <div className="flex items-center gap-2"><Badge variant={sub.status === 'active' ? 'success' : sub.status === 'canceled' ? 'destructive' : 'warning'} className="text-xs capitalize">{sub.status}</Badge><span className="text-xs text-muted-foreground">{formatDateTime(sub.current_period_end)}</span></div>
              </div>
            ))}</div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
