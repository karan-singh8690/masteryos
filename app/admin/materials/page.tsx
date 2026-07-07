'use client'

import * as React from 'react'
import { Upload, FileText, Trash2, Loader2, Search, Coins, Eye, Link2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { tokenStorage } from '@/lib/api-client'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Material {
  id: string
  title: string
  description: string | null
  page_count: number
  is_premium: boolean
  coin_cost: number
  material_type: string
  tags: string[]
  exam_name: string | null
  exam_year: number | null
  language: string
  created_at: string | null
  progress: { current_page: number; pages_read: number; is_completed: boolean }
}

export default function AdminMaterialsPage() {
  const [materials, setMaterials] = React.useState<Material[]>([])
  const [loading, setLoading] = React.useState(true)
  const [uploading, setUploading] = React.useState(false)
  const [linking, setLinking] = React.useState<string | null>(null)

  // Upload form state
  const [title, setTitle] = React.useState('')
  const [description, setDescription] = React.useState('')
  const [examName, setExamName] = React.useState('')
  const [language, setLanguage] = React.useState('en')
  const [materialType, setMaterialType] = React.useState('pdf')
  const [isPremium, setIsPremium] = React.useState(false)
  const [coinCost, setCoinCost] = React.useState(0)
  const [tags, setTags] = React.useState('')
  const [file, setFile] = React.useState<File | null>(null)

  // Link form state
  const [linkConceptId, setLinkConceptId] = React.useState('')
  const [linkIsPrereq, setLinkIsPrereq] = React.useState(false)
  const [linkMinPages, setLinkMinPages] = React.useState(1)

  React.useEffect(() => { fetchMaterials() }, [])

  async function fetchMaterials() {
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/materials?&page_size=100`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setMaterials(data.items || [])
      }
    } catch { /* empty */ }
    finally { setLoading(false) }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !title) {
      toast.error('Please provide a title and select a PDF file')
      return
    }

    setUploading(true)
    try {
      const token = tokenStorage.getAccessToken()
      const params = new URLSearchParams({
        title,
        description,
        language,
        material_type: materialType,
        is_premium: String(isPremium),
        coin_cost: String(coinCost),
        tags,
      })
      if (examName) params.set('exam_name', examName)

      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch(`${API_URL}/api/v1/materials/upload?${params}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })

      if (res.ok) {
        const data = await res.json()
        toast.success(`Uploaded! ${data.page_count} pages, ${Math.round(data.file_size_bytes / 1024)}KB`)
        // Reset form
        setTitle('')
        setDescription('')
        setExamName('')
        setTags('')
        setFile(null)
        setIsPremium(false)
        setCoinCost(0)
        // Refresh list
        fetchMaterials()
      } else {
        const err = await res.json().catch(() => ({}))
        toast.error(err.detail || 'Upload failed')
      }
    } catch {
      toast.error('Network error')
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this material? This cannot be undone.')) return
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/materials/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        toast.success('Material deleted')
        fetchMaterials()
      } else {
        toast.error('Delete failed')
      }
    } catch {
      toast.error('Network error')
    }
  }

  async function handleLink(materialId: string) {
    if (!linkConceptId) {
      toast.error('Enter a concept ID')
      return
    }
    setLinking(materialId)
    try {
      const token = tokenStorage.getAccessToken()
      const res = await fetch(`${API_URL}/api/v1/materials/${materialId}/concept-links`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          concept_id: linkConceptId,
          is_prerequisite: linkIsPrereq,
          min_pages_read: linkMinPages,
        }),
      })
      if (res.ok) {
        toast.success(`Linked to concept! ${linkIsPrereq ? 'Marked as prerequisite.' : ''}`)
        setLinkConceptId('')
        setLinkIsPrereq(false)
        setLinkMinPages(1)
      } else {
        toast.error('Link failed')
      }
    } catch {
      toast.error('Network error')
    } finally {
      setLinking(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Study Materials</h1>
        <p className="text-sm text-muted-foreground">Upload PDFs, set pricing, link to concepts</p>
      </div>

      {/* Upload Form */}
      <Card className="glass-card rounded-2xl">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500/20 to-teal-500/10 ring-1 ring-inset ring-emerald-500/20">
              <Upload className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <CardTitle>Upload New Material</CardTitle>
              <CardDescription>PDF files only — view-only, watermarked, no download</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label className="text-zinc-300">Title *</Label>
                <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Python Data Structures Notes" className="border-white/10 bg-white/5" required />
              </div>
              <div className="space-y-2">
                <Label className="text-zinc-300">Description</Label>
                <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Complete notes for DS chapter" className="border-white/10 bg-white/5" />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <Label className="text-zinc-300">Exam Name</Label>
                <Input value={examName} onChange={(e) => setExamName(e.target.value)} placeholder="JEE, GATE, NEET" className="border-white/10 bg-white/5" />
              </div>
              <div className="space-y-2">
                <Label className="text-zinc-300">Language</Label>
                <select value={language} onChange={(e) => setLanguage(e.target.value)} className="h-10 w-full rounded-lg border border-white/10 bg-white/5 px-3 text-sm text-white">
                  <option value="en">English</option>
                  <option value="hi">Hindi</option>
                  <option value="ta">Tamil</option>
                  <option value="te">Telugu</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label className="text-zinc-300">Type</Label>
                <select value={materialType} onChange={(e) => setMaterialType(e.target.value)} className="h-10 w-full rounded-lg border border-white/10 bg-white/5 px-3 text-sm text-white">
                  <option value="pdf">PDF Document</option>
                  <option value="notes">Notes</option>
                  <option value="formula_sheet">Formula Sheet</option>
                  <option value="pyq_paper">PYQ Paper</option>
                  <option value="reference">Reference</option>
                </select>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <Label className="text-zinc-300">Tags (comma-separated)</Label>
                <Input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="python, ds, formulas" className="border-white/10 bg-white/5" />
              </div>
              <div className="space-y-2">
                <Label className="text-zinc-300">Premium?</Label>
                <div className="flex h-10 items-center gap-2">
                  <input
                    type="checkbox"
                    id="is-premium"
                    checked={isPremium}
                    onChange={(e) => setIsPremium(e.target.checked)}
                    className="h-4 w-4 rounded accent-emerald-500"
                  />
                  <Label htmlFor="is-premium" className="text-sm text-zinc-300 cursor-pointer">Require coins to unlock</Label>
                </div>
              </div>
              {isPremium && (
                <div className="space-y-2">
                  <Label className="text-zinc-300">Coin Cost</Label>
                  <Input type="number" value={coinCost} onChange={(e) => setCoinCost(Number(e.target.value))} min={0} className="border-white/10 bg-white/5" placeholder="50" />
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label className="text-zinc-300">PDF File *</Label>
              <div className="flex items-center gap-3">
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-zinc-400 file:mr-4 file:rounded-lg file:border-0 file:bg-emerald-500/20 file:px-4 file:py-2 file:text-sm file:font-medium file:text-emerald-300 hover:file:bg-emerald-500/30"
                />
                {file && (
                  <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                    {Math.round(file.size / 1024)}KB
                  </Badge>
                )}
              </div>
              <p className="text-xs text-zinc-500">Max 50MB. PDF will be rendered as watermarked images — no download possible.</p>
            </div>

            <Button
              type="submit"
              disabled={uploading || !file || !title}
              className="btn-glow gradient-emerald font-semibold text-black shadow-lg shadow-emerald-500/30"
            >
              {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
              {uploading ? 'Uploading...' : 'Upload PDF'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Materials List */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-white">Uploaded Materials ({materials.length})</h2>
        {materials.length === 0 ? (
          <Card className="glass-card rounded-2xl border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="h-8 w-8 text-muted-foreground" />
              <p className="mt-3 text-sm text-muted-foreground">No materials uploaded yet</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {materials.map((m) => (
              <Card key={m.id} className="glass-card rounded-2xl">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-semibold text-white">{m.title}</h3>
                        {m.is_premium && (
                          <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-400 text-xs">
                            <Coins className="mr-1 h-3 w-3" /> {m.coin_cost} coins
                          </Badge>
                        )}
                        <Badge variant="secondary" className="text-xs">{m.material_type}</Badge>
                        <Badge variant="outline" className="text-xs">{m.language}</Badge>
                      </div>
                      {m.description && <p className="mt-1 text-sm text-zinc-400">{m.description}</p>}
                      <div className="mt-2 flex items-center gap-3 text-xs text-zinc-500">
                        <span className="flex items-center gap-1"><FileText className="h-3 w-3" /> {m.page_count} pages</span>
                        {m.exam_name && <Badge variant="outline" className="text-xs border-emerald-500/30 bg-emerald-500/10 text-emerald-300">{m.exam_name}</Badge>}
                        {m.tags?.map((t) => <Badge key={t} variant="secondary" className="text-xs">{t}</Badge>)}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <a href={`${API_URL.replace('trustworthy-adventure-production-a9cc', '')}/materials/${m.id}`} target="_blank" rel="noopener">
                        <Button size="sm" variant="ghost" className="h-8 w-8 p-0" title="Preview (opens in new tab)">
                          <Eye className="h-4 w-4" />
                        </Button>
                      </a>
                      <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-red-500" onClick={() => handleDelete(m.id)} title="Delete">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  {/* Link to concept section */}
                  <div className="mt-3 border-t border-white/5 pt-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link2 className="h-3.5 w-3.5 text-zinc-500" />
                      <span className="text-xs text-zinc-500">Link to concept:</span>
                      <input
                        type="text"
                        placeholder="Concept UUID"
                        value={linkConceptId}
                        onChange={(e) => setLinkConceptId(e.target.value)}
                        className="h-7 w-48 rounded-md border border-white/10 bg-white/5 px-2 text-xs text-white placeholder:text-zinc-600"
                      />
                      <label className="flex items-center gap-1 text-xs text-zinc-400">
                        <input type="checkbox" checked={linkIsPrereq} onChange={(e) => setLinkIsPrereq(e.target.checked)} className="h-3 w-3 accent-emerald-500" />
                        Prerequisite
                      </label>
                      {linkIsPrereq && (
                        <input
                          type="number"
                          placeholder="Min pages"
                          value={linkMinPages}
                          onChange={(e) => setLinkMinPages(Number(e.target.value))}
                          className="h-7 w-20 rounded-md border border-white/10 bg-white/5 px-2 text-xs text-white"
                          min={1}
                        />
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 gap-1 text-xs border-white/15 bg-white/5"
                        disabled={linking === m.id}
                        onClick={() => handleLink(m.id)}
                      >
                        {linking === m.id ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Link'}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
