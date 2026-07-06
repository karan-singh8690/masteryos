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
import { Palette, Bell, Moon, Sun, Monitor, Clock, Mail, Smartphone, Trophy, CalendarClock, Megaphone } from 'lucide-react'

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
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Settings</h1>
        <p className="mt-1 text-sm text-zinc-400">Manage your application preferences</p>
      </div>

      {/* Appearance */}
      <Card className="glass-card">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 ring-1 ring-inset ring-emerald-500/20">
              <Palette className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <CardTitle>Appearance</CardTitle>
              <CardDescription>Customize how MasteryOS looks</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label className="text-zinc-300">Theme</Label>
            {mounted && (
              <Select value={theme} onValueChange={setTheme}>
                <SelectTrigger className="border-white/10 bg-white/5 text-white">
                  <SelectValue placeholder="Select theme" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="light"><span className="flex items-center gap-2"><Sun className="h-4 w-4" /> Light</span></SelectItem>
                  <SelectItem value="dark"><span className="flex items-center gap-2"><Moon className="h-4 w-4" /> Dark</span></SelectItem>
                  <SelectItem value="system"><span className="flex items-center gap-2"><Monitor className="h-4 w-4" /> System</span></SelectItem>
                </SelectContent>
              </Select>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Notification preferences */}
      <Card className="glass-card">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 ring-1 ring-inset ring-emerald-500/20">
              <Bell className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <CardTitle>Notifications</CardTitle>
              <CardDescription>Choose what notifications you receive</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-1">
          <NotificationRow
            id="email-notif"
            icon={Mail}
            label="Email notifications"
            description="Receive notifications via email"
            defaultChecked
          />
          <NotificationRow
            id="inapp-notif"
            icon={Smartphone}
            label="In-app notifications"
            description="Show notifications in the app"
            defaultChecked
          />
          <NotificationRow
            id="achievement-notif"
            icon={Trophy}
            label="Achievement notifications"
            description="Notify when you unlock achievements"
            defaultChecked
          />
          <NotificationRow
            id="reminder-notif"
            icon={CalendarClock}
            label="Reminder notifications"
            description="Remind me about due reviews"
            defaultChecked
          />
          <NotificationRow
            id="marketing-notif"
            icon={Megaphone}
            label="Marketing emails"
            description="News + product updates"
          />
        </CardContent>
      </Card>

      {/* Quiet hours */}
      <Card className="glass-card">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 ring-1 ring-inset ring-emerald-500/20">
              <Clock className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <CardTitle>Quiet hours</CardTitle>
              <CardDescription>Don&apos;t send notifications during these hours</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="quiet-start" className="text-zinc-300">Start time</Label>
              <Input id="quiet-start" type="time" placeholder="22:00" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="quiet-end" className="text-zinc-300">End time</Label>
              <Input id="quiet-end" type="time" placeholder="07:00" />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="digest-freq" className="text-zinc-300">Digest frequency</Label>
            <Select defaultValue="immediate">
              <SelectTrigger id="digest-freq" className="border-white/10 bg-white/5 text-white">
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

function NotificationRow({
  id,
  icon: Icon,
  label,
  description,
  defaultChecked,
}: {
  id: string
  icon: React.ComponentType<{ className?: string }>
  label: string
  description: string
  defaultChecked?: boolean
}) {
  return (
    <div className="flex items-center justify-between rounded-xl px-3 py-3 transition-colors hover:bg-white/[0.03]">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/5 ring-1 ring-inset ring-white/10">
          <Icon className="h-4 w-4 text-zinc-400" />
        </div>
        <div className="space-y-0.5">
          <Label htmlFor={id} className="text-sm font-medium text-white">{label}</Label>
          <p className="text-xs text-zinc-500">{description}</p>
        </div>
      </div>
      <Switch id={id} defaultChecked={defaultChecked} />
    </div>
  )
}
