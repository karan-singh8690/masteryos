'use client'

import * as React from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Shield, Clock, Activity, UserX } from 'lucide-react'
import { toast } from 'sonner'

import { useAdminUser, useSuspendUser, useReactivateUser, useForceLogout, useAnonymizeUser } from '@/hooks/use-admin'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { formatDateTime, formatRelativeTime } from '@/lib/format'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog'

export default function AdminUserDetailPage() {
  const params = useParams()
  const userId = params.userId as string
  const { data: user, isLoading } = useAdminUser(userId)
  const suspendMutation = useSuspendUser()
  const reactivateMutation = useReactivateUser()
  const forceLogoutMutation = useForceLogout()
  const anonymizeMutation = useAnonymizeUser()
  const [showAnonymize, setShowAnonymize] = React.useState(false)

  if (isLoading) {
    return <div className="max-w-3xl space-y-6"><Skeleton className="h-8 w-32" /><Skeleton className="h-64 w-full" /></div>
  }

  if (!user) return <p className="text-sm text-muted-foreground">User not found</p>

  return (
    <div className="max-w-3xl space-y-6">
      <div><Link href="/admin/users" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-3 w-3" /> Back to users</Link></div>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <CardTitle className="text-xl">{user.display_name}</CardTitle>
              <CardDescription>{user.email}</CardDescription>
              <div className="flex flex-wrap gap-2 pt-2">
                <Badge variant={user.status === 'active' ? 'success' : user.status === 'suspended' ? 'destructive' : 'warning'} className="capitalize">{user.status.replace(/_/g, ' ')}</Badge>
                {user.mfa_enabled && <Badge variant="outline"><Shield className="mr-1 h-3 w-3" />MFA</Badge>}
                {user.roles.map((r) => <Badge key={r} variant="secondary">{r}</Badge>)}
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {user.status === 'active' ? (
              <Button variant="destructive" onClick={() => suspendMutation.mutateAsync({ id: userId, reason: 'Admin action' }).then(() => toast.success('User suspended')).catch(() => toast.error('Failed'))} loading={suspendMutation.isPending}>
                <UserX className="mr-2 h-4 w-4" />Suspend
              </Button>
            ) : user.status === 'suspended' ? (
              <Button onClick={() => reactivateMutation.mutateAsync(userId).then(() => toast.success('User reactivated')).catch(() => toast.error('Failed'))} loading={reactivateMutation.isPending}>
                Reactivate
              </Button>
            ) : null}
            <Button variant="outline" onClick={() => forceLogoutMutation.mutateAsync(userId).then(() => toast.success('User logged out')).catch(() => toast.error('Failed'))} loading={forceLogoutMutation.isPending}>
              Force Logout
            </Button>
            <Button variant="destructive" onClick={() => setShowAnonymize(true)}>GDPR Anonymize</Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Clock className="h-4 w-4" />Login History</CardTitle></CardHeader>
          <CardContent>
            {user.login_history.length === 0 ? <p className="text-sm text-muted-foreground">No login history</p> : (
              <ul className="space-y-2">{user.login_history.slice(0, 5).map((h) => (
                <li key={h.id} className="flex items-center justify-between text-sm">
                  <span className={h.success ? 'text-success' : 'text-destructive'}>{h.success ? '✓' : '✗'} {h.ip_address || 'Unknown IP'}</span>
                  <span className="text-xs text-muted-foreground">{formatRelativeTime(h.created_at)}</span>
                </li>
              ))}</ul>
            )}
          </CardContent>
        </Card>
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Activity className="h-4 w-4" />Active Sessions</CardTitle></CardHeader>
          <CardContent>
            {user.sessions.filter((s) => !s.revoked_at).length === 0 ? <p className="text-sm text-muted-foreground">No active sessions</p> : (
              <ul className="space-y-2">{user.sessions.filter((s) => !s.revoked_at).slice(0, 5).map((s) => (
                <li key={s.id} className="text-sm">
                  <span>{s.user_agent || 'Unknown device'}</span>
                  <span className="ml-2 text-xs text-muted-foreground">{s.last_ip}</span>
                </li>
              ))}</ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card><CardHeader><CardTitle className="text-base">Audit History</CardTitle></CardHeader>
        <CardContent>
          {user.audit_logs.length === 0 ? <p className="text-sm text-muted-foreground">No audit entries</p> : (
            <ul className="space-y-1">{user.audit_logs.slice(0, 10).map((log) => (
              <li key={log.id} className="flex items-center justify-between text-sm border-b pb-1">
                <span><Badge variant={log.success ? 'success' : 'destructive'} className="mr-2 text-xs">{log.action}</Badge></span>
                <span className="text-xs text-muted-foreground">{formatDateTime(log.created_at)}</span>
              </li>
            ))}</ul>
          )}
        </CardContent>
      </Card>

      <Dialog open={showAnonymize} onOpenChange={setShowAnonymize}>
        <DialogContent>
          <DialogHeader><DialogTitle>Anonymize User (GDPR)</DialogTitle>
            <DialogDescription>This will permanently scrub all PII. This cannot be undone.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAnonymize(false)}>Cancel</Button>
            <Button variant="destructive" loading={anonymizeMutation.isPending} onClick={async () => { try { await anonymizeMutation.mutateAsync(userId); toast.success('User anonymized'); setShowAnonymize(false) } catch { toast.error('Failed') } }}>Anonymize</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
