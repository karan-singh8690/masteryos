'use client'

import * as React from 'react'
import { Users, Search, Ban, Check, LogOut, UserX, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { tokenStorage } from '@/lib/api-client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface AdminUser {
  id: string
  email: string
  status: string
  role: string
  mfa_enabled: boolean
  email_verified: boolean
  created_at: string
  last_login_at: string | null
  display_name: string | null
}

export default function AdminUsersPage() {
  const [users, setUsers] = React.useState<AdminUser[]>([])
  const [loading, setLoading] = React.useState(true)
  const [search, setSearch] = React.useState('')
  const [actionLoading, setActionLoading] = React.useState<string | null>(null)

  React.useEffect(() => { fetchUsers() }, [])

  async function fetchUsers(searchQuery?: string) {
    try {
      const token = tokenStorage.getAccessToken()
      const url = searchQuery
        ? `${API_URL}/api/v1/admin/users?search=${encodeURIComponent(searchQuery)}`
        : `${API_URL}/api/v1/admin/users`
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (res.ok) {
        const data = await res.json()
        setUsers(data.items || data || [])
      }
    } catch { /* empty */ }
    finally { setLoading(false) }
  }

  async function handleAction(userId: string, action: 'suspend' | 'reactivate' | 'force-logout') {
    setActionLoading(userId + action)
    try {
      const token = tokenStorage.getAccessToken()
      await fetch(`${API_URL}/api/v1/admin/users/${userId}/${action}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      fetchUsers(search)
    } catch { /* empty */ }
    finally { setActionLoading(null) }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-10 w-full" />
        {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-16" />)}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Users</h1>
        <p className="text-sm text-muted-foreground">Manage user accounts ({users.length} total)</p>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search by email..."
          className="pl-9"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && fetchUsers(search)}
        />
      </div>

      {/* Users table */}
      <Card className="rounded-2xl">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="p-4 font-medium">User</th>
                  <th className="p-4 font-medium">Role</th>
                  <th className="p-4 font-medium">Status</th>
                  <th className="p-4 font-medium">MFA</th>
                  <th className="p-4 font-medium">Joined</th>
                  <th className="p-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr><td colSpan={6} className="p-8 text-center text-muted-foreground">No users found</td></tr>
                ) : (
                  users.map((user) => (
                    <tr key={user.id} className="border-b hover:bg-muted/30">
                      <td className="p-4">
                        <div className="font-medium">{user.display_name || user.email}</div>
                        <div className="text-xs text-muted-foreground">{user.email}</div>
                      </td>
                      <td className="p-4">
                        <Badge variant="secondary" className="capitalize">{user.role}</Badge>
                      </td>
                      <td className="p-4">
                        <Badge variant={user.status === 'active' ? 'success' : 'destructive'} className="text-xs capitalize">
                          {user.status}
                        </Badge>
                      </td>
                      <td className="p-4">{user.mfa_enabled ? '✅' : '❌'}</td>
                      <td className="p-4 text-muted-foreground">
                        {new Date(user.created_at).toLocaleDateString()}
                      </td>
                      <td className="p-4">
                        <div className="flex gap-1">
                          {user.status === 'active' ? (
                            <Button
                              size="sm" variant="ghost"
                              onClick={() => handleAction(user.id, 'suspend')}
                              disabled={actionLoading === user.id + 'suspend'}
                              className="h-8 gap-1 text-amber-500"
                            >
                              {actionLoading === user.id + 'suspend' ? <Loader2 className="h-3 w-3 animate-spin" /> : <Ban className="h-3 w-3" />}
                              Suspend
                            </Button>
                          ) : (
                            <Button
                              size="sm" variant="ghost"
                              onClick={() => handleAction(user.id, 'reactivate')}
                              disabled={actionLoading === user.id + 'reactivate'}
                              className="h-8 gap-1 text-emerald-500"
                            >
                              {actionLoading === user.id + 'reactivate' ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                              Reactivate
                            </Button>
                          )}
                          <Button
                            size="sm" variant="ghost"
                            onClick={() => handleAction(user.id, 'force-logout')}
                            disabled={actionLoading === user.id + 'force-logout'}
                            className="h-8 text-red-500"
                            title="Force logout all sessions"
                          >
                            {actionLoading === user.id + 'force-logout' ? <Loader2 className="h-3 w-3 animate-spin" /> : <LogOut className="h-3 w-3" />}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
