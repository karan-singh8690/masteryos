import type { Metadata } from 'next'

import { AppLayout } from '@/components/layout/app-layout'
import { ProtectedRoute } from '@/components/layout/route-protection'

export const metadata: Metadata = {
  title: 'Dashboard',
}

export default function AppLayoutRoute({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ProtectedRoute>
      <AppLayout>{children}</AppLayout>
    </ProtectedRoute>
  )
}
