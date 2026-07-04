'use client'

import * as React from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, BookOpen, Clock, GraduationCap, CheckCircle2 } from 'lucide-react'
import { toast } from 'sonner'

import { useSubject, useSubjectConcepts, useEnrollments, useEnroll } from '@/hooks/use-learner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ErrorState } from '@/components/ui/error-state'

export default function SubjectDetailPage() {
  const params = useParams()
  const router = useRouter()
  const subjectId = params.subjectId as string

  const { data: subject, isLoading, isError, refetch } = useSubject(subjectId)
  const { data: concepts } = useSubjectConcepts(subjectId)
  const { data: enrollments } = useEnrollments()
  const enrollMutation = useEnroll()

  const enrollment = React.useMemo(() => {
    return (enrollments || []).find((e) => e.subject_id === subjectId)
  }, [enrollments, subjectId])

  const handleEnroll = async () => {
    try {
      await enrollMutation.mutateAsync({ subject_id: subjectId })
      toast.success('Enrolled successfully!')
      router.push('/dashboard')
    } catch {
      toast.error('Failed to enroll. Please try again.')
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl space-y-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (isError || !subject) {
    return <ErrorState onRetry={() => refetch()} />
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <Link href="/subjects" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3 w-3" /> Back to subjects
        </Link>
      </div>

      {/* Subject header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <CardTitle className="text-2xl">{subject.name}</CardTitle>
                <Badge variant="secondary">{subject.difficulty_level}</Badge>
              </div>
              <CardDescription className="text-base">{subject.description}</CardDescription>
            </div>
            <BookOpen className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-6 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Clock className="h-4 w-4" aria-hidden="true" />
              {subject.estimated_hours} hours
            </span>
            <span>{subject.concept_count} concepts</span>
            <span>{subject.question_count} questions</span>
          </div>

          {enrollment ? (
            <Alert>
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>
                You&apos;re enrolled in this subject. Progress: {Math.round(enrollment.progress * 100)}%
              </AlertDescription>
            </Alert>
          ) : null}

          <div className="flex gap-2">
            {enrollment ? (
              <>
                <Button asChild>
                  <Link href={`/study/start?enrollment=${enrollment.id}`}>
                    <GraduationCap className="mr-2 h-4 w-4" />
                    Continue learning
                  </Link>
                </Button>
                <Button variant="outline" asChild>
                  <Link href="/mastery">View mastery</Link>
                </Button>
              </>
            ) : (
              <Button
                onClick={handleEnroll}
                loading={enrollMutation.isPending}
                disabled={enrollMutation.isPending}
              >
                Enroll now
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Concepts list */}
      {concepts && concepts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Concepts covered</CardTitle>
            <CardDescription>{concepts.length} concepts in this subject</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2" role="list">
              {concepts.map((concept, index) => (
                <li key={concept.id} className="flex items-start gap-3 rounded-md border p-3">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-medium">
                    {index + 1}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{concept.name}</p>
                      <Badge variant="outline" className="text-xs">{concept.difficulty}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{concept.description}</p>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
