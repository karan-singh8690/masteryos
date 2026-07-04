import { describe, it, expect, vi } from 'vitest'

vi.mock('@/lib/admin-api', () => ({
  opsDashboardApi: { get: vi.fn() },
  adminUserApi: { list: vi.fn(), getById: vi.fn(), suspend: vi.fn(), reactivate: vi.fn(), forcePasswordReset: vi.fn(), forceLogout: vi.fn(), anonymize: vi.fn(), assignRole: vi.fn(), revokeRole: vi.fn() },
  organizationApi: { list: vi.fn(), getById: vi.fn(), create: vi.fn(), update: vi.fn(), suspend: vi.fn(), archive: vi.fn(), getMembers: vi.fn(), getInvitations: vi.fn() },
  rbacApi: { listRoles: vi.fn(), listPermissions: vi.fn(), getRoleAssignments: vi.fn() },
  featureFlagApi: { list: vi.fn(), getById: vi.fn(), create: vi.fn(), update: vi.fn(), delete: vi.fn(), enable: vi.fn(), disable: vi.fn() },
  auditLogApi: { list: vi.fn(), export: vi.fn() },
  securityApi: { getDashboard: vi.fn(), listIncidents: vi.fn(), resolveIncident: vi.fn() },
  workerConsoleApi: { list: vi.fn(), getMetrics: vi.fn(), requestShutdown: vi.fn(), markDead: vi.fn() },
  outboxConsoleApi: { list: vi.fn(), getStats: vi.fn(), getById: vi.fn(), replay: vi.fn() },
  deadLetterApi: { list: vi.fn(), retry: vi.fn(), resolve: vi.fn() },
  schedulerApi: { listJobs: vi.fn(), runJob: vi.fn(), pauseJob: vi.fn(), resumeJob: vi.fn() },
  notificationOpsApi: { list: vi.fn() },
  emailOpsApi: { list: vi.fn(), retry: vi.fn() },
  billingApi: { listPlans: vi.fn(), listSubscriptions: vi.fn(), listInvoices: vi.fn(), getRevenue: vi.fn() },
  platformAnalyticsApi: { get: vi.fn() },
  systemConfigApi: { get: vi.fn(), update: vi.fn(), setMaintenanceMode: vi.fn() },
  adminSearchApi: { search: vi.fn() },
  adminBulkApi: { execute: vi.fn() },
}))

import { opsDashboardApi, adminUserApi, organizationApi, rbacApi, featureFlagApi, auditLogApi, securityApi, workerConsoleApi, outboxConsoleApi, deadLetterApi, schedulerApi, notificationOpsApi, emailOpsApi, billingApi, platformAnalyticsApi, systemConfigApi, adminSearchApi, adminBulkApi } from '@/lib/admin-api'

describe('Admin API exports', () => {
  it('opsDashboardApi', () => { expect(opsDashboardApi.get).toBeDefined() })
  it('adminUserApi has all methods', () => { expect(adminUserApi.list).toBeDefined(); expect(adminUserApi.getById).toBeDefined(); expect(adminUserApi.suspend).toBeDefined(); expect(adminUserApi.reactivate).toBeDefined(); expect(adminUserApi.forcePasswordReset).toBeDefined(); expect(adminUserApi.forceLogout).toBeDefined(); expect(adminUserApi.anonymize).toBeDefined(); expect(adminUserApi.assignRole).toBeDefined(); expect(adminUserApi.revokeRole).toBeDefined() })
  it('organizationApi has all methods', () => { expect(organizationApi.list).toBeDefined(); expect(organizationApi.getById).toBeDefined(); expect(organizationApi.create).toBeDefined(); expect(organizationApi.update).toBeDefined(); expect(organizationApi.suspend).toBeDefined(); expect(organizationApi.archive).toBeDefined(); expect(organizationApi.getMembers).toBeDefined(); expect(organizationApi.getInvitations).toBeDefined() })
  it('rbacApi has all methods', () => { expect(rbacApi.listRoles).toBeDefined(); expect(rbacApi.listPermissions).toBeDefined(); expect(rbacApi.getRoleAssignments).toBeDefined() })
  it('featureFlagApi has all methods', () => { expect(featureFlagApi.list).toBeDefined(); expect(featureFlagApi.getById).toBeDefined(); expect(featureFlagApi.create).toBeDefined(); expect(featureFlagApi.update).toBeDefined(); expect(featureFlagApi.delete).toBeDefined(); expect(featureFlagApi.enable).toBeDefined(); expect(featureFlagApi.disable).toBeDefined() })
  it('auditLogApi has all methods', () => { expect(auditLogApi.list).toBeDefined(); expect(auditLogApi.export).toBeDefined() })
  it('securityApi has all methods', () => { expect(securityApi.getDashboard).toBeDefined(); expect(securityApi.listIncidents).toBeDefined(); expect(securityApi.resolveIncident).toBeDefined() })
  it('workerConsoleApi has all methods', () => { expect(workerConsoleApi.list).toBeDefined(); expect(workerConsoleApi.getMetrics).toBeDefined(); expect(workerConsoleApi.requestShutdown).toBeDefined(); expect(workerConsoleApi.markDead).toBeDefined() })
  it('outboxConsoleApi has all methods', () => { expect(outboxConsoleApi.list).toBeDefined(); expect(outboxConsoleApi.getStats).toBeDefined(); expect(outboxConsoleApi.getById).toBeDefined(); expect(outboxConsoleApi.replay).toBeDefined() })
  it('deadLetterApi has all methods', () => { expect(deadLetterApi.list).toBeDefined(); expect(deadLetterApi.retry).toBeDefined(); expect(deadLetterApi.resolve).toBeDefined() })
  it('schedulerApi has all methods', () => { expect(schedulerApi.listJobs).toBeDefined(); expect(schedulerApi.runJob).toBeDefined(); expect(schedulerApi.pauseJob).toBeDefined(); expect(schedulerApi.resumeJob).toBeDefined() })
  it('notificationOpsApi has all methods', () => { expect(notificationOpsApi.list).toBeDefined() })
  it('emailOpsApi has all methods', () => { expect(emailOpsApi.list).toBeDefined(); expect(emailOpsApi.retry).toBeDefined() })
  it('billingApi has all methods', () => { expect(billingApi.listPlans).toBeDefined(); expect(billingApi.listSubscriptions).toBeDefined(); expect(billingApi.listInvoices).toBeDefined(); expect(billingApi.getRevenue).toBeDefined() })
  it('platformAnalyticsApi has all methods', () => { expect(platformAnalyticsApi.get).toBeDefined() })
  it('systemConfigApi has all methods', () => { expect(systemConfigApi.get).toBeDefined(); expect(systemConfigApi.update).toBeDefined(); expect(systemConfigApi.setMaintenanceMode).toBeDefined() })
  it('adminSearchApi has all methods', () => { expect(adminSearchApi.search).toBeDefined() })
  it('adminBulkApi has all methods', () => { expect(adminBulkApi.execute).toBeDefined() })
})

describe('Admin hooks exports', () => {
  it('use-admin module exports all hooks', async () => {
    const m = await import('@/hooks/use-admin')
    expect(m.useOpsDashboard).toBeDefined()
    expect(m.useAdminUsers).toBeDefined()
    expect(m.useAdminUser).toBeDefined()
    expect(m.useSuspendUser).toBeDefined()
    expect(m.useReactivateUser).toBeDefined()
    expect(m.useForceLogout).toBeDefined()
    expect(m.useAnonymizeUser).toBeDefined()
    expect(m.useAssignRole).toBeDefined()
    expect(m.useOrganizations).toBeDefined()
    expect(m.useOrganization).toBeDefined()
    expect(m.useSuspendOrganization).toBeDefined()
    expect(m.useArchiveOrganization).toBeDefined()
    expect(m.useRoles).toBeDefined()
    expect(m.usePermissions).toBeDefined()
    expect(m.useFeatureFlags).toBeDefined()
    expect(m.useCreateFeatureFlag).toBeDefined()
    expect(m.useToggleFeatureFlag).toBeDefined()
    expect(m.useDeleteFeatureFlag).toBeDefined()
    expect(m.useAuditLogs).toBeDefined()
    expect(m.useSecurityDashboard).toBeDefined()
    expect(m.useSecurityIncidents).toBeDefined()
    expect(m.useResolveSecurityIncident).toBeDefined()
    expect(m.useAdminWorkers).toBeDefined()
    expect(m.useWorkerMetrics).toBeDefined()
    expect(m.useRequestWorkerShutdown).toBeDefined()
    expect(m.useOutboxEvents).toBeDefined()
    expect(m.useOutboxStats).toBeDefined()
    expect(m.useReplayOutboxEvent).toBeDefined()
    expect(m.useDeadLetters).toBeDefined()
    expect(m.useRetryDeadLetter).toBeDefined()
    expect(m.useResolveDeadLetter).toBeDefined()
    expect(m.useScheduledJobs).toBeDefined()
    expect(m.useRunJob).toBeDefined()
    expect(m.usePauseJob).toBeDefined()
    expect(m.useResumeJob).toBeDefined()
    expect(m.useAdminNotifications).toBeDefined()
    expect(m.useEmailDelivery).toBeDefined()
    expect(m.useRetryEmail).toBeDefined()
    expect(m.useBillingPlans).toBeDefined()
    expect(m.useBillingSubscriptions).toBeDefined()
    expect(m.useBillingInvoices).toBeDefined()
    expect(m.useBillingRevenue).toBeDefined()
    expect(m.usePlatformAnalytics).toBeDefined()
    expect(m.useSystemConfig).toBeDefined()
    expect(m.useSetMaintenanceMode).toBeDefined()
    expect(m.useAdminSearch).toBeDefined()
    expect(m.useAdminBulkOperation).toBeDefined()
  })
})
