'use client'

import { Flag, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { useFeatureFlags, useToggleFeatureFlag, useDeleteFeatureFlag, useCreateFeatureFlag } from '@/hooks/use-admin'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from '@/components/ui/dialog'
import * as React from 'react'

export default function FeatureFlagsPage() {
  const { data: flags, isLoading } = useFeatureFlags()
  const toggleMutation = useToggleFeatureFlag()
  const deleteMutation = useDeleteFeatureFlag()
  const createMutation = useCreateFeatureFlag()
  const [showCreate, setShowCreate] = React.useState(false)
  const [newKey, setNewKey] = React.useState('')
  const [newName, setNewName] = React.useState('')

  const handleCreate = async () => {
    if (!newKey || !newName) { toast.error('Key and name are required'); return }
    try { await createMutation.mutateAsync({ key: newKey, name: newName }); toast.success('Feature flag created'); setShowCreate(false); setNewKey(''); setNewName('') } catch { toast.error('Failed') }
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold tracking-tight">Feature Flags</h1><p className="text-sm text-muted-foreground">Manage feature rollouts</p></div>
        <Dialog open={showCreate} onOpenChange={setShowCreate}>
          <DialogTrigger asChild><Button><Plus className="mr-2 h-4 w-4" />Create Flag</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Create Feature Flag</DialogTitle></DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2"><Label htmlFor="flag-key">Key</Label><Input id="flag-key" placeholder="new_feature" value={newKey} onChange={(e) => setNewKey(e.target.value)} /></div>
              <div className="space-y-2"><Label htmlFor="flag-name">Name</Label><Input id="flag-name" placeholder="New Feature" value={newName} onChange={(e) => setNewName(e.target.value)} /></div>
            </div>
            <DialogFooter><Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button><Button onClick={handleCreate} loading={createMutation.isPending}>Create</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}</div> : (
        !flags || flags.length === 0 ? <EmptyState icon={Flag} title="No feature flags" description="Create a feature flag to manage rollouts." /> : (
          <div className="space-y-2">
            {flags.map((flag) => (
              <Card key={flag.id} hover>
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex-1"><div className="flex items-center gap-2"><p className="text-sm font-medium">{flag.name}</p><Badge variant="outline" className="text-xs font-mono">{flag.key}</Badge>{flag.enabled ? <Badge variant="success" className="text-xs">Enabled</Badge> : <Badge variant="secondary" className="text-xs">Disabled</Badge>}</div>{flag.description && <p className="mt-1 text-xs text-muted-foreground">{flag.description}</p>}{flag.rollout_percentage < 100 && <p className="mt-1 text-xs text-muted-foreground">Rollout: {flag.rollout_percentage}%</p>}</div>
                  <div className="flex items-center gap-2">
                    <Switch checked={flag.enabled} onCheckedChange={(checked) => toggleMutation.mutateAsync({ id: flag.id, enabled: checked }).then(() => toast.success(`Flag ${checked ? 'enabled' : 'disabled'}`)).catch(() => toast.error('Failed'))} aria-label={`Toggle ${flag.name}`} />
                    <Button size="icon" variant="ghost" onClick={() => { if (confirm('Delete this flag?')) deleteMutation.mutateAsync(flag.id).then(() => toast.success('Deleted')).catch(() => toast.error('Failed')) }} aria-label="Delete flag"><Trash2 className="h-4 w-4 text-destructive" /></Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )
      )}
    </div>
  )
}
