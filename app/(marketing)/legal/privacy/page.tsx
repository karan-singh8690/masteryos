'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Shield, Lock, Eye, Database, Mail, FileText, CheckCircle2, AlertCircle } from 'lucide-react'

const SECTIONS = [
  {
    icon: Database,
    title: 'Information We Collect',
    content: [
      { heading: 'Account Information', text: 'When you create an account, we collect your email address, display name, and password. Passwords are hashed using Argon2id — we never store or see your plain-text password.' },
      { heading: 'Learning Data', text: 'We collect data about your learning activity including study sessions, question answers, mastery scores, review schedules, and progress analytics. This data powers the adaptive learning engine.' },
      { heading: 'Usage Data', text: 'We automatically collect information about how you use the Service, including pages visited, features used, device type, browser, IP address, and session duration. This helps us improve the platform.' },
      { heading: 'Communication Data', text: 'When you contact support or submit feedback, we collect the content of your messages, email address, and any attachments you provide.' },
    ],
  },
  {
    icon: Eye,
    title: 'How We Use Your Information',
    content: [
      { heading: 'Provide the Service', text: 'To operate, maintain, and improve MasteryOS — including adaptive question selection, mastery tracking, and personalized recommendations.' },
      { heading: 'Personalization', text: 'To customize your learning experience, track your progress, and schedule reviews at optimal intervals using spaced repetition.' },
      { heading: 'Communication', text: 'To send you service notifications (due reviews, achievements), important account updates, and responses to your support requests.' },
      { heading: 'Analytics & Improvement', text: 'To analyze usage patterns, measure feature adoption, and improve our algorithms. We use anonymized, aggregated data for product analytics.' },
      { heading: 'Security & Fraud Prevention', text: 'To detect and prevent fraud, abuse, unauthorized access, and other security threats. This includes monitoring for suspicious login activity.' },
      { heading: 'Legal Compliance', text: 'To comply with applicable laws, regulations, legal processes, and government requests.' },
    ],
  },
  {
    icon: Lock,
    title: 'Data Security',
    content: [
      { heading: 'Encryption', text: 'All data is encrypted in transit using TLS 1.2+ and at rest using industry-standard encryption. Passwords are hashed with Argon2id (memory-hard, resistant to GPU attacks).' },
      { heading: 'Authentication', text: 'We use RS256 JWT tokens for authentication with short-lived access tokens (15 minutes) and rotating refresh tokens. Multi-Factor Authentication (TOTP) is available and recommended.' },
      { heading: 'Access Control', text: 'Access to user data is strictly limited to authorized personnel on a need-to-know basis. All access is logged and audited. Role-based access control (RBAC) ensures least-privilege access.' },
      { heading: 'Infrastructure', text: 'Our infrastructure is hosted on Railway with managed PostgreSQL and Redis. Database connections are encrypted, and backups are encrypted at rest.' },
      { heading: 'Incident Response', text: 'We have an incident response plan in place. In the event of a data breach, we will notify affected users within 72 hours per GDPR Article 34.' },
    ],
  },
  {
    icon: Shield,
    title: 'Your Rights (GDPR & CCPA)',
    content: [
      { heading: 'Right to Access', text: 'You can request a copy of all personal data we hold about you. Visit Settings → Security → Export Data or email privacy@masteryos.com.' },
      { heading: 'Right to Rectification', text: 'You can correct inaccurate or incomplete data. Update your profile at /profile or contact us for assistance.' },
      { heading: 'Right to Erasure', text: 'You can request deletion of your account and personal data. Visit Settings → Security → Delete Account. Your data will be anonymized within 30 days.' },
      { heading: 'Right to Portability', text: 'You can export your learning data in JSON format at any time. Visit Portal → Account → Export Data.' },
      { heading: 'Right to Object', text: 'You can opt out of marketing emails, analytics tracking, and certain data processing. Visit Settings → Notifications to manage preferences.' },
      { heading: 'Right to Restrict Processing', text: 'You can request that we limit how we use your data while a complaint is being resolved.' },
    ],
    note: 'To exercise any of these rights, email privacy@masteryos.com with the subject line "Data Rights Request". We respond within 30 days.',
  },
  {
    icon: FileText,
    title: 'Data Retention',
    content: [
      { heading: 'Active Accounts', text: 'We retain your data for as long as your account is active. If you don\'t log in for 12 months, we will notify you before considering the account inactive.' },
      { heading: 'Deleted Accounts', text: 'When you delete your account, your personal data (email, name, profile) is anonymized within 30 days. Learning data (attempts, mastery scores) is retained in anonymized form for algorithm improvement.' },
      { heading: 'Audit Logs', text: 'Security audit logs (login attempts, password changes, MFA events) are retained for 2 years for security compliance, then automatically purged.' },
      { heading: 'Support Tickets', text: 'Support communications are retained for 3 years for quality assurance and dispute resolution.' },
    ],
  },
  {
    icon: Database,
    title: 'Data Sharing & Third Parties',
    content: [
      { heading: 'Service Providers', text: 'We use third-party services to operate MasteryOS: Railway (hosting), PostgreSQL (database), Redis (caching), Stripe (payments). Each provider has their own privacy policy and data protection measures.' },
      { heading: 'Analytics', text: 'We use internal analytics only. We do NOT use Google Analytics, Facebook Pixel, or third-party tracking cookies. Your learning data stays with us.' },
      { heading: 'Legal Requirements', text: 'We may disclose your data if required by law, court order, or government regulation. We will challenge requests that we believe are improper.' },
      { heading: 'Business Transfers', text: 'In the event of a merger, acquisition, or asset sale, your data may be transferred. We will notify you 30 days before any such transfer.' },
      { heading: 'No Sale of Data', text: 'We do NOT sell your personal data to anyone. Period. We do not share your learning data with third parties for advertising.' },
    ],
  },
  {
    icon: Mail,
    title: 'Contact Us',
    content: [
      { heading: 'Privacy Questions', text: 'Email privacy@masteryos.com for any privacy-related questions or data rights requests. We respond within 30 days.' },
      { heading: 'Data Protection Officer', text: 'Our DPO can be reached at dpo@masteryos.com for GDPR-related inquiries.' },
      { heading: 'Postal Address', text: 'Mastery Engine Inc., Attn: Privacy Team, [Your Business Address]' },
      { heading: 'Supervisory Authority', text: 'EU residents have the right to lodge a complaint with their local supervisory authority. You can also contact the Irish DPC at dataprotection.ie.' },
    ],
  },
]

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#08080A] text-white">
      {/* Background glow */}
      <div className="pointer-events-none fixed inset-0 glow-emerald opacity-20" />

      <div className="relative container mx-auto px-4 py-20">
        {/* Hero */}
        <div className="mx-auto mb-16 max-w-2xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-xs font-medium text-emerald-300 backdrop-blur-sm">
            <Shield className="h-3.5 w-3.5" />
            Your Privacy Matters
          </div>
          <h1 className="text-5xl font-bold tracking-tight">
            Privacy{' '}
            <span className="gradient-emerald-text">Policy</span>
          </h1>
          <p className="mt-4 text-lg text-zinc-400">
            Last updated: July 6, 2026
          </p>
          <p className="mx-auto mt-4 max-w-xl text-sm text-zinc-500">
            This Privacy Policy describes how Mastery Engine (&ldquo;we&rdquo;, &ldquo;us&rdquo;, or &ldquo;our&rdquo;)
            collects, uses, and protects your information when you use MasteryOS (the &ldquo;Service&rdquo;).
          </p>
        </div>

        {/* Quick summary */}
        <div className="mx-auto mb-16 max-w-3xl">
          <Card className="glass-card p-6">
            <h2 className="mb-4 flex items-center gap-2 text-lg font-bold text-white">
              <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              Key Points
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                'We do NOT sell your data',
                'We do NOT use third-party tracking cookies',
                'Passwords hashed with Argon2id',
                'All data encrypted in transit + at rest',
                'GDPR + CCPA compliant',
                'Export or delete your data anytime',
              ].map((point, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-zinc-300">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                  {point}
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Sections */}
        <div className="mx-auto max-w-3xl space-y-8">
          {SECTIONS.map((section, i) => {
            const SectionIcon = section.icon
            return (
              <div key={i} className="animate-fade-in-up" style={{ animationDelay: `${i * 0.1}s` }}>
                <div className="mb-4 flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 ring-1 ring-inset ring-emerald-500/20">
                    <SectionIcon className="h-5 w-5 text-emerald-400" />
                  </div>
                  <h2 className="text-2xl font-bold text-white">{section.title}</h2>
                </div>

                <Card className="glass-card">
                  <CardContent className="space-y-4 pt-6">
                    {section.content.map((item, j) => (
                      <div key={j}>
                        <h3 className="text-sm font-semibold text-emerald-400">{item.heading}</h3>
                        <p className="mt-1 text-sm leading-relaxed text-zinc-400">{item.text}</p>
                      </div>
                    ))}
                    {section.note && (
                      <div className="mt-4 flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
                        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
                        <p className="text-sm text-zinc-300">{section.note}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )
          })}
        </div>

        {/* Footer */}
        <div className="mx-auto mt-16 max-w-3xl text-center">
          <Card className="glass-card gradient-ring relative overflow-hidden p-8">
            <div className="absolute inset-0 glow-emerald-strong opacity-30" />
            <div className="relative">
              <Shield className="mx-auto h-10 w-10 text-emerald-400" />
              <h3 className="mt-4 text-xl font-bold text-white">
                Questions about your privacy?
              </h3>
              <p className="mt-2 text-sm text-zinc-400">
                We take your privacy seriously. Reach out anytime.
              </p>
              <a href="mailto:privacy@masteryos.com">
                <Badge variant="outline" className="mt-4 border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-300">
                  <Mail className="mr-2 h-4 w-4" />
                  privacy@masteryos.com
                </Badge>
              </a>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
