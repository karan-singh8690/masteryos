'use client'

import { Mail, Clock, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function InvitationsPage() {
  const invitations = [
    { id: 1, email: 'colleague@example.com', sentAt: '2 hours ago', status: 'pending' },
    { id: 2, email: 'student@example.com', sentAt: '1 day ago', status: 'accepted' },
    { id: 3, email: 'mentor@example.com', sentAt: '3 days ago', status: 'expired' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Invitations</h1>
          <p className="text-muted-foreground">Manage team invitations.</p>
        </div>
        <Button>
          <Mail className="mr-2 h-4 w-4" />
          Invite Member
        </Button>
      </div>

      <div className="space-y-3">
        {invitations.map((inv) => (
          <Card key={inv.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Mail className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <CardTitle className="text-base">{inv.email}</CardTitle>
                    <CardDescription className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Sent {inv.sentAt}
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {inv.status === 'accepted' ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-green-500/10 px-2 py-1 text-xs font-medium text-green-600">
                      <CheckCircle className="h-3 w-3" />
                      Accepted
                    </span>
                  ) : inv.status === 'expired' ? (
                    <span className="rounded-full bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
                      Expired
                    </span>
                  ) : (
                    <span className="rounded-full bg-yellow-500/10 px-2 py-1 text-xs font-medium text-yellow-600">
                      Pending
                    </span>
                  )}
                  {inv.status === 'pending' && (
                    <Button variant="ghost" size="sm">Resend</Button>
                  )}
                </div>
              </div>
            </CardHeader>
          </Card>
        ))}
      </div>
    </div>
  )
}
