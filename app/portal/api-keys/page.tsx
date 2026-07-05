'use client'

import * as React from 'react'
import { Key, Plus, Copy, Check, Trash2, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { tokenStorage } from '@/lib/api-client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ApiKey {
  id: string
  name: string
  key_prefix: string
  scopes: string[]
  last_used_at: string | null
  expires_at: string | null
  is_active: boolean
  created_at: string
}

export default function ApiKeysPage() {
  const [keys, setKeys] = React.useState<ApiKey[]>([])
  const [loading, setLoading] = React.useState(true)
  const [creating, setCreating] = React.useState(false)
  const [newKeyName, setNewKeyName] = React.useState('')
  const [newKeyScopes, setNewKeyScopes] = React.useState('')
  const [createdKey, setCreatedKey] = React.useState<string | null>(null)
  const [error, setError] = React.useState('')
  const [copied, setCopied] = React.useState(false)

  React.useEffect(() => {
    fetchKeys()
  }, [])

  async function fetchKeys() {
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/billing/api-keys`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) setKeys(await res.json())
    } catch {
      // Silent fail
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setCreating(true)
    setError('')
    try {
      const token = tokenStorage.getAccessToken()
      const scopes = newKeyScopes.split(',').map(s => s.trim()).filter(Boolean)
      const res = await fetch(`${API_URL}/api/v1/billing/api-keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name: newKeyName, scopes }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail?.message || 'Failed to create key')

      setCreatedKey(data.key)
      setNewKeyName('')
      setNewKeyScopes('')
      fetchKeys()
    } catch (err: any) {
      setError(err.message || 'Failed to create API key')
    } finally {
      setCreating(false)
    }
  }

  async function handleRevoke(id: string) {
    try {
      const token = tokenStorage.getAccessToken()
      await fetch(`${API_URL}/api/v1/billing/api-keys/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      fetchKeys()
    } catch {
      setError('Failed to revoke key')
    }
  }

  function copyKey() {
    if (createdKey) {
      navigator.clipboard.writeText(createdKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">API Keys</h1>
        <p className="text-sm text-muted-foreground">Manage API keys for programmatic access</p>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Created key banner */}
      {createdKey && (
        <Alert className="border-emerald-500/30 bg-emerald-500/5">
          <AlertDescription>
            <div className="space-y-2">
              <p className="font-semibold text-emerald-500">API Key Created — Copy it now (shown only once):</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 rounded bg-muted p-2 text-xs break-all">{createdKey}</code>
                <Button size="sm" variant="outline" onClick={copyKey} className="gap-1.5">
                  {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                  {copied ? 'Copied!' : 'Copy'}
                </Button>
              </div>
              <Button size="sm" variant="ghost" onClick={() => setCreatedKey(null)}>Dismiss</Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Create new key */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5 text-emerald-500" />
            Create New API Key
          </CardTitle>
          <CardDescription>Generate a new key for API access</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="keyname">Key Name</Label>
              <Input
                id="keyname"
                placeholder="e.g., Production API"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="scopes">Scopes (comma-separated)</Label>
              <Input
                id="scopes"
                placeholder="read,write,admin"
                value={newKeyScopes}
                onChange={(e) => setNewKeyScopes(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">Leave empty for full access</p>
            </div>
            <Button type="submit" disabled={creating} className="gap-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-white">
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Key className="h-4 w-4" />}
              Generate Key
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Existing keys */}
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle>Active Keys ({keys.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : keys.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No API keys yet. Create one above.</p>
          ) : (
            <div className="space-y-3">
              {keys.map((key) => (
                <div key={key.id} className="flex items-center justify-between rounded-lg border p-3">
                  <div>
                    <p className="font-medium">{key.name}</p>
                    <div className="mt-1 flex items-center gap-2">
                      <code className="text-xs text-muted-foreground">{key.key_prefix}</code>
                      {key.scopes.length > 0 && (
                        <Badge variant="secondary" className="text-xs">{key.scopes.join(', ')}</Badge>
                      )}
                      <span className="text-xs text-muted-foreground">
                        · Created {new Date(key.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRevoke(key.id)}
                    className="text-red-500 hover:text-red-600 gap-1.5"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Revoke
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
