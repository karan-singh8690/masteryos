'use client'

import * as React from 'react'
import Link from 'next/link'
import { BookOpen, Loader2, ChevronRight, GraduationCap } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
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
  const [subjects, setSubjects] = React.useState<Subject[]>([])
  const [loading, setLoading] = React.useState(true)
  const [enrolling, setEnrolling] = React.useState<string | null>(null)

  React.useEffect(() => {
    fetchSubjects()
  }, [])

  async function fetchSubjects() {
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/admin/subjects`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (res.ok) {
        const data = await res.json()
        setSubjects(Array.isArray(data) ? data : (data.items || []))
      }
    } catch {
      // Show default subject if API fails
      setSubjects([{
        id: 'default',
        code: 'PY-INTERVIEW',
        name: 'Python Technical Interview Prep',
        slug: 'python-interview-prep',
        description: 'Master Python technical interviews with adaptive practice on data structures, algorithms, OOP, Python internals, and system design.',
        status: 'published',
        published_at: null,
      }])
    } finally {
      setLoading(false)
    }
  }

  async function handleEnroll(subjectId: string) {
    setEnrolling(subjectId)
    try {
      const token = tokenStorage.getAccessToken()
      await fetch(`${API_URL}/api/v1/enrollments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ subject_id: subjectId }),
      })
      // Navigate to study
      window.location.href = '/study/start'
    } catch {
      // Navigate anyway
      window.location.href = '/study/start'
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
        <h1 className="text-2xl font-bold tracking-tight">Subjects</h1>
        <p className="text-sm text-muted-foreground">Choose a subject to start learning</p>
      </div>

      <div className="grid gap-4">
        {subjects.map((subject) => (
          <Card
            key={subject.id}
            className="group cursor-pointer rounded-2xl transition-all hover:border-emerald-500/30 hover:shadow-lg hover:shadow-emerald-500/5"
            onClick={() => handleEnroll(subject.id)}
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
                    <BookOpen className="h-4 w-4" /> 5 Concepts
                  </span>
                  <span className="flex items-center gap-1">
                    <GraduationCap className="h-4 w-4" /> 10 Questions
                  </span>
                </div>
                {enrolling === subject.id ? (
                  <Loader2 className="h-5 w-5 animate-spin text-emerald-500" />
                ) : (
                  <ChevronRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1" />
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
