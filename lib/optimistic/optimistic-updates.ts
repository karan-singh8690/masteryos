/**
 * Optimistic UI helpers — React Query mutation configuration for optimistic updates.
 *
 * Provides reusable optimistic update patterns:
 * - onMutate: cancel queries + snapshot + apply optimistic update
 * - onError: rollback to snapshot
 * - onSettled: invalidate to refetch
 */

import type { QueryClient } from '@tanstack/react-query'
import type { QueryKey } from '@tanstack/react-query'

/**
 * Optimistic update configuration for list operations (add/update/remove items).
 */
export function optimisticListUpdate<T extends { id: string }>(
  queryClient: QueryClient,
  queryKey: QueryKey,
  operation: 'add' | 'update' | 'remove',
  optimisticItem: T,
) {
  return {
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey })
      const previous = queryClient.getQueryData<T[]>(queryKey)

      queryClient.setQueryData<T[]>(queryKey, (old = []) => {
        switch (operation) {
          case 'add':
            return [...old, optimisticItem]
          case 'update':
            return old.map((item) => (item.id === optimisticItem.id ? optimisticItem : item))
          case 'remove':
            return old.filter((item) => item.id !== optimisticItem.id)
          default:
            return old
        }
      })

      return { previous }
    },
    onError: (_err: unknown, _variables: unknown, context: { previous?: T[] } | undefined) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKey, context.previous)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey })
    },
  }
}

/**
 * Optimistic update for a single item (e.g., toggle a feature flag).
 */
export function optimisticToggle(
  queryClient: QueryClient,
  queryKey: QueryKey,
  fieldName: string,
  newValue: unknown,
) {
  return {
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey })
      const previous = queryClient.getQueryData<Record<string, unknown>>(queryKey)
      queryClient.setQueryData<Record<string, unknown>>(queryKey, (old) => ({
        ...(old || {}),
        [fieldName]: newValue,
      }))
      return { previous }
    },
    onError: (_err: unknown, _variables: unknown, context: { previous?: Record<string, unknown> } | undefined) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKey, context.previous)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey })
    },
  }
}

/**
 * Optimistic update for notification read status.
 */
export function optimisticNotificationRead(queryClient: QueryClient, notificationId: string) {
  return {
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ['learner', 'notifications'] })
      const previous = queryClient.getQueryData<{ items: { id: string; status: string }[] }>(['learner', 'notifications'])
      if (previous) {
        queryClient.setQueryData(['learner', 'notifications'], {
          ...previous,
          items: previous.items.map((n) =>
            n.id === notificationId ? { ...n, status: 'opened' } : n,
          ),
        })
      }
      return { previous }
    },
    onError: (_err: unknown, _variables: unknown, context: { previous?: unknown } | undefined) => {
      if (context?.previous) {
        queryClient.setQueryData(['learner', 'notifications'], context.previous)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['learner', 'notifications'] })
      queryClient.invalidateQueries({ queryKey: ['learner', 'notifications', 'unread-count'] })
    },
  }
}

/**
 * Optimistic update for answer submission — immediately shows "submitting" state.
 */
export function optimisticAnswerSubmit(queryClient: QueryClient, questionInstanceId: string) {
  return {
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ['learner', 'questions', questionInstanceId] })
      const previous = queryClient.getQueryData(['learner', 'questions', questionInstanceId])
      // Mark question as "submitting" in cache
      queryClient.setQueryData(['learner', 'questions', questionInstanceId], (old: unknown) => ({
        ...(old as object),
        _submitting: true,
      }))
      return { previous }
    },
    onError: (_err: unknown, _variables: unknown, context: { previous?: unknown } | undefined) => {
      if (context?.previous) {
        queryClient.setQueryData(['learner', 'questions', questionInstanceId], context.previous)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['learner', 'dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['learner', 'mastery'] })
    },
  }
}

/**
 * Optimistic update for feature flag toggle.
 */
export function optimisticFeatureFlagToggle(
  queryClient: QueryClient,
  flagId: string,
  enabled: boolean,
) {
  return {
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ['admin', 'feature-flags'] })
      const previous = queryClient.getQueryData<{ id: string; enabled: boolean }[]>(['admin', 'feature-flags'])
      if (previous) {
        queryClient.setQueryData(['admin', 'feature-flags'], previous.map((f) =>
          f.id === flagId ? { ...f, enabled } : f,
        ))
      }
      return { previous }
    },
    onError: (_err: unknown, _variables: unknown, context: { previous?: unknown } | undefined) => {
      if (context?.previous) {
        queryClient.setQueryData(['admin', 'feature-flags'], context.previous)
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'feature-flags'] })
    },
  }
}
