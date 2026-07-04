'use client'

import * as React from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, RefreshCw, Eye, Hash } from 'lucide-react'
import { toast } from 'sonner'

import { useQuestionTemplate, useQuestionPreview } from '@/hooks/use-content'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function TemplatePreviewPage() {
  const params = useParams()
  const templateId = params.templateId as string

  const { data: template, isLoading } = useQuestionTemplate(templateId)
  const previewMutation = useQuestionPreview()

  const [seed, setSeed] = React.useState<number>(42)
  const [preview, setPreview] = React.useState<any>(null)

  const generatePreview = async (useSeed?: number) => {
    const s = useSeed ?? seed
    try {
      const result = await previewMutation.mutateAsync({
        template_id: templateId,
        seed: s,
      })
      setPreview(result)
    } catch {
      toast.error('Failed to generate preview. The backend QuestionFactory may not be available.')
    }
  }

  // Auto-generate on load
  React.useEffect(() => {
    if (templateId) {
      generatePreview(42)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [templateId])

  const handleRandomSeed = () => {
    const newSeed = Math.floor(Math.random() * 1000000)
    setSeed(newSeed)
    generatePreview(newSeed)
  }

  if (isLoading) {
    return (
      <div className="max-w-3xl space-y-6">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <Link href={`/content/templates/${templateId}`} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3 w-3" /> Back to template
        </Link>
        <h1 className="mt-2 text-2xl font-bold tracking-tight">Live preview</h1>
        <p className="text-sm text-muted-foreground">
          Generate deterministic questions using the backend QuestionFactory
        </p>
      </div>

      {/* Seed control */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Hash className="h-4 w-4" aria-hidden="true" />
            Generation seed
          </CardTitle>
          <CardDescription>Change the seed to generate different question variants</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-2">
            <div className="flex-1 space-y-2">
              <Label htmlFor="seed">Seed value</Label>
              <Input
                id="seed"
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                aria-label="Generation seed"
              />
            </div>
            <Button onClick={() => generatePreview()} loading={previewMutation.isPending}>
              <Eye className="mr-2 h-4 w-4" />
              Generate
            </Button>
            <Button variant="outline" onClick={handleRandomSeed}>
              <RefreshCw className="h-4 w-4" />
              Random
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Preview result */}
      {previewMutation.isPending && !preview && (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </CardContent>
        </Card>
      )}

      {preview && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Generated question</CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-xs capitalize">
                  {preview.question_type.replace(/_/g, ' ')}
                </Badge>
                <Badge variant="secondary" className="text-xs">
                  Seed: {preview.seed}
                </Badge>
                <Badge variant="secondary" className="text-xs font-mono">
                  Hash: {preview.render_hash?.slice(0, 8)}...
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Prompt */}
            <div>
              <p className="mb-1 text-xs font-semibold uppercase text-muted-foreground">Prompt</p>
              <div className="rounded-lg border p-4">
                <p className="text-sm">{preview.prompt?.text || 'No prompt text'}</p>
                {preview.prompt?.code && (
                  <pre className="mt-2 overflow-auto rounded-md bg-muted p-3 text-xs">
                    <code>{preview.prompt.code}</code>
                  </pre>
                )}
              </div>
            </div>

            {/* Choices */}
            {preview.choices && preview.choices.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase text-muted-foreground">Choices</p>
                <ul className="space-y-2">
                  {preview.choices.map((choice: any, index: number) => (
                    <li
                      key={choice.id || index}
                      className={`rounded-lg border p-3 text-sm ${
                        choice.is_correct ? 'border-success bg-success/5' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{choice.text}</span>
                        {choice.is_correct && (
                          <Badge variant="success" className="text-xs">Correct</Badge>
                        )}
                      </div>
                      {choice.explanation && (
                        <p className="mt-1 text-xs text-muted-foreground">{choice.explanation}</p>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Metadata */}
            <Separator />
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-muted-foreground">Difficulty:</span>{' '}
                <span className="font-medium capitalize">{preview.difficulty}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Estimated time:</span>{' '}
                <span className="font-medium">{preview.estimated_duration_seconds}s</span>
              </div>
              <div>
                <span className="text-muted-foreground">Concept IDs:</span>{' '}
                <span className="font-mono">{preview.concept_ids?.length || 0}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Render hash:</span>{' '}
                <span className="font-mono text-[10px]">{preview.render_hash}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {!preview && !previewMutation.isPending && previewMutation.isError && (
        <Alert variant="destructive">
          <AlertDescription>
            Failed to generate preview. This may be because the template is not yet published
            or the backend preview endpoint is not available. Make sure the template has a valid
            prompt template and generators.
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
