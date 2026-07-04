/**
 * Administration types — users, organizations, RBAC, feature flags,
 * audit logs, security, workers, outbox, scheduler, billing.
 */

import type { ISO8601, UUID, PaginatedResponse, PaginationParams } from './common'

// ============================================================
// Admin User Management
// ============================================================

export interface AdminUser {
  id: UUID
  email: string
  status: 'pending_verification' | 'active' | 'suspended' | 'deactivated' | 'pending_deletion' | 'anonymized'
  mfa_enabled: boolean
  email_verified_at: ISO8601 | null
  created_at: ISO8601
  updated_at: ISO8601
  roles: string[]
  last_login_at: ISO8601 | null
  organization_id: UUID | null
  display_name: string
}

export interface AdminUserDetail extends AdminUser {
  sessions: AdminSession[]
  audit_logs: AdminAuditLogEntry[]
  login_history: LoginHistoryEntry[]
  permissions: string[]
}

export interface AdminSession {
  id: UUID
  device_fingerprint: string | null
  last_ip: string | null
  user_agent: string | null
  expires_at: ISO8601
  last_seen_at: ISO8601
  created_at: ISO8601
  revoked_at: ISO8601 | null
}

export interface LoginHistoryEntry {
  id: UUID
  success: boolean
  ip_address: string | null
  user_agent: string | null
  created_at: ISO8601
}

export interface AdminUserListParams extends PaginationParams {
  search?: string
  status?: string
  role?: string
}

// ============================================================
// Organization Management
// ============================================================

export interface Organization {
  id: UUID
  name: string
  slug: string
  status: 'active' | 'suspended' | 'archived'
  member_count: number
  subject_count: number
  created_at: ISO8601
  updated_at: ISO8601
  settings: Record<string, unknown>
}

export interface OrganizationMember {
  id: UUID
  user_id: UUID
  email: string
  display_name: string
  role: string
  joined_at: ISO8601
}

export interface OrganizationInvitation {
  id: UUID
  email: string
  role: string
  status: 'pending' | 'accepted' | 'expired' | 'revoked'
  invited_at: ISO8601
  expires_at: ISO8601
}

// ============================================================
// RBAC (Role-Based Access Control)
// ============================================================

export interface Role {
  name: string
  description: string
  permissions: string[]
  user_count: number
  is_system: boolean
}

export interface Permission {
  code: string
  description: string
  category: string
}

export interface RoleAssignment {
  user_id: UUID
  role: string
  assigned_at: ISO8601
  assigned_by: UUID
  scope: 'global' | 'organization'
  scope_id: UUID | null
}

// ============================================================
// Feature Flags
// ============================================================

export interface FeatureFlag {
  id: UUID
  key: string
  name: string
  description: string
  enabled: boolean
  rollout_percentage: number
  target_users: UUID[]
  target_organizations: UUID[]
  scheduled_at: ISO8601 | null
  created_at: ISO8601
  updated_at: ISO8601
  created_by: UUID
}

export interface CreateFeatureFlagRequest {
  key: string
  name: string
  description?: string
  enabled?: boolean
  rollout_percentage?: number
}

// ============================================================
// Audit Logs
// ============================================================

export interface AdminAuditLogEntry {
  id: UUID
  user_id: UUID | null
  user_email: string | null
  action: string
  resource_type: string | null
  resource_id: UUID | null
  ip_address: string | null
  user_agent: string | null
  success: boolean
  details: Record<string, unknown>
  correlation_id: string | null
  created_at: ISO8601
}

export interface AuditLogFilter extends PaginationParams {
  user_id?: UUID
  action?: string
  resource_type?: string
  start_date?: ISO8601
  end_date?: ISO8601
  correlation_id?: string
  success?: boolean
}

// ============================================================
// Security Center
// ============================================================

export interface SecurityIncident {
  id: UUID
  user_id: UUID | null
  incident_type: string
  severity: 'info' | 'warning' | 'critical'
  description: string
  ip_address: string | null
  user_agent: string | null
  metadata: Record<string, unknown>
  resolved_at: ISO8601 | null
  resolved_by: UUID | null
  resolution_notes: string | null
  created_at: ISO8601
}

export interface SecurityDashboard {
  total_incidents: number
  unresolved_incidents: number
  critical_incidents: number
  failed_logins_24h: number
  suspicious_sessions: number
  mfa_adoption_rate: number
  password_resets_24h: number
  rate_limit_violations_24h: number
  recent_incidents: SecurityIncident[]
}

// ============================================================
// Worker Console (from Task 017)
// ============================================================

export interface AdminWorker {
  worker_id: string
  worker_type: string
  hostname: string | null
  process_id: number | null
  status: 'starting' | 'running' | 'draining' | 'stopped' | 'crashed'
  last_seen_at: ISO8601 | null
  started_at: ISO8601 | null
  jobs_processed: number
  jobs_failed: number
  current_job: string | null
  shutdown_requested: boolean
  is_stale: boolean
}

export interface WorkerMetrics {
  outbox: {
    pending: number
    dispatched: number
    dead_lettered: number
    in_progress: number
    oldest_pending_age_seconds: number | null
    avg_dispatch_latency_seconds: number | null
  }
  workers: {
    active: number
    dead: number
    total_processed: number
    total_failed: number
  }
  retries: { events_being_retried: number }
  dead_letters: { unresolved: number }
  email: {
    sent: number
    failed: number
    bounced: number
    pending_retry: number
  }
  notifications: {
    queued: number
    sent: number
    delivered: number
    failed: number
    avg_latency_seconds: number | null
  }
  throughput_per_minute: number | null
  collected_at: ISO8601
}

// ============================================================
// Outbox Console (from Task 017)
// ============================================================

export interface OutboxEvent {
  id: UUID
  event_type: string
  aggregate_id: UUID
  aggregate_type: string
  status: 'pending' | 'dispatched' | 'dead_lettered'
  dispatch_attempt_count: number
  last_dispatch_error: string | null
  created_at: ISO8601
  dispatched_at: ISO8601 | null
  leased_by: string | null
  next_retry_at: ISO8601 | null
}

export interface OutboxStats {
  pending: number
  dispatched: number
  dead_lettered: number
  leased_in_progress: number
  oldest_pending_age_seconds: number | null
}

export interface DeadLetter {
  id: UUID
  original_event_id: UUID
  event_type: string
  aggregate_id: UUID
  error_message: string
  error_type: string
  retry_count: number
  severity: 'warning' | 'error' | 'critical'
  resolved_at: ISO8601 | null
  created_at: ISO8601
}

// ============================================================
// Scheduler (from Task 017)
// ============================================================

export interface ScheduledJob {
  id: UUID
  name: string
  description: string | null
  handler_name: string
  schedule_type: 'cron' | 'interval' | 'one_time'
  schedule_expr: string
  status: 'active' | 'paused' | 'disabled'
  next_run_at: ISO8601
  last_run_at: ISO8601 | null
  last_run_status: 'success' | 'failed' | null
  last_run_error: string | null
  run_count: number
  failure_count: number
  consecutive_failures: number
}

// ============================================================
// Notification Operations (from Task 017)
// ============================================================

export interface AdminNotification {
  id: UUID
  user_id: UUID
  notification_type: string
  channel: string
  priority: string
  status: string
  title: string
  body: string
  created_at: ISO8601
  scheduled_at: ISO8601
  sent_at: ISO8601 | null
  delivered_at: ISO8601 | null
}

// ============================================================
// Email Operations (from Task 017)
// ============================================================

export interface EmailDeliveryLog {
  id: UUID
  notification_id: UUID | null
  user_id: UUID | null
  to_address: string
  from_address: string
  subject: string
  template_name: string
  status: 'queued' | 'sent' | 'delivered' | 'bounced' | 'failed' | 'deferred'
  message_id: string | null
  error_message: string | null
  bounce_type: string | null
  attempt_count: number
  sent_at: ISO8601 | null
  delivered_at: ISO8601 | null
  created_at: ISO8601
}

// ============================================================
// Billing Administration
// ============================================================

export interface BillingPlan {
  id: UUID
  name: string
  code: string
  price_monthly: number
  price_yearly: number
  features: Record<string, unknown>
  status: 'active' | 'archived'
  created_at: ISO8601
}

export interface AdminSubscription {
  id: UUID
  user_id: UUID
  plan_id: UUID
  plan_name: string
  status: 'active' | 'canceled' | 'past_due' | 'trialing'
  current_period_start: ISO8601
  current_period_end: ISO8601
  canceled_at: ISO8601 | null
  created_at: ISO8601
}

export interface AdminInvoice {
  id: UUID
  user_id: UUID
  subscription_id: UUID | null
  amount: number
  currency: string
  status: 'draft' | 'open' | 'paid' | 'uncollectible' | 'void'
  due_date: ISO8601
  paid_at: ISO8601 | null
  created_at: ISO8601
}

export interface RevenueDashboard {
  total_revenue: number
  monthly_revenue: number
  active_subscriptions: number
  trial_subscriptions: number
  churn_rate: number
  revenue_by_plan: { plan_name: string; revenue: number }[]
  revenue_trend: { date: string; revenue: number }[]
}

// ============================================================
// Platform Analytics
// ============================================================

export interface PlatformAnalytics {
  user_growth: { date: string; total_users: number; new_users: number }[]
  learning_activity: { date: string; sessions: number; questions_answered: number }[]
  content_growth: { date: string; templates: number; concepts: number }[]
  worker_throughput: { date: string; events_processed: number }[]
  email_metrics: { sent: number; failed: number; bounced: number }
  notification_metrics: { queued: number; delivered: number; failed: number }
  system_utilization: {
    cpu_usage: number
    memory_usage: number
    disk_usage: number
    db_connections: number
    redis_connections: number
  }
}

// ============================================================
// Operations Dashboard
// ============================================================

export interface OperationsDashboard {
  active_users: number
  daily_active_users: number
  active_study_sessions: number
  queue_throughput: number
  outbox_backlog: number
  worker_status: {
    active: number
    dead: number
    total: number
  }
  dead_letter_count: number
  notification_delivery_rate: number
  email_delivery_rate: number
  api_latency_ms: number
  error_rate: number
  database_health: 'healthy' | 'degraded' | 'down'
  redis_health: 'healthy' | 'degraded' | 'down'
  background_jobs: number
  storage_usage: { used: number; total: number }
  system_version: string
  feature_flags_enabled: number
  active_organizations: number
}

// ============================================================
// System Configuration
// ============================================================

export interface SystemConfig {
  maintenance_mode: boolean
  email: {
    from_address: string
    rate_limit_per_minute: number
    retry_enabled: boolean
  }
  queue: {
    batch_size: number
    visibility_timeout_seconds: number
    max_retries: number
  }
  scheduler: {
    poll_interval_seconds: number
    lock_duration_minutes: number
  }
  notifications: {
    default_channel: string
    digest_frequency: string
  }
  limits: {
    max_sessions_per_user: number
    max_enrollments_per_user: number
    rate_limit_per_minute: number
  }
}

// ============================================================
// Admin Search
// ============================================================

export interface AdminSearchResult {
  users: AdminUser[]
  organizations: Organization[]
  subjects: { id: UUID; name: string; code: string }[]
  templates: { id: UUID; code: string; question_type: string }[]
  notifications: AdminNotification[]
  jobs: ScheduledJob[]
  workers: AdminWorker[]
  audit_logs: AdminAuditLogEntry[]
  feature_flags: FeatureFlag[]
}

// ============================================================
// Bulk Operations
// ============================================================

export type AdminBulkAction =
  | 'suspend_users'
  | 'reactivate_users'
  | 'delete_notifications'
  | 'replay_events'
  | 'retry_emails'
  | 'assign_roles'
  | 'archive_organizations'

export interface BulkActionResult {
  success: boolean
  affected_count: number
  errors: { id: UUID; error: string }[]
}
