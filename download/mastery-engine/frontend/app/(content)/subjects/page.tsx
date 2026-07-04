'use client'

import * as React from 'react'
import Link from 'next/link'
import { Search, BookOpen, Plus, Clock } from 'lucide-react'

import { useContentSubjects } from '@/hooks/use-content'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/ui/empty-state'
import { useDebounce } from '@/hooks/use-debounce'
import { formatDate } from '@/lib/format'
import { cn } from '@/lib/cn'

export default function ContentSubjectsPage() {
  const { data: subjects, isLoading } = useContentSubjects()
  const [search, setSearch] = React.useState('')
  const debouncedSearch = useDebounce(search, 300)

  const filtered = React.useMemo(() => {
    if (!subjects) return []
    if (!debouncedSearch) return subjects
    const q = debouncedSearch.toLowerCase()
    return subjects.filter(
      (s) => s.name.toLowerCase().includes(q) || s.code.toLowerCase().includes(q),
    )
  }, [subjects, debouncedSearch])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-10 w-full" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Subjects</h1>
          <p className="text-sm text-muted-foreground">Create and manage curriculum subjects</p>
        </div>
        <Button asChild>
          <Link href="/content/subjects/create">
            <Plus className="mr-2 h-4 w-4" />
            Create subject
          </Link>
        </Button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <Input
          placeholder="Search subjects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
          aria-label="Search subjects"
        />
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No subjects found"
          description={debouncedSearch ? "Try a different search term." : "Create your first subject to get started."}
          action={debouncedSearch ? undefined : { label: 'Create subject', onClick: () => window.location.href = '/content/subjects/create' }}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3" role="list">
          {filtered.map((subject) => (
            <Card key={subject.id} hover role="listitem">
              <Link href={`/content/subjects/${subject.id}`} className="block">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium">{subject.name}</p>
                      <p className="text-xs text-muted-foreground">{subject.code}</p>
                    </div>
                    <Badge
                      variant={
                        subject.status === 'published' ? 'success' :
                        subject.status === 'archived' ? 'secondary' : 'warning'
                      }
                      className="text-xs capitalize"
                    >
                      {subject.status}
                    </Badge>
                  </div>
                  {subject.description && (
                    <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">{subject.description}</p>
                  )}
                  {subject.published_at && (
                    <p className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" aria-hidden="true" />
                      Published {formatDate(subject.published_at)}
                    </p>
                  )}
                </CardContent>
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
