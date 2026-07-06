'use client'

import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ChevronDown, Search, BookOpen, ArrowRight, Sparkles } from 'lucide-react'
import { Input } from '@/components/ui/input'

const FAQ_CATEGORIES = [
  {
    title: 'Getting Started',
    icon: Sparkles,
    faqs: [
      { q: 'How do I create an account?', a: 'Visit /register and sign up with your email. No credit card required — the Free plan includes all Python interview content, adaptive learning, and mastery tracking.' },
      { q: 'How do I start my first study session?', a: 'After logging in, go to Subjects → click "Python Technical Interview Prep" to enroll. Then go to Study → Start, pick your session type and question count, and begin!' },
      { q: 'What subjects are available?', a: 'Currently we offer Python Technical Interview Prep covering Data Structures, OOP, Algorithms, Python Internals, and System Design. More subjects coming soon!' },
      { q: 'How much does it cost?', a: 'The Free plan is free forever and includes all content + adaptive learning. Pro ($19/mo) adds AI explanations and advanced analytics.' },
    ],
  },
  {
    title: 'Account & Security',
    icon: BookOpen,
    faqs: [
      { q: 'How do I reset my password?', a: 'Go to /forgot-password and enter your email. You will receive a reset link valid for 15 minutes.' },
      { q: 'How do I set up MFA (Multi-Factor Authentication)?', a: 'After logging in, go to Settings → Security → Enable MFA. Scan the QR code with an authenticator app (Google Authenticator, Authy, etc.) and save your recovery codes.' },
      { q: 'Can I change my email address?', a: 'Currently, email changes require contacting support. Visit /support and submit a ticket with your current and new email.' },
      { q: 'How do I delete my account?', a: 'Go to Settings → Security → Account → Delete Account. This permanently anonymizes your data per GDPR. This action cannot be undone.' },
    ],
  },
  {
    title: 'Learning & Mastery',
    icon: Sparkles,
    faqs: [
      { q: 'What is the mastery score?', a: 'The mastery score (0-1) represents your durable understanding of a concept. It combines recent performance (memory) with long-term evidence (durable mastery). Higher = better retention.' },
      { q: 'How often should I study?', a: 'We recommend 10-20 questions per day. The adaptive engine schedules reviews at optimal intervals to maximize retention using spaced repetition.' },
      { q: 'What are weak concepts?', a: 'Weak concepts are topics where your mastery score is below the weakness threshold (typically 30%). These are prioritized in future study sessions to help you improve.' },
      { q: 'What is spaced repetition?', a: 'Spaced repetition is a scientifically-proven learning technique where reviews are scheduled at increasing intervals. This strengthens long-term memory and resists the forgetting curve.' },
      { q: 'Can I see my progress over time?', a: 'Yes! The Dashboard shows your mastery trends, streak, weekly learning activity, and interview readiness score — all updated in real-time.' },
    ],
  },
  {
    title: 'Technical & Billing',
    icon: BookOpen,
    faqs: [
      { q: 'Can I use MasteryOS offline?', a: 'Yes! The learner portal supports offline mode. Your actions are queued locally and synced automatically when you reconnect.' },
      { q: 'What browsers are supported?', a: 'MasteryOS works on all modern browsers: Chrome, Firefox, Safari, and Edge. For the best experience, use the latest version.' },
      { q: 'How do I upgrade to Pro?', a: 'Click the "Upgrade" button in the sidebar or visit /portal/billing. Pro is $19/month and includes AI explanations, advanced analytics, and unlimited study sessions.' },
      { q: 'How do I report a bug?', a: 'Use the floating feedback button in the app (bottom right), or email support@masteryos.com with a description and screenshot.' },
    ],
  },
]

export default function FAQPage() {
  return (
    <div className="min-h-screen bg-[#08080A] text-white">
      {/* Background glow */}
      <div className="pointer-events-none fixed inset-0 glow-emerald opacity-20" />

      <div className="relative container mx-auto px-4 py-20">
        {/* Hero */}
        <div className="mx-auto mb-16 max-w-2xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-xs font-medium text-emerald-300 backdrop-blur-sm">
            <BookOpen className="h-3.5 w-3.5" />
            Knowledge Base
          </div>
          <h1 className="text-5xl font-bold tracking-tight">
            Frequently Asked{' '}
            <span className="gradient-emerald-text">Questions</span>
          </h1>
          <p className="mt-4 text-lg text-zinc-400">
            Everything you need to know about MasteryOS. Can't find an answer?{' '}
            <Link href="/support" className="text-emerald-400 hover:text-emerald-300 transition-colors">
              Contact support
            </Link>
            .
          </p>

          {/* Search bar */}
          <div className="relative mx-auto mt-8 max-w-xl">
            <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-zinc-500" />
            <Input
              placeholder="Search questions..."
              className="h-12 rounded-xl border-white/10 bg-white/5 pl-12 text-base text-white placeholder:text-zinc-600"
            />
          </div>
        </div>

        {/* FAQ Categories */}
        <div className="mx-auto max-w-3xl space-y-12">
          {FAQ_CATEGORIES.map((category, catIdx) => {
            const CatIcon = category.icon
            return (
              <div key={catIdx}>
                {/* Category header */}
                <div className="mb-5 flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 ring-1 ring-inset ring-emerald-500/20">
                    <CatIcon className="h-5 w-5 text-emerald-400" />
                  </div>
                  <h2 className="text-2xl font-bold text-white">{category.title}</h2>
                </div>

                {/* FAQ items */}
                <div className="space-y-3">
                  {category.faqs.map((faq, i) => (
                    <details
                      key={i}
                      className="glass-card group rounded-2xl p-5 transition-all duration-300 hover:bg-white/[0.05]"
                    >
                      <summary className="flex cursor-pointer items-center justify-between font-medium text-white">
                        {faq.q}
                        <ChevronDown className="h-5 w-5 shrink-0 text-zinc-500 transition-transform duration-300 group-open:rotate-180 group-open:text-emerald-400" />
                      </summary>
                      <p className="mt-3 text-sm leading-relaxed text-zinc-400">{faq.a}</p>
                    </details>
                  ))}
                </div>
              </div>
            )
          })}
        </div>

        {/* Still need help CTA */}
        <div className="mx-auto mt-20 max-w-2xl">
          <Card className="glass-card gradient-ring relative overflow-hidden p-8 text-center">
            <div className="absolute inset-0 glow-emerald-strong opacity-30" />
            <div className="relative">
              <h3 className="text-2xl font-bold text-white">
                Still have{' '}
                <span className="gradient-emerald-text">questions?</span>
              </h3>
              <p className="mt-2 text-sm text-zinc-400">
                Our support team is here to help. Reach out and we'll respond within 24 hours.
              </p>
              <Link href="/support">
                <Button className="btn-glow mt-6 gradient-emerald font-semibold text-black shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50">
                  Contact Support
                  <ArrowRight className="ml-1 h-4 w-4" />
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
