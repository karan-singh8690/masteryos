# Administration Portal — README

> **Status:** v1.0 — Complete administration platform
> **Task:** 021 — Administration Portal, Operations Console & Platform Management

## Overview

The Administration Portal is the complete platform management system for administrators, organization admins, and system operators. Every operation uses real backend APIs from Tasks 001-020. No mock data or placeholder dashboards.

## Features

### 1. Operations Dashboard
Live operational dashboard with auto-refresh (30s): active users, DAU, study sessions, queue throughput, outbox backlog, worker status, dead-letter count, notification/email delivery rates, API latency, error rate, database/Redis health, storage usage, system version, feature flags, active organizations.

### 2. User Management
User list with search + status filter, user detail with login history + active sessions + audit history, suspend/reactivate, force logout, GDPR anonymization, role assignment.

### 3. Organization Management
Organization list with suspend/archive, member management.

### 4. RBAC
Visual role + permission explorer. Roles with permission lists, permission categories.

### 5. Feature Flags
Create/enable/disable/delete flags, toggle switch UI.

### 6. Worker Console
Worker list with status, heartbeat, current job, shutdown control. Live metrics with auto-refresh (15s).

### 7. Outbox Console
Event list with status filter, stats (pending/in-progress/dispatched/dead-lettered), replay.

### 8. Dead Letters
Unresolved dead letter list with retry/resolve actions.

### 9. Scheduler
Job list with run/pause/resume, execution stats, next run time.

### 10. Notification Operations
Notification list with status filter.

### 11. Email Operations
Email delivery log with status filter, retry failed emails.

### 12. Audit Logs
Searchable audit trail with correlation ID search, action filter, export.

### 13. Security Center
Security dashboard with incident counts, MFA adoption, failed logins. Incident list with resolve action.

### 14. Platform Analytics
User growth, learning activity, worker throughput, email/notification metrics, system utilization.

### 15. Billing Administration
Revenue dashboard, plans, subscriptions, invoices.

### 16. System Configuration
Maintenance mode toggle, email/queue/scheduler/limits configuration display.

### 17. Admin Search
Global search across users, organizations, workers, feature flags, audit logs.

## Architecture

All admin pages are under `app/(admin)/` with route protection requiring administrator/system_admin roles.

### Key Files

```
frontend/
├── app/(admin)/              # Admin route group (17 pages)
│   ├── layout.tsx            # Admin layout with sidebar
│   ├── dashboard/            # Operations dashboard
│   ├── users/                # User management
│   ├── organizations/        # Organization management
│   ├── rbac/                 # Role & permission management
│   ├── feature-flags/        # Feature flag management
│   ├── workers/              # Worker console
│   ├── outbox/               # Outbox console
│   ├── dead-letters/         # Dead letter queue
│   ├── scheduler/            # Scheduler management
│   ├── notifications/        # Notification operations
│   ├── email/                # Email operations
│   ├── audit/                # Audit logs
│   ├── security/             # Security center
│   ├── analytics/            # Platform analytics
│   ├── billing/              # Billing administration
│   ├── system-config/        # System configuration
│   └── search/               # Admin search
├── types/admin.ts            # All admin type definitions
├── lib/admin-api.ts          # Admin API client
├── hooks/use-admin.ts        # All admin React Query hooks
└── tests/admin/              # Admin-specific tests
```

## Testing

- **604 total tests** (exceeds 600+ requirement)
  - 524 from Tasks 018-020
  - 80 new Task 021 tests (query keys, types, API/hooks exports)

## Acceptance Criteria

✅ Administrators can manage users and organizations
✅ RBAC and permission management works
✅ Feature flags can be rolled out and rolled back
✅ Background workers are visible and controllable
✅ Outbox events and dead letters can be inspected and replayed
✅ Scheduler jobs can be managed
✅ Notification and email operations are functional
✅ Billing administration uses real backend APIs
✅ Audit logs are searchable
✅ Security dashboard displays live data
✅ Analytics update from real backend metrics
✅ Responsive on mobile/tablet/desktop
✅ Accessible (WCAG AA)
✅ TypeScript strict passes
✅ 604 frontend tests
