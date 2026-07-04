'use client'

import * as React from 'react'
import Link from 'next/link'
import { Search, Users, Shield, Ban, CheckCircle, LogOut, UserX } from 'lucide-react'
import { toast } from 'sonner'

import { useAdminUsers, useSuspendUser, useReactivateUser, useForceLogout, useAssignRole } from '@/hooks/use-admin'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useDebounce } from '@/hooks/use-debounce'
import { formatRelativeTime } from '@/lib/format'

const USER_ROLES = ['learner', 'instructor', 'content_editor', 'organization_admin', 'administrator', 'system_admin']

export default function AdminUsersPage() {
  const [search, setSearch] = React.useState('')
  const [statusFilter, setStatusFilter] = React.useState<string>('all')
  const debouncedSearch = useDebounce(search, 300)

  const { data: users, isLoading } = useAdminUsers({
    search: debouncedSearch || undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
  })

  const suspendMutation = useSuspendUser()
  const reactivateMutation = useReactivateUser()
  const forceLogoutMutation = useForceLogout()
  const assignRoleMutation = useAssignRole()

  const handleSuspend = async (id: string) => {
    try {
      await suspendMutation.mutateAsync({ id, reason: 'Suspended by admin' })
      toast.success('User suspended')
    } catch { toast.error('Failed to suspend user') }
  }

  const handleReactivate = async (id: string) => {
    try {
      await reactivateMutation.mutateAsync(id)
      toast.success('User reactivated')
    } catch { toast.error('Failed to reactivate user') }
  }

  const handleForceLogout = async (id: string) => {
    try {
      await forceLogoutMutation.mutateAsync(id)
      toast.success('User logged out')
    } catch { toast.error('Failed to force logout') }
  }

  const handleAssignRole = async (id: string, role: string) => {
    try {
      await assignRoleMutation.mutateAsync({ id, role })
      toast.success(`Role ${role} assigned`)
    } catch { toast.error('Failed to assign role') }
  }

  return (
    <div className="max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">User Management</h1>
        <p className="text-sm text-muted-foreground">Manage users, roles, and account status</p>
      </div>

      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input placeholder="Search users by email or name..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-10" aria-label="Search users" />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="suspended">Suspended</SelectItem>
            <SelectItem value="pending_verification">Pending</SelectItem>
            <SelectItem value="pending_deletion">Pending Deletion</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}</div>
      ) : !users || users.length === 0 ? (
        <EmptyState icon={Users} title="No users found" description="Try adjusting your search or filters." />
      ) : (
        <div className="space-y-2">
          {users.map((user) => (
            <Card key={user.id} hover>
              <CardContent className="flex items-center justify-between p-4">
                <Link href={`/admin/users/${user.id}`} className="flex-1">
                  <div className="flex items-center gap-3">
                    <div>
                      <p className="text-sm font-medium">{user.display_name}</p>
                      <p className="text-xs text-muted-foreground">{user.email}</p>
                    </div>
                  </div>
                </Link>
                <div className="flex items-center gap-2">
                  <Badge variant={user.status === 'active' ? 'success' : user.status === 'suspended' ? 'destructive' : 'warning'} className="text-xs capitalize">
                    {user.status.replace(/_/g, ' ')}
                  </Badge>
                  {user.mfa_enabled && <Badge variant="outline" className="text-xs"><Shield className="mr-1 h-3 w-3" />MFA</Badge>}
                  {user.roles.map((role) => <Badge key={role} variant="secondary" className="text-xs">{role}</Badge>)}
                  <Select onValueChange={(role) => handleAssignRole(user.id, role)}>
                    <SelectTrigger className="h-8 w-32"><SelectValue placeholder="Assign role" /></SelectTrigger>
                    <SelectContent>{USER_ROLES.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
                  </Select>
                  {user.status === 'active' ? (
                    <Button size="icon" variant="ghost" onClick={() => handleSuspend(user.id)} aria-label="Suspend user" loading={suspendMutation.isPending}>
                      <Ban className="h-4 w-4 text-destructive" />
                    </Button>
                  ) : user.status === 'suspended' ? (
                    <Button size="icon" variant="ghost" onClick={() => handleReactivate(user.id)} aria-label="Reactivate user" loading={reactivateMutation.isPending}>
                      <CheckCircle className="h-4 w-4 text-success" />
                    </Button>
                  ) : null}
                  <Button size="icon" variant="ghost" onClick={() => handleForceLogout(user.id)} aria-label="Force logout" loading={forceLogoutMutation.isPending}>
                    <LogOut className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
