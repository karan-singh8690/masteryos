'use client'

import * as React from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, FileCode, Eye, Send, Archive,
  Copy, History, Trash2,
} from 'lucide-react'
import { toast } from 'sonner'

import {
  useQuestionTemplate,
  usePublishTemplate,
  useArchiveTemplate,
  useDuplicateTemplate,
} from '@/hooks/use-content'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { ErrorState } from '@/components/ui/error-state'

export default function TemplateDetailPage() {
  const params = useParams()
  const router = useRouter()
  const templateId = params.templateId as string

  const { data: template, isLoading, isError, refetch } = useQuestionTemplate(templateId)
  const publishMutation = usePublishTemplate()
  const archiveMutation = useArchiveTemplate()
  const duplicateMutation = useDuplicateTemplate()

  const handlePublish = async () => {
    try {
      await publishMutation.mutateAsync(templateId)
      toast.success('Template published!')
    } catch {
      toast.error('Failed to publish template')
    }
  }

  const handleArchive = async () => {
    try {
      await archiveMutation.mutateAsync(templateId)
      toast.success('Template archived')
      router.push('/content/subjects')
    } catch {
      toast.error('Failed to archive template')
    }
  }

  const handleDuplicate = async () => {
    try {
      const result = await duplicateMutation.mutateAsync(templateId)
      toast.success('Template duplicated!')
      router.push(`/content/templates/${result.id}`)
    } catch {
      toast.error('Failed to duplicate template')
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl space-y-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (isError || !template) {
    return <ErrorState onRetry={() => refetch()} />
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <Link href="/content/subjects" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3 w-3" /> Back to subjects
        </Link>
      </div>

      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <CardTitle className="text-xl">Template {template.template_id}</CardTitle>
                <Badge variant="secondary">v{template.version_number}</Badge>
              </div>
              <CardDescription>Template version details</CardDescription>
            </div>
            <FileCode className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Button onClick={handlePublish} loading={publishMutation.isPending} disabled={publishMutation.isPending}>
              <Send className="mr-2 h-4 w-4" />
              Publish
            </Button>
            <Button variant="outline" asChild>
              <Link href={`/content/templates/${templateId}/preview`}>
                <Eye className="mr-2 h-4 w-4" />
                Live preview
              </Link>
            </Button>
            <Button variant="outline" onClick={handleDuplicate} loading={duplicateMutation.isPending}>
              <Copy className="mr-2 h-4 w-4" />
              Duplicate
            </Button>
            <Button variant="outline" asChild>
              <Link href={`/content/templates/${templateId}/versions`}>
                <History className="mr-2 h-4 w-4" />
                Version history
              </Link>
            </Button>
            <Button variant="outline" onClick={handleArchive} loading={archiveMutation.isPending}>
              <Archive className="mr-2 h-4 w-4" />
              Archive
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Template details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Template specification</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs text-muted-foreground">Version number</p>
              <p className="text-sm font-medium">{template.version_number}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Difficulty</p>
              <p className="text-sm font-medium capitalize">{template.difficulty_estimate}</p>
            </div>
          </div>

          <Separator />

          {/* Prompt template */}
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Prompt template</p>
            <pre className="overflow-auto rounded-md bg-muted p-3 text-xs">
              <code>{JSON.stringify(template.prompt_template, null, 2)}</code>
            </pre>
          </div>

          {/* Parameter schema */}
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Parameter schema</p>
            <pre className="overflow-auto rounded-md bg-muted p-3 text-xs">
              <code>{JSON.stringify(template.parameter_schema, null, 2)}</code>
            </pre>
          </div>

          {/* Correct answer generator */}
          <div>
            <p className="mb-1 text-xs text-muted-foreground">Correct answer generator</p>
            <pre className="overflow-auto rounded-md bg-muted p-3 text-xs">
              <code>{JSON.stringify(template.correct_answer_generator, null, 2)}</code>
            </pre>
          </div>

          {/* Distractor generator */}
          {template.distractor_generator && (
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Distractor generator</p>
              <pre className="overflow-auto rounded-md bg-muted p-3 text-xs">
                <code>{JSON.stringify(template.distractor_generator, null, 2)}</code>
              </pre>
            </div>
          )}

          {/* Hint tiers */}
          {template.hint_tiers.length > 0 && (
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Hint tiers ({template.hint_tiers.length})</p>
              <ul className="space-y-1">
                {template.hint_tiers.map((hint, i) => (
                  <li key={i} className="text-sm">
                    <span className="text-muted-foreground">Tier {i + 1}:</span> {hint}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Concept IDs */}
          {template.concept_ids.length > 0 && (
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Linked concepts ({template.concept_ids.length})</p>
              <div className="flex flex-wrap gap-1">
                {template.concept_ids.map((id) => (
                  <Badge key={id} variant="outline" className="text-xs">
                    {id}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
