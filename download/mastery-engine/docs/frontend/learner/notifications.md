# Notifications

> In-app notification center.

## Page (`/notifications`)

- Header with total count + "Mark all read" button
- Paginated list of notifications (20 per page)
- Each notification shows:
  - Title
  - Body text
  - Smart date (Today at HH:MM, Yesterday at HH:MM, or full date)
  - Unread indicator (blue dot)
  - "Mark as read" button (✓)
  - "Dismiss" button (✗)
- Unread notifications have a primary border + background tint

## Actions

### Mark as Read

Calls `POST /notifications/{id}/open`:
- Updates notification status to "opened"
- Removes the unread indicator
- Decrements the unread count in the notification store

### Dismiss

Calls `POST /notifications/{id}/dismiss`:
- Updates notification status to "dismissed"
- Removes the notification from the visible list (on next refetch)

### Mark All as Read

Calls `POST /notifications/mark-all-open`:
- Marks all delivered/sent notifications as opened
- Clears the unread badge in the header

## Data Sources

- `GET /notifications` — Paginated list
- `POST /notifications/{id}/open` — Mark as read
- `POST /notifications/{id}/dismiss` — Dismiss
- `POST /notifications/mark-all-open` — Mark all as read
- `GET /notifications/unread-count` — Unread count (polled every 60s)

## Notification Header Badge

The header `NotificationMenu` component shows an unread count badge that updates via the notification store. The store is populated by the `useUnreadNotificationCount` hook which polls every 60 seconds.
