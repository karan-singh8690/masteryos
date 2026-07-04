'use client'

import Link from 'next/link'
import { ShieldX } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { ROUTES } from '@/lib/constants'

export default function UnauthorizedPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-destructive/10">
        <ShieldX className="h-10 w-10 text-destructive" aria-hidden="true" />
      </div>
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">Unauthorized</h1>
        <p className="max-w-md text-muted-foreground">
          You need to be logged in to access this page.
        </p>
      </div>
      <Button asChild>
        <Link href={ROUTES.LOGIN}>Log in</Link>
      </Button>
    </div>
  )
}
