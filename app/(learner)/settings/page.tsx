'use client'

import * as React from 'react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { useTheme } from 'next-themes'

export default function SettingsPage() {
  return <SettingsContent />
}

function SettingsContent() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    setMounted(true)
  }, [])

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Manage your application preferences</p>
      </div>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>Customize how Mastery Engine looks</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Theme</Label>
            {mounted && (
              <Select value={theme} onValueChange={setTheme}>
                <SelectTrigger>
                  <SelectValue placeholder="Select theme" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="dark">Dark</SelectItem>
                  <SelectItem value="system">System</SelectItem>
                </SelectContent>
              </Select>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Notification preferences */}
      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
          <CardDescription>Choose what notifications you receive</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="email-notif">Email notifications</Label>
              <p className="text-xs text-muted-foreground">Receive notifications via email</p>
            </div>
            <Switch id="email-notif" defaultChecked />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="inapp-notif">In-app notifications</Label>
              <p className="text-xs text-muted-foreground">Show notifications in the app</p>
            </div>
            <Switch id="inapp-notif" defaultChecked />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="achievement-notif">Achievement notifications</Label>
              <p className="text-xs text-muted-foreground">Notify when you unlock achievements</p>
            </div>
            <Switch id="achievement-notif" defaultChecked />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="reminder-notif">Reminder notifications</Label>
              <p className="text-xs text-muted-foreground">Remind me about due reviews</p>
            </div>
            <Switch id="reminder-notif" defaultChecked />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="marketing-notif">Marketing emails</Label>
              <p className="text-xs text-muted-foreground">News + product updates</p>
            </div>
            <Switch id="marketing-notif" />
          </div>
        </CardContent>
      </Card>

      {/* Quiet hours */}
      <Card>
        <CardHeader>
          <CardTitle>Quiet hours</CardTitle>
          <CardDescription>Don&apos;t send notifications during these hours</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="quiet-start">Start time</Label>
              <Input id="quiet-start" type="time" placeholder="22:00" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="quiet-end">End time</Label>
              <Input id="quiet-end" type="time" placeholder="07:00" />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="digest-freq">Digest frequency</Label>
            <Select defaultValue="immediate">
              <SelectTrigger id="digest-freq">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="immediate">Immediate</SelectItem>
                <SelectItem value="hourly">Hourly digest</SelectItem>
                <SelectItem value="daily">Daily digest</SelectItem>
                <SelectItem value="weekly">Weekly digest</SelectItem>
                <SelectItem value="never">Never</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
