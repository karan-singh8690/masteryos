'use client'

import * as React from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Mail, Lock, User as UserIcon, ArrowRight, TrendingUp, Sparkles, Shield, BarChart3, CheckCircle2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input, PasswordInput } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/forms/form'
import { PasswordStrengthMeter } from '@/components/forms/password-strength-meter'
import { authApi, ApiError, tokenStorage } from '@/lib/api-client'
import { registerSchema, type RegisterFormData } from '@/lib/validations'
import { ROUTES } from '@/lib/constants'
import { toast } from 'sonner'

export default function RegisterPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [error, setError] = React.useState<string | null>(null)
  const [password, setPassword] = React.useState('')

  const redirect = searchParams.get('redirect') || ROUTES.DASHBOARD
  const inviteToken = searchParams.get('invite_token') || ''

  const form = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema) as any,
    defaultValues: {
      email: '',
      password: '',
      confirmPassword: '',
      displayName: '',
      timezone: 'UTC',
      locale: 'en-US',
      acceptTerms: false,
    },
  })

  const onSubmit = async (data: RegisterFormData) => {
    setError(null)
    try {
      const response = await authApi.register({
        email: data.email,
        password: data.password,
        display_name: data.displayName,
        invite_token: inviteToken || undefined,
      })
      tokenStorage.setAccessToken(response.access_token)
      if (response.refresh_token) {
        tokenStorage.setRefreshToken(response.refresh_token)
      }
      // Set auth cookie for middleware
      document.cookie = 'mastery-authenticated=true; path=/; SameSite=Strict; max-age=2592000'
      // Don't call setUser with bare User — auth provider will fetch CurrentUser via useQuery
      toast.success('Account created! Welcome to MasteryOS.')
      router.push(ROUTES.DASHBOARD)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.code === 'EMAIL_ALREADY_REGISTERED') {
          setError('An account with this email already exists.')
        } else if (err.fieldErrors) {
          for (const [field, messages] of Object.entries(err.fieldErrors)) {
            if (messages.length > 0) {
              form.setError(field as keyof RegisterFormData, {
                type: 'server',
                message: messages[0]!,
              })
            }
          }
        } else {
          setError(err.message)
        }
      } else {
        setError('An unexpected error occurred. Please try again.')
      }
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
        className="relative hidden overflow-hidden bg-[#08080A] p-10 text-white lg:flex lg:w-1/2 lg:flex-col lg:justify-between xl:p-14"
        aria-label="MasteryOS branding"
      >
        {/* Glow orbs */}
        <div className="pointer-events-none absolute -left-32 top-1/4 h-96 w-96 rounded-full bg-emerald-500/15 blur-3xl animate-glow-pulse" aria-hidden="true" />
        <div className="pointer-events-none absolute -right-20 bottom-1/4 h-80 w-80 rounded-full bg-teal-500/10 blur-3xl animate-glow-pulse" style={{ animationDelay: '2s' }} aria-hidden="true" />
        {/* Decorative dot grid */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.08]"
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
      </aside>

      {/* ============================================================ */}
      {/* Right panel — registration form                              */}
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
            <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">Create your account</h2>
            <p className="text-sm text-muted-foreground">
              Free to start. No credit card required.
            </p>
          </div>

          {/* Card */}
          <div className="glass-card mt-8 rounded-2xl p-6 sm:p-8">
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-medium">Email</FormLabel>
                      <FormControl>
                        <Input
                          type="email"
                          placeholder="you@example.com"
                          leftIcon={<Mail className="h-4 w-4" />}
                          autoComplete="email"
                          autoFocus
                          aria-required="true"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="displayName"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-medium">Display name</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Your name"
                          leftIcon={<UserIcon className="h-4 w-4" />}
                          autoComplete="name"
                          aria-required="true"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-medium">Password</FormLabel>
                      <FormControl>
                        <PasswordInput
                          placeholder="Create a strong password"
                          leftIcon={<Lock className="h-4 w-4" />}
                          autoComplete="new-password"
                          aria-required="true"
                          {...field}
                          onChange={(e) => {
                            field.onChange(e)
                            setPassword(e.target.value)
                          }}
                        />
                      </FormControl>
                      <FormMessage />
                      <PasswordStrengthMeter password={password} />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="confirmPassword"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-medium">Confirm password</FormLabel>
                      <FormControl>
                        <PasswordInput
                          placeholder="Re-enter your password"
                          leftIcon={<Lock className="h-4 w-4" />}
                          autoComplete="new-password"
                          aria-required="true"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="acceptTerms"
                  render={({ field }) => (
                    <FormItem className="pt-1">
                      <div className="flex items-start gap-2.5">
                        <Checkbox
                          id="acceptTerms"
                          checked={field.value}
                          onCheckedChange={field.onChange}
                          className="mt-0.5"
                        />
                        <label htmlFor="acceptTerms" className="text-sm text-muted-foreground">
                          I agree to the{' '}
                          <Link
                            href="/terms"
                            className="font-medium text-emerald-600 hover:underline dark:text-emerald-400"
                          >
                            Terms of Service
                          </Link>{' '}
                          and{' '}
                          <Link
                            href="/privacy"
                            className="font-medium text-emerald-600 hover:underline dark:text-emerald-400"
                          >
                            Privacy Policy
                          </Link>
                          .
                        </label>
                      </div>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <Button
                  type="submit"
                  className="btn-glow w-full gradient-emerald border-0 text-white shadow-lg shadow-emerald-500/30 transition-all hover:opacity-90 hover:shadow-emerald-500/50"
                  loading={form.formState.isSubmitting}
                  disabled={form.formState.isSubmitting}
                >
                  {!form.formState.isSubmitting && (
                    <>
                      Create account
                      <ArrowRight className="ml-1 h-4 w-4" aria-hidden="true" />
                    </>
                  )}
                </Button>

                {/* Trust row */}
                <div className="flex items-center justify-center gap-4 pt-2 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" aria-hidden="true" />
                    Free forever plan
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" aria-hidden="true" />
                    No credit card
                  </span>
                </div>
              </form>
            </Form>
          </div>

          {/* Footer link */}
          <p className="mt-6 text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link
              href={ROUTES.LOGIN}
              className="font-semibold text-emerald-600 transition-colors hover:underline dark:text-emerald-400"
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
