import { describe, it, expect } from 'vitest'
import {
  validateFile,
  MAX_FILE_SIZE,
  CHUNK_SIZE,
} from '@/lib/uploads/upload-pipeline'

describe('File Upload Pipeline', () => {
  describe('validateFile', () => {
    it('rejects files over max size', () => {
      const file = new File(['x'.repeat(MAX_FILE_SIZE + 1)], 'test.json', { type: 'application/json' })
      const error = validateFile(file, 'json')
      expect(error).toContain('exceeds')
    })

    it('accepts valid JSON file', () => {
      const file = new File(['{"test": true}'], 'data.json', { type: 'application/json' })
      const error = validateFile(file, 'json')
      expect(error).toBeNull()
    })

    it('accepts valid CSV file', () => {
      const file = new File(['a,b,c\n1,2,3'], 'data.csv', { type: 'text/csv' })
      const error = validateFile(file, 'csv')
      expect(error).toBeNull()
    })

    it('accepts valid Markdown file', () => {
      const file = new File(['# Title'], 'doc.md', { type: 'text/markdown' })
      const error = validateFile(file, 'markdown')
      expect(error).toBeNull()
    })

    it('accepts valid ZIP file', () => {
      const file = new File(['zip data'], 'archive.zip', { type: 'application/zip' })
      const error = validateFile(file, 'zip')
      expect(error).toBeNull()
    })

    it('accepts valid PNG image', () => {
      const file = new File(['png data'], 'image.png', { type: 'image/png' })
      const error = validateFile(file, 'image')
      expect(error).toBeNull()
    })

    it('rejects wrong extension', () => {
      const file = new File(['data'], 'data.txt', { type: 'text/plain' })
      const error = validateFile(file, 'json')
      expect(error).toContain('Invalid file extension')
    })

    it('rejects wrong MIME type', () => {
      const file = new File(['data'], 'data.json', { type: 'text/plain' })
      const error = validateFile(file, 'json')
      expect(error).toContain('Invalid file type')
    })

    it('accepts .markdown extension for markdown type', () => {
      const file = new File(['# Title'], 'doc.markdown', { type: 'text/markdown' })
      const error = validateFile(file, 'markdown')
      expect(error).toBeNull()
    })

    it('accepts .jpeg extension for image type', () => {
      const file = new File(['jpeg data'], 'photo.jpeg', { type: 'image/jpeg' })
      const error = validateFile(file, 'image')
      expect(error).toBeNull()
    })
  })

  describe('Constants', () => {
    it('MAX_FILE_SIZE is 100MB', () => {
      expect(MAX_FILE_SIZE).toBe(100 * 1024 * 1024)
    })
    it('CHUNK_SIZE is 5MB', () => {
      expect(CHUNK_SIZE).toBe(5 * 1024 * 1024)
    })
  })
})
