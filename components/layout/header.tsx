'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Menu, Moon, Sun, Monitor } from 'lucide-react'
import { useTheme } from 'next-themes'

import { cn } from '@/lib/cn'
import { APP_NAME, ROUTES } from '@/lib/constants'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Breadcrumb, type BreadcrumbItem } from '@/components/ui/breadcrumb'
import { ProfileMenu } from '@/components/layout/profile-menu'
import { NotificationMenu } from '@/components/layout/notification-menu'
import { useUIStore } from '@/stores/ui-store'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { Sidebar } from '@/components/layout/sidebar'

export function Header() {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)
  const { mobileNavOpen, setMobileNavOpen } = useUIStore()

  React.useEffect(() => {
    setMounted(true)
  }, [])

  const breadcrumbItems = React.useMemo(() => {
    return pathToBreadcrumbs(pathname)
  }, [pathname])

  return (
    <header
      className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60"
      role="banner"
    >
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={() => setMobileNavOpen(true)}
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* Breadcrumbs */}
      <div className="hidden flex-1 md:block">
        {breadcrumbItems.length > 0 && <Breadcrumb items={breadcrumbItems} />}
      </div>

      {/* Mobile: show app name */}
      <div className="flex-1 md:hidden">
        <span className="text-sm font-semibold">{APP_NAME}</span>
      </div>

      {/* Right side actions */}
      <div className="flex items-center gap-2">
        {/* Theme toggle */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Toggle theme">
              {mounted && theme === 'dark' ? (
                <Moon className="h-5 w-5" />
              ) : mounted && theme === 'light' ? (
                <Sun className="h-5 w-5" />
              ) : (
                <Monitor className="h-5 w-5" />
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setTheme('light')}>
              <Sun className="mr-2 h-4 w-4" /> Light
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme('dark')}>
              <Moon className="mr-2 h-4 w-4" /> Dark
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme('system')}>
              <Monitor className="mr-2 h-4 w-4" /> System
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <NotificationMenu />
        <ProfileMenu />
      </div>

      {/* Mobile sidebar */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-72 p-0">
          <Sidebar />
        </SheetContent>
      </Sheet>
    </header>
  )
}

function pathToBreadcrumbs(pathname: string): BreadcrumbItem[] {
  if (pathname === ROUTES.HOME) return []
  if (pathname === ROUTES.DASHBOARD) return [{ label: 'Dashboard' }]

  const segments = pathname.split('/').filter(Boolean)
  const items: BreadcrumbItem[] = [{ label: 'Home', href: ROUTES.HOME }]

  let currentPath = ''
  for (const segment of segments) {
    currentPath += `/${segment}`
    const label = segment
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
    items.push({ label, href: currentPath })
  }

  // Mark last item as current (no href)
  if (items.length > 0) {
    const last = items[items.length - 1]!
    if (last) {
      last.href = undefined
    }
  }

  return items
}
