'use client'

import * as React from 'react'
import { Crown, Check, Loader2, CreditCard, Zap, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { tokenStorage } from '@/lib/api-client'

interface Plan {
  slug: string
  name: string
  description: string | null
  price_cents: number
  currency: string
  interval: string
  features: Record<string, unknown>
  max_users: number
  max_api_calls: number
  max_study_sessions: number
}

interface Subscription {
  plan_slug: string
  status: string
  current_period_start: string | null
  current_period_end: string | null
  cancel_at_period_end: boolean
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function BillingPage() {
  const [plans, setPlans] = React.useState<Plan[]>([])
  const [subscription, setSubscription] = React.useState<Subscription | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [subscribing, setSubscribing] = React.useState<string | null>(null)
  const [error, setError] = React.useState('')
  const [success, setSuccess] = React.useState('')

  React.useEffect(() => {
    fetchData()
  }, [])

  async function fetchData() {
    try {
      const token = tokenStorage.getAccessToken()
      const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {}

      const [plansRes, subRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/billing/plans`),
        fetch(`${API_URL}/api/v1/billing/subscription`, { headers }),
      ])

      if (plansRes.ok) {
        const data = await plansRes.json()
        setPlans(data.plans || [])
      }
      if (subRes.ok) {
        setSubscription(await subRes.json())
      }
    } catch {
      // Use default plans on error
      setPlans([
        { slug: 'free', name: 'Free', description: 'Perfect for getting started', price_cents: 0, currency: 'usd', interval: 'month', features: { study_sessions: '10 per month', ai_explanations: 'Basic only' }, max_users: 1, max_api_calls: 100, max_study_sessions: 10 },
        { slug: 'pro', name: 'Pro', description: 'For serious learners', price_cents: 1999, currency: 'usd', interval: 'month', features: { study_sessions: 'Unlimited', ai_explanations: 'Full access', analytics: 'Advanced' }, max_users: 1, max_api_calls: 10000, max_study_sessions: 999999 },
        { slug: 'team', name: 'Team', description: 'For teams and classrooms', price_cents: 4999, currency: 'usd', interval: 'month', features: { study_sessions: 'Unlimited', ai_explanations: 'Full access', team_dashboard: true }, max_users: 25, max_api_calls: 50000, max_study_sessions: 999999 },
      ])
    } finally {
      setLoading(false)
    }
  }

  async function handleSubscribe(planSlug: string) {
    setSubscribing(planSlug)
    setError('')
    setSuccess('')
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/billing/subscribe?plan_slug=${planSlug}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail?.message || data.detail || 'Failed to subscribe')

      // Redirect to Stripe checkout or success URL
      if (data.url) {
        window.location.href = data.url
      } else {
        setSuccess(`Successfully subscribed to ${planSlug}!`)
        fetchData() // Refresh subscription
      }
    } catch (err: any) {
      setError(err.message || 'Failed to subscribe')
    } finally {
      setSubscribing(null)
    }
  }

  async function handleCancel() {
    try {
      const token = tokenStorage.getAccessToken()
      await fetch(`${API_URL}/api/v1/billing/cancel`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      setSuccess('Subscription canceled.')
      fetchData()
    } catch {
      setError('Failed to cancel subscription')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
      </div>
    )
  }

  const currentPlan = subscription?.plan_slug || 'free'

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Billing & Plans</h1>
        <p className="text-sm text-muted-foreground">Manage your subscription and payment methods</p>
      </div>

      {/* Alerts */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert>
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      )}

      {/* Current Plan */}
      <Card className="rounded-2xl border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 to-transparent">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Crown className="h-5 w-5 text-emerald-500" />
            Current Plan: <span className="capitalize">{currentPlan}</span>
          </CardTitle>
          <CardDescription>
            {subscription?.status === 'active' && !subscription?.cancel_at_period_end
              ? 'Your subscription is active'
              : subscription?.cancel_at_period_end
              ? 'Subscription will cancel at period end'
              : 'You are on the free plan'}
          </CardDescription>
        </CardHeader>
        {currentPlan !== 'free' && (
          <CardContent>
            <Button variant="outline" onClick={handleCancel} className="gap-2">
              <X className="h-4 w-4" />
              Cancel Subscription
            </Button>
          </CardContent>
        )}
      </Card>

      {/* Plans Grid */}
      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((plan) => {
          const isCurrent = currentPlan === plan.slug
          const isPro = plan.slug === 'pro'
          const price = plan.price_cents === 0 ? 'Free' : `$${(plan.price_cents / 100).toFixed(0)}`
          const period = plan.price_cents === 0 ? '' : `/${plan.interval}`

          return (
            <Card
              key={plan.slug}
              className={`relative rounded-2xl transition-all ${
                isPro ? 'border-emerald-500 shadow-lg shadow-emerald-500/10' : ''
              } ${isCurrent ? 'ring-2 ring-emerald-500' : ''}`}
            >
              {isPro && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white">
                    Most Popular
                  </Badge>
                </div>
              )}
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {plan.slug === 'free' && <Zap className="h-5 w-5 text-zinc-400" />}
                  {plan.slug === 'pro' && <Crown className="h-5 w-5 text-emerald-500" />}
                  {plan.slug === 'team' && <CreditCard className="h-5 w-5 text-blue-500" />}
                  {plan.name}
                </CardTitle>
                <CardDescription>{plan.description}</CardDescription>
                <div className="mt-4">
                  <span className="text-3xl font-bold">{price}</span>
                  <span className="text-sm text-muted-foreground">{period}</span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Features */}
                <ul className="space-y-2">
                  {Object.entries(plan.features).map(([key, value]) => (
                    <li key={key} className="flex items-start gap-2 text-sm">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                      <span className="capitalize">{key.replace(/_/g, ' ')}: {String(value)}</span>
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                {isCurrent ? (
                  <Button variant="outline" disabled className="w-full gap-2">
                    <Check className="h-4 w-4 text-emerald-500" />
                    Current Plan
                  </Button>
                ) : (
                  <Button
                    onClick={() => handleSubscribe(plan.slug)}
                    disabled={subscribing === plan.slug}
                    className={`w-full gap-2 ${
                      isPro
                        ? 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white hover:from-emerald-600 hover:to-teal-600'
                        : ''
                    }`}
                  >
                    {subscribing === plan.slug && <Loader2 className="h-4 w-4 animate-spin" />}
                    {plan.price_cents === 0 ? 'Get Started' : 'Upgrade'}
                  </Button>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Usage Stats */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle>Usage This Period</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <p className="text-xs text-muted-foreground">Study Sessions</p>
              <p className="mt-1 text-xl font-bold">0 / {plans.find(p => p.slug === currentPlan)?.max_study_sessions === 999999 ? '∞' : plans.find(p => p.slug === currentPlan)?.max_study_sessions || 10}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">API Calls</p>
              <p className="mt-1 text-xl font-bold">0 / {plans.find(p => p.slug === currentPlan)?.max_api_calls || 100}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Team Seats</p>
              <p className="mt-1 text-xl font-bold">1 / {plans.find(p => p.slug === currentPlan)?.max_users || 1}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Status</p>
              <p className="mt-1 text-xl font-bold text-emerald-500">Active</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
