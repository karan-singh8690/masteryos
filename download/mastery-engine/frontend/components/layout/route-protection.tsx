'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'

import { useAuth } from '@/providers/auth-provider'
import { ROUTES } from '@/lib/constants'
import { CenteredSpinner } from '@/components/ui/spinner'

interface ProtectedRouteProps {
  children: React.ReactNode
  requireRoles?: string[]
}

export function ProtectedRoute({ children, requireRoles }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth()
  const router = useRouter()

  React.useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push(ROUTES.LOGIN)
    }
  }, [isLoading, isAuthenticated, router])

  React.useEffect(() => {
    if (!isLoading && isAuthenticated && requireRoles && user) {
      const hasRole = user.roles.some((role) => requireRoles.includes(role))
      if (!hasRole) {
        router.push(ROUTES.FORBIDDEN)
      }
    }
  }, [isLoading, isAuthenticated, requireRoles, user, router])

  if (isLoading) {
    return <CenteredSpinner label="Loading..." />
  }

  if (!isAuthenticated) {
    return null
  }

  if (requireRoles && user) {
    const hasRole = user.roles.some((role) => requireRoles.includes(role))
    if (!hasRole) return null
  }

  return <>{children}</>
}

interface PermissionGuardProps {
  children: React.ReactNode
  permission: string
  fallback?: React.ReactNode
}

export function PermissionGuard({
  children,
  permission,
  fallback = null,
}: PermissionGuardProps) {
  const { user } = useAuth()

  if (!user || !user.permissions.includes(permission)) {
    return <>{fallback}</>
  }

  return <>{children}</>
}

interface RoleGuardProps {
  children: React.ReactNode
  roles: string[]
  fallback?: React.ReactNode
}

export function RoleGuard({ children, roles, fallback = null }: RoleGuardProps) {
  const { user } = useAuth()

  if (!user || !user.roles.some((role) => roles.includes(role))) {
    return <>{fallback}</>
  }

  return <>{children}</>
}
