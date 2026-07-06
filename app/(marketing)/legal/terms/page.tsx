'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { FileText, CheckCircle2, AlertCircle, XCircle } from 'lucide-react'

const SECTIONS = [
  {
    title: '1. Acceptance of Terms',
    content: 'By creating an account or using MasteryOS (the "Service"), you agree to be bound by these Terms of Service ("Terms"). If you do not agree, do not use the Service. These Terms form a legally binding agreement between you and Mastery Engine Inc. ("MasteryOS", "we", "us", or "our").',
  },
  {
    title: '2. Description of Service',
    content: 'MasteryOS is an adaptive learning platform that provides personalized interview preparation through mastery tracking, spaced repetition, and AI-powered explanations. The Service includes study sessions, progress analytics, and review scheduling. We may modify or discontinue features at any time with reasonable notice.',
  },
  {
    title: '3. Account Registration',
    content: 'You must provide accurate, complete information when creating an account. You must be at least 13 years old to use the Service. Users under 18 require parental consent. You are responsible for maintaining the security of your account credentials and for all activities under your account. Notify us immediately of any unauthorized use.',
  },
  {
    title: '4. Acceptable Use',
    items: [
      'Use the Service only for lawful purposes and in accordance with these Terms',
      'Do not share, sell, or transfer your account to others',
      'Do not attempt to reverse engineer, decompile, or disassemble the Service',
      'Do not use bots, scrapers, or automated tools to access the Service',
      'Do not upload viruses, malware, or harmful code',
      'Do not harass, abuse, or harm other users',
      'Do not use the Service to cheat on interviews or exams',
    ],
    note: 'Violation of these rules may result in account suspension or termination without notice.',
  },
  {
    title: '5. Intellectual Property',
    content: 'All content on MasteryOS — including questions, explanations, algorithms, design, and software — is owned by Mastery Engine Inc. and protected by copyright, trademark, and other intellectual property laws. You may not copy, reproduce, distribute, or create derivative works without our written permission. Your learning data (answers, progress) belongs to you, and you can export it at any time.',
  },
  {
    title: '6. Subscription & Billing',
    items: [
      'Free Plan: Includes all Python interview content, adaptive learning, and mastery tracking at no cost',
      'Pro Plan ($19/month): Adds AI explanations, advanced analytics, and unlimited study sessions',
      'Payments are processed securely via Stripe. We do not store your credit card information',
      'Subscriptions auto-renew unless cancelled. You can cancel anytime at /portal/billing',
      'Refunds are available within 7 days of payment for annual plans, 3 days for monthly plans',
      'Price changes will be announced 30 days in advance via email',
    ],
  },
  {
    title: '7. Data & Privacy',
    content: 'Your use of the Service is also governed by our Privacy Policy, which describes how we collect, use, and protect your data. By using the Service, you consent to the data practices described in our Privacy Policy. You can view it at /legal/privacy.',
  },
  {
    title: '8. Disclaimers',
    items: [
      'The Service is provided "as is" and "as available" without warranties of any kind',
      'We do not guarantee that the Service will be uninterrupted, error-free, or secure',
      'We do not guarantee that using the Service will result in passing interviews or exams',
      'Your use of the Service is at your own risk',
      'Any reliance on information from the Service is at your own discretion',
    ],
    note: 'Some jurisdictions do not allow certain warranty exclusions, so some of the above may not apply to you.',
  },
  {
    title: '9. Limitation of Liability',
    content: 'To the maximum extent permitted by law, Mastery Engine Inc. shall not be liable for any indirect, incidental, special, consequential, or punitive damages — including loss of profits, data, use, or goodwill — arising from your use of the Service. Our total liability for any claim shall not exceed the amount you paid in the 12 months preceding the claim, or $50, whichever is greater.',
  },
  {
    title: '10. Indemnification',
    content: 'You agree to indemnify and hold harmless Mastery Engine Inc., its officers, directors, employees, and agents from any claims, damages, losses, or expenses (including legal fees) arising from your use of the Service, your violation of these Terms, or your infringement of any third-party rights.',
  },
  {
    title: '11. Termination',
    content: 'You may delete your account at any time via Settings → Security → Delete Account. We may suspend or terminate your account if you violate these Terms, engage in fraudulent activity, or for any other reason with 30 days notice. Upon termination, your data will be anonymized per our Privacy Policy. Sections on intellectual property, disclaimers, and limitation of liability survive termination.',
  },
  {
    title: '12. Changes to Terms',
    content: 'We may update these Terms from time to time. We will notify you of material changes via email 30 days before they take effect. Continued use of the Service after changes take effect constitutes acceptance of the updated Terms.',
  },
  {
    title: '13. Governing Law',
    content: 'These Terms are governed by the laws of the State of Delaware, USA, without regard to conflict of law principles. Any disputes will be resolved in the state or federal courts located in Delaware. EU users retain the right to bring proceedings in their local courts under GDPR.',
  },
  {
    title: '14. Contact',
    content: 'Questions about these Terms? Email legal@masteryos.com or visit our Support Center at /support. We respond to all inquiries within 5 business days.',
  },
]

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#08080A] text-white">
      {/* Background glow */}
      <div className="pointer-events-none fixed inset-0 glow-emerald opacity-20" />

      <div className="relative container mx-auto px-4 py-20">
        {/* Hero */}
        <div className="mx-auto mb-16 max-w-2xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-xs font-medium text-emerald-300 backdrop-blur-sm">
            <FileText className="h-3.5 w-3.5" />
            Legal Agreement
          </div>
          <h1 className="text-5xl font-bold tracking-tight">
            Terms of{' '}
            <span className="gradient-emerald-text">Service</span>
          </h1>
          <p className="mt-4 text-lg text-zinc-400">
            Last updated: July 6, 2026
          </p>
          <p className="mx-auto mt-4 max-w-xl text-sm text-zinc-500">
            These Terms govern your use of MasteryOS. Please read them carefully — by using the Service, you agree to be bound by them.
          </p>
        </div>

        {/* Quick summary */}
        <div className="mx-auto mb-16 max-w-3xl">
          <Card className="glass-card p-6">
            <h2 className="mb-4 flex items-center gap-2 text-lg font-bold text-white">
              <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              Summary
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="flex items-center gap-2 text-sm text-zinc-300">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                Free plan is free forever
              </div>
              <div className="flex items-center gap-2 text-sm text-zinc-300">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                Cancel anytime
              </div>
              <div className="flex items-center gap-2 text-sm text-zinc-300">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                Your data belongs to you
              </div>
              <div className="flex items-center gap-2 text-sm text-zinc-300">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                7-day refund on annual plans
              </div>
              <div className="flex items-center gap-2 text-sm text-zinc-300">
                <XCircle className="h-4 w-4 shrink-0 text-red-400" />
                Don&apos;t share accounts
              </div>
              <div className="flex items-center gap-2 text-sm text-zinc-300">
                <XCircle className="h-4 w-4 shrink-0 text-red-400" />
                Don&apos;t reverse engineer
              </div>
            </div>
          </Card>
        </div>

        {/* Sections */}
        <div className="mx-auto max-w-3xl space-y-6">
          {SECTIONS.map((section, i) => (
            <div key={i} className="animate-fade-in-up" style={{ animationDelay: `${i * 0.05}s` }}>
              <Card className="glass-card">
                <CardContent className="pt-6">
                  <h2 className="mb-3 text-lg font-bold text-white">{section.title}</h2>
                  {section.content && (
                    <p className="text-sm leading-relaxed text-zinc-400">{section.content}</p>
                  )}
                  {section.items && (
                    <ul className="space-y-2">
                      {section.items.map((item, j) => (
                        <li key={j} className="flex items-start gap-2 text-sm text-zinc-400">
                          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  )}
                  {section.note && (
                    <div className="mt-4 flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
                      <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
                      <p className="text-sm text-zinc-300">{section.note}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="mx-auto mt-16 max-w-3xl text-center">
          <Card className="glass-card gradient-ring relative overflow-hidden p-8">
            <div className="absolute inset-0 glow-emerald-strong opacity-30" />
            <div className="relative">
              <FileText className="mx-auto h-10 w-10 text-emerald-400" />
              <h3 className="mt-4 text-xl font-bold text-white">
                Questions about these Terms?
              </h3>
              <p className="mt-2 text-sm text-zinc-400">
                We&apos;re happy to clarify anything in these Terms.
              </p>
              <a href="mailto:legal@masteryos.com">
                <Badge variant="outline" className="mt-4 border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-300">
                  legal@masteryos.com
                </Badge>
              </a>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
