'use client'

import * as React from 'react'
import { Mail, Send, Copy, Check, Loader2, UserPlus, Clock, Inbox } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { tokenStorage } from '@/lib/api-client'
import { cn } from '@/lib/cn'

interface Invite {
  id: string
  email: string
  invite_token: string
  expires_at: string
  used_at: string | null
  created_at: string
}

type InviteStatus = 'pending' | 'used' | 'expired'

function getInviteStatus(invite: Invite): InviteStatus {
  if (invite.used_at) return 'used'
  if (new Date(invite.expires_at).getTime() < Date.now()) return 'expired'
  return 'pending'
}

const STATUS_STYLES: Record<InviteStatus, { badge: string; variant: 'warning' | 'success' | 'secondary'; label: string }> = {
  pending: { badge: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 ring-1 ring-amber-500/20', variant: 'warning', label: 'Pending' },
  used: { badge: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 ring-1 ring-emerald-500/20', variant: 'success', label: 'Used' },
  expired: { badge: 'bg-zinc-500/10 text-zinc-500 dark:text-zinc-400 ring-1 ring-zinc-500/20', variant: 'secondary', label: 'Expired' },
}

export default function InvitesPage() {
  const [email, setEmail] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState('')
  const [success, setSuccess] = React.useState('')
  const [invites, setInvites] = React.useState<Invite[]>([])
  const [copiedId, setCopiedId] = React.useState<string | null>(null)
  const [listLoading, setListLoading] = React.useState(true)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Fetch existing invites
  React.useEffect(() => {
    fetchInvites()
  }, [])

  async function fetchInvites() {
    setListLoading(true)
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/admin/beta/invites`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setInvites(Array.isArray(data) ? data : (data.invites || []))
      }
    } catch {
      // Ignore — invites will just be empty
    } finally {
      setListLoading(false)
    }
  }

  async function handleCreateInvite(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/admin/beta/invites`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ email }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail?.message || data.detail || 'Failed to create invite')
      }
      setSuccess(`Invite created! Link: ${window.location.origin}/register?invite_token=${data.invite_token}&email=${encodeURIComponent(email)}`)
      setEmail('')
      fetchInvites()
    } catch (err: any) {
      setError(err.message || 'Failed to create invite')
    } finally {
      setLoading(false)
    }
  }

  function copyInviteUrl(invite: Invite) {
    const url = `${window.location.origin}/register?invite_token=${invite.invite_token}&email=${encodeURIComponent(invite.email)}`
    navigator.clipboard.writeText(url)
    setCopiedId(invite.id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  // Summary counts
  const counts = React.useMemo(() => {
    return invites.reduce(
      (acc, inv) => {
        acc[getInviteStatus(inv)] += 1
        return acc
      },
      { pending: 0, used: 0, expired: 0 } as Record<InviteStatus, number>,
    )
  }, [invites])

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Beta Invites</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Send invite links to users for closed beta registration.
        </p>
      </div>

      {/* Summary chips */}
      <div className="grid grid-cols-3 gap-3 sm:max-w-md">
        <SummaryChip label="Pending" value={counts.pending} tone="amber" />
        <SummaryChip label="Used" value={counts.used} tone="emerald" />
        <SummaryChip label="Expired" value={counts.expired} tone="zinc" />
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Create Invite */}
        <Card className="overflow-hidden rounded-2xl lg:col-span-2">
          <CardHeader className="border-b border-border/60 bg-muted/30 px-6 py-5">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-500">
                <UserPlus className="h-5 w-5" aria-hidden="true" />
              </span>
              <div>
                <CardTitle className="text-base">Create New Invite</CardTitle>
                <CardDescription className="mt-0.5">
                  Send a single-use registration link.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6">
            <form onSubmit={handleCreateInvite} className="space-y-4">
              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              {success && (
                <Alert className="border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
                  <Check className="h-4 w-4 text-emerald-500" aria-hidden="true" />
                  <AlertDescription className="break-all">{success}</AlertDescription>
                </Alert>
              )}
              <div className="space-y-2">
                <Label htmlFor="email" className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Email Address
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="friend@example.com"
                    className="h-11 rounded-xl border-border/60 bg-background pl-9"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>
              <Button
                type="submit"
                disabled={loading}
                className="h-11 w-full rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-600 text-white shadow-lg shadow-emerald-500/20 transition-all hover:from-emerald-600 hover:to-emerald-700 hover:shadow-emerald-500/30 disabled:opacity-60"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sending…
                  </>
                ) : (
                  <>
                    <Send className="mr-2 h-4 w-4" />
                    Send Invite
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Existing Invites */}
        <Card className="overflow-hidden rounded-2xl lg:col-span-3">
          <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 bg-muted/30 px-6 py-5">
            <div>
              <CardTitle className="text-base">Invitations</CardTitle>
              <CardDescription className="mt-0.5">
                {invites.length} total · click copy to share a link
              </CardDescription>
            </div>
            <Badge variant="secondary" className="font-mono">
              {invites.length}
            </Badge>
          </CardHeader>
          <CardContent className="p-0">
            {listLoading ? (
              <div className="space-y-2 p-5">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-16 w-full rounded-xl" />
                ))}
              </div>
            ) : invites.length === 0 ? (
              <div className="flex flex-col items-center justify-center px-6 py-16 text-center">
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-muted">
                  <Inbox className="h-6 w-6 text-muted-foreground" aria-hidden="true" />
                </div>
                <p className="text-sm font-medium text-foreground">No invites yet</p>
                <p className="mt-1 max-w-xs text-xs text-muted-foreground">
                  Create one using the form to the left.
                </p>
              </div>
            ) : (
              <ul className="divide-y divide-border/40">
                {invites.map((invite) => {
                  const status = getInviteStatus(invite)
                  const style = STATUS_STYLES[status]
                  const canCopy = status === 'pending'
                  return (
                    <li
                      key={invite.id}
                      className="flex flex-col gap-3 px-5 py-4 transition-colors hover:bg-muted/20 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <span
                          className={cn(
                            'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-xs font-bold',
                            style.badge,
                          )}
                          aria-hidden="true"
                        >
                          {invite.email.charAt(0).toUpperCase()}
                        </span>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-foreground">
                            {invite.email}
                          </p>
                          <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" aria-hidden="true" />
                            Expires {new Date(invite.expires_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 pl-12 sm:pl-0">
                        <span
                          className={cn(
                            'inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold',
                            style.badge,
                          )}
                        >
                          {style.label}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => copyInviteUrl(invite)}
                          disabled={!canCopy}
                          className={cn(
                            'h-8 rounded-lg border-border/60 text-xs',
                            copiedId === invite.id &&
                              'border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
                          )}
                        >
                          {copiedId === invite.id ? (
                            <>
                              <Check className="mr-1.5 h-3.5 w-3.5" />
                              Copied
                            </>
                          ) : (
                            <>
                              <Copy className="mr-1.5 h-3.5 w-3.5" />
                              Copy Link
                            </>
                          )}
                        </Button>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function SummaryChip({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: 'amber' | 'emerald' | 'zinc'
}) {
  const toneClasses = {
    amber: 'text-amber-600 dark:text-amber-400',
    emerald: 'text-emerald-600 dark:text-emerald-400',
    zinc: 'text-zinc-500 dark:text-zinc-400',
  }[tone]
  return (
    <div className="rounded-xl border border-border/60 bg-card px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      <p className={cn('mt-1 text-2xl font-bold tracking-tight', toneClasses)}>{value}</p>
    </div>
  )
}
