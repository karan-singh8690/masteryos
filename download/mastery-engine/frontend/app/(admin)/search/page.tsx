'use client'

import * as React from 'react'
import { Search, Users, Building2, Server, FileText, Flag } from 'lucide-react'

import { useAdminSearch } from '@/hooks/use-admin'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/ui/empty-state'
import { useDebounce } from '@/hooks/use-debounce'

export default function AdminSearchPage() {
  const [query, setQuery] = React.useState('')
  const debounced = useDebounce(query, 300)
  const { data: results, isLoading } = useAdminSearch(debounced, debounced.length > 0)

  const hasResults = results && (results.users.length > 0 || results.organizations.length > 0 || results.workers.length > 0 || results.audit_logs.length > 0 || results.feature_flags.length > 0)

  return (
    <div className="max-w-3xl space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Admin Search</h1><p className="text-sm text-muted-foreground">Search across all platform entities</p></div>
      <div className="relative"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" /><Input placeholder="Search users, organizations, workers..." value={query} onChange={(e) => setQuery(e.target.value)} className="pl-10 h-12 text-base" aria-label="Admin search" autoFocus /></div>

      {isLoading && <p className="text-sm text-muted-foreground">Searching...</p>}
      {!isLoading && !debounced && <EmptyState icon={Search} title="Start searching" description="Type to search across all admin entities." />}
      {!isLoading && debounced && !hasResults && <EmptyState icon={Search} title="No results found" description={`No matches for "${debounced}".`} />}
      {!isLoading && hasResults && results && (
        <div className="space-y-6">
          {results.users.length > 0 && <Section icon={Users} title="Users" items={results.users.map(u => ({ id: u.id, name: `${u.display_name} (${u.email})`, status: u.status }))} />}
          {results.organizations.length > 0 && <Section icon={Building2} title="Organizations" items={results.organizations.map(o => ({ id: o.id, name: o.name, status: o.status }))} />}
          {results.workers.length > 0 && <Section icon={Server} title="Workers" items={results.workers.map(w => ({ id: w.worker_id, name: w.worker_id, status: w.status }))} />}
          {results.feature_flags.length > 0 && <Section icon={Flag} title="Feature Flags" items={results.feature_flags.map(f => ({ id: f.id, name: f.name, status: f.enabled ? 'enabled' : 'disabled' }))} />}
          {results.audit_logs.length > 0 && <Section icon={FileText} title="Audit Logs" items={results.audit_logs.map(a => ({ id: a.id, name: `${a.action} — ${a.user_email || 'system'}`, status: a.success ? 'success' : 'failed' }))} />}
        </div>
      )}
    </div>
  )
}

function Section({ icon: Icon, title, items }: { icon: React.ComponentType<{ className?: string }>; title: string; items: { id: string; name: string; status?: string }[] }) {
  return (
    <div>
      <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground"><Icon className="h-4 w-4" aria-hidden="true" />{title} ({items.length})</h2>
      <ul className="space-y-1" role="list">{items.map((item) => (
        <li key={item.id}><Card hover><CardContent className="flex items-center justify-between p-3"><span className="text-sm font-medium">{item.name}</span>{item.status && <Badge variant="outline" className="text-xs capitalize">{item.status}</Badge>}</CardContent></Card></li>
      ))}</ul>
    </div>
  )
}
