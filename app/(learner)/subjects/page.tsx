'use client'

import * as React from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { BookOpen, Loader2, ChevronRight, GraduationCap, Sparkles, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import { tokenStorage } from '@/lib/api-client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Subject {
  id: string
  code: string
  name: string
  slug: string
  description: string | null
  status: string
  published_at: string | null
}

export default function SubjectsPage() {
  const router = useRouter()
  const [subjects, setSubjects] = React.useState<Subject[]>([])
  const [loading, setLoading] = React.useState(true)
  const [enrolling, setEnrolling] = React.useState<string | null>(null)
  const [conceptCounts, setConceptCounts] = React.useState<Record<string, number>>({})

  React.useEffect(() => {
    fetchSubjects()
  }, [])

  async function fetchSubjects() {
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/subjects`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (res.ok) {
        const data = await res.json()
        const list = Array.isArray(data) ? data : (data.items || [])
        setSubjects(list)
        // Fetch concept counts for each subject (parallel)
        await Promise.all(list.map((s: Subject) => fetchConceptCount(s.id)))
      }
    } catch {
      // Network error — show empty state
      setSubjects([])
    } finally {
      setLoading(false)
    }
  }

  async function fetchConceptCount(subjectId: string) {
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/subjects/${subjectId}/concepts`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (res.ok) {
        const data = await res.json()
        const count = Array.isArray(data) ? data.length : (data.items?.length || 0)
        setConceptCounts((prev) => ({ ...prev, [subjectId]: count }))
      }
    } catch {
      // ignore
    }
  }

  async function handleEnroll(subjectId: string, subjectName: string) {
    setEnrolling(subjectId)
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/enrollments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ subject_id: subjectId }),
      })
      if (res.ok) {
        toast.success(`Enrolled in ${subjectName}! Starting study session…`)
        // Navigate to study start
        router.push('/study/start')
      } else if (res.status === 409) {
        // Already enrolled — go to study
        toast.info(`You're already enrolled in ${subjectName}`)
        router.push('/study/start')
      } else {
        const err = await res.json().catch(() => ({}))
        toast.error(err.detail?.message || 'Failed to enroll. Please try again.')
      }
    } catch {
      toast.error('Network error. Please check your connection.')
    } finally {
      setEnrolling(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Subjects</h1>
        <p className="mt-1 text-sm text-zinc-400">Choose a subject to start learning</p>
      </div>

      {subjects.length === 0 ? (
        <Card className="rounded-2xl border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <div className="rounded-full bg-muted p-4">
              <AlertCircle className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="mt-4 text-lg font-semibold">No subjects available yet</h3>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">
              Content is being seeded. Please check back in a minute, or contact an admin
              to seed learning content.
            </p>
            <Button
              variant="outline"
              className="mt-4 gap-2"
              onClick={() => {
                setLoading(true)
                fetchSubjects()
              }}
            >
              <Loader2 className="h-4 w-4" />
              Refresh
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {subjects.map((subject) => {
            const conceptCount = conceptCounts[subject.id] ?? 0
            const isEnrolling = enrolling === subject.id
            return (
              <Card
                key={subject.id}
                className="glass-card group cursor-pointer rounded-2xl"
                onClick={() => !isEnrolling && handleEnroll(subject.id, subject.name)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className="rounded-xl bg-gradient-to-br from-emerald-500/10 to-teal-500/5 p-3 ring-1 ring-inset ring-emerald-500/20">
                        <GraduationCap className="h-6 w-6 text-emerald-500" />
                      </div>
                      <div>
                        <CardTitle className="text-lg">{subject.name}</CardTitle>
                        <CardDescription className="mt-1">{subject.description}</CardDescription>
                      </div>
                    </div>
                    <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-600">
                      {subject.code}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <BookOpen className="h-4 w-4" />
                        {conceptCount > 0 ? `${conceptCount} Concepts` : 'Concepts loading…'}
                      </span>
                      <span className="flex items-center gap-1">
                        <Sparkles className="h-4 w-4" />
                        Adaptive practice
                      </span>
                    </div>
                    {isEnrolling ? (
                      <Loader2 className="h-5 w-5 animate-spin text-emerald-500" />
                    ) : (
                      <ChevronRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1" />
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
