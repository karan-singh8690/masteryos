'use client'

import * as React from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, BookOpen, FileCode, Plus, Trash2,
  PublishIcon, Target, AlertTriangle, Lightbulb,
} from 'lucide-react'
import { toast } from 'sonner'

import {
  useContentSubject,
  useContentConcepts,
  useQuestionTemplates,
  usePublishSubject,
  useDeleteConcept,
} from '@/hooks/use-content'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'

export default function SubjectDetailPage() {
  const params = useParams()
  const router = useRouter()
  const subjectId = params.subjectId as string

  const { data: subject, isLoading, isError, refetch } = useContentSubject(subjectId)
  const { data: concepts } = useContentConcepts(subjectId)
  const { data: templates } = useQuestionTemplates(subjectId)
  const publishMutation = usePublishSubject()
  const deleteConceptMutation = useDeleteConcept()

  const [conceptToDelete, setConceptToDelete] = React.useState<string | null>(null)

  const handlePublish = async () => {
    try {
      await publishMutation.mutateAsync(subjectId)
      toast.success('Subject published!')
    } catch {
      toast.error('Failed to publish subject')
    }
  }

  const handleDeleteConcept = async () => {
    if (!conceptToDelete) return
    try {
      await deleteConceptMutation.mutateAsync(conceptToDelete)
      toast.success('Concept deleted')
      setConceptToDelete(null)
    } catch {
      toast.error('Failed to delete concept')
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl space-y-6">
        <Skeleton className="h-8 w-32" />
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
        <Link href="/content/subjects" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3 w-3" /> Back to subjects
        </Link>
      </div>

      {/* Subject header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <CardTitle className="text-2xl">{subject.name}</CardTitle>
                <Badge
                  variant={
                    subject.status === 'published' ? 'success' :
                    subject.status === 'archived' ? 'secondary' : 'warning'
                  }
                  className="capitalize"
                >
                  {subject.status}
                </Badge>
              </div>
              <CardDescription className="text-base">
                Code: {subject.code} • Slug: {subject.slug}
              </CardDescription>
              {subject.description && <p className="text-sm text-muted-foreground">{subject.description}</p>}
            </div>
            <BookOpen className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {subject.status !== 'published' && (
              <Button onClick={handlePublish} loading={publishMutation.isPending} disabled={publishMutation.isPending}>
                <PublishIcon className="mr-2 h-4 w-4" />
                Publish subject
              </Button>
            )}
            <Button variant="outline" asChild>
              <Link href={`/content/subjects/${subjectId}/concepts/create`}>
                <Plus className="mr-2 h-4 w-4" />
                Add concept
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href={`/content/templates/create?subject=${subjectId}`}>
                <FileCode className="mr-2 h-4 w-4" />
                Add template
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="concepts">
        <TabsList>
          <TabsTrigger value="concepts">Concepts ({concepts?.length || 0})</TabsTrigger>
          <TabsTrigger value="templates">Templates ({templates?.length || 0})</TabsTrigger>
        </TabsList>

        {/* Concepts tab */}
        <TabsContent value="concepts" className="space-y-3">
          {!concepts || concepts.length === 0 ? (
            <EmptyState
              icon={Target}
              title="No concepts yet"
              description="Add concepts to structure your curriculum."
              action={{ label: 'Add concept', onClick: () => router.push(`/content/subjects/${subjectId}/concepts/create`) }}
            />
          ) : (
            <ul className="space-y-2" role="list">
              {concepts.map((concept) => (
                <li key={concept.id}>
                  <Card hover>
                    <CardContent className="flex items-center justify-between p-4">
                      <Link href={`/content/concepts/${concept.id}`} className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium">{concept.name}</p>
                          <Badge variant="outline" className="text-xs capitalize">{concept.difficulty}</Badge>
                          <Badge variant="outline" className="text-xs capitalize">{concept.importance}</Badge>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground line-clamp-1">{concept.description}</p>
                      </Link>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => setConceptToDelete(concept.id)}
                        aria-label={`Delete ${concept.name}`}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </CardContent>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>

        {/* Templates tab */}
        <TabsContent value="templates" className="space-y-3">
          {!templates || templates.length === 0 ? (
            <EmptyState
              icon={FileCode}
              title="No templates yet"
              description="Create question templates for this subject."
              action={{ label: 'Add template', onClick: () => router.push(`/content/templates/create?subject=${subjectId}`) }}
            />
          ) : (
            <ul className="space-y-2" role="list">
              {templates.map((template) => (
                <li key={template.id}>
                  <Card hover>
                    <CardContent className="flex items-center justify-between p-4">
                      <Link href={`/content/templates/${template.id}`} className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium">{template.code}</p>
                          <Badge variant="outline" className="text-xs">{template.question_type}</Badge>
                          <Badge
                            variant={
                              template.status === 'published' ? 'success' :
                              template.status === 'archived' ? 'secondary' : 'warning'
                            }
                            className="text-xs capitalize"
                          >
                            {template.status}
                          </Badge>
                        </div>
                      </Link>
                      <Button size="sm" variant="outline" asChild>
                        <Link href={`/content/templates/${template.id}/preview`}>Preview</Link>
                      </Button>
                    </CardContent>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>
      </Tabs>

      {/* Delete confirmation */}
      <Dialog open={!!conceptToDelete} onOpenChange={(open) => !open && setConceptToDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete concept?</DialogTitle>
            <DialogDescription>
              This will permanently delete the concept and all related data. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConceptToDelete(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDeleteConcept} loading={deleteConceptMutation.isPending}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
