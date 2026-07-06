'use client'

import { Building2, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function OrganizationsPage() {
  const orgs = [
    { id: 1, name: 'Personal', role: 'Owner', members: 1, plan: 'Free' },
    { id: 2, name: 'Acme Corp', role: 'Admin', members: 24, plan: 'Team' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Organizations</h1>
          <p className="text-muted-foreground">Manage organizations you belong to.</p>
        </div>
        <Button>
          <Building2 className="mr-2 h-4 w-4" />
          New Organization
        </Button>
      </div>

      <div className="space-y-3">
        {orgs.map((org) => (
          <Card key={org.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-primary/10 p-2">
                    <Building2 className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-base">{org.name}</CardTitle>
                    <CardDescription>
                      <span className="inline-flex items-center gap-1">
                        <Users className="h-3 w-3" />
                        {org.members} members
                      </span>
                      {' · '}
                      {org.plan} plan
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="rounded-full bg-muted px-2 py-1 text-xs font-medium">
                    {org.role}
                  </span>
                  <Button variant="ghost" size="sm">Manage</Button>
                </div>
              </div>
            </CardHeader>
          </Card>
        ))}
      </div>
    </div>
  )
}
