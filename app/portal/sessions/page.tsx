'use client'

import { Monitor, Smartphone, Tablet } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function SessionsPage() {
  const sessions = [
    { id: 1, device: 'Chrome on macOS', ip: '192.168.1.1', lastActive: '2 minutes ago', current: true },
    { id: 2, device: 'Safari on iPhone', ip: '10.0.0.42', lastActive: '1 hour ago', current: false },
    { id: 3, device: 'Firefox on Linux', ip: '172.16.0.5', lastActive: '3 days ago', current: false },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Active Sessions</h1>
        <p className="text-muted-foreground">Manage devices logged into your account.</p>
      </div>

      <div className="space-y-3">
        {sessions.map((session) => (
          <Card key={session.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {session.device.includes('iPhone') ? (
                    <Smartphone className="h-5 w-5 text-muted-foreground" />
                  ) : session.device.includes('Tablet') ? (
                    <Tablet className="h-5 w-5 text-muted-foreground" />
                  ) : (
                    <Monitor className="h-5 w-5 text-muted-foreground" />
                  )}
                  <div>
                    <CardTitle className="text-base">{session.device}</CardTitle>
                    <CardDescription>{session.ip} · {session.lastActive}</CardDescription>
                  </div>
                </div>
                {session.current ? (
                  <span className="rounded-full bg-green-500/10 px-2 py-1 text-xs font-medium text-green-600">
                    Current Session
                  </span>
                ) : (
                  <button className="text-sm text-destructive hover:underline">
                    Revoke
                  </button>
                )}
              </div>
            </CardHeader>
          </Card>
        ))}
      </div>

      <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4">
        <h3 className="font-semibold text-destructive">Revoke All Sessions</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Sign out of all devices except this one.
        </p>
        <button className="mt-3 rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:bg-destructive/90">
          Revoke All Other Sessions
        </button>
      </div>
    </div>
  )
}
