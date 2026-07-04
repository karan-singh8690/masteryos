'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

import { APP_NAME, ROUTES } from '@/lib/constants'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { useAuth } from '@/providers/auth-provider'

interface PublicLayoutProps {
  children: React.ReactNode
}

export function PublicLayout({ children }: PublicLayoutProps) {
  const pathname = usePathname()
  const { isAuthenticated } = useAuth()

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <Link href={ROUTES.HOME} className="flex items-center gap-2">
            <span className="text-lg font-bold">{APP_NAME}</span>
          </Link>
          <nav className="flex items-center gap-2">
            <ThemeToggle />
            {isAuthenticated ? (
              <Button asChild size="sm">
                <Link href={ROUTES.DASHBOARD}>Dashboard</Link>
              </Button>
            ) : (
              <>
                <Button asChild variant="ghost" size="sm">
                  <Link href={ROUTES.LOGIN}>Log in</Link>
                </Button>
                <Button asChild size="sm">
                  <Link href={ROUTES.REGISTER}>Sign up</Link>
                </Button>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t py-6">
        <div className="container flex flex-col items-center justify-between gap-4 text-sm text-muted-foreground sm:flex-row">
          <p>&copy; {new Date().getFullYear()} {APP_NAME}. All rights reserved.</p>
          <nav className="flex gap-4">
            <Link href="/about" className="hover:text-foreground">About</Link>
            <Link href="/privacy" className="hover:text-foreground">Privacy</Link>
            <Link href="/terms" className="hover:text-foreground">Terms</Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}
