'use client'

import Link from 'next/link'
import { Clock, LogIn } from 'lucide-react'

import { AuthLayout } from '@/components/layout/auth-layout'
import { Button } from '@/components/ui/button'
import { ROUTES } from '@/lib/constants'

export default function SessionExpiredPage() {
  return (
    <AuthLayout
      title="Session expired"
      description="Your session has expired. Please log in again."
    >
      <div className="space-y-6 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-warning/10">
          <Clock className="h-8 w-8 text-warning" aria-hidden="true" />
        </div>
        <p className="text-sm text-muted-foreground">
          For your security, you&apos;ve been logged out after a period of inactivity.
        </p>
        <Button className="w-full" asChild leftIcon={<LogIn className="h-4 w-4" />}>
          <Link href={ROUTES.LOGIN}>Log in again</Link>
        </Button>
      </div>
    </AuthLayout>
  )
}
