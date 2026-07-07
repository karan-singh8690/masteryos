'use client'

import * as React from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ChevronLeft, ChevronRight, FileText, Loader2, AlertCircle, Eye, Lock, Coins, CheckCircle2 } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { tokenStorage } from '@/lib/api-client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function MaterialViewerPage() {
  const params = useParams()
  const router = useRouter()
  const materialId = params.materialId as string

  const [material, setMaterial] = React.useState<any>(null)
  const [access, setAccess] = React.useState<any>(null)
  const [currentPage, setCurrentPage] = React.useState(1)
  const [pageImageUrl, setPageImageUrl] = React.useState<string | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [pageLoading, setPageLoading] = React.useState(false)
  const [error, setError] = React.useState('')
  const readTimeRef = React.useRef(Date.now())

  React.useEffect(() => {
    fetchMaterial()
  }, [materialId])

  React.useEffect(() => {
    if (material) {
      fetchPage(currentPage)
    }
  }, [currentPage, material])

  // Disable right-click and text selection
  React.useEffect(() => {
    const handleContextMenu = (e: MouseEvent) => e.preventDefault()
    const handleSelectStart = (e: Event) => e.preventDefault()
    const handleDragStart = (e: DragEvent) => e.preventDefault()
    const handleKeyDown = (e: KeyboardEvent) => {
      // Block Ctrl+S (save), Ctrl+P (print), Ctrl+U (view source)
      if ((e.ctrlKey || e.metaKey) && ['s', 'p', 'u'].includes(e.key.toLowerCase())) {
        e.preventDefault()
      }
    }

    document.addEventListener('contextmenu', handleContextMenu)
    document.addEventListener('selectstart', handleSelectStart)
    document.addEventListener('dragstart', handleDragStart)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('contextmenu', handleContextMenu)
      document.removeEventListener('selectstart', handleSelectStart)
      document.removeEventListener('dragstart', handleDragStart)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  // Save progress on unmount or page change
  React.useEffect(() => {
    return () => {
      if (material) {
        const readTime = Math.floor((Date.now() - readTimeRef.current) / 1000)
        saveProgress(currentPage, readTime)
      }
    }
  }, [currentPage, material])

  async function fetchMaterial() {
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/materials/${materialId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setMaterial(data)

        // Phase C: Check access
        const accessRes = await fetch(`${API_URL}/api/v1/materials/${materialId}/access`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (accessRes.ok) {
          const accessData = await accessRes.json()
          setAccess(accessData)
          if (accessData.has_access) {
            // Load saved progress
            const progRes = await fetch(`${API_URL}/api/v1/materials/${materialId}/progress`, {
              headers: { Authorization: `Bearer ${token}` },
            })
            if (progRes.ok) {
              const prog = await progRes.json()
              if (prog.current_page > 0) {
                setCurrentPage(prog.current_page)
              }
            }
          }
        }
      } else {
        setError('Material not found')
      }
    } catch {
      setError('Failed to load material')
    } finally {
      setLoading(false)
    }
  }

  async function fetchPage(pageNum: number) {
    setPageLoading(true)
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/materials/${materialId}/page/${pageNum}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const blob = await res.blob()
        setPageImageUrl(URL.createObjectURL(blob))
      } else {
        setError('Failed to load page')
      }
    } catch {
      setError('Failed to load page')
    } finally {
      setPageLoading(false)
    }
  }

  async function saveProgress(page: number, readTime: number) {
    try {
      const token = tokenStorage.getAccessToken()
      await fetch(`${API_URL}/api/v1/materials/${materialId}/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ current_page: page, read_time_seconds: readTime }),
      })
    } catch { /* ignore */ }
  }

  function goToPage(page: number) {
    if (page < 1 || page > (material?.page_count || 1)) return
    const readTime = Math.floor((Date.now() - readTimeRef.current) / 1000)
    saveProgress(currentPage, readTime)
    readTimeRef.current = Date.now()
    setCurrentPage(page)
  }

  async function handleUnlock() {
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/materials/${materialId}/unlock`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        toast.success(data.message)
        // Refresh access
        setAccess({ has_access: true, is_premium: true, coin_cost: material?.coin_cost || 0, unlock_method: data.unlock_method })
        // Fetch first page
        if (material) fetchPage(1)
      } else {
        const err = await res.json().catch(() => ({}))
        toast.error(err.detail?.message || 'Failed to unlock')
      }
    } catch {
      toast.error('Network error')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
      </div>
    )
  }

  if (error || !material) {
    return (
      <div className="mx-auto max-w-2xl">
        <Card className="glass-card rounded-2xl border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <AlertCircle className="h-8 w-8 text-red-400" />
            <h3 className="mt-4 text-lg font-semibold text-white">{error || 'Material not found'}</h3>
            <Button className="mt-4" variant="outline" onClick={() => router.push('/materials')}>
              Back to materials
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const progressPct = material.page_count > 0 ? Math.round((currentPage / material.page_count) * 100) : 0

  return (
    <div
      className="mx-auto max-w-3xl space-y-4 select-none"
      onContextMenu={(e) => e.preventDefault()}
      onDragStart={(e) => e.preventDefault()}
      style={{ WebkitUserSelect: 'none', MozUserSelect: 'none', userSelect: 'none' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <button
            onClick={() => router.push('/materials')}
            className="mb-2 inline-flex items-center gap-1 text-sm text-zinc-400 hover:text-emerald-400 transition-colors"
          >
            <ChevronLeft className="h-4 w-4" /> Back to materials
          </button>
          <h1 className="truncate text-xl font-bold text-white">{material.title}</h1>
          <div className="mt-1 flex items-center gap-2 text-xs text-zinc-500">
            <span className="flex items-center gap-1"><FileText className="h-3 w-3" /> {material.page_count} pages</span>
            <span className="flex items-center gap-1"><Eye className="h-3 w-3" /> View only</span>
            {material.exam_name && (
              <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-xs">
                {material.exam_name}
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="flex items-center gap-3">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <span className="shrink-0 text-xs font-medium text-zinc-400">
          Page {currentPage} of {material.page_count} ({progressPct}%)
        </span>
      </div>

      {/* Watermark notice */}
      <div className="flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-400">
        <Eye className="h-3.5 w-3.5" />
        Each page is watermarked with your email. Screenshots are traceable.
      </div>

      {/* Phase C: Premium lock overlay */}
      {access && !access.has_access && (
        <Card className="glass-card rounded-2xl border-amber-500/30">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-500/10 ring-1 ring-inset ring-amber-500/20">
              <Lock className="h-8 w-8 text-amber-400" />
            </div>
            <h3 className="mt-4 text-xl font-bold text-white">Premium Material</h3>
            <p className="mt-2 max-w-sm text-sm text-zinc-400">
              This material requires {access.coin_cost} coins to unlock. You currently have {access.your_coins} coins.
            </p>
            {access.can_afford ? (
              <Button
                className="btn-glow mt-6 gradient-emerald font-semibold text-black shadow-lg shadow-emerald-500/30"
                onClick={handleUnlock}
              >
                <Coins className="mr-2 h-4 w-4" />
                Unlock for {access.coin_cost} coins
              </Button>
            ) : (
              <div className="mt-6 space-y-2">
                <p className="text-sm text-red-400">You need {access.coin_cost - access.your_coins} more coins.</p>
                <Button variant="outline" className="border-white/15 bg-white/5 text-white" onClick={() => router.push('/study/start')}>
                  Study to earn coins
                </Button>
              </div>
            )}
            <p className="mt-4 text-xs text-zinc-600">Once unlocked, you can read all {material?.page_count} pages. View-only — no download.</p>
          </CardContent>
        </Card>
      )}

      {/* PDF page viewer — only shown if user has access */}
      {access?.has_access && (
      <Card className="glass-card overflow-hidden rounded-2xl">
        <CardContent className="p-0">
          {pageLoading ? (
            <div className="flex items-center justify-center py-32">
              <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
            </div>
          ) : pageImageUrl ? (
            <div className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={pageImageUrl}
                alt={`Page ${currentPage}`}
                className="w-full select-none"
                draggable={false}
                onContextMenu={(e) => e.preventDefault()}
              />
            </div>
          ) : (
            <div className="flex items-center justify-center py-32 text-zinc-500">
              Failed to load page
            </div>
          )}
        </CardContent>
      </Card>
      )}

      {/* Page navigation — only shown if user has access */}
      {access?.has_access && (
      <div className="flex items-center justify-between gap-4">
        <Button
          variant="outline"
          onClick={() => goToPage(currentPage - 1)}
          disabled={currentPage <= 1 || pageLoading}
          className="border-white/15 bg-white/5 text-white hover:bg-white/10"
        >
          <ChevronLeft className="mr-1 h-4 w-4" /> Previous
        </Button>

        <div className="flex items-center gap-2">
          {Array.from({ length: Math.min(material.page_count, 10) }, (_, i) => {
            const pageNum = i + 1
            return (
              <button
                key={pageNum}
                onClick={() => goToPage(pageNum)}
                className={`h-8 w-8 rounded-lg text-xs font-medium transition-all ${
                  currentPage === pageNum
                    ? 'bg-emerald-500 text-black'
                    : 'bg-white/5 text-zinc-400 hover:bg-white/10'
                }`}
              >
                {pageNum}
              </button>
            )
          })}
          {material.page_count > 10 && <span className="text-xs text-zinc-600">...</span>}
        </div>

        <Button
          variant="outline"
          onClick={() => goToPage(currentPage + 1)}
          disabled={currentPage >= material.page_count || pageLoading}
          className="border-white/15 bg-white/5 text-white hover:bg-white/10"
        >
          Next <ChevronRight className="ml-1 h-4 w-4" />
        </Button>
      </div>
      )}
    </div>
  )
}
