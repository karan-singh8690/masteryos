'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
      const response = await authApi.login({ email, password })

      if (response.requires_mfa) {
        const params = new URLSearchParams({
          mfa_session_token: response.mfa_session_token || '',
          redirect,
        })
        router.push(`/mfa/verify?${params}`)
        return
      }

      tokenStorage.setAccessToken(response.access_token)
      if (response.refresh_token) {
        tokenStorage.setRefreshToken(response.refresh_token)
      }

      document.cookie = 'mastery-authenticated=true; path=/; SameSite=Strict; max-age=2592000'

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
    <div className="flex min-h-screen bg-[#08080A]">
      {/* ============================================================ */}
      {/* Left panel — branding / emerald gradient                     */}
      {/* ============================================================ */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-gradient-to-br from-emerald-600 via-teal-700 to-emerald-900 p-12 lg:flex">
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
            <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
            The Operating System for Learning
          </div>
          <h1 className="text-4xl font-bold leading-[1.1] tracking-tight xl:text-5xl">
            Start your{' '}
            <span className="bg-gradient-to-r from-emerald-200 to-teal-100 bg-clip-text text-transparent">
              mastery journey
            </span>{' '}
            today.
          </h1>
          <p className="text-base leading-relaxed text-emerald-50/80 xl:text-lg">
            Join thousands of learners using adaptive practice, spaced repetition, and AI-driven
            insights to actually retain what they study.
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

          {/* Social proof */}
          <div className="flex items-center gap-4 rounded-2xl bg-white/5 p-4 ring-1 ring-inset ring-white/10 backdrop-blur-sm">
            <div className="flex -space-x-2">
              {['A', 'K', 'M', 'S'].map((initial, i) => (
                <div
                  key={i}
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-emerald-300 to-teal-400 text-xs font-bold text-emerald-900 ring-2 ring-emerald-700"
                >
                  {initial}
                </div>
              ))}
            </div>
            <div className="text-sm">
              <p className="font-semibold text-white">10,000+ learners</p>
              <p className="text-emerald-50/70">mastering daily</p>
            </div>
          </div>
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
      </div>

      {/* ============================================================ */}
      {/* Right panel — login form                                     */}
      {/* ============================================================ */}
      <div className="relative flex flex-1 items-center justify-center overflow-hidden px-4 py-10 sm:px-6 lg:px-12">
        {/* Subtle glow background */}
        <div className="pointer-events-none absolute inset-0 glow-emerald opacity-30" />

        <div className="relative w-full max-w-md">
          {/* Mobile brand */}
          <div className="mb-8 flex items-center justify-center gap-2.5 lg:hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-sm">
              <img src="/brand/logo-mark.svg" alt="" className="h-6 w-6" />
            </div>
            <span className="text-lg font-bold tracking-tight text-white">MasteryOS</span>
          </div>

          {/* Heading */}
          <div className="space-y-2">
            <h2 className="text-3xl font-bold tracking-tight text-white">Welcome back</h2>
            <p className="text-sm text-zinc-400">
              Sign in to continue your mastery journey
            </p>
          </div>

          {/* Card */}
          <div className="mt-8 glass-card rounded-2xl p-6 sm:p-8">
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium text-zinc-300">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="border-white/10 bg-white/5 text-white placeholder:text-zinc-600 focus:border-emerald-500/50 focus:ring-emerald-500/20"
                  autoComplete="email"
                  required
                  autoFocus
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-sm font-medium text-zinc-300">Password</Label>
                  <Link href="/forgot-password" className="text-xs font-medium text-emerald-400 hover:text-emerald-300 transition-colors">
                    Forgot?
                  </Link>
                </div>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="border-white/10 bg-white/5 text-white placeholder:text-zinc-600 focus:border-emerald-500/50 focus:ring-emerald-500/20"
                  autoComplete="current-password"
                  required
                />
              </div>

              <Button
                type="submit"
                className="btn-glow w-full gradient-emerald font-semibold text-black shadow-lg shadow-emerald-500/30 hover:shadow-emerald-500/50"
                disabled={loading}
              >
                {loading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <>
                    Sign In
                    <ArrowRight className="ml-1 h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            {/* Divider */}
            <div className="my-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-white/10" />
              <span className="text-xs text-zinc-600">OR</span>
              <div className="h-px flex-1 bg-white/10" />
            </div>

            <Link href="/register">
              <Button variant="outline" className="w-full border-white/20 bg-transparent text-white hover:bg-white/10">
                Create new account
              </Button>
            </Link>
          </div>

          {/* Footer link */}
          <p className="mt-6 text-center text-sm text-zinc-500">
            Don&apos;t have an account?{' '}
            <Link
              href="/register"
              className="font-semibold text-emerald-400 transition-colors hover:text-emerald-300"
            >
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
