'use client'

import Link from 'next/link'
import { Home } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { ROUTES } from '@/lib/constants'

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <p className="text-7xl font-bold text-primary">404</p>
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">Page not found</h1>
        <p className="max-w-md text-muted-foreground">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
      </div>
      <Button asChild leftIcon={<Home className="h-4 w-4" />}>
        <Link href={ROUTES.HOME}>Back to home</Link>
      </Button>
    </div>
  )
}
