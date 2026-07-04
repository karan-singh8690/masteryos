'use client'

import * as React from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, FileCode, Save, Eye } from 'lucide-react'
import { toast } from 'sonner'

import { useCreateQuestionTemplate, useContentConcepts, useContentSubjects } from '@/hooks/use-content'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Separator } from '@/components/ui/separator'

const QUESTION_TYPES = [
  { value: 'multiple_choice', label: 'Multiple Choice' },
  { value: 'multiple_select', label: 'Multiple Select' },
  { value: 'true_false', label: 'True/False' },
  { value: 'ordering', label: 'Ordering' },
  { value: 'fill_blank', label: 'Fill in the Blank' },
  { value: 'code_output', label: 'Code Output' },
  { value: 'short_answer', label: 'Short Answer' },
  { value: 'numerical', label: 'Numerical' },
]

const DIFFICULTY_LEVELS = [
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
]

export default function CreateTemplatePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const subjectIdParam = searchParams.get('subject')

  const { data: subjects } = useContentSubjects()
  const [selectedSubjectId, setSelectedSubjectId] = React.useState(subjectIdParam || '')
  const { data: concepts } = useContentConcepts(selectedSubjectId || null)
  const createMutation = useCreateQuestionTemplate()

  // Form state
  const [code, setCode] = React.useState('')
  const [questionType, setQuestionType] = React.useState('multiple_choice')
  const [promptText, setPromptText] = React.useState('')
  const [parameterSchema, setParameterSchema] = React.useState('{}')
  const [correctAnswerGenerator, setCorrectAnswerGenerator] = React.useState('{}')
  const [distractorGenerator, setDistractorGenerator] = React.useState('{}')
  const [explanationTemplate, setExplanationTemplate] = React.useState('{}')
  const [hintTiers, setHintTiers] = React.useState<string[]>([])
  const [difficulty, setDifficulty] = React.useState('medium')
  const [selectedConceptIds, setSelectedConceptIds] = React.useState<string[]>([])
  const [explanations, setExplanations] = React.useState<{ variant_type: string; content: string }[]>([
    { variant_type: 'correct', content: '' },
    { variant_type: 'incorrect', content: '' },
  ])

  const handleHintAdd = () => setHintTiers([...hintTiers, ''])
  const handleHintChange = (index: number, value: string) => {
    const updated = [...hintTiers]
    updated[index] = value
    setHintTiers(updated)
  }
  const handleHintRemove = (index: number) => {
    setHintTiers(hintTiers.filter((_, i) => i !== index))
  }

  const toggleConcept = (id: string) => {
    setSelectedConceptIds((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    )
  }

  const handleExplanationChange = (index: number, field: 'variant_type' | 'content', value: string) => {
    const updated = [...explanations]
    if (updated[index]) {
      updated[index] = { ...updated[index]!, [field]: value }
    }
    setExplanations(updated)
  }

  const handleAddExplanation = () => {
    setExplanations([...explanations, { variant_type: 'hint', content: '' }])
  }

  const handleRemoveExplanation = (index: number) => {
    setExplanations(explanations.filter((_, i) => i !== index))
  }

  const handleSubmit = async () => {
    if (!selectedSubjectId) {
      toast.error('Please select a subject')
      return
    }
    if (!code || !promptText) {
      toast.error('Code and prompt are required')
      return
    }

    try {
      // Parse JSON fields
      const parsedSchema = JSON.parse(parameterSchema)
      const parsedCorrect = JSON.parse(correctAnswerGenerator)
      const parsedDistractor = distractorGenerator.trim() ? JSON.parse(distractorGenerator) : null
      const parsedExplanation = JSON.parse(explanationTemplate)

      const result = await createMutation.mutateAsync({
        subjectId: selectedSubjectId,
        data: {
          code,
          question_type: questionType,
          prompt_template: { text: promptText },
          parameter_schema: parsedSchema,
          correct_answer_generator: parsedCorrect,
          distractor_generator: parsedDistractor,
          explanation_template: parsedExplanation,
          hint_tiers: hintTiers.filter((h) => h.trim()),
          difficulty_estimate: difficulty,
          discrimination_estimate: 0.5,
          concept_ids: selectedConceptIds,
          explanations: explanations.filter((e) => e.content.trim()),
        },
      })
      toast.success('Template created!')
      router.push(`/content/templates/${result.id}`)
    } catch (err) {
      if (err instanceof SyntaxError) {
        toast.error('Invalid JSON in one of the generator fields')
      } else {
        toast.error('Failed to create template')
      }
    }
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <Link href="/content/subjects" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3 w-3" /> Back to subjects
        </Link>
        <h1 className="mt-2 text-2xl font-bold tracking-tight">Create question template</h1>
        <p className="text-sm text-muted-foreground">Build a parametrized question template</p>
      </div>

      {/* Basic info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileCode className="h-4 w-4" aria-hidden="true" />
            Basic information
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="subject">Subject</Label>
              <Select value={selectedSubjectId} onValueChange={setSelectedSubjectId}>
                <SelectTrigger id="subject">
                  <SelectValue placeholder="Select subject" />
                </SelectTrigger>
                <SelectContent>
                  {subjects?.map((s) => (
                    <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="code">Template code</Label>
              <Input
                id="code"
                placeholder="DEC-001"
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="questionType">Question type</Label>
              <Select value={questionType} onValueChange={setQuestionType}>
                <SelectTrigger id="questionType">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {QUESTION_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="difficulty">Difficulty</Label>
              <Select value={difficulty} onValueChange={setDifficulty}>
                <SelectTrigger id="difficulty">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DIFFICULTY_LEVELS.map((d) => (
                    <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Prompt */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Prompt template</CardTitle>
          <CardDescription>The question prompt (supports variables like {'{variable_name}'})</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            placeholder="What is the output of the following code?\n\n```python\n{code_snippet}\n```"
            rows={5}
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            aria-label="Prompt template"
          />
        </CardContent>
      </Card>

      {/* Generators */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Generators</CardTitle>
          <CardDescription>JSON configuration for parameter generation</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="paramSchema">Parameter schema (JSON)</Label>
            <Textarea
              id="paramSchema"
              placeholder='{"variables": {"n": {"type": "int", "min": 1, "max": 10}}}'
              rows={4}
              value={parameterSchema}
              onChange={(e) => setParameterSchema(e.target.value)}
              className="font-mono text-xs"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="correctGen">Correct answer generator (JSON)</Label>
            <Textarea
              id="correctGen"
              placeholder='{"type": "expression", "expression": "n * 2"}'
              rows={4}
              value={correctAnswerGenerator}
              onChange={(e) => setCorrectAnswerGenerator(e.target.value)}
              className="font-mono text-xs"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="distractorGen">Distractor generator (JSON, optional)</Label>
            <Textarea
              id="distractorGen"
              placeholder='{"type": "wrong_answers", "count": 3}'
              rows={4}
              value={distractorGenerator}
              onChange={(e) => setDistractorGenerator(e.target.value)}
              className="font-mono text-xs"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="explanationTemplate">Explanation template (JSON)</Label>
            <Textarea
              id="explanationTemplate"
              placeholder='{"correct": "The answer is {n * 2} because..."}'
              rows={4}
              value={explanationTemplate}
              onChange={(e) => setExplanationTemplate(e.target.value)}
              className="font-mono text-xs"
            />
          </div>
        </CardContent>
      </Card>

      {/* Hints */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Hint tiers</CardTitle>
          <CardDescription>Progressive hints (each tier reveals more)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {hintTiers.map((hint, index) => (
            <div key={index} className="flex gap-2">
              <Input
                placeholder={`Hint ${index + 1}`}
                value={hint}
                onChange={(e) => handleHintChange(index, e.target.value)}
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => handleHintRemove(index)}
                aria-label={`Remove hint ${index + 1}`}
              >
                ×
              </Button>
            </div>
          ))}
          <Button type="button" variant="outline" size="sm" onClick={handleHintAdd}>
            + Add hint tier
          </Button>
        </CardContent>
      </Card>

      {/* Concept mapping */}
      {concepts && concepts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Concept mapping</CardTitle>
            <CardDescription>Link this template to concepts</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {concepts.map((concept) => (
                <label key={concept.id} className="flex items-center gap-2">
                  <Checkbox
                    checked={selectedConceptIds.includes(concept.id)}
                    onCheckedChange={() => toggleConcept(concept.id)}
                  />
                  <span className="text-sm">{concept.name}</span>
                  <Badge variant="outline" className="text-xs capitalize">{concept.difficulty}</Badge>
                </label>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Explanation variants */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Explanation variants</CardTitle>
          <CardDescription>Different explanations for different outcomes</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {explanations.map((exp, index) => (
            <div key={index} className="space-y-2 rounded-lg border p-3">
              <div className="flex items-center justify-between">
                <Select
                  value={exp.variant_type}
                  onValueChange={(v) => handleExplanationChange(index, 'variant_type', v)}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="correct">Correct</SelectItem>
                    <SelectItem value="incorrect">Incorrect</SelectItem>
                    <SelectItem value="hint">Hint</SelectItem>
                    <SelectItem value="interview">Interview</SelectItem>
                    <SelectItem value="beginner">Beginner</SelectItem>
                  </SelectContent>
                </Select>
                {explanations.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveExplanation(index)}
                  >
                    Remove
                  </Button>
                )}
              </div>
              <Textarea
                placeholder="Explanation content (Markdown supported)..."
                rows={3}
                value={exp.content}
                onChange={(e) => handleExplanationChange(index, 'content', e.target.value)}
              />
            </div>
          ))}
          <Button type="button" variant="outline" size="sm" onClick={handleAddExplanation}>
            + Add explanation variant
          </Button>
        </CardContent>
      </Card>

      <Separator />

      {/* Actions */}
      <div className="flex justify-end gap-2">
        <Button variant="outline" asChild>
          <Link href="/content/subjects">Cancel</Link>
        </Button>
        <Button
          onClick={handleSubmit}
          loading={createMutation.isPending}
          disabled={createMutation.isPending}
          leftIcon={<Save className="h-4 w-4" />}
        >
          Save template
        </Button>
      </div>
    </div>
  )
}
