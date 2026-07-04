'use client'

import * as React from 'react'
import {
  Star,
  ThumbsUp,
  ThumbsDown,
  Copy,
  Pencil,
  Search,
  Flame,
  Layers,
} from 'lucide-react'
import { toast } from 'sonner'

import {
  useFeedbackPlatform,
  useVoteOnFeedback,
  useUpdateFeedbackMeta,
  useMarkDuplicate,
} from '@/hooks/use-beta-ops'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
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
import { formatNumber, formatRelativeTime } from '@/lib/format'
import type { FeedbackItem } from '@/lib/beta-ops-api'

const PRIORITY_VARIANT: Record<string, 'destructive' | 'warning' | 'secondary' | 'default'> = {
  critical: 'destructive',
  high: 'destructive',
  medium: 'warning',
  low: 'secondary',
}

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'success' | 'warning' | 'destructive'> = {
  open: 'default',
  in_progress: 'warning',
  resolved: 'success',
  closed: 'secondary',
  duplicate: 'secondary',
}

function Stars({ rating }: { rating: number }) {
  return (
    <span
      className="inline-flex items-center"
      aria-label={`${rating} out of 5 stars`}
    >
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={cn(
            'h-3.5 w-3.5',
            i < rating ? 'fill-warning text-warning' : 'text-muted-foreground',
          )}
          aria-hidden="true"
        />
      ))}
    </span>
  )
}

interface EditMetaDialogProps {
  feedback: FeedbackItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

function EditMetaDialog({ feedback, open, onOpenChange }: EditMetaDialogProps) {
  const updateMeta = useUpdateFeedbackMeta()
  const [priority, setPriority] = React.useState('')
  const [roadmapStatus, setRoadmapStatus] = React.useState('')
  const [roadmapLink, setRoadmapLink] = React.useState('')
  const [assignedTo, setAssignedTo] = React.useState('')
  const [tagsText, setTagsText] = React.useState('')

  React.useEffect(() => {
    if (feedback) {
      setPriority(feedback.priority ?? '')
      setRoadmapStatus(feedback.roadmap_status ?? '')
      setRoadmapLink('')
      setAssignedTo('')
      setTagsText((feedback.tags ?? []).join(', '))
    }
  }, [feedback])

  const handleSubmit = async () => {
    if (!feedback) return
    try {
      await updateMeta.mutateAsync({
        feedbackId: feedback.id,
        payload: {
          priority: priority || undefined,
          roadmap_status: roadmapStatus || undefined,
          roadmap_link: roadmapLink || undefined,
          assigned_to: assignedTo || undefined,
          tags: tagsText
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean),
        },
      })
      toast.success('Feedback metadata updated')
      onOpenChange(false)
    } catch {
      toast.error('Failed to update feedback')
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Feedback Metadata</DialogTitle>
          <DialogDescription>
            Update priority, roadmap status, and tags for this feedback item.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="meta-priority">Priority</Label>
            <Select value={priority} onValueChange={setPriority}>
              <SelectTrigger id="meta-priority">
                <SelectValue placeholder="Select priority" />
              </SelectTrigger>
              <SelectContent>
                {['critical', 'high', 'medium', 'low'].map((p) => (
                  <SelectItem key={p} value={p}>
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="meta-roadmap">Roadmap status</Label>
            <Select value={roadmapStatus} onValueChange={setRoadmapStatus}>
              <SelectTrigger id="meta-roadmap">
                <SelectValue placeholder="Select roadmap status" />
              </SelectTrigger>
              <SelectContent>
                {['idea', 'exploring', 'planned', 'in_progress', 'shipped', 'declined'].map((p) => (
                  <SelectItem key={p} value={p}>
                    {p.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="meta-link">Roadmap link</Label>
            <Input
              id="meta-link"
              placeholder="https://github.com/org/repo/issues/123"
              value={roadmapLink}
              onChange={(e) => setRoadmapLink(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="meta-assignee">Assigned to</Label>
            <Input
              id="meta-assignee"
              placeholder="user id or username"
              value={assignedTo}
              onChange={(e) => setAssignedTo(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="meta-tags">Tags (comma separated)</Label>
            <Textarea
              id="meta-tags"
              placeholder="ui, regression, onboarding"
              value={tagsText}
              onChange={(e) => setTagsText(e.target.value)}
              rows={2}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} loading={updateMeta.isPending}>
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function FeedbackRow({
  item,
  onEdit,
}: {
  item: FeedbackItem
  onEdit: (item: FeedbackItem) => void
}) {
  const voteMutation = useVoteOnFeedback()
  const markDuplicate = useMarkDuplicate()
  const [duplicateOf, setDuplicateOf] = React.useState('')

  const handleVote = async (vote: number) => {
    try {
      await voteMutation.mutateAsync({ feedbackId: item.id, vote })
      toast.success(vote > 0 ? 'Upvoted' : 'Downvoted')
    } catch {
      toast.error('Failed to register vote')
    }
  }

  const handleMarkDuplicate = async () => {
    if (!duplicateOf) {
      toast.error('Enter the duplicate-of feedback ID first')
      return
    }
    try {
      await markDuplicate.mutateAsync({ feedbackId: item.id, duplicateOf })
      toast.success('Marked as duplicate')
      setDuplicateOf('')
    } catch {
      toast.error('Failed to mark duplicate')
    }
  }

  return (
    <article className="rounded-lg border p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Stars rating={item.rating} />
            <Badge variant="secondary" className="text-xs">
              {item.category}
            </Badge>
            <Badge
              variant={PRIORITY_VARIANT[item.priority] ?? 'secondary'}
              className="text-xs capitalize"
            >
              {item.priority}
            </Badge>
            {item.roadmap_status && (
              <Badge variant="outline" className="text-xs capitalize">
                {item.roadmap_status.replace(/_/g, ' ')}
              </Badge>
            )}
            {item.duplicate_of && (
              <Badge variant="secondary" className="text-xs">
                Duplicate of {item.duplicate_of.slice(0, 8)}
              </Badge>
            )}
          </div>
          <p className="text-sm text-foreground">{item.comment}</p>
          {item.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {item.tags.map((t) => (
                <span
                  key={t}
                  className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                >
                  #{t}
                </span>
              ))}
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            {formatRelativeTime(item.created_at)} • user {item.user_id.slice(0, 8)}
          </p>
        </div>

        <div className="flex shrink-0 flex-col items-end gap-2">
          <div className="flex items-center gap-2">
            <Button
              size="icon"
              variant="ghost"
              aria-label="Upvote"
              onClick={() => handleVote(1)}
              loading={voteMutation.isPending}
            >
              <ThumbsUp className="h-4 w-4" aria-hidden="true" />
            </Button>
            <span className="min-w-[2rem] text-center text-sm font-semibold tabular-nums">
              {item.vote_score}
            </span>
            <Button
              size="icon"
              variant="ghost"
              aria-label="Downvote"
              onClick={() => handleVote(-1)}
              loading={voteMutation.isPending}
            >
              <ThumbsDown className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => onEdit(item)}>
              <Pencil className="mr-1 h-3 w-3" aria-hidden="true" />
              Edit Meta
            </Button>
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 border-t pt-3">
        <Input
          aria-label={`Duplicate-of ID for feedback ${item.id}`}
          placeholder="Duplicate of (feedback id)"
          value={duplicateOf}
          onChange={(e) => setDuplicateOf(e.target.value)}
          className="h-8 max-w-xs text-xs"
        />
        <Button
          size="sm"
          variant="ghost"
          onClick={handleMarkDuplicate}
          loading={markDuplicate.isPending}
        >
          <Copy className="mr-1 h-3 w-3" aria-hidden="true" />
          Mark Duplicate
        </Button>
      </div>
    </article>
  )
}

function FeedbackSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading feedback">
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-10 w-full" />
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-28 w-full" />
      ))}
    </div>
  )
}

export default function FeedbackPage() {
  const { data, isLoading, isError, error, refetch } = useFeedbackPlatform(100)
  const [categoryFilter, setCategoryFilter] = React.useState('all')
  const [priorityFilter, setPriorityFilter] = React.useState('all')
  const [statusFilter, setStatusFilter] = React.useState('all')
  const [search, setSearch] = React.useState('')
  const [editing, setEditing] = React.useState<FeedbackItem | null>(null)
  const [editOpen, setEditOpen] = React.useState(false)

  const handleEdit = (item: FeedbackItem) => {
    setEditing(item)
    setEditOpen(true)
  }

  if (isLoading) return <FeedbackSkeleton />
  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to load feedback"
        description="We couldn't fetch the feedback platform data."
        error={error as Error | undefined}
        onRetry={() => refetch()}
      />
    )
  }

  const categories = Object.keys(data.by_category ?? {})
  const priorities = Object.keys(data.by_priority ?? {})
  const statuses = Object.keys(data.by_status ?? {})

  const filtered = (data.items ?? []).filter((item) => {
    if (categoryFilter !== 'all' && item.category !== categoryFilter) return false
    if (priorityFilter !== 'all' && item.priority !== priorityFilter) return false
    if (statusFilter !== 'all' && item.status !== statusFilter) return false
    if (search) {
      const q = search.toLowerCase()
      if (
        !item.comment.toLowerCase().includes(q) &&
        !item.category.toLowerCase().includes(q) &&
        !item.tags.some((t) => t.toLowerCase().includes(q))
      )
        return false
    }
    return true
  })

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Feedback Review</h1>
        <p className="text-sm text-muted-foreground">
          Triage, vote on, and route beta feedback to your roadmap.
        </p>
      </header>

      <section
        aria-label="Feedback summary"
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total</CardDescription>
            <CardTitle className="text-3xl">{formatNumber(data.total)}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Open</CardDescription>
            <CardTitle className="text-3xl">
              {formatNumber(data.by_status?.open ?? 0)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Avg Vote Score</CardDescription>
            <CardTitle className="text-3xl">
              {data.avg_vote_score.toFixed(1)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Categories</CardDescription>
            <CardContent className="pt-2 text-xs text-muted-foreground">
              {categories.length === 0 ? (
                <span>—</span>
              ) : (
                <ul className="space-y-1">
                  {categories.slice(0, 4).map((c) => (
                    <li key={c} className="flex justify-between">
                      <span className="capitalize">{c}</span>
                      <span className="font-medium text-foreground">
                        {formatNumber(data.by_category[c] ?? 0)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </CardHeader>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Search className="h-4 w-4" aria-hidden="true" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="filter-search">Search</Label>
              <Input
                id="filter-search"
                placeholder="Keyword, tag…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="filter-category">Category</Label>
              <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                <SelectTrigger id="filter-category">
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  {categories.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="filter-priority">Priority</Label>
              <Select value={priorityFilter} onValueChange={setPriorityFilter}>
                <SelectTrigger id="filter-priority">
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  {priorities.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="filter-status">Status</Label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger id="filter-status">
                  <SelectValue placeholder="All" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  {statuses.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <section aria-label="Feedback list" className="space-y-3">
          <h2 className="text-lg font-semibold">
            Feedback ({formatNumber(filtered.length)} shown)
          </h2>
          {filtered.length === 0 ? (
            <EmptyState
              icon={Layers}
              title="No feedback matches filters"
              description="Try adjusting your filters or search query."
            />
          ) : (
            filtered.map((item) => (
              <FeedbackRow key={item.id} item={item} onEdit={handleEdit} />
            ))
          )}
        </section>

        <aside aria-label="Top voted feedback" className="space-y-3">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Flame className="h-4 w-4 text-warning" aria-hidden="true" />
                Top Voted
              </CardTitle>
              <CardDescription>Highest-scoring feedback items.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {(data.top_voted ?? []).slice(0, 10).map((item, idx) => (
                <div key={item.id} className="space-y-1 border-b pb-2 last:border-0">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-medium text-muted-foreground">
                      #{idx + 1}
                    </span>
                    <Badge variant="secondary" className="text-xs">
                      {item.vote_score} votes
                    </Badge>
                  </div>
                  <p className="line-clamp-2 text-sm">{item.comment}</p>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant="outline" className="text-xs">
                      {item.category}
                    </Badge>
                    <span>{formatRelativeTime(item.created_at)}</span>
                  </div>
                </div>
              ))}
              {(!data.top_voted || data.top_voted.length === 0) && (
                <p className="text-sm text-muted-foreground">No voted feedback yet.</p>
              )}
            </CardContent>
          </Card>
        </aside>
      </div>

      <section aria-label="Potential duplicates" className="space-y-3">
        <h2 className="text-lg font-semibold">Potential Duplicates</h2>
        {(data.potential_duplicates ?? []).length === 0 ? (
          <Card>
            <CardContent>
              <p className="py-6 text-center text-sm text-muted-foreground">
                No potential duplicates detected.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {(data.potential_duplicates ?? []).map((pair, idx) => {
              const a = (pair.feedback_a as FeedbackItem | undefined) ?? (pair.a as FeedbackItem | undefined)
              const b = (pair.feedback_b as FeedbackItem | undefined) ?? (pair.b as FeedbackItem | undefined)
              const similarity = (pair.similarity as number | undefined) ?? (pair.score as number | undefined) ?? 0
              return (
                <Card key={idx}>
                  <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0 flex-1 space-y-1 text-sm">
                      <p>
                        <span className="font-medium">{a ? a.comment.slice(0, 80) : '—'}</span>
                      </p>
                      <p className="text-muted-foreground">
                        ↔ {b ? b.comment.slice(0, 80) : '—'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Similarity: <span className="font-medium text-foreground">{(similarity * 100).toFixed(1)}%</span>
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => toast.info('Merge action coming soon')}
                    >
                      Merge
                    </Button>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </section>

      <EditMetaDialog feedback={editing} open={editOpen} onOpenChange={setEditOpen} />
    </div>
  )
}
