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
import { useAuth } from '@/providers/auth-provider'

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
      // Call login API directly (don't use auth-provider login which sets wrong user type)
      const response = await authApi.login({ email, password })

      // Handle MFA challenge
      if (response.requires_mfa) {
        const params = new URLSearchParams({
          mfa_session_token: response.mfa_session_token || '',
          redirect,
        })
        router.push(`/mfa/verify?${params}`)
        return
      }

      // Store tokens using tokenStorage (correct keys)
      tokenStorage.setAccessToken(response.access_token)
      if (response.refresh_token) {
        tokenStorage.setRefreshToken(response.refresh_token)
      }

      // Set auth cookie for middleware (presence check)
      document.cookie = 'mastery-authenticated=true; path=/; SameSite=Strict'

      // Fetch full CurrentUser (with roles + permissions) to set in store
      try {
        const me = await authApi.me()
        // Ensure roles and permissions are arrays (defensive)
        if (me && typeof me === 'object') {
          const safeUser = {
            ...me,
            roles: Array.isArray(me.roles) ? me.roles : [],
            permissions: Array.isArray(me.permissions) ? me.permissions : [],
          }
          setUser(safeUser as any)

          // Set role cookie for middleware admin check
          if (safeUser.roles.length > 0) {
            document.cookie = `mastery-role=${safeUser.roles[0]}; path=/; SameSite=Strict`
          }
        }
      } catch (meErr) {
        // If /users/me fails, still proceed with basic auth
        console.warn('Failed to fetch user profile:', meErr)
      }

      router.push(redirect)
    } catch (err: any) {
      if (err instanceof ApiError) {
        setError(err.message || 'Login failed')
      } else if (err instanceof Error) {
        setError(err.message || 'Login failed')
      } else {
        setError('Login failed. Please check your credentials.')
      }
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
