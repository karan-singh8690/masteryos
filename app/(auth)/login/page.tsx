'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Mail, Lock, ArrowRight, TrendingUp, Sparkles, Shield, BarChart3 } from 'lucide-react'
import { authApi, ApiError, tokenStorage } from '@/lib/api-client'
import { useAuth, MfaRequiredError } from '@/providers/auth-provider'

export default function LoginPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { login, setUser } = useAuth()
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
      // Use the typed API client + AuthProvider login
      await login(email, password)

      // Set auth cookie for middleware (presence check)
      document.cookie = 'mastery-authenticated=true; path=/; SameSite=Strict'

      // Fetch user to get role, then set role cookie for middleware admin check
      try {
        const me = await authApi.me()
        if (me.roles?.length) {
          document.cookie = `mastery-role=${me.roles[0]}; path=/; SameSite=Strict`
          setUser(me)
        }
      } catch {
        // Role fetch failed — non-fatal, user can still access non-admin routes
      }

      router.push(redirect)
    } catch (err: any) {
      if (err instanceof MfaRequiredError) {
        // Redirect to MFA verify with session token
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
      {/* ============================================================ */}
      {/* Left panel — branding / emerald gradient                      */}
      {/* ============================================================ */}
      <aside
        className="relative hidden overflow-hidden bg-gradient-to-br from-emerald-600 via-emerald-700 to-teal-800 p-10 text-white lg:flex lg:w-1/2 lg:flex-col lg:justify-between xl:p-14"
        aria-label="MasteryOS branding"
      >
        {/* Decorative dot grid */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.12]"
          style={{
            backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
            backgroundSize: '28px 28px',
          }}
          aria-hidden="true"
        />
        {/* Glow blobs */}
        <div className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-emerald-300/30 blur-3xl" aria-hidden="true" />
        <div className="pointer-events-none absolute -bottom-32 -left-24 h-96 w-96 rounded-full bg-teal-300/25 blur-3xl" aria-hidden="true" />

        {/* Logo + brand */}
        <div className="relative z-10 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 backdrop-blur-sm ring-1 ring-inset ring-white/20">
            <img src="/brand/logo-mark.svg" alt="" className="h-7 w-7" />
          </div>
          <span className="text-xl font-bold tracking-tight">MasteryOS</span>
        </div>

        {/* Hero copy */}
        <div className="relative z-10 max-w-md space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-emerald-50 ring-1 ring-inset ring-white/20 backdrop-blur-sm">
            <BarChart3 className="h-3.5 w-3.5" aria-hidden="true" />
            The Operating System for Learning
          </div>
          <h1 className="text-4xl font-bold leading-[1.1] tracking-tight xl:text-5xl">
            Master any subject,{' '}
            <span className="bg-gradient-to-r from-emerald-200 to-teal-100 bg-clip-text text-transparent">
              one concept at a time.
            </span>
          </h1>
          <p className="text-base leading-relaxed text-emerald-50/80 xl:text-lg">
            Adaptive learning, spaced repetition, and AI-powered insights designed to take you from
            novice to interview-ready.
          </p>

          <ul className="space-y-3 pt-2">
            {highlights.map((feature) => (
              <li key={feature.title} className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10 ring-1 ring-inset ring-white/20 backdrop-blur-sm">
                  <feature.icon className="h-4 w-4 text-emerald-50" aria-hidden="true" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{feature.title}</p>
                  <p className="text-sm text-emerald-50/70">{feature.description}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* Footer */}
        <div className="relative z-10 flex items-center gap-4 text-xs text-emerald-100/60">
          <span>© {new Date().getFullYear()} MasteryOS</span>
          <span className="h-1 w-1 rounded-full bg-emerald-100/40" aria-hidden="true" />
          <Link href="/" className="transition-colors hover:text-white">
            Privacy
          </Link>
          <span className="h-1 w-1 rounded-full bg-emerald-100/40" aria-hidden="true" />
          <Link href="/" className="transition-colors hover:text-white">
            Terms
          </Link>
        </div>
      </aside>

      {/* ============================================================ */}
      {/* Right panel — login form                                     */}
      {/* ============================================================ */}
      <div className="flex flex-1 items-center justify-center px-4 py-10 sm:px-6 lg:px-12">
        <div className="w-full max-w-md">
          {/* Mobile brand */}
          <div className="mb-8 flex items-center justify-center gap-2.5 lg:hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-sm">
              <img src="/brand/logo-mark.svg" alt="" className="h-6 w-6" />
            </div>
            <span className="text-lg font-bold tracking-tight">MasteryOS</span>
          </div>

          {/* Heading */}
          <div className="space-y-2">
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">Welcome back</h2>
            <p className="text-sm text-muted-foreground">
              Sign in to your account to continue your mastery journey.
            </p>
          </div>

          {/* Card */}
          <div className="mt-8 rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium">
                  Email
                </Label>
                <div className="relative">
                  <Mail
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    className="pl-9"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    autoFocus
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-sm font-medium">
                    Password
                  </Label>
                  <Link
                    href="/forgot-password"
                    className="text-xs font-medium text-emerald-600 transition-colors hover:text-emerald-500 dark:text-emerald-400 dark:hover:text-emerald-300"
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <Lock
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <Input
                    id="password"
                    type="password"
                    placeholder="Enter your password"
                    className="pl-9"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                  />
                </div>
              </div>

              <Button
                type="submit"
                className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-lg shadow-emerald-500/20 transition-all hover:from-emerald-600 hover:to-teal-600 hover:shadow-emerald-500/30"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    Signing in…
                  </>
                ) : (
                  <>
                    Sign In
                    <ArrowRight className="ml-1 h-4 w-4" aria-hidden="true" />
                  </>
                )}
              </Button>
            </form>
          </div>

          {/* Footer link */}
          <p className="mt-6 text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{' '}
            <Link
              href="/register"
              className="font-semibold text-emerald-600 transition-colors hover:underline dark:text-emerald-400"
            >
              Sign up for free
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
