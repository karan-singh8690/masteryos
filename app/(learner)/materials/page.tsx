'use client'

import * as React from 'react'
import Link from 'next/link'
import { FileText, Clock, BookOpen, Lock, ChevronRight, Search } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { tokenStorage } from '@/lib/api-client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Material {
  id: string
  title: string
  description: string | null
  exam_name: string | null
  exam_year: number | null
  language: string
  page_count: number
  is_premium: boolean
  coin_cost: number
  material_type: string
  tags: string[]
  created_at: string | null
  progress: { current_page: number; pages_read: number; is_completed: boolean }
}

export default function MaterialsPage() {
  const [materials, setMaterials] = React.useState<Material[]>([])
  const [loading, setLoading] = React.useState(true)
  const [search, setSearch] = React.useState('')

  React.useEffect(() => { fetchMaterials() }, [])

  async function fetchMaterials() {
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/materials`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setMaterials(data.items || [])
      }
    } catch { /* empty */ }
    finally { setLoading(false) }
  }

  const filtered = materials.filter(m =>
    !search || m.title.toLowerCase().includes(search.toLowerCase()) ||
    m.tags?.some((t: string) => t.toLowerCase().includes(search.toLowerCase()))
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-500/20 border-t-emerald-500" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white">Study Materials</h1>
        <p className="mt-1 text-sm text-zinc-400">Read PDFs, notes, and formula sheets — view only, no download</p>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input placeholder="Search materials..." className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {filtered.length === 0 ? (
        <Card className="glass-card rounded-2xl border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <div className="rounded-full bg-white/5 p-4"><FileText className="h-8 w-8 text-muted-foreground" /></div>
            <h3 className="mt-4 text-lg font-semibold text-white">No materials available yet</h3>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">Study materials will appear here once uploaded by your instructor or admin.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filtered.map((m) => {
            const progressPct = m.page_count > 0 ? Math.round((m.progress.pages_read / m.page_count) * 100) : 0
            return (
              <Link key={m.id} href={`/materials/${m.id}`}>
                <Card className="glass-card group cursor-pointer rounded-2xl">
                  <CardContent className="flex items-start gap-4 p-5">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 ring-1 ring-inset ring-emerald-500/20 transition-transform group-hover:scale-110">
                      <FileText className="h-6 w-6 text-emerald-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="font-semibold text-white group-hover:text-emerald-400 transition-colors">{m.title}</h3>
                        {m.is_premium && (
                          <Badge variant="outline" className="shrink-0 border-amber-500/30 bg-amber-500/10 text-amber-400">
                            <Lock className="mr-1 h-3 w-3" />{m.coin_cost > 0 ? `${m.coin_cost} coins` : 'Premium'}
                          </Badge>
                        )}
                      </div>
                      {m.description && <p className="mt-1 text-sm text-zinc-400 line-clamp-2">{m.description}</p>}
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                        <span className="flex items-center gap-1"><FileText className="h-3 w-3" />{m.page_count} pages</span>
                        {m.exam_name && <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-xs">{m.exam_name}{m.exam_year ? ` ${m.exam_year}` : ''}</Badge>}
                        {m.tags?.map((tag) => <Badge key={tag} variant="secondary" className="text-xs bg-white/5 text-zinc-400">{tag}</Badge>)}
                      </div>
                      {m.progress.pages_read > 0 && (
                        <div className="mt-3">
                          <div className="flex items-center justify-between text-xs text-zinc-500">
                            <span>{m.progress.is_completed ? 'Completed' : `Page ${m.progress.current_page} of ${m.page_count}`}</span>
                            <span>{progressPct}%</span>
                          </div>
                          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
                            <div className={`h-full rounded-full ${m.progress.is_completed ? 'bg-emerald-500' : 'bg-gradient-to-r from-emerald-500 to-teal-500'}`} style={{ width: `${progressPct}%` }} />
                          </div>
                        </div>
                      )}
                    </div>
                    <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1" />
                  </CardContent>
                </Card>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
