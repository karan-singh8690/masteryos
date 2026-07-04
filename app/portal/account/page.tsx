'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Shield, Mail, Lock } from 'lucide-react'

export default function AccountPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-3xl font-bold">Account Settings</h1>
      <Card>
        <CardHeader><CardTitle>Profile</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div><Label htmlFor="name">Display Name</Label><Input id="name" defaultValue="Jane Developer" /></div>
          <div><Label htmlFor="email">Email</Label><Input id="email" type="email" defaultValue="jane@example.com" /></div>
          <div><Label htmlFor="timezone">Timezone</Label><Input id="timezone" defaultValue="UTC" /></div>
          <Button>Save Changes</Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Lock className="h-5 w-5" /> Password</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div><Label htmlFor="current">Current Password</Label><Input id="current" type="password" /></div>
          <div><Label htmlFor="new">New Password</Label><Input id="new" type="password" /></div>
          <Button>Change Password</Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><Shield className="h-5 w-5" /> Two-Factor Authentication</CardTitle></CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-muted-foreground">Add an extra layer of security to your account.</p>
          <Button variant="outline">Enable MFA</Button>
        </CardContent>
      </Card>
    </div>
  )
}
