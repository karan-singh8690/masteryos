'use client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Check, X } from 'lucide-react'
import Link from 'next/link'

const PLANS = [
  { name: 'Free', price: '$0', period: 'forever', desc: 'Perfect for self-study', features: ['All Python interview content', 'Adaptive learning engine', 'Mastery tracking', 'Spaced repetition', 'Progress dashboard', 'Community support'], limitations: ['No AI explanations', 'Limited analytics', 'Single device'], cta: 'Get Started', href: '/register' },
  { name: 'Pro', price: '$19', period: 'per month', desc: 'For serious interview prep', features: ['Everything in Free', 'AI-powered explanations', 'Advanced analytics', 'Interview readiness score', 'Unlimited devices', 'Priority support', 'Custom study plans'], limitations: [], cta: 'Start Pro Trial', href: '/register', popular: true },
  { name: 'Team', price: '$49', period: 'per month', desc: 'For study groups & teams', features: ['Everything in Pro', 'Team dashboard', 'Shared progress tracking', 'Admin controls', 'SSO/SAML', 'Dedicated support', 'Custom content packs'], limitations: [], cta: 'Contact Sales', href: '/contact' },
]

const COMPARISON = [
  { feature: 'Adaptive Learning', free: true, pro: true, team: true },
  { feature: 'Mastery Tracking', free: true, pro: true, team: true },
  { feature: 'Spaced Repetition', free: true, pro: true, team: true },
  { feature: 'AI Explanations', free: false, pro: true, team: true },
  { feature: 'Advanced Analytics', free: false, pro: true, team: true },
  { feature: 'Interview Readiness Score', free: false, pro: true, team: true },
  { feature: 'Team Dashboard', free: false, pro: false, team: true },
  { feature: 'SSO/SAML', free: false, pro: false, team: true },
  { feature: 'Custom Content Packs', free: false, pro: false, team: true },
  { feature: 'Priority Support', free: false, pro: true, team: true },
]

const FAQS = [
  { q: 'Can I switch plans anytime?', a: 'Yes. Upgrades take effect immediately. Downgrades take effect at the end of your billing cycle.' },
  { q: 'Do you offer student discounts?', a: 'Yes! Students get 50% off the Pro plan with a valid .edu email. Contact support for details.' },
  { q: 'What payment methods do you accept?', a: 'We accept all major credit cards, PayPal, and bank transfers for Team plans.' },
  { q: 'Is there a money-back guarantee?', a: 'Yes. We offer a 30-day money-back guarantee on all paid plans, no questions asked.' },
]

export default function PricingPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto mb-16 max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">Pricing</h1>
        <p className="mt-4 text-lg text-muted-foreground">Start free. Upgrade when you are ready.</p>
      </div>
      <div className="grid gap-6 md:grid-cols-3">
        {PLANS.map((plan) => (
          <Card key={plan.name} className={plan.popular ? 'border-blue-600 shadow-lg' : ''}>
            {plan.popular && <Badge className="absolute -top-3 left-1/2 -translate-x-1/2">Most Popular</Badge>}
            <CardHeader>
              <CardTitle>{plan.name}</CardTitle>
              <CardDescription>{plan.desc}</CardDescription>
              <div className="mt-4">
                <span className="text-4xl font-extrabold">{plan.price}</span>
                <span className="text-muted-foreground"> /{plan.period}</span>
              </div>
            </CardHeader>
            <CardContent>
              <Button className="w-full" variant={plan.popular ? 'default' : 'outline'} asChild>
                <Link href={plan.href}>{plan.cta}</Link>
              </Button>
              <ul className="mt-6 space-y-2">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-teal-500" /> {f}
                  </li>
                ))}
                {plan.limitations.map((l) => (
                  <li key={l} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <X className="mt-0.5 h-4 w-4 shrink-0" /> {l}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="mx-auto mt-20 max-w-3xl">
        <h2 className="mb-6 text-2xl font-bold">Feature comparison</h2>
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="py-3 text-left">Feature</th>
              <th className="py-3 text-center">Free</th>
              <th className="py-3 text-center">Pro</th>
              <th className="py-3 text-center">Team</th>
            </tr>
          </thead>
          <tbody>
            {COMPARISON.map((row) => (
              <tr key={row.feature} className="border-b">
                <td className="py-3">{row.feature}</td>
                <td className="py-3 text-center">{row.free ? <Check className="mx-auto h-4 w-4 text-teal-500" /> : <X className="mx-auto h-4 w-4 text-muted-foreground" />}</td>
                <td className="py-3 text-center">{row.pro ? <Check className="mx-auto h-4 w-4 text-teal-500" /> : <X className="mx-auto h-4 w-4 text-muted-foreground" />}</td>
                <td className="py-3 text-center">{row.team ? <Check className="mx-auto h-4 w-4 text-teal-500" /> : <X className="mx-auto h-4 w-4 text-muted-foreground" />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mx-auto mt-20 max-w-3xl">
        <h2 className="mb-6 text-2xl font-bold">FAQ</h2>
        <div className="space-y-4">
          {FAQS.map((faq) => (
            <div key={faq.q} className="rounded-lg border p-4">
              <h3 className="font-semibold">{faq.q}</h3>
              <p className="mt-2 text-muted-foreground">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
