# State Management

> Minimal Zustand for global state; React Query for server state.

## Philosophy

- **Server state** → React Query (caching, invalidation, optimistic updates)
- **Global UI state** → Zustand (minimal: auth, theme, notifications, sidebar)
- **Local component state** → React useState

No Redux. No context for server state.

## Zustand Stores

### `auth-store.ts`

```typescript
interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  setUser: (user: User | null) => void
  logout: () => void
  updateProfile: (profile: Partial<User>) => void
}
```

### `ui-store.ts`

```typescript
interface UIState {
  sidebarOpen: boolean
  mobileNavOpen: boolean
  commandPaletteOpen: boolean
  toggleSidebar: () => void
  setMobileNavOpen: (open: boolean) => void
}
```

### `notification-store.ts`

```typescript
interface NotificationState {
  unreadCount: number
  setUnreadCount: (count: number) => void
  incrementUnread: () => void
  decrementUnread: () => void
}
```

## React Query

### Query Key Factory

```typescript
import { queryKey } from '@/lib/query-keys'

queryKey.users.me()              // ['users', 'me']
queryKey.notifications.list()    // ['notifications', 'list', undefined]
queryKey.admin.outbox({ status: 'pending' }) // ['admin', 'outbox', { status: 'pending' }]
```

### Usage

```typescript
const { data, isLoading } = useQuery({
  queryKey: queryKey.users.me(),
  queryFn: () => userApi.me(),
})

const mutation = useMutation({
  mutationFn: userApi.updateProfile,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: queryKey.users.me() })
  },
})
```

## Theme

Theme is managed by `next-themes` (not Zustand):

```typescript
import { useTheme } from 'next-themes'

const { theme, setTheme } = useTheme()
setTheme('dark')
```
