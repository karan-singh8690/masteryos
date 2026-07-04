# Offline UX

> Offline detection and cached data handling.

## Approach

The Mastery Engine frontend uses React Query's built-in caching to provide a graceful offline experience:

1. **Cached data**: React Query keeps data in memory. When offline, the UI shows the last cached data.
2. **Error handling**: Network errors are caught and displayed as error states with retry buttons.
3. **Reconnection**: When the network is restored, React Query automatically refetches stale queries.

## Offline Detection

The `useOnlineStatus` hook (future) will detect offline state:

```typescript
const isOnline = useOnlineStatus()
// When offline, show cached data with a banner
```

## Cached Pages

| Page | Cached Data | Behavior When Offline |
|---|---|---|
| Dashboard | Last dashboard data | Shows cached data with "offline" banner |
| Mastery | Last mastery scores | Shows cached scores |
| Reviews | Last due reviews | Shows cached review list |
| Study Session | Current question | Can submit when reconnected (queued) |

## Queued Mutations

When offline, mutations (submit answer, mark notification read) are queued and retried when reconnected. This is handled by React Query's `onError` retry logic.

## Reconnect Handling

- React Query automatically refetches all stale queries when the window regains focus
- The API client's 401 interceptor handles token refresh on reconnection
- The user sees fresh data without manual refresh

## Offline Page

A dedicated `/offline` page is shown when the user navigates to a page that requires network access and no cached data is available.

## Future Enhancements

- Service Worker for offline page caching
- IndexedDB persistence for React Query cache
- Background sync for queued mutations
- Progressive loading of cached dashboard data
