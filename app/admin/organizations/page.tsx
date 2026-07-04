'use client'

import { Building2, Archive, Ban } from 'lucide-react'
import { toast } from 'sonner'

import { useOrganizations, useSuspendOrganization, useArchiveOrganization } from '@/hooks/use-admin'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'

export default function AdminOrganizationsPage() {
  const { data: orgs, isLoading } = useOrganizations()
  const suspendMutation = useSuspendOrganization()
  const archiveMutation = useArchiveOrganization()

  if (isLoading) return <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}</div>

  return (
    <div className="max-w-4xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Organizations</h1><p className="text-sm text-muted-foreground">Manage organizations</p></div>
      {!orgs || orgs.length === 0 ? (
        <EmptyState icon={Building2} title="No organizations" description="No organizations have been created yet." />
      ) : (
        <div className="space-y-2">
          {orgs.map((org) => (
            <Card key={org.id} hover>
              <CardContent className="flex items-center justify-between p-4">
                <div><p className="text-sm font-medium">{org.name}</p><p className="text-xs text-muted-foreground">{org.slug} • {org.member_count} members • {org.subject_count} subjects</p></div>
                <div className="flex items-center gap-2">
                  <Badge variant={org.status === 'active' ? 'success' : org.status === 'suspended' ? 'destructive' : 'secondary'} className="capitalize">{org.status}</Badge>
                  {org.status === 'active' && (
                    <Button size="sm" variant="ghost" onClick={() => suspendMutation.mutateAsync(org.id).then(() => toast.success('Suspended')).catch(() => toast.error('Failed'))} loading={suspendMutation.isPending}>
                      <Ban className="h-4 w-4 text-destructive" />
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" onClick={() => archiveMutation.mutateAsync(org.id).then(() => toast.success('Archived')).catch(() => toast.error('Failed'))} loading={archiveMutation.isPending}>
                    <Archive className="h-4 w-4" />
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
