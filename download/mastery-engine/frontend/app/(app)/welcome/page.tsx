'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { Check, ChevronRight, User, Target, BookOpen, GraduationCap } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/cn'

const STEPS = [
  { id: 0, label: 'Profile', icon: User },
  { id: 1, label: 'Learning Goal', icon: Target },
  { id: 2, label: 'Subject', icon: BookOpen },
  { id: 3, label: 'Tutorial', icon: GraduationCap },
]

const TIMEZONES = ['UTC', 'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles', 'Europe/London', 'Europe/Paris', 'Asia/Tokyo', 'Asia/Calcutta']

export default function WelcomePage() {
  const router = useRouter()
  const [step, setStep] = React.useState(0)
  const [displayName, setDisplayName] = React.useState('')
  const [timezone, setTimezone] = React.useState('UTC')
  const [dailyGoal, setDailyGoal] = React.useState('10')
  const [subject, setSubject] = React.useState('')

  const progress = ((step + 1) / STEPS.length) * 100

  const handleNext = () => {
    if (step < STEPS.length - 1) {
      setStep(step + 1)
    } else {
      // Complete — save profile + redirect to dashboard
      router.push('/dashboard')
    }
  }

  const handleSkip = () => {
    router.push('/dashboard')
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold tracking-tight">Welcome to Mastery Engine! 👋</h1>
        <p className="mt-1 text-sm text-muted-foreground">Let's set up your learning experience in just a few steps.</p>
      </div>

      {/* Progress */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          {STEPS.map((s, i) => {
            const Icon = s.icon
            return (
              <div key={s.id} className="flex items-center">
                <div
                  className={cn(
                    'flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-medium transition-colors',
                    i < step && 'border-success bg-success text-success-foreground',
                    i === step && 'border-primary bg-primary text-primary-foreground',
                    i > step && 'border-muted text-muted-foreground',
                  )}
                >
                  {i < step ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                </div>
                {i < STEPS.length - 1 && (
                  <div className={cn('h-0.5 w-12', i < step ? 'bg-success' : 'bg-muted')} />
                )}
              </div>
            )
          })}
        </div>
        <Progress value={progress} className="h-1" />
      </div>

      <Card>
        <CardContent className="pt-6">
          {/* Step 0: Profile */}
          {step === 0 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold">Your Profile</h2>
                <p className="text-sm text-muted-foreground">Tell us a bit about yourself.</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="displayName">Display Name</Label>
                <Input
                  id="displayName"
                  placeholder="Your name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Timezone</Label>
                <Select value={timezone} onValueChange={setTimezone}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {TIMEZONES.map((tz) => (
                      <SelectItem key={tz} value={tz}>{tz}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {/* Step 1: Learning Goal */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold">Set Your Daily Goal</h2>
                <p className="text-sm text-muted-foreground">How many questions do you want to answer per day?</p>
              </div>
              <div className="grid grid-cols-4 gap-2">
                {['5', '10', '15', '20'].map((count) => (
                  <button
                    key={count}
                    type="button"
                    onClick={() => setDailyGoal(count)}
                    className={cn(
                      'rounded-lg border p-4 text-center transition-colors',
                      dailyGoal === count
                        ? 'border-primary bg-primary/5 text-primary'
                        : 'hover:bg-muted/50',
                    )}
                  >
                    <span className="text-2xl font-bold">{count}</span>
                    <span className="block text-xs text-muted-foreground">questions/day</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: Subject */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold">Choose a Subject</h2>
                <p className="text-sm text-muted-foreground">Select a subject to start learning.</p>
              </div>
              <div className="space-y-2">
                {['Python Interview Prep', 'Data Structures', 'Algorithms'].map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setSubject(s)}
                    className={cn(
                      'flex w-full items-center justify-between rounded-lg border p-4 text-left transition-colors',
                      subject === s
                        ? 'border-primary bg-primary/5'
                        : 'hover:bg-muted/50',
                    )}
                  >
                    <div>
                      <p className="text-sm font-medium">{s}</p>
                      <p className="text-xs text-muted-foreground">Click to select</p>
                    </div>
                    {subject === s && <Check className="h-4 w-4 text-primary" />}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 3: Tutorial */}
          {step === 3 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold">You're All Set! 🎉</h2>
                <p className="text-sm text-muted-foreground">Here's what you can do in Mastery Engine:</p>
              </div>
              <ul className="space-y-3">
                <li className="flex items-start gap-3">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">1</div>
                  <div><p className="text-sm font-medium">Start a Study Session</p><p className="text-xs text-muted-foreground">Answer adaptive questions tailored to your level</p></div>
                </li>
                <li className="flex items-start gap-3">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">2</div>
                  <div><p className="text-sm font-medium">Track Your Mastery</p><p className="text-xs text-muted-foreground">Watch your mastery scores grow as you learn</p></div>
                </li>
                <li className="flex items-start gap-3">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">3</div>
                  <div><p className="text-sm font-medium">Review & Improve</p><p className="text-xs text-muted-foreground">Spaced repetition ensures concepts stick</p></div>
                </li>
                <li className="flex items-start gap-3">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">4</div>
                  <div><p className="text-sm font-medium">Give Feedback</p><p className="text-xs text-muted-foreground">Use the feedback button to help us improve</p></div>
                </li>
              </ul>
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between pt-4">
            <Button variant="ghost" onClick={handleSkip} size="sm">Skip for now</Button>
            <Button onClick={handleNext} size="sm" rightIcon={<ChevronRight className="h-4 w-4" />}>
              {step === STEPS.length - 1 ? 'Get Started' : 'Next'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
