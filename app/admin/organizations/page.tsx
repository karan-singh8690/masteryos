'use client'

import * as React from 'react'
import { Building2, Loader2 } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { tokenStorage } from '@/lib/api-client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Org {
  id: string
  name: string
  slug: string
  plan: string
  seats: number
  status: string
  created_at: string | null
}

export default function OrganizationsPage() {
  const [orgs, setOrgs] = React.useState<Org[]>([])
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => { fetchOrgs() }, [])

  async function fetchOrgs() {
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/admin/organizations`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setOrgs(data.items || data || [])
      }
    } catch { /* empty */ }
    finally { setLoading(false) }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-20" />)}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Organizations</h1>
        <p className="text-sm text-muted-foreground">Manage customer organizations ({orgs.length} total)</p>
      </div>

      {orgs.length === 0 ? (
        <Card className="rounded-2xl">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Building2 className="h-10 w-10 text-muted-foreground" />
            <p className="mt-4 text-sm text-muted-foreground">No organizations yet</p>
            <p className="text-xs text-muted-foreground">Organizations are created when users subscribe to Team plan</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {orgs.map((org) => (
            <Card key={org.id} className="rounded-2xl">
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-xl bg-emerald-500/10 p-2.5">
                    <Building2 className="h-5 w-5 text-emerald-500" />
                  </div>
                  <div>
                    <p className="font-medium">{org.name}</p>
                    <p className="text-xs text-muted-foreground">{org.slug} · {org.seats} seats</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="capitalize">{org.plan}</Badge>
                  <Badge variant={org.status === 'active' ? 'success' : 'destructive'} className="text-xs capitalize">{org.status}</Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
