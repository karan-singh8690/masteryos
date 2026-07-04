'use client'

import { Shield, Lock } from 'lucide-react'

import { useRoles, usePermissions } from '@/hooks/use-admin'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

export default function RBACPage() {
  const { data: roles, isLoading: rolesLoading } = useRoles()
  const { data: permissions, isLoading: permsLoading } = usePermissions()

  return (
    <div className="max-w-4xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Role & Permission Management</h1><p className="text-sm text-muted-foreground">View roles and their effective permissions</p></div>

      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><Shield className="h-4 w-4" />Roles</CardTitle><CardDescription>System roles and their permissions</CardDescription></CardHeader>
        <CardContent>
          {rolesLoading ? <Skeleton className="h-48 w-full" /> : (
            <div className="space-y-4">
              {roles?.map((role) => (
                <div key={role.name} className="rounded-lg border p-4">
                  <div className="flex items-center justify-between">
                    <div><p className="text-sm font-medium capitalize">{role.name.replace(/_/g, ' ')}</p><p className="text-xs text-muted-foreground">{role.description}</p></div>
                    <div className="flex items-center gap-2">
                      {role.is_system && <Badge variant="outline" className="text-xs"><Lock className="mr-1 h-3 w-3" />System</Badge>}
                      <Badge variant="secondary" className="text-xs">{role.user_count} users</Badge>
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {role.permissions.map((p) => <Badge key={p} variant="outline" className="text-xs font-mono">{p}</Badge>)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Permission Explorer</CardTitle><CardDescription>All available permissions grouped by category</CardDescription></CardHeader>
        <CardContent>
          {permsLoading ? <Skeleton className="h-48 w-full" /> : (
            <div className="space-y-4">
              {Object.entries(groupByCategory(permissions || [])).map(([category, perms]) => (
                <div key={category}>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">{category}</p>
                  <div className="flex flex-wrap gap-1">
                    {perms.map((p) => (
                      <div key={p.code} className="rounded border p-2 text-xs">
                        <p className="font-mono font-medium">{p.code}</p>
                        <p className="text-muted-foreground">{p.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function groupByCategory(perms: { code: string; description: string; category: string }[]): Record<string, typeof perms> {
  return perms.reduce((acc, p) => { (acc[p.category] = acc[p.category] || []).push(p); return acc }, {})
}
