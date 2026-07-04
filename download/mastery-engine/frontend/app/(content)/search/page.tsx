'use client'

import * as React from 'react'
import { Search as SearchIcon, BookOpen, FileCode, Target, AlertTriangle, Package } from 'lucide-react'

import { useContentSearch } from '@/hooks/use-content'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { EmptyState } from '@/components/ui/empty-state'
import { useDebounce } from '@/hooks/use-debounce'
import { Skeleton } from '@/components/ui/skeleton'

export default function ContentSearchPage() {
  const [query, setQuery] = React.useState('')
  const debouncedQuery = useDebounce(query, 300)

  const { data: results, isLoading } = useContentSearch(
    debouncedQuery,
    debouncedQuery.length > 0,
  )

  const hasResults = results && (
    results.subjects.length > 0 ||
    results.concepts.length > 0 ||
    results.templates.length > 0 ||
    results.objectives.length > 0 ||
    results.misconceptions.length > 0 ||
    results.content_packs.length > 0
  )

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Content search</h1>
        <p className="text-sm text-muted-foreground">Search across all content types</p>
      </div>

      <div className="relative">
        <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <Input
          placeholder="Search subjects, concepts, templates..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10 h-12 text-base"
          aria-label="Search content"
          autoFocus
        />
      </div>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {!isLoading && !debouncedQuery && (
        <EmptyState
          icon={SearchIcon}
          title="Start searching"
          description="Type to search across subjects, concepts, templates, objectives, and misconceptions."
        />
      )}

      {!isLoading && debouncedQuery && !hasResults && (
        <EmptyState
          icon={SearchIcon}
          title="No results found"
          description={`No content matches "${debouncedQuery}".`}
        />
      )}

      {!isLoading && hasResults && results && (
        <div className="space-y-6">
          {/* Subjects */}
          {results.subjects.length > 0 && (
            <ResultSection icon={BookOpen} title="Subjects" items={results.subjects.map(s => ({ id: s.id, name: s.name, subtitle: s.code, status: s.status }))} />
          )}

          {/* Concepts */}
          {results.concepts.length > 0 && (
            <ResultSection icon={Target} title="Concepts" items={results.concepts.map(c => ({ id: c.id, name: c.name, subtitle: c.slug, status: c.status }))} />
          )}

          {/* Templates */}
          {results.templates.length > 0 && (
            <ResultSection icon={FileCode} title="Templates" items={results.templates.map(t => ({ id: t.id, name: t.code, subtitle: t.question_type, status: t.status }))} />
          )}

          {/* Objectives */}
          {results.objectives.length > 0 && (
            <ResultSection icon={Target} title="Learning objectives" items={results.objectives.map(o => ({ id: o.id, name: o.statement, subtitle: '', status: o.status }))} />
          )}

          {/* Misconceptions */}
          {results.misconceptions.length > 0 && (
            <ResultSection icon={AlertTriangle} title="Misconceptions" items={results.misconceptions.map(m => ({ id: m.id, name: m.name, subtitle: m.description, status: m.status }))} />
          )}

          {/* Content packs */}
          {results.content_packs.length > 0 && (
            <ResultSection icon={Package} title="Content packs" items={results.content_packs.map(p => ({ id: p.id, name: p.name, subtitle: p.description || '', status: p.status }))} />
          )}
        </div>
      )}
    </div>
  )
}

function ResultSection({
  icon: Icon,
  title,
  items,
}: {
  icon: React.ComponentType<{ className?: string }>
  title: string
  items: { id: string; name: string; subtitle?: string; status?: string }[]
}) {
  return (
    <div>
      <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        <Icon className="h-4 w-4" aria-hidden="true" />
        {title} ({items.length})
      </h2>
      <ul className="space-y-2" role="list">
        {items.map((item) => (
          <li key={item.id}>
            <Card hover>
              <CardContent className="flex items-center justify-between p-3">
                <div className="flex-1">
                  <p className="text-sm font-medium">{item.name}</p>
                  {item.subtitle && <p className="text-xs text-muted-foreground">{item.subtitle}</p>}
                </div>
                {item.status && (
                  <Badge
                    variant={item.status === 'published' ? 'success' : 'warning'}
                    className="text-xs capitalize"
                  >
                    {item.status}
                  </Badge>
                )}
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  )
}
