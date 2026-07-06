/**
 * Admin API client — all administration API calls.
 */

import { apiClient } from '@/lib/api-client'
import type { UUID, PaginationParams } from '@/types/common'
import type {
  AdminUser, AdminUserDetail, AdminUserListParams,
  Organization, OrganizationMember, OrganizationInvitation,
  Role, Permission, RoleAssignment,
  FeatureFlag, CreateFeatureFlagRequest,
  AdminAuditLogEntry, AuditLogFilter,
  SecurityDashboard, SecurityIncident,
  AdminWorker, WorkerMetrics,
  OutboxEvent, OutboxStats, DeadLetter,
  ScheduledJob,
  AdminNotification,
  EmailDeliveryLog,
  BillingPlan, AdminSubscription, AdminInvoice, RevenueDashboard,
  PlatformAnalytics,
  OperationsDashboard,
  SystemConfig,
  AdminSearchResult,
  AdminBulkAction, BulkActionResult,
} from '@/types/admin'

// ============================================================
// Operations Dashboard
// ============================================================

export const opsDashboardApi = {
  get: () => apiClient.get<OperationsDashboard>('/admin/bg/operations'),
}

// ============================================================
// User Management
// ============================================================

export const adminUserApi = {
  list: (params?: AdminUserListParams) =>
    apiClient.get<AdminUser[]>('/admin/users', { params }),

  getById: (id: UUID) =>
    apiClient.get<AdminUserDetail>(`/admin/users/${id}`),

  suspend: (id: UUID, reason: string) =>
    apiClient.post<{ message: string }>(`/admin/users/${id}/suspend`, { reason }),

  reactivate: (id: UUID) =>
    apiClient.post<{ message: string }>(`/admin/users/${id}/reactivate`),

  forcePasswordReset: (id: UUID) =>
    apiClient.post<{ message: string }>(`/admin/users/${id}/force-password-reset`),

  forceLogout: (id: UUID) =>
    apiClient.post<{ message: string }>(`/admin/users/${id}/force-logout`),

  anonymize: (id: UUID) =>
    apiClient.post<{ message: string }>(`/admin/users/${id}/anonymize`),

  assignRole: (id: UUID, role: string) =>
    apiClient.post<{ message: string }>(`/admin/users/${id}/roles`, { role }),

  revokeRole: (id: UUID, role: string) =>
    apiClient.delete<{ message: string }>(`/admin/users/${id}/roles/${role}`),
}

// ============================================================
// Organization Management
// ============================================================

export const organizationApi = {
  list: () => apiClient.get<Organization[]>('/admin/organizations'),
  getById: (id: UUID) => apiClient.get<Organization>(`/admin/organizations/${id}`),
  create: (data: Partial<Organization>) => apiClient.post<Organization>('/admin/organizations', data),
  update: (id: UUID, data: Partial<Organization>) => apiClient.patch<Organization>(`/admin/organizations/${id}`, data),
  suspend: (id: UUID) => apiClient.post<{ message: string }>(`/admin/organizations/${id}/suspend`),
  archive: (id: UUID) => apiClient.post<{ message: string }>(`/admin/organizations/${id}/archive`),
  getMembers: (id: UUID) => apiClient.get<OrganizationMember[]>(`/admin/organizations/${id}/members`),
  getInvitations: (id: UUID) => apiClient.get<OrganizationInvitation[]>(`/admin/organizations/${id}/invitations`),
}

// ============================================================
// RBAC
// ============================================================

export const rbacApi = {
  listRoles: () => apiClient.get<Role[]>('/admin/rbac/roles'),
  listPermissions: () => apiClient.get<Permission[]>('/admin/rbac/permissions'),
  getRoleAssignments: (userId?: UUID) =>
    apiClient.get<RoleAssignment[]>(`/admin/rbac/assignments${userId ? `?user_id=${userId}` : ''}`),
}

// ============================================================
// Feature Flags
// ============================================================

export const featureFlagApi = {
  list: async (): Promise<FeatureFlag[]> => {
    const res = await apiClient.get<{ flags: FeatureFlag[] } | FeatureFlag[]>('/admin/feature-flags')
    // Backend returns { flags: [...] }, extract the array
    if (res && typeof res === 'object' && 'flags' in res && Array.isArray((res as any).flags)) {
      return (res as any).flags
    }
    // Fallback: if it's already an array
    if (Array.isArray(res)) {
      return res
    }
    return []
  },
  getById: (id: UUID) => apiClient.get<FeatureFlag>(`/admin/feature-flags/${id}`),
  create: (data: CreateFeatureFlagRequest) => apiClient.post<FeatureFlag>('/admin/feature-flags', data),
  update: (id: UUID, data: Partial<FeatureFlag>) => apiClient.patch<FeatureFlag>(`/admin/feature-flags/${id}`, data),
  delete: (id: UUID) => apiClient.delete<void>(`/admin/feature-flags/${id}`),
  enable: (id: UUID) => apiClient.post<FeatureFlag>(`/admin/feature-flags/${id}/enable`),
  disable: (id: UUID) => apiClient.post<FeatureFlag>(`/admin/feature-flags/${id}/disable`),
}

// ============================================================
// Audit Logs
// ============================================================

export const auditLogApi = {
  list: async (params?: AuditLogFilter): Promise<AdminAuditLogEntry[]> => {
    const res = await apiClient.get<AdminAuditLogEntry[] | { items: AdminAuditLogEntry[] }>('/admin/audit-logs', { params })
    return Array.isArray(res) ? res : (res?.items ?? [])
  },
  export: (params?: AuditLogFilter) =>
    apiClient.post<Blob>('/admin/audit-logs/export', params, { responseType: 'blob' }),
}

// ============================================================
// Security Center
// ============================================================

export const securityApi = {
  getDashboard: () => apiClient.get<SecurityDashboard>('/admin/security/dashboard'),
  listIncidents: async (params?: PaginationParams): Promise<SecurityIncident[]> => {
    const res = await apiClient.get<SecurityIncident[] | { items: SecurityIncident[] }>('/admin/security/incidents', { params })
    return Array.isArray(res) ? res : (res?.items ?? [])
  },
  resolveIncident: (id: UUID, notes?: string) =>
    apiClient.post<{ message: string }>(`/admin/security/incidents/${id}/resolve`, { notes }),
}

// ============================================================
// Worker Console (from Task 017 admin API)
// ============================================================

export const workerConsoleApi = {
  list: () => apiClient.get<AdminWorker[]>('/admin/bg/workers'),
  getMetrics: () => apiClient.get<WorkerMetrics>('/admin/bg/workers/metrics'),
  requestShutdown: (workerId: string) =>
    apiClient.post<{ message: string }>(`/admin/bg/workers/${workerId}/shutdown`),
  markDead: (workerId: string) =>
    apiClient.post<{ message: string }>(`/admin/bg/workers/${workerId}/mark-dead`),
}

// ============================================================
// Outbox Console (from Task 017 admin API)
// ============================================================

export const outboxConsoleApi = {
  list: (params?: { status?: string; event_type?: string }) =>
    apiClient.get<OutboxEvent[]>('/admin/bg/outbox', { params }),
  getStats: () => apiClient.get<OutboxStats>('/admin/bg/outbox/stats'),
  getById: (id: UUID) => apiClient.get<OutboxEvent>(`/admin/bg/outbox/${id}`),
  replay: (id: UUID) => apiClient.post<{ message: string }>(`/admin/bg/outbox/${id}/replay`),
}

// ============================================================
// Dead Letters (from Task 017 admin API)
// ============================================================

export const deadLetterApi = {
  list: (params?: { resolved?: boolean }) =>
    apiClient.get<DeadLetter[]>('/admin/bg/dead-letters', { params }),
  retry: (id: UUID) => apiClient.post<{ message: string }>(`/admin/bg/dead-letters/${id}/retry`),
  resolve: (id: UUID, notes?: string) =>
    apiClient.post<{ message: string }>(`/admin/bg/dead-letters/${id}/resolve`, { notes }),
}

// ============================================================
// Scheduler (from Task 017 admin API)
// ============================================================

export const schedulerApi = {
  listJobs: () => apiClient.get<ScheduledJob[]>('/admin/bg/jobs'),
  runJob: (name: string) => apiClient.post<{ message: string }>('/admin/bg/jobs/run', { job_name: name }),
  pauseJob: (id: UUID) => apiClient.post<{ message: string }>(`/admin/bg/jobs/${id}/pause`),
  resumeJob: (id: UUID) => apiClient.post<{ message: string }>(`/admin/bg/jobs/${id}/resume`),
}

// ============================================================
// Notification Operations (from Task 017 admin API)
// ============================================================

export const notificationOpsApi = {
  list: (params?: { status?: string }) =>
    apiClient.get<AdminNotification[]>('/admin/bg/notifications', { params }),
}

// ============================================================
// Email Operations
// ============================================================

export const emailOpsApi = {
  list: async (params?: { status?: string }): Promise<EmailDeliveryLog[]> => {
    const res = await apiClient.get<EmailDeliveryLog[] | { items: EmailDeliveryLog[] }>('/admin/bg/email-delivery', { params })
    return Array.isArray(res) ? res : (res?.items ?? [])
  },
  retry: (id: UUID) => apiClient.post<{ message: string }>(`/admin/bg/email-delivery/${id}/retry`),
}

// ============================================================
// Billing
// ============================================================

export const billingApi = {
  listPlans: () => apiClient.get<BillingPlan[]>('/admin/billing/plans'),
  listSubscriptions: () => apiClient.get<AdminSubscription[]>('/admin/billing/subscriptions'),
  listInvoices: () => apiClient.get<AdminInvoice[]>('/admin/billing/invoices'),
  getRevenue: () => apiClient.get<RevenueDashboard>('/admin/billing/revenue'),
}

// ============================================================
// Platform Analytics
// ============================================================

export const platformAnalyticsApi = {
  get: () => apiClient.get<PlatformAnalytics>('/admin/analytics'),
}

// ============================================================
// System Configuration
// ============================================================

export const systemConfigApi = {
  get: () => apiClient.get<SystemConfig>('/admin/system-config'),
  update: (data: Partial<SystemConfig>) => apiClient.patch<SystemConfig>('/admin/system-config', data),
  setMaintenanceMode: (enabled: boolean) =>
    apiClient.post<{ message: string }>('/admin/system-config/maintenance', { enabled }),
}

// ============================================================
// Admin Search
// ============================================================

export const adminSearchApi = {
  search: (query: string) =>
    apiClient.get<AdminSearchResult>(`/admin/search?q=${encodeURIComponent(query)}`),
}

// ============================================================
// Bulk Operations
// ============================================================

export const adminBulkApi = {
  execute: (action: AdminBulkAction, ids: UUID[], options?: Record<string, unknown>) =>
    apiClient.post<BulkActionResult>('/admin/bulk', { action, ids, options }),
}
