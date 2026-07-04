'use client'

import * as React from 'react'
import Link from 'next/link'
import { Search, BookOpen, Clock, ChevronRight } from 'lucide-react'

import { useSubjects, useEnrollments } from '@/hooks/use-learner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { useDebounce } from '@/hooks/use-debounce'

export default function SubjectsPage() {
  const { data: subjects, isLoading } = useSubjects()
  const { data: enrollments } = useEnrollments()
  const [search, setSearch] = React.useState('')
  const debouncedSearch = useDebounce(search, 300)

  const enrolledSubjectIds = React.useMemo(() => {
    return new Set((enrollments || []).map((e) => e.subject_id))
  }, [enrollments])

  const filtered = React.useMemo(() => {
    if (!subjects) return []
    const published = subjects.filter((s) => s.status === 'published')
    if (!debouncedSearch) return published
    const q = debouncedSearch.toLowerCase()
    return published.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q),
    )
  }, [subjects, debouncedSearch])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-8 w-48" />
          <Skeleton className="mt-2 h-4 w-72" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Subjects</h1>
        <p className="text-sm text-muted-foreground">Browse and enroll in learning subjects</p>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            placeholder="Search subjects..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
            aria-label="Search subjects"
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No subjects found"
          description={debouncedSearch ? "Try a different search term." : "No subjects are available yet."}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3" role="list">
          {filtered.map((subject) => {
            const isEnrolled = enrolledSubjectIds.has(subject.id)
            return (
              <Card key={subject.id} hover role="listitem">
                <CardHeader>
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-1">
                      <CardTitle className="text-base">{subject.name}</CardTitle>
                      <Badge variant={isEnrolled ? 'success' : 'secondary'}>
                        {isEnrolled ? 'Enrolled' : subject.difficulty_level}
                      </Badge>
                    </div>
                    <BookOpen className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                  </div>
                  <CardDescription className="line-clamp-2">
                    {subject.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" aria-hidden="true" />
                      {subject.estimated_hours}h
                    </span>
                    <span>{subject.concept_count} concepts</span>
                    <span>{subject.question_count} questions</span>
                  </div>
                  <Button asChild variant={isEnrolled ? 'outline' : 'default'} className="w-full" size="sm">
                    <Link href={`/subjects/${subject.id}`}>
                      {isEnrolled ? 'Continue learning' : 'View details'}
                      <ChevronRight className="h-4 w-4" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
