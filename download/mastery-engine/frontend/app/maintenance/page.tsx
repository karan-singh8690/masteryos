'use client'

import { Wrench } from 'lucide-react'

export default function MaintenancePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-warning/10">
        <Wrench className="h-10 w-10 text-warning" aria-hidden="true" />
      </div>
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">Under maintenance</h1>
        <p className="max-w-md text-muted-foreground">
          We&apos;re performing scheduled maintenance. We&apos;ll be back shortly.
        </p>
      </div>
      <p className="text-sm text-muted-foreground">
        Thank you for your patience.
      </p>
    </div>
  )
}
