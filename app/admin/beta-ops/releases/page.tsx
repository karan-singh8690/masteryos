'use client'

import * as React from 'react'
import {
  Rocket,
  Plus,
  Pencil,
  GitBranch,
  History,
  Snowflake,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Bug,
  Sparkles,
  AlertTriangle,
  CircleAlert,
} from 'lucide-react'
import { toast } from 'sonner'

import {
  useReleases,
  useCreateRelease,
  useUpdateRelease,
  useAddReleaseStage,
} from '@/hooks/use-beta-ops'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
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
import { formatDateTime, formatRelativeTime } from '@/lib/format'
import type { ReleaseNote } from '@/lib/beta-ops-api'

const RELEASE_TYPES = ['major', 'minor', 'patch', 'hotfix', 'beta']
const STAGE_OPTIONS = [
  'draft',
  'internal',
  'canary',
  'beta',
  'rolling',
  'general_availability',
  'rollback',
]

function prettyStage(stage: string | null): string {
  if (!stage) return '—'
  return stage.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function ReleaseTypeBadge({ type }: { type: string }) {
  const variant =
    type === 'major'
      ? 'default'
      : type === 'minor'
        ? 'secondary'
        : type === 'patch'
          ? 'outline'
          : type === 'hotfix'
            ? 'destructive'
            : 'warning'
  return (
    <Badge variant={variant as 'default' | 'secondary' | 'outline' | 'destructive' | 'warning'} className="capitalize">
      {type}
    </Badge>
  )
}

interface CreateReleaseDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function CreateReleaseDialog({ open, onOpenChange }: CreateReleaseDialogProps) {
  const createMutation = useCreateRelease()
  const [version, setVersion] = React.useState('')
  const [releaseType, setReleaseType] = React.useState('minor')
  const [title, setTitle] = React.useState('')
  const [summary, setSummary] = React.useState('')
  const [body, setBody] = React.useState('')
  const [featureFreeze, setFeatureFreeze] = React.useState(false)
  const [published, setPublished] = React.useState(false)

  const reset = () => {
    setVersion('')
    setReleaseType('minor')
    setTitle('')
    setSummary('')
    setBody('')
    setFeatureFreeze(false)
    setPublished(false)
  }

  const handleSubmit = async () => {
    if (!version || !title) {
      toast.error('Version and title are required')
      return
    }
    try {
      await createMutation.mutateAsync({
        version,
        release_type: releaseType,
        title,
        summary: summary || null,
        body,
        feature_freeze: featureFreeze,
        published,
      })
      toast.success('Release created')
      reset()
      onOpenChange(false)
    } catch {
      toast.error('Failed to create release')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Release</DialogTitle>
          <DialogDescription>
            Publish a new release note. Set feature freeze to block new features from shipping.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="rel-version">Version</Label>
              <Input
                id="rel-version"
                placeholder="1.2.3"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="rel-type">Release type</Label>
              <Select value={releaseType} onValueChange={setReleaseType}>
                <SelectTrigger id="rel-type">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  {RELEASE_TYPES.map((t) => (
                    <SelectItem key={t} value={t} className="capitalize">
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="rel-title">Title</Label>
            <Input
              id="rel-title"
              placeholder="A short, descriptive title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="rel-summary">Summary</Label>
            <Input
              id="rel-summary"
              placeholder="One-line summary"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="rel-body">Body (Markdown)</Label>
            <Textarea
              id="rel-body"
              placeholder="## What's new…"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={5}
            />
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <Checkbox
                id="rel-freeze"
                checked={featureFreeze}
                onCheckedChange={(v) => setFeatureFreeze(Boolean(v))}
              />
              <Label htmlFor="rel-freeze" className="cursor-pointer">
                Feature freeze
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="rel-published"
                checked={published}
                onCheckedChange={(v) => setPublished(Boolean(v))}
              />
              <Label htmlFor="rel-published" className="cursor-pointer">
                Publish immediately
              </Label>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={createMutation.isPending}>
            Create release
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

interface EditReleaseDialogProps {
  release: ReleaseNote | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function EditReleaseDialog({ release, open, onOpenChange }: EditReleaseDialogProps) {
  const updateMutation = useUpdateRelease()
  const [title, setTitle] = React.useState('')
  const [summary, setSummary] = React.useState('')
  const [body, setBody] = React.useState('')
  const [featureFreeze, setFeatureFreeze] = React.useState(false)
  const [published, setPublished] = React.useState(false)

  React.useEffect(() => {
    if (release) {
      setTitle(release.title ?? '')
      setSummary(release.summary ?? '')
      setBody(release.body ?? '')
      setFeatureFreeze(release.feature_freeze ?? false)
      setPublished(Boolean(release.published_at))
    }
  }, [release])

  const handleSubmit = async () => {
    if (!release) return
    try {
      await updateMutation.mutateAsync({
        releaseId: release.id,
        payload: {
          title,
          summary: summary || null,
          body,
          feature_freeze: featureFreeze,
          published: published,
        },
      })
      toast.success('Release updated')
      onOpenChange(false)
    } catch {
      toast.error('Failed to update release')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit Release {release?.version}</DialogTitle>
          <DialogDescription>
            Update release metadata, body, or freeze state.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="edit-title">Title</Label>
            <Input
              id="edit-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-summary">Summary</Label>
            <Input
              id="edit-summary"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-body">Body (Markdown)</Label>
            <Textarea
              id="edit-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={5}
            />
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <Checkbox
                id="edit-freeze"
                checked={featureFreeze}
                onCheckedChange={(v) => setFeatureFreeze(Boolean(v))}
              />
              <Label htmlFor="edit-freeze" className="cursor-pointer">
                Feature freeze
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id="edit-published"
                checked={published}
                onCheckedChange={(v) => setPublished(Boolean(v))}
              />
              <Label htmlFor="edit-published" className="cursor-pointer">
                Published
              </Label>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={updateMutation.isPending}>
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

interface AddStageDialogProps {
  release: ReleaseNote | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function AddStageDialog({ release, open, onOpenChange }: AddStageDialogProps) {
  const addStage = useAddReleaseStage()
  const [stage, setStage] = React.useState('canary')
  const [rollout, setRollout] = React.useState('25')
  const [notes, setNotes] = React.useState('')

  React.useEffect(() => {
    if (open) {
      setStage('canary')
      setRollout('25')
      setNotes('')
    }
  }, [open])

  const handleSubmit = async () => {
    if (!release) return
    const pct = Number(rollout)
    if (!Number.isFinite(pct) || pct < 0 || pct > 100) {
      toast.error('Rollout percentage must be 0–100')
      return
    }
    try {
      await addStage.mutateAsync({
        releaseId: release.id,
        payload: { stage, rollout_percentage: pct, notes: notes || undefined },
      })
      toast.success('Stage added')
      onOpenChange(false)
    } catch {
      toast.error('Failed to add stage')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Stage to {release?.version}</DialogTitle>
          <DialogDescription>
            Advance this release to the next rollout stage.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="stage-name">Stage</Label>
            <Select value={stage} onValueChange={setStage}>
              <SelectTrigger id="stage-name">
                <SelectValue placeholder="Stage" />
              </SelectTrigger>
              <SelectContent>
                {STAGE_OPTIONS.map((s) => (
                  <SelectItem key={s} value={s}>
                    {prettyStage(s)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="stage-rollout">Rollout percentage</Label>
            <Input
              id="stage-rollout"
              type="number"
              min={0}
              max={100}
              value={rollout}
              onChange={(e) => setRollout(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="stage-notes">Notes</Label>
            <Textarea
              id="stage-notes"
              placeholder="Optional context for this stage"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={addStage.isPending}>
            Add stage
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

interface ReleaseSectionListProps {
  title: string
  icon: React.ComponentType<{ className?: string }>
  items: Array<Record<string, unknown>>
}

function ReleaseSectionList({ title, icon: Icon, items }: ReleaseSectionListProps) {
  if (!items || items.length === 0) return null
  return (
    <div>
      <h4 className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        <Icon className="h-3 w-3" aria-hidden="true" />
        {title}
      </h4>
      <ul className="space-y-1 pl-1 text-sm">
        {items.map((item, i) => (
          <li key={i} className="text-foreground">
            {String(item.title ?? item.description ?? item.summary ?? JSON.stringify(item))}
          </li>
        ))}
      </ul>
    </div>
  )
}

function ReleaseCard({
  release,
  onEdit,
  onAddStage,
}: {
  release: ReleaseNote
  onEdit: (r: ReleaseNote) => void
  onAddStage: (r: ReleaseNote) => void
}) {
  const [expanded, setExpanded] = React.useState(false)

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="text-lg">{release.version}</CardTitle>
              <ReleaseTypeBadge type={release.release_type} />
              <Badge variant="outline" className="text-xs">
                {prettyStage(release.current_stage)}
              </Badge>
              {release.feature_freeze && (
                <Badge variant="warning" className="text-xs">
                  <Snowflake className="mr-1 h-3 w-3" aria-hidden="true" />
                  Freeze
                </Badge>
              )}
              {release.published_at && (
                <Badge variant="success" className="text-xs">
                  <CheckCircle2 className="mr-1 h-3 w-3" aria-hidden="true" />
                  Published
                </Badge>
              )}
            </div>
            <CardDescription className="mt-1">
              {release.title}
              {release.published_at && (
                <> • published {formatRelativeTime(release.published_at)}</>
              )}
            </CardDescription>
          </div>
          <div className="flex shrink-0 gap-2">
            <Button size="sm" variant="outline" onClick={() => onEdit(release)}>
              <Pencil className="mr-1 h-3 w-3" aria-hidden="true" />
              Edit
            </Button>
            <Button size="sm" variant="outline" onClick={() => onAddStage(release)}>
              <GitBranch className="mr-1 h-3 w-3" aria-hidden="true" />
              Add Stage
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {release.summary && <p className="text-sm text-muted-foreground">{release.summary}</p>}

        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Rollout</span>
            <span className="font-medium">{release.rollout_percentage}%</span>
          </div>
          <Progress value={release.rollout_percentage} />
        </div>

        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          aria-expanded={expanded}
        >
          {expanded ? (
            <ChevronDown className="h-3 w-3" aria-hidden="true" />
          ) : (
            <ChevronRight className="h-3 w-3" aria-hidden="true" />
          )}
          {expanded ? 'Hide details' : 'Show details'}
        </button>

        {expanded && (
          <div className="grid gap-4 border-t pt-3 sm:grid-cols-2">
            <ReleaseSectionList title="Features" icon={Sparkles} items={release.features ?? []} />
            <ReleaseSectionList title="Bug Fixes" icon={Bug} items={release.bug_fixes ?? []} />
            <ReleaseSectionList
              title="Breaking Changes"
              icon={AlertTriangle}
              items={release.breaking_changes ?? []}
            />
            <ReleaseSectionList
              title="Known Issues"
              icon={CircleAlert}
              items={release.known_issues ?? []}
            />
            {release.body && (
              <div className="sm:col-span-2">
                <h4 className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Body
                </h4>
                <pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-muted p-2 text-xs">
                  {release.body}
                </pre>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ReleasesSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading releases">
      <Skeleton className="h-10 w-72" />
      <Skeleton className="h-24 w-full" />
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-40 w-full" />
      ))}
    </div>
  )
}

export default function ReleasesPage() {
  const { data, isLoading, isError, error, refetch } = useReleases()
  const [createOpen, setCreateOpen] = React.useState(false)
  const [editing, setEditing] = React.useState<ReleaseNote | null>(null)
  const [editOpen, setEditOpen] = React.useState(false)
  const [staging, setStaging] = React.useState<ReleaseNote | null>(null)
  const [stageOpen, setStageOpen] = React.useState(false)

  const handleEdit = (r: ReleaseNote) => {
    setEditing(r)
    setEditOpen(true)
  }
  const handleAddStage = (r: ReleaseNote) => {
    setStaging(r)
    setStageOpen(true)
  }

  if (isLoading) return <ReleasesSkeleton />
  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to load releases"
        description="We couldn't fetch the release management data."
        error={error as Error | undefined}
        onRetry={() => refetch()}
      />
    )
  }

  const releases = data.releases ?? []
  const timeline = data.version_timeline ?? []
  const rollbackHistory = data.rollback_history ?? []

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <Rocket className="h-6 w-6 text-primary" aria-hidden="true" />
            Releases
          </h1>
          <p className="text-sm text-muted-foreground">
            Manage release notes, rollout stages, and version history.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} leftIcon={<Plus className="h-4 w-4" aria-hidden="true" />}>
          Create Release
        </Button>
      </header>

      <section className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Current Version</CardDescription>
            <CardTitle className="text-3xl">
              {data.current_version ?? '—'}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card
          className={cn(
            data.feature_freeze_active ? 'border-warning/50 bg-warning/5' : '',
          )}
        >
          <CardHeader className="pb-2">
            <CardDescription>Feature Freeze</CardDescription>
            <CardTitle className="flex items-center gap-2 text-2xl">
              <Snowflake
                className={cn(
                  'h-5 w-5',
                  data.feature_freeze_active ? 'text-warning' : 'text-muted-foreground',
                )}
                aria-hidden="true"
              />
              {data.feature_freeze_active ? 'Active' : 'Inactive'}
            </CardTitle>
          </CardHeader>
        </Card>
      </section>

      <section aria-label="Releases" className="space-y-4">
        <h2 className="text-lg font-semibold">Releases</h2>
        {releases.length === 0 ? (
          <EmptyState
            icon={Rocket}
            title="No releases yet"
            description="Create your first release to start tracking rollouts."
          />
        ) : (
          releases.map((r) => (
            <ReleaseCard
              key={r.id}
              release={r}
              onEdit={handleEdit}
              onAddStage={handleAddStage}
            />
          ))
        )}
      </section>

      <section aria-label="Version timeline" className="space-y-3">
        <h2 className="text-lg font-semibold">Version Timeline</h2>
        {timeline.length === 0 ? (
          <Card>
            <CardContent>
              <p className="py-6 text-center text-sm text-muted-foreground">
                No timeline events yet.
              </p>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="p-4">
              <ol className="relative space-y-4 border-l-2 border-border pl-6">
                {timeline.map((event, idx) => (
                  <li key={idx} className="relative">
                    <span
                      className="absolute -left-[27px] top-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary"
                      aria-hidden="true"
                    >
                      <span className="h-2 w-2 rounded-full bg-primary-foreground" />
                    </span>
                    <div className="flex flex-wrap items-baseline gap-2">
                      <span className="font-mono text-sm font-semibold">
                        {String(event.version ?? event.release_version ?? '—')}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {prettyStage(String(event.stage ?? event.current_stage ?? '—'))}
                      </Badge>
                      {typeof event.timestamp === 'string' && (
                        <span className="text-xs text-muted-foreground">
                          {formatDateTime(String(event.timestamp))}
                        </span>
                      )}
                    </div>
                    {typeof event.notes === 'string' && event.notes && (
                      <p className="mt-1 text-sm text-muted-foreground">
                        {String(event.notes)}
                      </p>
                    )}
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        )}
      </section>

      <section aria-label="Rollback history" className="space-y-3">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <History className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
          Rollback History
        </h2>
        {rollbackHistory.length === 0 ? (
          <Card>
            <CardContent>
              <p className="py-6 text-center text-sm text-muted-foreground">
                No rollbacks recorded.
              </p>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="p-0">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b text-xs uppercase tracking-wider text-muted-foreground">
                    <th scope="col" className="px-3 py-2 font-semibold">Version</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Rolled back to</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Timestamp</th>
                    <th scope="col" className="px-3 py-2 font-semibold">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {rollbackHistory.map((r, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="px-3 py-2 font-mono text-xs">
                        {String(r.version ?? r.from_version ?? '—')}
                      </td>
                      <td className="px-3 py-2 font-mono text-xs">
                        {String(r.rolled_back_to ?? r.to_version ?? '—')}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {r.timestamp ? formatDateTime(String(r.timestamp)) : '—'}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {String(r.reason ?? '—')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}
      </section>

      <CreateReleaseDialog open={createOpen} onOpenChange={setCreateOpen} />
      <EditReleaseDialog release={editing} open={editOpen} onOpenChange={setEditOpen} />
      <AddStageDialog release={staging} open={stageOpen} onOpenChange={setStageOpen} />
    </div>
  )
}
