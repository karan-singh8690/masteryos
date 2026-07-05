'use client'

import * as React from 'react'
import {
  Users, Search, Ban, Check, LogOut, UserX, Loader2,
  Shield, ShieldCheck, ShieldAlert, MoreHorizontal, Eye,
  UserCog, Trash2, Mail, Calendar, Clock, KeyRound, BadgeCheck,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger, DropdownMenuLabel,
  DropdownMenuSub, DropdownMenuSubTrigger, DropdownMenuSubContent,
} from '@/components/ui/dropdown-menu'
import {
  Dialog, DialogContent, DialogDescription, DialogHeader,
  DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { toast } from 'sonner'
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

interface UserDetail extends AdminUser {
  profile?: { timezone?: string | null; locale?: string | null } | null
  session_count?: number
  organizations?: unknown[]
}

const ROLES = [
  { value: 'learner', label: 'Learner' },
  { value: 'instructor', label: 'Instructor' },
  { value: 'content_editor', label: 'Content Editor' },
  { value: 'organization_admin', label: 'Org Admin' },
  { value: 'administrator', label: 'Administrator' },
  { value: 'system_admin', label: 'System Admin' },
]

function roleLabel(role: string): string {
  return ROLES.find((r) => r.value === role)?.label || role.replace(/_/g, ' ')
}

function getInitials(email: string): string {
  if (!email || typeof email !== 'string') return '?'
  const name = email.split('@')[0]
  if (!name) return '?'
  return name.slice(0, 2).toUpperCase()
}

function showToast(kind: 'success' | 'error', msg: string) {
  if (kind === 'success') {
    toast.success(msg)
  } else {
    toast.error(msg)
  }
}

export default function AdminUsersPage() {
  const [users, setUsers] = React.useState<AdminUser[]>([])
  const [loading, setLoading] = React.useState(true)
  const [search, setSearch] = React.useState('')
  const [actionLoading, setActionLoading] = React.useState<string | null>(null)
  const [detailUser, setDetailUser] = React.useState<UserDetail | null>(null)
  const [detailLoading, setDetailLoading] = React.useState(false)
  const [confirmAnonymize, setConfirmAnonymize] = React.useState<AdminUser | null>(null)

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

  async function handleAction(
    userId: string,
    action: 'suspend' | 'reactivate' | 'force-logout' | 'anonymize',
    successMsg?: string,
  ) {
    setActionLoading(userId + action)
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/admin/users/${userId}/${action}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        showToast('success', successMsg || 'Action completed')
      } else {
        const err = await res.json().catch(() => ({}))
        showToast('error', err.detail || `Failed: ${res.status}`)
      }
      fetchUsers(search)
    } catch (e) {
      showToast('error', 'Network error')
    }
    finally { setActionLoading(null) }
  }

  async function handleChangeRole(userId: string, role: string) {
    setActionLoading(userId + 'role')
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(
        `${API_URL}/api/v1/admin/users/${userId}/roles?role=${encodeURIComponent(role)}`,
        { method: 'POST', headers: { Authorization: `Bearer ${token}` } },
      )
      if (res.ok) {
        showToast('success', `Role changed to ${roleLabel(role)}`)
      } else {
        const err = await res.json().catch(() => ({}))
        showToast('error', err.detail || 'Failed to change role')
      }
      fetchUsers(search)
    } catch {
      showToast('error', 'Network error')
    }
    finally { setActionLoading(null) }
  }

  async function viewUserDetails(userId: string) {
    setDetailLoading(true)
    setDetailUser(null)
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/admin/users/${userId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setDetailUser(data)
      } else {
        showToast('error', 'Failed to load user details')
      }
    } catch {
      showToast('error', 'Network error')
    }
    finally { setDetailLoading(false) }
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Users</h1>
          <p className="text-sm text-muted-foreground">Manage user accounts ({users.length} total)</p>
        </div>
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
                <tr className="border-b text-left bg-muted/30">
                  <th className="p-4 font-medium">User</th>
                  <th className="p-4 font-medium">Role</th>
                  <th className="p-4 font-medium">Status</th>
                  <th className="p-4 font-medium">MFA</th>
                  <th className="p-4 font-medium">Joined</th>
                  <th className="p-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr><td colSpan={6} className="p-8 text-center text-muted-foreground">No users found</td></tr>
                ) : (
                  users.map((user) => {
                    const isSuspended = user.status === 'suspended'
                    const isAnonymized = user.status === 'anonymized'
                    return (
                      <tr key={user.id} className="border-b hover:bg-muted/30 transition-colors">
                        <td className="p-4">
                          <div className="flex items-center gap-3">
                            <Avatar className="h-9 w-9">
                              <AvatarFallback className="bg-gradient-to-br from-emerald-500 to-emerald-700 text-white text-xs">
                                {getInitials(user.email)}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <div className="font-medium flex items-center gap-1.5">
                                {user.display_name || user.email.split('@')[0]}
                                {user.email_verified && (
                                  <BadgeCheck className="h-3.5 w-3.5 text-emerald-500" />
                                )}
                              </div>
                              <div className="text-xs text-muted-foreground">{user.email}</div>
                            </div>
                          </div>
                        </td>
                        <td className="p-4">
                          <Badge variant="secondary" className="capitalize text-xs">
                            {roleLabel(user.role)}
                          </Badge>
                        </td>
                        <td className="p-4">
                          {user.status === 'active' ? (
                            <Badge variant="success" className="text-xs">
                              <span className="mr-1 h-1.5 w-1.5 rounded-full bg-emerald-500" />
                              Active
                            </Badge>
                          ) : isSuspended ? (
                            <Badge variant="destructive" className="text-xs">
                              <span className="mr-1 h-1.5 w-1.5 rounded-full bg-amber-500" />
                              Suspended
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="text-xs capitalize">{user.status}</Badge>
                          )}
                        </td>
                        <td className="p-4">
                          {user.mfa_enabled ? (
                            <Badge variant="success" className="text-xs gap-1">
                              <ShieldCheck className="h-3 w-3" />
                              Enabled
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="text-xs gap-1 text-muted-foreground">
                              <ShieldAlert className="h-3 w-3" />
                              Disabled
                            </Badge>
                          )}
                        </td>
                        <td className="p-4 text-muted-foreground">
                          {new Date(user.created_at).toLocaleDateString()}
                        </td>
                        <td className="p-4">
                          <div className="flex items-center justify-end gap-1">
                            {/* Quick suspend/reactivate */}
                            {!isAnonymized && (
                              <Button
                                size="sm" variant="ghost"
                                onClick={() => handleAction(
                                  user.id,
                                  isSuspended ? 'reactivate' : 'suspend',
                                  isSuspended ? 'User reactivated' : 'User suspended',
                                )}
                                disabled={actionLoading === user.id + (isSuspended ? 'reactivate' : 'suspend')}
                                className="h-8 gap-1"
                                title={isSuspended ? 'Reactivate' : 'Suspend'}
                              >
                                {actionLoading === user.id + (isSuspended ? 'reactivate' : 'suspend') ? (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : isSuspended ? (
                                  <Check className="h-3.5 w-3.5 text-emerald-500" />
                                ) : (
                                  <Ban className="h-3.5 w-3.5 text-amber-500" />
                                )}
                              </Button>
                            )}

                            {/* More actions dropdown */}
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button size="sm" variant="ghost" className="h-8 w-8 p-0">
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end" className="w-56">
                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                <DropdownMenuItem onClick={() => viewUserDetails(user.id)}>
                                  <Eye className="mr-2 h-4 w-4" />
                                  View details
                                </DropdownMenuItem>

                                <DropdownMenuSub>
                                  <DropdownMenuSubTrigger>
                                    <UserCog className="mr-2 h-4 w-4" />
                                    Change role
                                  </DropdownMenuSubTrigger>
                                  <DropdownMenuSubContent className="w-48">
                                    {ROLES.map((r) => (
                                      <DropdownMenuItem
                                        key={r.value}
                                        onClick={() => handleChangeRole(user.id, r.value)}
                                        disabled={user.role === r.value}
                                      >
                                        <span className={user.role === r.value ? 'font-semibold text-emerald-600' : ''}>
                                          {r.label}
                                        </span>
                                        {user.role === r.value && (
                                          <Check className="ml-auto h-3.5 w-3.5 text-emerald-600" />
                                        )}
                                      </DropdownMenuItem>
                                    ))}
                                  </DropdownMenuSubContent>
                                </DropdownMenuSub>

                                <DropdownMenuItem
                                  onClick={() => handleAction(user.id, 'force-logout', 'All sessions revoked')}
                                  disabled={isAnonymized}
                                >
                                  <LogOut className="mr-2 h-4 w-4" />
                                  Force logout
                                </DropdownMenuItem>

                                <DropdownMenuSeparator />

                                <DropdownMenuItem
                                  onClick={() => setConfirmAnonymize(user)}
                                  disabled={isAnonymized}
                                  className="text-red-600 focus:text-red-600"
                                >
                                  <Trash2 className="mr-2 h-4 w-4" />
                                  Anonymize (GDPR)
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* User Details Dialog */}
      <Dialog open={!!detailUser || detailLoading} onOpenChange={(o) => !o && setDetailUser(null)}>
        <DialogContent className="sm:max-w-[520px]">
          <DialogHeader>
            <DialogTitle>User details</DialogTitle>
            <DialogDescription>
              Detailed information about this user account.
            </DialogDescription>
          </DialogHeader>

          {detailLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : detailUser ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Avatar className="h-12 w-12">
                  <AvatarFallback className="bg-gradient-to-br from-emerald-500 to-emerald-700 text-white">
                    {getInitials(detailUser.email)}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <div className="font-semibold flex items-center gap-1.5">
                    {detailUser.display_name || detailUser.email.split('@')[0]}
                    {detailUser.email_verified && (
                      <BadgeCheck className="h-4 w-4 text-emerald-500" />
                    )}
                  </div>
                  <div className="text-sm text-muted-foreground">{detailUser.email}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <DetailRow icon={<BadgeCheck className="h-4 w-4" />} label="Role" value={roleLabel(detailUser.role)} />
                <DetailRow
                  icon={<Shield className="h-4 w-4" />}
                  label="MFA"
                  value={
                    detailUser.mfa_enabled
                      ? <Badge variant="success" className="text-xs">Enabled</Badge>
                      : <Badge variant="outline" className="text-xs">Disabled</Badge>
                  }
                />
                <DetailRow
                  icon={<Mail className="h-4 w-4" />}
                  label="Email"
                  value={detailUser.email_verified ? 'Verified' : 'Unverified'}
                />
                <DetailRow
                  icon={<KeyRound className="h-4 w-4" />}
                  label="Status"
                  value={<Badge variant={detailUser.status === 'active' ? 'success' : 'destructive'} className="text-xs capitalize">{detailUser.status}</Badge>}
                />
                <DetailRow
                  icon={<Calendar className="h-4 w-4" />}
                  label="Joined"
                  value={new Date(detailUser.created_at).toLocaleString()}
                />
                <DetailRow
                  icon={<Clock className="h-4 w-4" />}
                  label="Last login"
                  value={detailUser.last_login_at ? new Date(detailUser.last_login_at).toLocaleString() : 'Never'}
                />
                <DetailRow
                  icon={<Users className="h-4 w-4" />}
                  label="Sessions"
                  value={String(detailUser.session_count ?? 0)}
                />
                <DetailRow
                  icon={<UserX className="h-4 w-4" />}
                  label="Orgs"
                  value={String(detailUser.organizations?.length ?? 0)}
                />
              </div>

              {detailUser.profile && (
                <div className="rounded-lg border bg-muted/30 p-3 text-sm">
                  <div className="text-xs font-medium text-muted-foreground mb-1">Profile</div>
                  <div>Timezone: {detailUser.profile.timezone || '—'}</div>
                  <div>Locale: {detailUser.profile.locale || '—'}</div>
                </div>
              )}

              <DialogFooter className="gap-2">
                <Button
                  variant="outline" size="sm"
                  onClick={() => handleAction(detailUser.id, 'force-logout', 'All sessions revoked')}
                  disabled={actionLoading === detailUser.id + 'force-logout'}
                  className="gap-1"
                >
                  {actionLoading === detailUser.id + 'force-logout' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <LogOut className="h-3.5 w-3.5" />}
                  Force logout
                </Button>
                <Button
                  variant="outline" size="sm"
                  onClick={() => {
                    handleAction(
                      detailUser.id,
                      detailUser.status === 'suspended' ? 'reactivate' : 'suspend',
                      detailUser.status === 'suspended' ? 'User reactivated' : 'User suspended',
                    )
                  }}
                  disabled={actionLoading === detailUser.id + (detailUser.status === 'suspended' ? 'reactivate' : 'suspend')}
                  className="gap-1"
                >
                  {actionLoading === detailUser.id + (detailUser.status === 'suspended' ? 'reactivate' : 'suspend') ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : detailUser.status === 'suspended' ? (
                    <Check className="h-3.5 w-3.5 text-emerald-500" />
                  ) : (
                    <Ban className="h-3.5 w-3.5 text-amber-500" />
                  )}
                  {detailUser.status === 'suspended' ? 'Reactivate' : 'Suspend'}
                </Button>
              </DialogFooter>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      {/* Anonymize confirmation */}
      <Dialog open={!!confirmAnonymize} onOpenChange={(o) => !o && setConfirmAnonymize(null)}>
        <DialogContent className="sm:max-w-[440px]">
          <DialogHeader>
            <DialogTitle className="text-red-600">Anonymize user data?</DialogTitle>
            <DialogDescription>
              This is a <strong>GDPR-compliant irreversible action</strong>. The user&apos;s email will be
              replaced with <code className="text-xs">anonymized_&lt;id&gt;@deleted.local</code>,
              their MFA disabled, all sessions revoked, and status set to <code>anonymized</code>.
              This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {confirmAnonymize && (
            <div className="rounded-md border border-red-200 bg-red-50 dark:bg-red-950/30 p-3 text-sm">
              <div className="font-medium">{confirmAnonymize.email}</div>
              <div className="text-xs text-muted-foreground mt-0.5">
                Joined {new Date(confirmAnonymize.created_at).toLocaleDateString()} · {roleLabel(confirmAnonymize.role)}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmAnonymize(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={!confirmAnonymize || actionLoading === confirmAnonymize?.id + 'anonymize'}
              onClick={() => {
                if (!confirmAnonymize) return
                handleAction(confirmAnonymize.id, 'anonymize', 'User data anonymized')
                setConfirmAnonymize(null)
              }}
              className="gap-1"
            >
              {actionLoading === confirmAnonymize?.id + 'anonymize' ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Trash2 className="h-3.5 w-3.5" />
              )}
              Yes, anonymize
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function DetailRow({
  icon, label, value,
}: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <div className="mt-0.5 text-muted-foreground">{icon}</div>
      <div>
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="font-medium">{value}</div>
      </div>
    </div>
  )
}
