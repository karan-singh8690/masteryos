'use client'

import * as React from 'react'
import { Mail, Send, Copy, Check, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { tokenStorage } from '@/lib/api-client'

interface Invite {
  id: string
  email: string
  invite_token: string
  expires_at: string
  used_at: string | null
  created_at: string
}

export default function InvitesPage() {
  const [email, setEmail] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState('')
  const [success, setSuccess] = React.useState('')
  const [invites, setInvites] = React.useState<Invite[]>([])
  const [copiedId, setCopiedId] = React.useState<string | null>(null)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Fetch existing invites
  React.useEffect(() => {
    fetchInvites()
  }, [])

  async function fetchInvites() {
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

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Beta Invites</h1>
        <p className="text-muted-foreground">Send invite links to users for closed beta registration.</p>
      </div>

      {/* Create Invite */}
      <Card>
        <CardHeader>
          <CardTitle>Create New Invite</CardTitle>
          <CardDescription>Enter the email of the person you want to invite.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreateInvite} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            {success && (
              <Alert>
                <AlertDescription className="break-all">{success}</AlertDescription>
              </Alert>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">Email Address</Label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="friend@example.com"
                    className="pl-9"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                <Button type="submit" disabled={loading}>
                  {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
                  Send Invite
                </Button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Existing Invites */}
      <Card>
        <CardHeader>
          <CardTitle>Existing Invites ({invites.length})</CardTitle>
          <CardDescription>Click copy to get the registration link.</CardDescription>
        </CardHeader>
        <CardContent>
          {invites.length === 0 ? (
            <p className="text-sm text-muted-foreground">No invites yet. Create one above.</p>
          ) : (
            <div className="space-y-2">
              {invites.map((invite) => (
                <div key={invite.id} className="flex items-center justify-between rounded-lg border p-3">
                  <div>
                    <p className="font-medium">{invite.email}</p>
                    <p className="text-xs text-muted-foreground">
                      {invite.used_at ? '✅ Used' : '⏳ Pending'} · Expires: {new Date(invite.expires_at).toLocaleDateString()}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyInviteUrl(invite)}
                    disabled={!!invite.used_at}
                  >
                    {copiedId === invite.id ? (
                      <><Check className="mr-2 h-4 w-4" /> Copied!</>
                    ) : (
                      <><Copy className="mr-2 h-4 w-4" /> Copy Link</>
                    )}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
