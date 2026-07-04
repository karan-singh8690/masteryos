'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { BookOpen, Mail, MessageCircle, Activity, ChevronDown } from 'lucide-react'

const SUPPORT_CARDS = [
  { icon: BookOpen, title: 'Knowledge Base', desc: 'Browse articles and guides', href: '/docs' },
  { icon: Mail, title: 'Contact Support', desc: 'Send us a message', href: '#contact-form' },
  { icon: MessageCircle, title: 'Community', desc: 'Join the discussion', href: '#' },
  { icon: Activity, title: 'System Status', desc: 'Check platform health', href: '/status' },
]

const FAQS = [
  { q: 'How do I get an invite to the Closed Beta?', a: 'Request an invite at masteryos.com/register. We are rolling out invites in batches of 5-20 users.' },
  { q: 'How do I reset my password?', a: 'Go to /forgot-password and enter your email. You will receive a reset link valid for 15 minutes.' },
  { q: 'How do I set up MFA?', a: 'After logging in, go to Settings → Security → Enable MFA. Scan the QR code with an authenticator app and save your recovery codes.' },
  { q: 'Can I use MasteryOS offline?', a: 'Yes! The learner portal supports offline mode. Actions are queued and synced when you reconnect.' },
  { q: 'How do I get an API key?', a: 'Once logged in, go to Portal → API Keys. Create a new key and copy it immediately (it is only shown once).' },
  { q: 'What is the mastery score?', a: 'The mastery score is a 0-1 value representing your durable understanding of a concept. It combines recent performance (memory) with long-term evidence (durable mastery).' },
  { q: 'How often should I study?', a: 'We recommend 10-20 questions per day. The adaptive engine will schedule reviews at optimal intervals.' },
  { q: 'Can I export my data?', a: 'Yes. Go to Portal → Account → Export Data. You will receive a JSON file with all your learning history.' },
  { q: 'Is MasteryOS free?', a: 'The Free plan includes all Python interview content, adaptive learning, and mastery tracking. Pro ($19/mo) adds AI explanations and advanced analytics.' },
  { q: 'How do I report a bug?', a: 'Use the floating feedback button in the app, or email support@masteryos.com with a description and screenshot.' },
]

export default function SupportPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto mb-16 max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">Support Center</h1>
        <p className="mt-4 text-lg text-muted-foreground">How can we help you?</p>
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {SUPPORT_CARDS.map((card) => {
          const Icon = card.icon
          return (
            <a key={card.title} href={card.href}>
              <Card className="h-full transition-shadow hover:shadow-lg">
                <CardContent className="pt-6 text-center">
                  <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600/10">
                    <Icon className="h-6 w-6 text-blue-600" />
                  </div>
                  <h3 className="font-semibold">{card.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{card.desc}</p>
                </CardContent>
              </Card>
            </a>
          )
        })}
      </div>
      <div className="mx-auto mt-20 max-w-3xl">
        <h2 className="mb-6 text-2xl font-bold">Frequently Asked Questions</h2>
        <div className="space-y-4">
          {FAQS.map((faq) => (
            <details key={faq.q} className="group rounded-lg border p-4">
              <summary className="flex cursor-pointer items-center justify-between font-semibold">
                {faq.q}
                <ChevronDown className="h-5 w-5 text-muted-foreground transition-transform group-open:rotate-180" />
              </summary>
              <p className="mt-3 text-muted-foreground">{faq.a}</p>
            </details>
          ))}
        </div>
      </div>
      <div id="contact-form" className="mx-auto mt-20 max-w-2xl">
        <Card>
          <CardHeader><CardTitle>Contact Support</CardTitle></CardHeader>
          <CardContent>
            <form className="space-y-4">
              <div><Label htmlFor="name">Name</Label><Input id="name" placeholder="Your name" /></div>
              <div><Label htmlFor="email">Email</Label><Input id="email" type="email" placeholder="you@example.com" /></div>
              <div><Label htmlFor="subject">Subject</Label><Input id="subject" placeholder="Brief description" /></div>
              <div><Label htmlFor="message">Message</Label><Textarea id="message" rows={5} placeholder="Describe your issue in detail..." /></div>
              <Button className="w-full">Submit Ticket</Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
