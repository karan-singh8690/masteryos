'use client'

import * as React from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, History, GitCompare } from 'lucide-react'

import { useQuestionTemplate } from '@/hooks/use-content'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'

export default function VersionHistoryPage() {
  const params = useParams()
  const templateId = params.templateId as string

  const { data: template, isLoading } = useQuestionTemplate(templateId)

  if (isLoading) {
    return (
      <div className="max-w-3xl space-y-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (!template) {
    return <p className="text-sm text-muted-foreground">Template not found</p>
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <Link href={`/content/templates/${templateId}`} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3 w-3" /> Back to template
        </Link>
        <h1 className="mt-2 text-2xl font-bold tracking-tight">Version history</h1>
        <p className="text-sm text-muted-foreground">View and compare template versions</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <History className="h-4 w-4" aria-hidden="true" />
            Version {template.version_number}
            <Badge variant="secondary">Current</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs text-muted-foreground">Version</p>
              <p className="text-sm font-medium">{template.version_number}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Difficulty</p>
              <p className="text-sm font-medium capitalize">{template.difficulty_estimate}</p>
            </div>
          </div>

          <Separator />

          <div>
            <p className="mb-1 text-xs text-muted-foreground">Prompt template</p>
            <pre className="overflow-auto rounded-md bg-muted p-3 text-xs">
              <code>{JSON.stringify(template.prompt_template, null, 2)}</code>
            </pre>
          </div>

          <div>
            <p className="mb-1 text-xs text-muted-foreground">Correct answer generator</p>
            <pre className="overflow-auto rounded-md bg-muted p-3 text-xs">
              <code>{JSON.stringify(template.correct_answer_generator, null, 2)}</code>
            </pre>
          </div>

          {template.concept_ids.length > 0 && (
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Concept IDs</p>
              <div className="flex flex-wrap gap-1">
                {template.concept_ids.map((id) => (
                  <Badge key={id} variant="outline" className="text-xs font-mono">{id}</Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <GitCompare className="h-4 w-4" aria-hidden="true" />
            Version diff
          </CardTitle>
          <CardDescription>Compare this version with previous versions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="secondary">v{template.version_number}</Badge>
              <span className="text-xs text-muted-foreground">← Current version</span>
            </div>
            {template.version_number > 1 && (
              <div className="flex items-center gap-2">
                <Badge variant="outline">v{template.version_number - 1}</Badge>
                <span className="text-xs text-muted-foreground">← Previous version</span>
              </div>
            )}
            <Separator />
            <p className="text-xs text-muted-foreground">
              This is the first version of this template. Future versions will show a diff comparison.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
