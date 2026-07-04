'use client'

import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Mail, Lock } from 'lucide-react'
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

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <img src="/brand/logo-mark.svg" alt="MasteryOS" className="mx-auto mb-4 h-12 w-12" />
          <CardTitle className="text-2xl">Welcome back</CardTitle>
          <CardDescription>Sign in to your MasteryOS account</CardDescription>
        </CardHeader>
        <CardContent>
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
                <Input id="email" type="email" placeholder="you@example.com" className="pl-9" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link href="/forgot-password" className="text-xs text-muted-foreground hover:text-primary">Forgot password?</Link>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input id="password" type="password" placeholder="••••••••" className="pl-9" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </div>
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Sign In
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              Don&apos;t have an account?{' '}
              <Link href="/register" className="font-medium text-primary hover:underline">Sign up</Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
