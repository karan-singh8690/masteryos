'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Shield, Lock, KeyRound, FileCheck, Eye, Server } from 'lucide-react'

const SECURITY_FEATURES = [
  { icon: KeyRound, title: 'Argon2id Password Hashing', desc: 'OWASP 2024 recommended parameters (19 MB memory, 2 iterations). Resistant to GPU and ASIC attacks.' },
  { icon: Lock, title: 'RS256 JWT Authentication', desc: 'Asymmetric RSA 4096-bit key pairs. Access tokens (15 min) + refresh tokens (30 days) with family-based rotation reuse detection.' },
  { icon: Shield, title: 'MFA / TOTP', desc: 'Optional two-factor authentication via authenticator apps (Google Authenticator, 1Password, Authy). 10 one-time recovery codes.' },
  { icon: FileCheck, title: 'RBAC', desc: 'Role-based access control with 6 roles (learner, instructor, content_editor, organization_admin, administrator, system_admin) and 30+ fine-grained permissions.' },
  { icon: Eye, title: 'Audit Logging', desc: 'Immutable, append-only audit trail of all authentication events. 22 action types tracked with IP, user agent, and correlation ID.' },
  { icon: Server, title: 'Rate Limiting', desc: 'Redis-backed sliding-window rate limiting per IP and per user. Configurable per endpoint (auth: 10/min, API: 60/min, AI: 20/min).' },
]

const COMPLIANCE = [
  'GDPR Compliant', 'OWASP Top 10 Protected', 'SOC 2 Ready', 'Data Encryption at Rest',
  'TLS 1.2+ in Transit', 'CSP Headers', 'HSTS Enabled', 'Regular Security Audits',
]

export default function SecurityPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto mb-16 max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">Security</h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Enterprise-grade security built in from day one.
        </p>
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {SECURITY_FEATURES.map((f) => {
          const Icon = f.icon
          return (
            <Card key={f.title}>
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/10">
                  <Icon className="h-5 w-5 text-blue-600" />
                </div>
                <CardTitle className="text-lg">{f.title}</CardTitle>
              </CardHeader>
              <CardContent><p className="text-sm text-muted-foreground">{f.desc}</p></CardContent>
            </Card>
          )
        })}
      </div>
      <div className="mt-16 rounded-lg border bg-muted/30 p-8">
        <h2 className="mb-4 text-2xl font-bold">Compliance & Standards</h2>
        <div className="flex flex-wrap gap-3">
          {COMPLIANCE.map((c) => (
            <span key={c} className="rounded-full border bg-background px-4 py-2 text-sm font-medium">{c}</span>
          ))}
        </div>
      </div>
    </div>
  )
}
