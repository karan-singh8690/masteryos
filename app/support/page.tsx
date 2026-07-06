'use client'

import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { BookOpen, Mail, MessageCircle, Activity, ChevronDown, Search, ArrowRight, Sparkles } from 'lucide-react'
import { cn } from '@/lib/cn'

const SUPPORT_CARDS = [
  { icon: BookOpen, title: 'Knowledge Base', desc: 'Browse articles and guides', href: '/docs/faq' },
  { icon: Mail, title: 'Contact Support', desc: 'Send us a message', href: '#contact-form' },
  { icon: MessageCircle, title: 'Community', desc: 'Join the discussion', href: '#' },
  { icon: Activity, title: 'System Status', desc: 'Check platform health', href: '/status' },
]

const FAQS = [
  { q: 'How do I get started?', a: 'Sign up for free at /register, then enroll in the Python Technical Interview Prep subject. Start a study session and answer questions — the adaptive engine will do the rest!' },
  { q: 'How do I reset my password?', a: 'Go to /forgot-password and enter your email. You will receive a reset link valid for 15 minutes.' },
  { q: 'How do I set up MFA?', a: 'After logging in, go to Settings → Security → Enable MFA. Scan the QR code with an authenticator app and save your recovery codes.' },
  { q: 'What is the mastery score?', a: 'The mastery score is a 0-1 value representing your durable understanding of a concept. It combines recent performance (memory) with long-term evidence (durable mastery). Higher = better.' },
  { q: 'How often should I study?', a: 'We recommend 10-20 questions per day. The adaptive engine will schedule reviews at optimal intervals to maximize retention.' },
  { q: 'Can I use MasteryOS offline?', a: 'Yes! The learner portal supports offline mode. Actions are queued and synced when you reconnect.' },
  { q: 'Is MasteryOS free?', a: 'The Free plan includes all Python interview content, adaptive learning, and mastery tracking. Pro ($19/mo) adds AI explanations and advanced analytics.' },
  { q: 'How do I report a bug?', a: 'Use the floating feedback button in the app, or email support@masteryos.com with a description and screenshot.' },
]

export default function SupportPage() {
  return (
    <div className="min-h-screen bg-[#08080A] text-white">
      {/* Background glow */}
      <div className="pointer-events-none fixed inset-0 glow-emerald opacity-20" />

      <div className="relative container mx-auto px-4 py-20">
        {/* Hero */}
        <div className="mx-auto mb-16 max-w-2xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-xs font-medium text-emerald-300 backdrop-blur-sm">
            <Sparkles className="h-3.5 w-3.5" />
            We're here to help
          </div>
          <h1 className="text-5xl font-bold tracking-tight">
            Support{' '}
            <span className="gradient-emerald-text">Center</span>
          </h1>
          <p className="mt-4 text-lg text-zinc-400">
            How can we help you? Search our knowledge base or reach out directly.
          </p>

          {/* Search bar */}
          <div className="relative mx-auto mt-8 max-w-xl">
            <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-zinc-500" />
            <Input
              placeholder="Search for help articles..."
              className="h-12 rounded-xl border-white/10 bg-white/5 pl-12 text-base text-white placeholder:text-zinc-600"
            />
          </div>
        </div>

        {/* Support cards */}
        <div className="mx-auto max-w-5xl">
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {SUPPORT_CARDS.map((card, i) => {
              const Icon = card.icon
              return (
                <a key={card.title} href={card.href}>
                  <Card
                    className="glass-card h-full cursor-pointer group animate-fade-in-up"
                    style={{ animationDelay: `${i * 0.1}s` }}
                  >
                    <CardContent className="pt-6 text-center">
                      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 ring-1 ring-inset ring-emerald-500/20 transition-transform duration-300 group-hover:scale-110">
                        <Icon className="h-7 w-7 text-emerald-400" />
                      </div>
                      <h3 className="font-semibold text-white">{card.title}</h3>
                      <p className="mt-1 text-sm text-zinc-400">{card.desc}</p>
                    </CardContent>
                  </Card>
                </a>
              )
            })}
          </div>
        </div>

        {/* FAQ Section */}
        <div className="mx-auto mt-20 max-w-3xl">
          <div className="mb-8 text-center">
            <h2 className="text-3xl font-bold tracking-tight">
              Frequently Asked{' '}
              <span className="gradient-emerald-text">Questions</span>
            </h2>
            <p className="mt-2 text-sm text-zinc-400">Quick answers to common questions</p>
          </div>

          <div className="space-y-3">
            {FAQS.map((faq, i) => (
              <details
                key={i}
                className="glass-card group rounded-2xl p-5 transition-all duration-300 hover:bg-white/[0.05] animate-fade-in-up"
                style={{ animationDelay: `${i * 0.05}s` }}
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

        {/* Contact Form */}
        <div id="contact-form" className="mx-auto mt-20 max-w-2xl">
          <div className="mb-8 text-center">
            <h2 className="text-3xl font-bold tracking-tight">
              Still need{' '}
              <span className="gradient-emerald-text">help?</span>
            </h2>
            <p className="mt-2 text-sm text-zinc-400">Send us a message and we'll get back to you within 24 hours</p>
          </div>

          <Card className="glass-card">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 ring-1 ring-inset ring-emerald-500/20">
                  <Mail className="h-5 w-5 text-emerald-400" />
                </div>
                <div>
                  <CardTitle>Contact Support</CardTitle>
                  <CardDescription>We typically respond within 24 hours</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <form className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="name" className="text-zinc-300">Name</Label>
                    <Input id="name" placeholder="Your name" className="border-white/10 bg-white/5 text-white placeholder:text-zinc-600" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-zinc-300">Email</Label>
                    <Input id="email" type="email" placeholder="you@example.com" className="border-white/10 bg-white/5 text-white placeholder:text-zinc-600" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="subject" className="text-zinc-300">Subject</Label>
                  <Input id="subject" placeholder="Brief description" className="border-white/10 bg-white/5 text-white placeholder:text-zinc-600" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="message" className="text-zinc-300">Message</Label>
                  <Textarea
                    id="message"
                    rows={5}
                    placeholder="Describe your issue in detail..."
                    className="border-white/10 bg-white/5 text-white placeholder:text-zinc-600"
                  />
                </div>
                <Button className="btn-glow w-full gradient-emerald font-semibold text-black shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50">
                  Submit Ticket
                  <ArrowRight className="ml-1 h-4 w-4" />
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
