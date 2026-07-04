'use client'

import * as React from 'react'
import {
  FlaskConical,
  Plus,
  Play,
  Square,
  UserPlus,
  BarChart3,
  CheckCircle2,
  XCircle,
  Trophy,
  Filter,
} from 'lucide-react'
import { toast } from 'sonner'

import {
  useExperiments,
  useExperiment,
  useCreateExperiment,
  useUpdateExperiment,
  useAssignVariant,
  useRecordExperimentResult,
} from '@/hooks/use-beta-ops'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { ErrorState } from '@/components/ui/error-state'
import { EmptyState } from '@/components/ui/empty-state'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/cn'
import { formatDateTime, formatNumber } from '@/lib/format'
import type { Experiment, ExperimentResults } from '@/lib/beta-ops-api'

const EXPERIMENT_TYPES = ['ab_test', 'feature_flag', 'multivariate', 'holdout']
const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'success' | 'warning' | 'destructive'> = {
  draft: 'secondary',
  running: 'default',
  completed: 'success',
  stopped: 'warning',
}

interface CreateExperimentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function CreateExperimentDialog({ open, onOpenChange }: CreateExperimentDialogProps) {
  const createMutation = useCreateExperiment()
  const [id, setId] = React.useState('')
  const [name, setName] = React.useState('')
  const [description, setDescription] = React.useState('')
  const [experimentType, setExperimentType] = React.useState('ab_test')
  const [variantA, setVariantA] = React.useState('')
  const [variantB, setVariantB] = React.useState('')
  const [rollout, setRollout] = React.useState('50')
  const [targetMetric, setTargetMetric] = React.useState('')
  const [minSample, setMinSample] = React.useState('1000')

  const reset = () => {
    setId('')
    setName('')
    setDescription('')
    setExperimentType('ab_test')
    setVariantA('')
    setVariantB('')
    setRollout('50')
    setTargetMetric('')
    setMinSample('1000')
  }

  const handleSubmit = async () => {
    if (!id || !name || !variantA || !variantB) {
      toast.error('ID, name, and both variants are required')
      return
    }
    try {
      await createMutation.mutateAsync({
        id,
        name,
        description: description || null,
        experiment_type: experimentType,
        variant_a: variantA,
        variant_b: variantB,
        rollout_percentage: Number(rollout) || 50,
        target_metric: targetMetric || null,
        min_sample_size: Number(minSample) || 0,
      })
      toast.success('Experiment created')
      reset()
      onOpenChange(false)
    } catch {
      toast.error('Failed to create experiment')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Experiment</DialogTitle>
          <DialogDescription>
            Set up a new A/B test or feature rollout experiment.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="exp-id">ID</Label>
              <Input
                id="exp-id"
                placeholder="checkout_redesign_v2"
                value={id}
                onChange={(e) => setId(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="exp-type">Type</Label>
              <Select value={experimentType} onValueChange={setExperimentType}>
                <SelectTrigger id="exp-type">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  {EXPERIMENT_TYPES.map((t) => (
                    <SelectItem key={t} value={t} className="capitalize">
                      {t.replace(/_/g, ' ')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="exp-name">Name</Label>
            <Input
              id="exp-name"
              placeholder="Checkout Redesign v2"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="exp-desc">Description</Label>
            <Textarea
              id="exp-desc"
              placeholder="What are we testing and why?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="exp-va">Variant A (control)</Label>
              <Input
                id="exp-va"
                placeholder="control"
                value={variantA}
                onChange={(e) => setVariantA(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="exp-vb">Variant B (treatment)</Label>
              <Input
                id="exp-vb"
                placeholder="treatment"
                value={variantB}
                onChange={(e) => setVariantB(e.target.value)}
              />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-2">
              <Label htmlFor="exp-rollout">Rollout %</Label>
              <Input
                id="exp-rollout"
                type="number"
                min={0}
                max={100}
                value={rollout}
                onChange={(e) => setRollout(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="exp-metric">Target metric</Label>
              <Input
                id="exp-metric"
                placeholder="conversion_rate"
                value={targetMetric}
                onChange={(e) => setTargetMetric(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="exp-sample">Min sample</Label>
              <Input
                id="exp-sample"
                type="number"
                min={0}
                value={minSample}
                onChange={(e) => setMinSample(e.target.value)}
              />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={createMutation.isPending}>
            Create experiment
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

interface AssignVariantDialogProps {
  experiment: Experiment | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function AssignVariantDialog({ experiment, open, onOpenChange }: AssignVariantDialogProps) {
  const assignMutation = useAssignVariant()
  const [userId, setUserId] = React.useState('')

  React.useEffect(() => {
    if (open) setUserId('')
  }, [open])

  const handleSubmit = async () => {
    if (!experiment || !userId) {
      toast.error('User ID is required')
      return
    }
    try {
      await assignMutation.mutateAsync({ experimentId: experiment.id, userId })
      toast.success('Variant assigned')
      onOpenChange(false)
    } catch {
      toast.error('Failed to assign variant')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign Variant — {experiment?.name}</DialogTitle>
          <DialogDescription>
            Manually assign a specific user to a variant for this experiment.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="assign-user">User ID</Label>
            <Input
              id="assign-user"
              placeholder="00000000-0000-0000-0000-000000000000"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={assignMutation.isPending}>
            Assign variant
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

interface RecordResultDialogProps {
  experiment: Experiment | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function RecordResultDialog({ experiment, open, onOpenChange }: RecordResultDialogProps) {
  const recordMutation = useRecordExperimentResult()
  const [variant, setVariant] = React.useState('')
  const [sampleSize, setSampleSize] = React.useState('')
  const [metricValue, setMetricValue] = React.useState('')
  const [conversionCount, setConversionCount] = React.useState('')

  React.useEffect(() => {
    if (open && experiment) {
      setVariant(experiment.variant_a)
      setSampleSize('')
      setMetricValue('')
      setConversionCount('')
    }
  }, [open, experiment])

  const handleSubmit = async () => {
    if (!experiment) return
    if (!variant || !sampleSize || !conversionCount) {
      toast.error('Variant, sample size, and conversion count are required')
      return
    }
    try {
      await recordMutation.mutateAsync({
        experimentId: experiment.id,
        payload: {
          variant,
          sample_size: Number(sampleSize),
          metric_value: metricValue ? Number(metricValue) : undefined,
          conversion_count: Number(conversionCount),
        },
      })
      toast.success('Result recorded')
      onOpenChange(false)
    } catch {
      toast.error('Failed to record result')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Record Result — {experiment?.name}</DialogTitle>
          <DialogDescription>
            Submit new variant results for this experiment.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="result-variant">Variant</Label>
            <Select value={variant} onValueChange={setVariant}>
              <SelectTrigger id="result-variant">
                <SelectValue placeholder="Variant" />
              </SelectTrigger>
              <SelectContent>
                {experiment && (
                  <>
                    <SelectItem value={experiment.variant_a}>{experiment.variant_a}</SelectItem>
                    <SelectItem value={experiment.variant_b}>{experiment.variant_b}</SelectItem>
                  </>
                )}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="result-sample">Sample size</Label>
              <Input
                id="result-sample"
                type="number"
                min={0}
                value={sampleSize}
                onChange={(e) => setSampleSize(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="result-conversions">Conversion count</Label>
              <Input
                id="result-conversions"
                type="number"
                min={0}
                value={conversionCount}
                onChange={(e) => setConversionCount(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="result-metric">Metric value (optional)</Label>
            <Input
              id="result-metric"
              type="number"
              step="any"
              placeholder="e.g. 12.34"
              value={metricValue}
              onChange={(e) => setMetricValue(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={recordMutation.isPending}>
            Record result
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

interface ExperimentDetailDialogProps {
  experiment: Experiment | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function ExperimentDetailDialog({ experiment, open, onOpenChange }: ExperimentDetailDialogProps) {
  const { data, isLoading, isError } = useExperiment(experiment ? experiment.id : null)

  const renderResults = (results: Record<string, unknown> | undefined, variant: string) => {
    if (!results || Object.keys(results).length === 0) {
      return <p className="text-sm text-muted-foreground">No results yet for {variant}.</p>
    }
    return (
      <dl className="space-y-1 text-sm">
        {Object.entries(results).map(([k, v]) => (
          <div key={k} className="flex justify-between">
            <dt className="text-muted-foreground">{k.replace(/_/g, ' ')}</dt>
            <dd className="font-medium tabular-nums">
              {typeof v === 'number' ? (Number.isInteger(v) ? formatNumber(v) : v.toFixed(4)) : String(v)}
            </dd>
          </div>
        ))}
      </dl>
    )
  }

  const stats = (data?.statistical_significance ?? {}) as Record<string, unknown>

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{experiment?.name}</DialogTitle>
          <DialogDescription>
            {experiment?.id} • {experiment?.experiment_type.replace(/_/g, ' ')}
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="space-y-2" role="status" aria-label="Loading experiment detail">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : isError ? (
          <ErrorState title="Failed to load detail" description="We couldn't fetch this experiment's results." />
        ) : data ? (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Variant A — {experiment?.variant_a}</CardTitle>
                </CardHeader>
                <CardContent>{renderResults(data.variant_a_results, experiment?.variant_a ?? 'A')}</CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Variant B — {experiment?.variant_b}</CardTitle>
                </CardHeader>
                <CardContent>{renderResults(data.variant_b_results, experiment?.variant_b ?? 'B')}</CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <BarChart3 className="h-4 w-4" aria-hidden="true" />
                  Statistical Significance
                </CardTitle>
              </CardHeader>
              <CardContent>
                {Object.keys(stats).length === 0 ? (
                  <p className="text-sm text-muted-foreground">No significance data yet.</p>
                ) : (
                  <dl className="grid grid-cols-2 gap-2 text-sm">
                    {Object.entries(stats).map(([k, v]) => (
                      <div key={k} className="flex justify-between border-b pb-1">
                        <dt className="text-muted-foreground">{k.replace(/_/g, ' ')}</dt>
                        <dd className="font-medium tabular-nums">
                          {typeof v === 'number' ? (Number.isInteger(v) ? formatNumber(v) : v.toFixed(4)) : String(v)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Recommendation</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{data.recommendation || 'No recommendation available yet.'}</p>
              </CardContent>
            </Card>
          </div>
        ) : (
          <EmptyState
            icon={FlaskConical}
            title="No detail available"
            description="Experiment detail could not be loaded."
          />
        )}
      </DialogContent>
    </Dialog>
  )
}

function ExperimentsSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading experiments">
      <Skeleton className="h-10 w-72" />
      <Skeleton className="h-10 w-full" />
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-full" />
      ))}
    </div>
  )
}

const STATUS_FILTERS = ['all', 'draft', 'running', 'completed', 'stopped'] as const
type StatusFilter = (typeof STATUS_FILTERS)[number]

export default function ExperimentsPage() {
  const { data: experiments, isLoading, isError, error, refetch } = useExperiments()
  const updateMutation = useUpdateExperiment()

  const [statusFilter, setStatusFilter] = React.useState<StatusFilter>('all')
  const [createOpen, setCreateOpen] = React.useState(false)
  const [detailExp, setDetailExp] = React.useState<Experiment | null>(null)
  const [detailOpen, setDetailOpen] = React.useState(false)
  const [assignExp, setAssignExp] = React.useState<Experiment | null>(null)
  const [assignOpen, setAssignOpen] = React.useState(false)
  const [recordExp, setRecordExp] = React.useState<Experiment | null>(null)
  const [recordOpen, setRecordOpen] = React.useState(false)

  const handleStart = async (exp: Experiment) => {
    try {
      await updateMutation.mutateAsync({ experimentId: exp.id, payload: { status: 'running' } })
      toast.success(`Experiment "${exp.name}" started`)
    } catch {
      toast.error('Failed to start experiment')
    }
  }

  const handleStop = async (exp: Experiment) => {
    try {
      await updateMutation.mutateAsync({ experimentId: exp.id, payload: { status: 'stopped' } })
      toast.success(`Experiment "${exp.name}" stopped`)
    } catch {
      toast.error('Failed to stop experiment')
    }
  }

  const handleRowClick = (exp: Experiment) => {
    setDetailExp(exp)
    setDetailOpen(true)
  }

  const handleAssign = (exp: Experiment) => {
    setAssignExp(exp)
    setAssignOpen(true)
  }

  const handleRecord = (exp: Experiment) => {
    setRecordExp(exp)
    setRecordOpen(true)
  }

  if (isLoading) return <ExperimentsSkeleton />
  if (isError || !experiments) {
    return (
      <ErrorState
        title="Failed to load experiments"
        description="We couldn't fetch the experiments list."
        error={error as Error | undefined}
        onRetry={() => refetch()}
      />
    )
  }

  const filtered = experiments.filter((e) => statusFilter === 'all' || e.status === statusFilter)

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <FlaskConical className="h-6 w-6 text-primary" aria-hidden="true" />
            Experiments
          </h1>
          <p className="text-sm text-muted-foreground">
            A/B tests and feature rollout experiments for the beta platform.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} leftIcon={<Plus className="h-4 w-4" aria-hidden="true" />}>
          Create Experiment
        </Button>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Filter className="h-4 w-4" aria-hidden="true" />
            Filter
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Status filter">
            {STATUS_FILTERS.map((s) => (
              <Button
                key={s}
                size="sm"
                variant={statusFilter === s ? 'default' : 'outline'}
                onClick={() => setStatusFilter(s)}
                aria-pressed={statusFilter === s}
                className="capitalize"
              >
                {s}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <section aria-label="Experiments">
        {filtered.length === 0 ? (
          <EmptyState
            icon={FlaskConical}
            title="No experiments found"
            description="Adjust your filter or create a new experiment to get started."
          />
        ) : (
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b text-xs uppercase tracking-wider text-muted-foreground">
                      <th scope="col" className="px-3 py-2 font-semibold">Experiment</th>
                      <th scope="col" className="px-3 py-2 font-semibold">Type</th>
                      <th scope="col" className="px-3 py-2 font-semibold">Status</th>
                      <th scope="col" className="px-3 py-2 font-semibold">Rollout</th>
                      <th scope="col" className="px-3 py-2 text-right font-semibold">Sample A</th>
                      <th scope="col" className="px-3 py-2 text-right font-semibold">Sample B</th>
                      <th scope="col" className="px-3 py-2 font-semibold">Significant</th>
                      <th scope="col" className="px-3 py-2 font-semibold">Winner</th>
                      <th scope="col" className="px-3 py-2 text-right font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((exp) => (
                      <tr
                        key={exp.id}
                        className="cursor-pointer border-b transition-colors last:border-0 hover:bg-muted/40"
                        onClick={() => handleRowClick(exp)}
                      >
                        <td className="px-3 py-2">
                          <div className="font-mono text-xs text-muted-foreground">{exp.id}</div>
                          <div className="font-medium">{exp.name}</div>
                        </td>
                        <td className="px-3 py-2">
                          <Badge variant="outline" className="capitalize">
                            {exp.experiment_type.replace(/_/g, ' ')}
                          </Badge>
                        </td>
                        <td className="px-3 py-2">
                          <Badge variant={STATUS_VARIANT[exp.status] ?? 'secondary'} className="capitalize">
                            {exp.status}
                          </Badge>
                        </td>
                        <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                          <div className="w-24 space-y-1">
                            <Progress value={exp.rollout_percentage} />
                            <p className="text-xs text-muted-foreground">{exp.rollout_percentage}%</p>
                          </div>
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {formatNumber(exp.sample_size_a)}
                        </td>
                        <td className="px-3 py-2 text-right tabular-nums">
                          {formatNumber(exp.sample_size_b)}
                        </td>
                        <td className="px-3 py-2">
                          {exp.is_statistically_significant ? (
                            <Badge variant="success" className="text-xs">
                              <CheckCircle2 className="mr-1 h-3 w-3" aria-hidden="true" />
                              Yes
                            </Badge>
                          ) : (
                            <Badge variant="destructive" className="text-xs">
                              <XCircle className="mr-1 h-3 w-3" aria-hidden="true" />
                              No
                            </Badge>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          {exp.winner ? (
                            <Badge variant="success" className="text-xs">
                              <Trophy className="mr-1 h-3 w-3" aria-hidden="true" />
                              {exp.winner}
                            </Badge>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex justify-end gap-1">
                            {exp.status === 'draft' && (
                              <Button
                                size="icon"
                                variant="ghost"
                                aria-label={`Start ${exp.name}`}
                                onClick={() => handleStart(exp)}
                                loading={updateMutation.isPending}
                              >
                                <Play className="h-4 w-4" aria-hidden="true" />
                              </Button>
                            )}
                            {exp.status === 'running' && (
                              <Button
                                size="icon"
                                variant="ghost"
                                aria-label={`Stop ${exp.name}`}
                                onClick={() => handleStop(exp)}
                                loading={updateMutation.isPending}
                              >
                                <Square className="h-4 w-4" aria-hidden="true" />
                              </Button>
                            )}
                            <Button
                              size="icon"
                              variant="ghost"
                              aria-label={`Assign variant for ${exp.name}`}
                              onClick={() => handleAssign(exp)}
                            >
                              <UserPlus className="h-4 w-4" aria-hidden="true" />
                            </Button>
                            <Button
                              size="icon"
                              variant="ghost"
                              aria-label={`Record result for ${exp.name}`}
                              onClick={() => handleRecord(exp)}
                            >
                              <BarChart3 className="h-4 w-4" aria-hidden="true" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}
      </section>

      <CreateExperimentDialog open={createOpen} onOpenChange={setCreateOpen} />
      <ExperimentDetailDialog
        experiment={detailExp}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />
      <AssignVariantDialog
        experiment={assignExp}
        open={assignOpen}
        onOpenChange={setAssignOpen}
      />
      <RecordResultDialog
        experiment={recordExp}
        open={recordOpen}
        onOpenChange={setRecordOpen}
      />
    </div>
  )
}
