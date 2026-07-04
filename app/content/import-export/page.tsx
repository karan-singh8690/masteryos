'use client'

import * as React from 'react'
import { Upload, Download, FileJson, FileText, FileSpreadsheet, Package, AlertCircle, CheckCircle2 } from 'lucide-react'
import { toast } from 'sonner'

import { useImportContent, useExportContent } from '@/hooks/use-content'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const FORMATS = [
  { value: 'json', label: 'JSON', icon: FileJson, description: 'Structured data format' },
  { value: 'markdown', label: 'Markdown', icon: FileText, description: 'Human-readable text format' },
  { value: 'csv', label: 'CSV', icon: FileSpreadsheet, description: 'Spreadsheet format' },
  { value: 'zip', label: 'ZIP Package', icon: Package, description: 'Complete archive' },
]

export default function ImportExportPage() {
  const importMutation = useImportContent()
  const exportMutation = useExportContent()

  const [importFormat, setImportFormat] = React.useState('json')
  const [exportFormat, setExportFormat] = React.useState('json')
  const [importData, setImportData] = React.useState('')
  const [importPreview, setImportPreview] = React.useState<{
    items: { type: string; name: string; action: string }[]
    warnings: string[]
    errors: string[]
  } | null>(null)

  const handlePreviewImport = () => {
    try {
      const parsed = JSON.parse(importData)
      // Simulate preview
      setImportPreview({
        items: Array.isArray(parsed)
          ? parsed.map((item: any) => ({
              type: item.type || 'unknown',
              name: item.name || item.code || 'Unnamed',
              action: 'create',
            }))
          : [{ type: 'subject', name: parsed.name || 'Subject', action: 'create' }],
        warnings: [],
        errors: [],
      })
    } catch {
      setImportPreview({
        items: [],
        warnings: [],
        errors: ['Invalid JSON format'],
      })
    }
  }

  const handleImport = async () => {
    try {
      const parsed = JSON.parse(importData)
      const result = await importMutation.mutateAsync({
        format: importFormat,
        data: parsed,
      })
      toast.success(`Imported ${result.imported} items`)
      setImportData('')
      setImportPreview(null)
    } catch (err) {
      toast.error('Import failed')
    }
  }

  const handleExport = async () => {
    try {
      const blob = await exportMutation.mutateAsync({
        format: exportFormat,
      })
      // Download the blob
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `mastery-content-export.${exportFormat}`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Export downloaded')
    } catch {
      toast.error('Export failed')
    }
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Import / Export</h1>
        <p className="text-sm text-muted-foreground">Import and export content in various formats</p>
      </div>

      {/* Import section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Upload className="h-4 w-4" aria-hidden="true" />
            Import content
          </CardTitle>
          <CardDescription>Paste JSON data or upload a file to import</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Format</Label>
            <Select value={importFormat} onValueChange={setImportFormat}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FORMATS.map((f) => (
                  <SelectItem key={f.value} value={f.value}>
                    {f.label} — {f.description}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="importData">Content data (JSON)</Label>
            <textarea
              id="importData"
              className="flex min-h-[150px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              placeholder='[{"type": "concept", "name": "Decorators", "slug": "decorators", "description": "..."}]'
              value={importData}
              onChange={(e) => setImportData(e.target.value)}
              aria-label="Import data"
            />
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handlePreviewImport}
              disabled={!importData}
            >
              Preview import
            </Button>
            <Button
              onClick={handleImport}
              loading={importMutation.isPending}
              disabled={!importData || importMutation.isPending}
            >
              Import
            </Button>
          </div>

          {/* Import preview */}
          {importPreview && (
            <div className="space-y-3 rounded-lg border p-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold">Import preview</h4>
                <div className="flex gap-2">
                  {importPreview.errors.length > 0 && (
                    <Badge variant="destructive" className="text-xs">
                      {importPreview.errors.length} errors
                    </Badge>
                  )}
                  {importPreview.warnings.length > 0 && (
                    <Badge variant="warning" className="text-xs">
                      {importPreview.warnings.length} warnings
                    </Badge>
                  )}
                  {importPreview.items.length > 0 && (
                    <Badge variant="success" className="text-xs">
                      {importPreview.items.length} items
                    </Badge>
                  )}
                </div>
              </div>

              {importPreview.errors.map((err, i) => (
                <Alert key={i} variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{err}</AlertDescription>
                </Alert>
              ))}

              {importPreview.warnings.map((warn, i) => (
                <Alert key={i} variant="warning">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{warn}</AlertDescription>
                </Alert>
              ))}

              {importPreview.items.length > 0 && (
                <ul className="space-y-1" role="list">
                  {importPreview.items.map((item, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm">
                      <CheckCircle2 className="h-3 w-3 text-success" aria-hidden="true" />
                      <span className="font-medium">{item.name}</span>
                      <Badge variant="outline" className="text-xs">{item.type}</Badge>
                      <Badge variant="secondary" className="text-xs capitalize">{item.action}</Badge>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Export section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Download className="h-4 w-4" aria-hidden="true" />
            Export content
          </CardTitle>
          <CardDescription>Download content in various formats</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Format</Label>
            <Select value={exportFormat} onValueChange={setExportFormat}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FORMATS.map((f) => (
                  <SelectItem key={f.value} value={f.value}>
                    {f.label} — {f.description}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button
            onClick={handleExport}
            loading={exportMutation.isPending}
            disabled={exportMutation.isPending}
          >
            <Download className="mr-2 h-4 w-4" />
            Export content
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
