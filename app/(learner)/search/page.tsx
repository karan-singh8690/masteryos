'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { Search, BookOpen, GraduationCap, Clock } from 'lucide-react'

import { useSubjects } from '@/hooks/use-learner'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { useDebounce } from '@/hooks/use-debounce'
import { cn } from '@/lib/cn'

const SEARCH_CATEGORIES = [
  { key: 'subjects', label: 'Subjects', icon: BookOpen, href: '/subjects' },
  { key: 'study', label: 'Study', icon: GraduationCap, href: '/study/start' },
  { key: 'reviews', label: 'Reviews', icon: Clock, href: '/reviews' },
]

export default function SearchPage() {
  const router = useRouter()
  const [query, setQuery] = React.useState('')
  const debouncedQuery = useDebounce(query, 300)
  const { data: subjects } = useSubjects()

  const results = React.useMemo(() => {
    if (!debouncedQuery || !subjects) return []
    const q = debouncedQuery.toLowerCase()
    return subjects
      .filter((s) => s.status === 'published')
      .filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q),
      )
      .slice(0, 10)
  }, [subjects, debouncedQuery])

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Search</h1>
        <p className="text-sm text-muted-foreground">Find subjects, concepts, and more</p>
      </div>

      <Input
        type="search"
        placeholder="Search..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        autoFocus
        aria-label="Search"
        leftIcon={<Search className="h-4 w-4" />}
        className="h-12 text-base"
      />

      {/* Quick links */}
      {!debouncedQuery && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Quick links
          </h2>
          <div className="grid gap-2 sm:grid-cols-3">
            {SEARCH_CATEGORIES.map((cat) => {
              const Icon = cat.icon
              return (
                <button
                  key={cat.key}
                  onClick={() => router.push(cat.href)}
                  className="flex items-center gap-3 rounded-lg border p-4 text-left transition-colors hover:bg-muted/50"
                >
                  <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
                  <span className="text-sm font-medium">{cat.label}</span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Results */}
      {debouncedQuery && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Results ({results.length})
          </h2>
          {results.length === 0 ? (
            <EmptyState
              icon={Search}
              title="No results found"
              description={`No subjects match "${debouncedQuery}".`}
            />
          ) : (
            <ul className="space-y-2" role="list">
              {results.map((subject) => (
                <li key={subject.id}>
                  <Card hover>
                    <CardContent className="p-4">
                      <button
                        onClick={() => router.push(`/subjects/${subject.id}`)}
                        className="w-full text-left"
                      >
                        <div className="flex items-center gap-3">
                          <BookOpen className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                          <div className="flex-1">
                            <p className="text-sm font-medium">{subject.name}</p>
                            <p className="text-xs text-muted-foreground line-clamp-1">
                              {subject.description}
                            </p>
                          </div>
                        </div>
                      </button>
                    </CardContent>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
