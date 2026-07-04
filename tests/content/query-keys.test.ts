import { describe, it, expect } from 'vitest'

import { queryKey } from '@/lib/query-keys'

describe('Content authoring query keys', () => {
  describe('dashboard', () => {
    it('generates dashboard key', () => {
      expect(queryKey.content.dashboard()).toEqual(['content-authoring', 'dashboard'])
    })
  })

  describe('analytics', () => {
    it('generates analytics key without subject', () => {
      expect(queryKey.content.analytics()).toEqual(['content-authoring', 'analytics', 'all'])
    })

    it('generates analytics key with subject', () => {
      expect(queryKey.content.analytics('sub-1')).toEqual(['content-authoring', 'analytics', 'sub-1'])
    })
  })

  describe('subjects', () => {
    it('generates subjects list key', () => {
      expect(queryKey.content.subjects()).toEqual(['content-authoring', 'subjects'])
    })

    it('generates subject detail key', () => {
      expect(queryKey.content.subject('sub-1')).toEqual(['content-authoring', 'subjects', 'sub-1'])
    })
  })

  describe('concepts', () => {
    it('generates concepts key', () => {
      expect(queryKey.content.concepts('sub-1')).toEqual([
        'content-authoring', 'subjects', 'sub-1', 'concepts',
      ])
    })

    it('generates concept detail key', () => {
      expect(queryKey.content.concept('concept-1')).toEqual([
        'content-authoring', 'concepts', 'concept-1',
      ])
    })
  })

  describe('objectives', () => {
    it('generates objectives key', () => {
      expect(queryKey.content.objectives('concept-1')).toEqual([
        'content-authoring', 'concepts', 'concept-1', 'objectives',
      ])
    })
  })

  describe('misconceptions', () => {
    it('generates misconceptions key', () => {
      expect(queryKey.content.misconceptions('concept-1')).toEqual([
        'content-authoring', 'concepts', 'concept-1', 'misconceptions',
      ])
    })
  })

  describe('templates', () => {
    it('generates templates list key', () => {
      expect(queryKey.content.templates('sub-1')).toEqual([
        'content-authoring', 'subjects', 'sub-1', 'templates',
      ])
    })

    it('generates template detail key', () => {
      expect(queryKey.content.template('tpl-1')).toEqual([
        'content-authoring', 'templates', 'tpl-1',
      ])
    })

    it('generates template preview key with default seed', () => {
      expect(queryKey.content.templatePreview('tpl-1')).toEqual([
        'content-authoring', 'templates', 'tpl-1', 'preview', 'default',
      ])
    })

    it('generates template preview key with custom seed', () => {
      expect(queryKey.content.templatePreview('tpl-1', 42)).toEqual([
        'content-authoring', 'templates', 'tpl-1', 'preview', 42,
      ])
    })
  })

  describe('search', () => {
    it('generates search key', () => {
      expect(queryKey.content.search('decorator')).toEqual([
        'content-authoring', 'search', 'decorator',
      ])
    })
  })
})
