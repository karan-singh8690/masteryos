/**
 * Admin hooks — React Query hooks for all administration operations.
 */

'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { queryKey } from '@/lib/query-keys'
import {
  opsDashboardApi, adminUserApi, organizationApi, rbacApi, featureFlagApi,
  auditLogApi, securityApi, workerConsoleApi, outboxConsoleApi, deadLetterApi,
  schedulerApi, notificationOpsApi, emailOpsApi, billingApi, platformAnalyticsApi,
  systemConfigApi, adminSearchApi, adminBulkApi,
} from '@/lib/admin-api'
import type { UUID } from '@/types/common'
import type {
  AdminUserListParams, AuditLogFilter, CreateFeatureFlagRequest,
  AdminBulkAction,
} from '@/types/admin'

// Operations Dashboard
export function useOpsDashboard() {
  return useQuery({ queryKey: queryKey.admin.opsDashboard(), queryFn: () => opsDashboardApi.get(), staleTime: 15_000, refetchInterval: 30_000 })
}

// Users
export function useAdminUsers(params?: AdminUserListParams) {
  return useQuery({ queryKey: queryKey.admin.users(params), queryFn: () => adminUserApi.list(params) })
}
export function useAdminUser(id: UUID | null) {
  return useQuery({ queryKey: queryKey.admin.user(id!), queryFn: () => adminUserApi.getById(id!), enabled: !!id })
}
export function useSuspendUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: UUID; reason: string }) => adminUserApi.suspend(id, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}
export function useReactivateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => adminUserApi.reactivate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}
export function useForceLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => adminUserApi.forceLogout(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}
export function useAnonymizeUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => adminUserApi.anonymize(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}
export function useAssignRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, role }: { id: UUID; role: string }) => adminUserApi.assignRole(id, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })
}

// Organizations
export function useOrganizations() {
  return useQuery({ queryKey: queryKey.admin.organizations(), queryFn: () => organizationApi.list() })
}
export function useOrganization(id: UUID | null) {
  return useQuery({ queryKey: queryKey.admin.organization(id!), queryFn: () => organizationApi.getById(id!), enabled: !!id })
}
export function useSuspendOrganization() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => organizationApi.suspend(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey.admin.organizations() }),
  })
}
export function useArchiveOrganization() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => organizationApi.archive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey.admin.organizations() }),
  })
}

// RBAC
export function useRoles() {
  return useQuery({ queryKey: queryKey.admin.roles(), queryFn: () => rbacApi.listRoles() })
}
export function usePermissions() {
  return useQuery({ queryKey: queryKey.admin.permissions(), queryFn: () => rbacApi.listPermissions() })
}

// Feature Flags
export function useFeatureFlags() {
  return useQuery({ queryKey: queryKey.admin.featureFlags(), queryFn: () => featureFlagApi.list() })
}
export function useCreateFeatureFlag() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateFeatureFlagRequest) => featureFlagApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey.admin.featureFlags() }),
  })
}
export function useToggleFeatureFlag() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, enabled }: { id: UUID; enabled: boolean }) =>
      enabled ? featureFlagApi.enable(id) : featureFlagApi.disable(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey.admin.featureFlags() }),
  })
}
export function useDeleteFeatureFlag() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => featureFlagApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey.admin.featureFlags() }),
  })
}

// Audit Logs
export function useAuditLogs(params?: AuditLogFilter) {
  return useQuery({ queryKey: queryKey.admin.auditLogs(params), queryFn: () => auditLogApi.list(params) })
}

// Security
export function useSecurityDashboard() {
  return useQuery({ queryKey: queryKey.admin.securityDashboard(), queryFn: () => securityApi.getDashboard() })
}
export function useSecurityIncidents(params?: Record<string, unknown>) {
  return useQuery({ queryKey: queryKey.admin.securityIncidents(params), queryFn: () => securityApi.listIncidents(params) })
}
export function useResolveSecurityIncident() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, notes }: { id: UUID; notes?: string }) => securityApi.resolveIncident(id, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'security'] })
    },
  })
}

// Worker Console
export function useAdminWorkers() {
  return useQuery({ queryKey: queryKey.admin.workers(), queryFn: () => workerConsoleApi.list() })
}
export function useWorkerMetrics() {
  return useQuery({ queryKey: queryKey.admin.workerMetrics(), queryFn: () => workerConsoleApi.getMetrics(), refetchInterval: 15_000 })
}
export function useRequestWorkerShutdown() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (workerId: string) => workerConsoleApi.requestShutdown(workerId),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey.admin.workers() }),
  })
}

// Outbox
export function useOutboxEvents(params?: Record<string, unknown>) {
  return useQuery({ queryKey: queryKey.admin.outbox(params), queryFn: () => outboxConsoleApi.list(params) })
}
export function useOutboxStats() {
  return useQuery({ queryKey: queryKey.admin.outboxStats(), queryFn: () => outboxConsoleApi.getStats() })
}
export function useReplayOutboxEvent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => outboxConsoleApi.replay(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'outbox'] }),
  })
}

// Dead Letters
export function useDeadLetters(params?: Record<string, unknown>) {
  return useQuery({ queryKey: queryKey.admin.deadLetters(params), queryFn: () => deadLetterApi.list(params) })
}
export function useRetryDeadLetter() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => deadLetterApi.retry(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'dead-letters'] }),
  })
}
export function useResolveDeadLetter() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, notes }: { id: UUID; notes?: string }) => deadLetterApi.resolve(id, notes),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'dead-letters'] }),
  })
}

// Scheduler
export function useScheduledJobs() {
  return useQuery({ queryKey: queryKey.admin.jobs(), queryFn: () => schedulerApi.listJobs() })
}
export function useRunJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => schedulerApi.runJob(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey.admin.jobs() }),
  })
}
export function usePauseJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => schedulerApi.pauseJob(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey.admin.jobs() }),
  })
}
export function useResumeJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => schedulerApi.resumeJob(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey.admin.jobs() }),
  })
}

// Notifications
export function useAdminNotifications(params?: Record<string, unknown>) {
  return useQuery({ queryKey: queryKey.admin.notifications(params), queryFn: () => notificationOpsApi.list(params) })
}

// Email
export function useEmailDelivery(params?: Record<string, unknown>) {
  return useQuery({ queryKey: queryKey.admin.emailDelivery(params), queryFn: () => emailOpsApi.list(params) })
}
export function useRetryEmail() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: UUID) => emailOpsApi.retry(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'email-delivery'] }),
  })
}

// Billing
export function useBillingPlans() {
  return useQuery({ queryKey: queryKey.admin.billingPlans(), queryFn: () => billingApi.listPlans() })
}
export function useBillingSubscriptions() {
  return useQuery({ queryKey: queryKey.admin.billingSubscriptions(), queryFn: () => billingApi.listSubscriptions() })
}
export function useBillingInvoices() {
  return useQuery({ queryKey: queryKey.admin.billingInvoices(), queryFn: () => billingApi.listInvoices() })
}
export function useBillingRevenue() {
  return useQuery({ queryKey: queryKey.admin.billingRevenue(), queryFn: () => billingApi.getRevenue() })
}

// Analytics
export function usePlatformAnalytics() {
  return useQuery({ queryKey: queryKey.admin.analytics(), queryFn: () => platformAnalyticsApi.get() })
}

// System Config
export function useSystemConfig() {
  return useQuery({ queryKey: queryKey.admin.systemConfig(), queryFn: () => systemConfigApi.get() })
}
export function useSetMaintenanceMode() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (enabled: boolean) => systemConfigApi.setMaintenanceMode(enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKey.admin.systemConfig() }),
  })
}

// Search
export function useAdminSearch(query: string, enabled = true) {
  return useQuery({
    queryKey: queryKey.admin.search(query),
    queryFn: () => adminSearchApi.search(query),
    enabled: enabled && query.length > 0,
    staleTime: 10_000,
  })
}

// Bulk Operations
export function useAdminBulkOperation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ action, ids, options }: { action: AdminBulkAction; ids: UUID[]; options?: Record<string, unknown> }) =>
      adminBulkApi.execute(action, ids, options),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin'] }),
  })
}
