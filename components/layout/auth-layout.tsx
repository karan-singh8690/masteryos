'use client'

import * as React from 'react'
import Link from 'next/link'

import { APP_NAME, ROUTES } from '@/lib/constants'
import { ThemeToggle } from '@/components/layout/theme-toggle'

interface AuthLayoutProps {
  children: React.ReactNode
  title?: string
  description?: string
  footer?: React.ReactNode
}

export function AuthLayout({
  children,
  title,
  description,
  footer,
}: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col bg-muted/30">
      <header className="flex h-16 items-center justify-between px-4">
        <Link href={ROUTES.HOME} className="text-lg font-bold">
          {APP_NAME}
        </Link>
        <ThemeToggle />
      </header>
      <main className="flex flex-1 items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          <div className="rounded-lg border bg-card p-8 shadow-sm">
            {(title || description) && (
              <div className="mb-6 space-y-2 text-center">
                {title && (
                  <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
                )}
                {description && (
                  <p className="text-sm text-muted-foreground">{description}</p>
                )}
              </div>
            )}
            {children}
          </div>
          {footer && (
            <div className="mt-4 text-center text-sm text-muted-foreground">
              {footer}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
