import { describe, it, expect } from 'vitest'
import { queryKey } from '@/lib/query-keys'

describe('Production Query Key Completeness', () => {
  it('auth keys are complete', () => {
    expect(queryKey.auth.me()).toBeDefined()
    expect(queryKey.auth.session()).toBeDefined()
  })

  it('learner keys cover all entities', () => {
    expect(queryKey.learner.dashboard()).toBeDefined()
    expect(queryKey.learner.subjects()).toBeDefined()
    expect(queryKey.learner.enrollments()).toBeDefined()
    expect(queryKey.learner.sessions()).toBeDefined()
    expect(queryKey.learner.question('q1')).toBeDefined()
    expect(queryKey.learner.mastery('e1')).toBeDefined()
    expect(queryKey.learner.dueReviews('e1')).toBeDefined()
    expect(queryKey.learner.recommendations()).toBeDefined()
    expect(queryKey.learner.achievements()).toBeDefined()
    expect(queryKey.learner.notifications()).toBeDefined()
    expect(queryKey.learner.unreadNotificationCount()).toBeDefined()
  })

  it('content keys cover all entities', () => {
    expect(queryKey.content.dashboard()).toBeDefined()
    expect(queryKey.content.subjects()).toBeDefined()
    expect(queryKey.content.concepts('s1')).toBeDefined()
    expect(queryKey.content.objectives('c1')).toBeDefined()
    expect(queryKey.content.misconceptions('c1')).toBeDefined()
    expect(queryKey.content.templates('s1')).toBeDefined()
    expect(queryKey.content.template('t1')).toBeDefined()
    expect(queryKey.content.templatePreview('t1')).toBeDefined()
    expect(queryKey.content.search('test')).toBeDefined()
  })

  it('admin keys cover all entities', () => {
    expect(queryKey.admin.opsDashboard()).toBeDefined()
    expect(queryKey.admin.users()).toBeDefined()
    expect(queryKey.admin.organizations()).toBeDefined()
    expect(queryKey.admin.roles()).toBeDefined()
    expect(queryKey.admin.featureFlags()).toBeDefined()
    expect(queryKey.admin.auditLogs()).toBeDefined()
    expect(queryKey.admin.securityDashboard()).toBeDefined()
    expect(queryKey.admin.workers()).toBeDefined()
    expect(queryKey.admin.outbox()).toBeDefined()
    expect(queryKey.admin.deadLetters()).toBeDefined()
    expect(queryKey.admin.jobs()).toBeDefined()
    expect(queryKey.admin.notifications()).toBeDefined()
    expect(queryKey.admin.emailDelivery()).toBeDefined()
    expect(queryKey.admin.billingPlans()).toBeDefined()
    expect(queryKey.admin.analytics()).toBeDefined()
    expect(queryKey.admin.systemConfig()).toBeDefined()
    expect(queryKey.admin.search('test')).toBeDefined()
  })

  it('query keys return arrays', () => {
    expect(Array.isArray(queryKey.learner.dashboard())).toBe(true)
    expect(Array.isArray(queryKey.content.subjects())).toBe(true)
    expect(Array.isArray(queryKey.admin.workers())).toBe(true)
  })

  it('query keys are unique per entity', () => {
    const key1 = queryKey.learner.subject('s1')
    const key2 = queryKey.learner.subject('s2')
    expect(key1).not.toEqual(key2)
  })

  it('query keys with filters differ from without', () => {
    const withFilter = queryKey.admin.outbox({ status: 'pending' })
    const withoutFilter = queryKey.admin.outbox()
    expect(withFilter).not.toEqual(withoutFilter)
  })
})
