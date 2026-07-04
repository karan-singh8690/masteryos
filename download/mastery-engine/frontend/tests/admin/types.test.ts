import { describe, it, expect } from 'vitest'
import type {
  AdminUser, AdminUserDetail, AdminSession, LoginHistoryEntry,
  Organization, OrganizationMember, OrganizationInvitation,
  Role, Permission, RoleAssignment,
  FeatureFlag, CreateFeatureFlagRequest,
  AdminAuditLogEntry, AuditLogFilter,
  SecurityDashboard, SecurityIncident,
  AdminWorker, WorkerMetrics,
  OutboxEvent, OutboxStats, DeadLetter,
  ScheduledJob, AdminNotification, EmailDeliveryLog,
  BillingPlan, AdminSubscription, AdminInvoice, RevenueDashboard,
  PlatformAnalytics, OperationsDashboard, SystemConfig,
  AdminSearchResult, AdminBulkAction, BulkActionResult,
} from '@/types/admin'

describe('Admin types', () => {
  it('AdminUser has all fields', () => {
    const u: AdminUser = { id: 'u1', email: 'test@test.com', status: 'active', mfa_enabled: false, email_verified_at: null, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z', roles: ['learner'], last_login_at: null, organization_id: null, display_name: 'Test' }
    expect(u.email).toBe('test@test.com')
  })
  it('AdminUserDetail extends AdminUser', () => {
    const d: AdminUserDetail = { id: 'u1', email: 't@t.com', status: 'active', mfa_enabled: false, email_verified_at: null, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z', roles: [], last_login_at: null, organization_id: null, display_name: 'T', sessions: [], audit_logs: [], login_history: [], permissions: [] }
    expect(d.sessions).toEqual([])
  })
  it('AdminSession has all fields', () => {
    const s: AdminSession = { id: 's1', device_fingerprint: null, last_ip: '1.2.3.4', user_agent: 'Chrome', expires_at: '2024-01-02T00:00:00Z', last_seen_at: '2024-01-01T00:00:00Z', created_at: '2024-01-01T00:00:00Z', revoked_at: null }
    expect(s.last_ip).toBe('1.2.3.4')
  })
  it('LoginHistoryEntry has all fields', () => {
    const h: LoginHistoryEntry = { id: 'h1', success: true, ip_address: '1.2.3.4', user_agent: 'Chrome', created_at: '2024-01-01T00:00:00Z' }
    expect(h.success).toBe(true)
  })
  it('Organization has all fields', () => {
    const o: Organization = { id: 'o1', name: 'Acme', slug: 'acme', status: 'active', member_count: 10, subject_count: 5, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z', settings: {} }
    expect(o.member_count).toBe(10)
  })
  it('OrganizationMember has all fields', () => {
    const m: OrganizationMember = { id: 'm1', user_id: 'u1', email: 't@t.com', display_name: 'T', role: 'learner', joined_at: '2024-01-01T00:00:00Z' }
    expect(m.role).toBe('learner')
  })
  it('OrganizationInvitation has all fields', () => {
    const i: OrganizationInvitation = { id: 'i1', email: 't@t.com', role: 'learner', status: 'pending', invited_at: '2024-01-01T00:00:00Z', expires_at: '2024-01-02T00:00:00Z' }
    expect(i.status).toBe('pending')
  })
  it('Role has all fields', () => {
    const r: Role = { name: 'learner', description: 'Standard learner', permissions: ['identity:user:read_self'], user_count: 100, is_system: true }
    expect(r.is_system).toBe(true)
  })
  it('Permission has all fields', () => {
    const p: Permission = { code: 'identity:user:read_self', description: 'Read own profile', category: 'identity' }
    expect(p.category).toBe('identity')
  })
  it('RoleAssignment has all fields', () => {
    const a: RoleAssignment = { user_id: 'u1', role: 'learner', assigned_at: '2024-01-01T00:00:00Z', assigned_by: 'u2', scope: 'global', scope_id: null }
    expect(a.scope).toBe('global')
  })
  it('FeatureFlag has all fields', () => {
    const f: FeatureFlag = { id: 'f1', key: 'new_feature', name: 'New Feature', description: '', enabled: true, rollout_percentage: 100, target_users: [], target_organizations: [], scheduled_at: null, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z', created_by: 'u1' }
    expect(f.enabled).toBe(true)
  })
  it('CreateFeatureFlagRequest has required fields', () => {
    const r: CreateFeatureFlagRequest = { key: 'test', name: 'Test' }
    expect(r.key).toBe('test')
  })
  it('AdminAuditLogEntry has all fields', () => {
    const e: AdminAuditLogEntry = { id: 'a1', user_id: 'u1', user_email: 't@t.com', action: 'LOGIN_SUCCESS', resource_type: null, resource_id: null, ip_address: '1.2.3.4', user_agent: 'Chrome', success: true, details: {}, correlation_id: 'corr-1', created_at: '2024-01-01T00:00:00Z' }
    expect(e.action).toBe('LOGIN_SUCCESS')
  })
  it('AuditLogFilter has optional fields', () => {
    const f: AuditLogFilter = { action: 'LOGIN_SUCCESS', page: 1, pageSize: 20 }
    expect(f.action).toBe('LOGIN_SUCCESS')
  })
  it('SecurityDashboard has all fields', () => {
    const d: SecurityDashboard = { total_incidents: 5, unresolved_incidents: 2, critical_incidents: 1, failed_logins_24h: 10, suspicious_sessions: 3, mfa_adoption_rate: 0.8, password_resets_24h: 5, rate_limit_violations_24h: 2, recent_incidents: [] }
    expect(d.mfa_adoption_rate).toBe(0.8)
  })
  it('SecurityIncident has all fields', () => {
    const i: SecurityIncident = { id: 'si1', user_id: 'u1', incident_type: 'login_brute_force', severity: 'critical', description: 'Multiple failed logins', ip_address: '1.2.3.4', user_agent: 'Chrome', metadata: {}, resolved_at: null, resolved_by: null, resolution_notes: null, created_at: '2024-01-01T00:00:00Z' }
    expect(i.severity).toBe('critical')
  })
  it('AdminWorker has all fields', () => {
    const w: AdminWorker = { worker_id: 'w1', worker_type: 'dispatcher', hostname: 'host1', process_id: 123, status: 'running', last_seen_at: '2024-01-01T00:00:00Z', started_at: '2024-01-01T00:00:00Z', jobs_processed: 100, jobs_failed: 5, current_job: 'event-1', shutdown_requested: false, is_stale: false }
    expect(w.status).toBe('running')
  })
  it('WorkerMetrics has all fields', () => {
    const m: WorkerMetrics = { outbox: { pending: 5, dispatched: 100, dead_lettered: 2, in_progress: 3, oldest_pending_age_seconds: 30, avg_dispatch_latency_seconds: 1.5 }, workers: { active: 3, dead: 0, total_processed: 1000, total_failed: 10 }, retries: { events_being_retried: 1 }, dead_letters: { unresolved: 2 }, email: { sent: 50, failed: 2, bounced: 1, pending_retry: 3 }, notifications: { queued: 5, sent: 100, delivered: 98, failed: 2, avg_latency_seconds: 0.5 }, throughput_per_minute: 12.5, collected_at: '2024-01-01T00:00:00Z' }
    expect(m.workers.active).toBe(3)
  })
  it('OutboxEvent has all fields', () => {
    const e: OutboxEvent = { id: 'e1', event_type: 'UserRegistered', aggregate_id: 'a1', aggregate_type: 'User', status: 'pending', dispatch_attempt_count: 0, last_dispatch_error: null, created_at: '2024-01-01T00:00:00Z', dispatched_at: null, leased_by: null, next_retry_at: null }
    expect(e.status).toBe('pending')
  })
  it('OutboxStats has all fields', () => {
    const s: OutboxStats = { pending: 5, dispatched: 100, dead_lettered: 2, leased_in_progress: 3, oldest_pending_age_seconds: 30 }
    expect(s.pending).toBe(5)
  })
  it('DeadLetter has all fields', () => {
    const d: DeadLetter = { id: 'd1', original_event_id: 'e1', event_type: 'TestEvent', aggregate_id: 'a1', error_message: 'Failed', error_type: 'ValueError', retry_count: 6, severity: 'error', resolved_at: null, created_at: '2024-01-01T00:00:00Z' }
    expect(d.severity).toBe('error')
  })
  it('ScheduledJob has all fields', () => {
    const j: ScheduledJob = { id: 'j1', name: 'cleanup', description: 'Cleanup job', handler_name: 'cleanup_handler', schedule_type: 'interval', schedule_expr: '3600', status: 'active', next_run_at: '2024-01-01T00:00:00Z', last_run_at: null, last_run_status: null, last_run_error: null, run_count: 0, failure_count: 0, consecutive_failures: 0 }
    expect(j.schedule_type).toBe('interval')
  })
  it('AdminNotification has all fields', () => {
    const n: AdminNotification = { id: 'n1', user_id: 'u1', notification_type: 'review_due', channel: 'in_app', priority: 'normal', status: 'delivered', title: 'Review due', body: 'You have reviews', created_at: '2024-01-01T00:00:00Z', scheduled_at: '2024-01-01T00:00:00Z', sent_at: null, delivered_at: null }
    expect(n.status).toBe('delivered')
  })
  it('EmailDeliveryLog has all fields', () => {
    const e: EmailDeliveryLog = { id: 'e1', notification_id: null, user_id: 'u1', to_address: 't@t.com', from_address: 'noreply@me.com', subject: 'Test', template_name: 'verification', status: 'sent', message_id: 'msg-1', error_message: null, bounce_type: null, attempt_count: 1, sent_at: '2024-01-01T00:00:00Z', delivered_at: null, created_at: '2024-01-01T00:00:00Z' }
    expect(e.status).toBe('sent')
  })
  it('BillingPlan has all fields', () => {
    const p: BillingPlan = { id: 'p1', name: 'Pro', code: 'pro', price_monthly: 29, price_yearly: 290, features: {}, status: 'active', created_at: '2024-01-01T00:00:00Z' }
    expect(p.price_monthly).toBe(29)
  })
  it('AdminSubscription has all fields', () => {
    const s: AdminSubscription = { id: 's1', user_id: 'u1', plan_id: 'p1', plan_name: 'Pro', status: 'active', current_period_start: '2024-01-01T00:00:00Z', current_period_end: '2024-02-01T00:00:00Z', canceled_at: null, created_at: '2024-01-01T00:00:00Z' }
    expect(s.status).toBe('active')
  })
  it('AdminInvoice has all fields', () => {
    const i: AdminInvoice = { id: 'i1', user_id: 'u1', subscription_id: 's1', amount: 29, currency: 'usd', status: 'paid', due_date: '2024-01-15T00:00:00Z', paid_at: '2024-01-10T00:00:00Z', created_at: '2024-01-01T00:00:00Z' }
    expect(i.status).toBe('paid')
  })
  it('RevenueDashboard has all fields', () => {
    const r: RevenueDashboard = { total_revenue: 10000, monthly_revenue: 1000, active_subscriptions: 100, trial_subscriptions: 10, churn_rate: 0.05, revenue_by_plan: [], revenue_trend: [] }
    expect(r.churn_rate).toBe(0.05)
  })
  it('PlatformAnalytics has all fields', () => {
    const a: PlatformAnalytics = { user_growth: [], learning_activity: [], content_growth: [], worker_throughput: [], email_metrics: { sent: 0, failed: 0, bounced: 0 }, notification_metrics: { queued: 0, delivered: 0, failed: 0 }, system_utilization: { cpu_usage: 0, memory_usage: 0, disk_usage: 0, db_connections: 0, redis_connections: 0 } }
    expect(a.system_utilization.cpu_usage).toBe(0)
  })
  it('OperationsDashboard has all fields', () => {
    const d: OperationsDashboard = { active_users: 100, daily_active_users: 50, active_study_sessions: 10, queue_throughput: 15, outbox_backlog: 5, worker_status: { active: 3, dead: 0, total: 3 }, dead_letter_count: 2, notification_delivery_rate: 0.95, email_delivery_rate: 0.98, api_latency_ms: 50, error_rate: 0.01, database_health: 'healthy', redis_health: 'healthy', background_jobs: 8, storage_usage: { used: 5e9, total: 50e9 }, system_version: '1.0.0', feature_flags_enabled: 5, active_organizations: 10 }
    expect(d.database_health).toBe('healthy')
  })
  it('SystemConfig has all fields', () => {
    const c: SystemConfig = { maintenance_mode: false, email: { from_address: 'noreply@me.com', rate_limit_per_minute: 60, retry_enabled: true }, queue: { batch_size: 100, visibility_timeout_seconds: 30, max_retries: 6 }, scheduler: { poll_interval_seconds: 5, lock_duration_minutes: 5 }, notifications: { default_channel: 'in_app', digest_frequency: 'immediate' }, limits: { max_sessions_per_user: 10, max_enrollments_per_user: 5, rate_limit_per_minute: 60 } }
    expect(c.maintenance_mode).toBe(false)
  })
  it('AdminSearchResult has all fields', () => {
    const r: AdminSearchResult = { users: [], organizations: [], subjects: [], templates: [], notifications: [], jobs: [], workers: [], audit_logs: [], feature_flags: [] }
    expect(r.users).toEqual([])
  })
  it('AdminBulkAction has all valid values', () => {
    const actions: AdminBulkAction[] = ['suspend_users', 'reactivate_users', 'delete_notifications', 'replay_events', 'retry_emails', 'assign_roles', 'archive_organizations']
    expect(actions).toHaveLength(7)
  })
  it('BulkActionResult has all fields', () => {
    const r: BulkActionResult = { success: true, affected_count: 10, errors: [] }
    expect(r.affected_count).toBe(10)
  })
})
