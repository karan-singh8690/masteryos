'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
// Note: Card components may be used in other parts; keeping import for compatibility
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Mail, Lock, ArrowRight, TrendingUp, Sparkles, Shield } from 'lucide-react'
import { authApi, userApi, ApiError, tokenStorage } from '@/lib/api-client'
import { useAuth, MfaRequiredError } from '@/providers/auth-provider'

export default function LoginPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { setUser } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const redirect = searchParams.get('redirect') || '/dashboard'

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      // 1. Call login API directly
      const response = await authApi.login({ email, password })

      // 2. Handle MFA
      if (response.requires_mfa) {
        const params = new URLSearchParams({
          mfa_session_token: response.mfa_session_token || '',
          redirect,
        })
        router.push(`/mfa/verify?${params}`)
        return
      }

      // 3. Store tokens IMMEDIATELY
      tokenStorage.setAccessToken(response.access_token)
      if (response.refresh_token) {
        tokenStorage.setRefreshToken(response.refresh_token)
      }

      // 4. Set auth cookie IMMEDIATELY (before anything else)
      // This is what middleware checks — must be set before redirect
      document.cookie = 'mastery-authenticated=true; path=/; SameSite=Strict; max-age=2592000'

      // 5. Try to fetch full CurrentUser (with roles + profile + permissions)
      try {
        const me = await userApi.me()
        if (me && me.roles && Array.isArray(me.roles) && me.roles.length > 0) {
          document.cookie = `mastery-role=${me.roles[0]}; path=/; SameSite=Strict; max-age=2592000`
        }
        if (me && me.user && me.profile) {
          setUser(me)
        }
      } catch {
        // Profile fetch failed — auth provider will retry via useQuery
      }

      // 6. Navigate — cookie is already set, middleware will allow
      router.push(redirect)
    } catch (err: any) {
      if (err instanceof MfaRequiredError) {
        const params = new URLSearchParams({
          mfa_session_token: err.mfaSessionToken,
          redirect,
        })
        router.push(`/mfa/verify?${params}`)
        return
      }
      setError(err instanceof ApiError ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const highlights = [
    { icon: TrendingUp, title: 'Adaptive mastery', description: 'Tracks what you know — and what you don\'t.' },
    { icon: Sparkles, title: 'AI guidance', description: 'Personalized next steps after every session.' },
    { icon: Shield, title: 'Spaced repetition', description: 'Review scheduling that actually sticks.' },
  ]

  return (
    <div className="flex min-h-screen bg-background">
      {/* Left branding panel — dark premium with emerald glow */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-[#08080A] p-12 lg:flex">
        {/* Glow orbs */}
        <div className="pointer-events-none absolute -left-32 top-1/4 h-96 w-96 rounded-full bg-emerald-500/15 blur-3xl animate-glow-pulse" aria-hidden="true" />
        <div className="pointer-events-none absolute -right-20 bottom-1/4 h-80 w-80 rounded-full bg-teal-500/10 blur-3xl animate-glow-pulse" style={{ animationDelay: '2s' }} aria-hidden="true" />
        {/* Grid */}
        <div className="pointer-events-none absolute inset-0 bg-grid opacity-30" aria-hidden="true" />

        <div className="relative z-10">
          <div className="flex items-center gap-2">
            <img src="/brand/logo-mark.svg" alt="MasteryOS" className="h-10 w-10" />
            <span className="text-xl font-bold text-white">MasteryOS</span>
          </div>
        </div>
        <div className="relative z-10 space-y-8">
          <h1 className="text-4xl font-bold leading-tight text-white">
            The Operating System for{' '}
            <span className="gradient-emerald-text">Learning</span>
          </h1>
          <div className="space-y-4">
            {highlights.map((h) => (
              <div key={h.title} className="flex items-start gap-3">
                <div className="rounded-lg bg-white/10 p-2">
                  <h.icon className="h-5 w-5 text-white" />
                </div>
                <div>
                  <p className="font-semibold text-white">{h.title}</p>
                  <p className="text-sm text-emerald-100">{h.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <p className="text-sm text-emerald-200">© 2026 MasteryOS. All rights reserved.</p>
      </div>

      {/* Right login form — dark premium */}
      <div className="relative flex w-full items-center justify-center p-6 lg:w-1/2">
        {/* Subtle glow */}
        <div className="pointer-events-none absolute top-1/2 left-1/2 h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full bg-emerald-500/5 blur-3xl" aria-hidden="true" />
        <div className="glass-card relative z-10 w-full max-w-md rounded-2xl p-8">
          <div className="text-center">
            <img src="/brand/logo-mark.svg" alt="MasteryOS" className="mx-auto mb-4 h-12 w-12 lg:hidden" />
            <h2 className="text-2xl font-bold">Welcome back</h2>
            <p className="mt-1 text-sm text-muted-foreground">Sign in to your MasteryOS account</p>
          </div>
          <div className="mt-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    className="pl-9"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <Link href="/forgot-password" className="text-xs text-muted-foreground hover:text-primary">Forgot password?</Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    className="pl-9"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
              </div>
              <Button type="submit" className="btn-glow w-full gap-2 gradient-emerald border-0 text-white hover:opacity-90" disabled={loading}>
                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                Sign In
              </Button>
              <p className="text-center text-sm text-muted-foreground">
                Don&apos;t have an account?{' '}
                <Link href="/register" className="font-medium text-primary hover:underline">Sign up</Link>
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
