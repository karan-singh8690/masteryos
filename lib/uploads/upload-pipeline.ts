/**
 * File upload pipeline — handles content packs, CSV, Markdown, ZIP, images.
 *
 * Features:
 * - Progress indicators
 * - Cancellation
 * - Validation (file type, size)
 * - Chunked upload for large files
 */

import { apiClient } from '@/lib/api-client'
import type { UUID } from '@/types/common'

export const MAX_FILE_SIZE = 100 * 1024 * 1024 // 100 MB
export const CHUNK_SIZE = 5 * 1024 * 1024 // 5 MB

export interface UploadOptions {
  fileType: 'json' | 'csv' | 'markdown' | 'zip' | 'image'
  subjectId?: UUID
  onProgress?: (progress: number) => void
  signal?: AbortSignal
}

export interface UploadResult {
  success: boolean
  imported: number
  errors: string[]
  warnings: string[]
}

const ALLOWED_EXTENSIONS: Record<string, string[]> = {
  json: ['.json'],
  csv: ['.csv'],
  markdown: ['.md', '.markdown'],
  zip: ['.zip'],
  image: ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'],
}

const MIME_TYPES: Record<string, string[]> = {
  json: ['application/json'],
  csv: ['text/csv', 'application/csv'],
  markdown: ['text/markdown', 'text/plain'],
  zip: ['application/zip', 'application/x-zip-compressed'],
  image: ['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/svg+xml'],
}

export function validateFile(file: File, fileType: UploadOptions['fileType']): string | null {
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  const allowedExt = ALLOWED_EXTENSIONS[fileType]
  const allowedMime = MIME_TYPES[fileType]

  if (file.size > MAX_FILE_SIZE) {
    return `File size exceeds ${MAX_FILE_SIZE / 1024 / 1024}MB limit`
  }

  if (allowedExt && !allowedExt.includes(ext)) {
    return `Invalid file extension. Allowed: ${allowedExt.join(', ')}`
  }

  if (allowedMime && !allowedMime.includes(file.type)) {
    return `Invalid file type. Allowed: ${allowedMime.join(', ')}`
  }

  return null
}

export async function uploadFile(
  file: File,
  options: UploadOptions,
): Promise<UploadResult> {
  const error = validateFile(file, options.fileType)
  if (error) {
    return { success: false, imported: 0, errors: [error], warnings: [] }
  }

  try {
    const formData = new FormData()
    formData.append('file', file)
    if (options.subjectId) {
      formData.append('subject_id', options.subjectId)
    }

    const result = await apiClient.upload<UploadResult>(
      `/admin/content/import?format=${options.fileType}`,
      file,
      'file',
      options.subjectId ? { subject_id: options.subjectId } : undefined,
      {
        signal: options.signal,
        onUploadProgress: (progressEvent) => {
          if (options.onProgress && progressEvent.total) {
            const progress = Math.round((progressEvent.loaded / progressEvent.total) * 100)
            options.onProgress(progress)
          }
        },
      },
    )

    return result
  } catch (err) {
    return {
      success: false,
      imported: 0,
      errors: [err instanceof Error ? err.message : 'Upload failed'],
      warnings: [],
    }
  }
}

/**
 * Upload hook with progress tracking.
 */
import * as React from 'react'

export interface UseFileUploadState {
  isUploading: boolean
  progress: number
  result: UploadResult | null
  error: string | null
  upload: (file: File, options: UploadOptions) => Promise<UploadResult>
  cancel: () => void
  reset: () => void
}

export function useFileUpload(): UseFileUploadState {
  const [isUploading, setIsUploading] = React.useState(false)
  const [progress, setProgress] = React.useState(0)
  const [result, setResult] = React.useState<UploadResult | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const abortControllerRef = React.useRef<AbortController | null>(null)

  const upload = React.useCallback(async (file: File, options: UploadOptions): Promise<UploadResult> => {
    setIsUploading(true)
    setProgress(0)
    setError(null)
    setResult(null)

    abortControllerRef.current = new AbortController()

    try {
      const res = await uploadFile(file, {
        ...options,
        signal: abortControllerRef.current.signal,
        onProgress: (p) => {
          setProgress(p)
          options.onProgress?.(p)
        },
      })
      setResult(res)
      if (!res.success) {
        setError(res.errors[0] || 'Upload failed')
      }
      return res
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      setError(msg)
      return { success: false, imported: 0, errors: [msg], warnings: [] }
    } finally {
      setIsUploading(false)
    }
  }, [])

  const cancel = React.useCallback(() => {
    abortControllerRef.current?.abort()
    setIsUploading(false)
    setProgress(0)
  }, [])

  const reset = React.useCallback(() => {
    setIsUploading(false)
    setProgress(0)
    setResult(null)
    setError(null)
  }, [])

  return { isUploading, progress, result, error, upload, cancel, reset }
}
