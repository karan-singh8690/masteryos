'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  BookOpen,
  FileCode,
  Search,
  BarChart3,
  Upload,
  type LucideIcon,
} from 'lucide-react'

import { ProtectedRoute } from '@/components/layout/route-protection'
import { cn } from '@/lib/cn'
import { useUIStore } from '@/stores/ui-store'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Menu } from 'lucide-react'

interface NavItem {
  label: string
  href: string
  icon: LucideIcon
}

const CONTENT_NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/content/dashboard', icon: LayoutDashboard },
  { label: 'Subjects', href: '/content/subjects', icon: BookOpen },
  { label: 'Templates', href: '/content/templates', icon: FileCode },
  { label: 'Search', href: '/content/search', icon: Search },
  { label: 'Analytics', href: '/content/analytics', icon: BarChart3 },
  { label: 'Import/Export', href: '/content/import-export', icon: Upload },
]

function ContentSidebar({ className }: { className?: string }) {
  const pathname = usePathname()

  return (
    <aside
      className={cn('flex h-full w-64 flex-col border-r bg-card', className)}
      aria-label="Content authoring navigation"
    >
      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Main">
        <div className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Content
        </div>
        {CONTENT_NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                active
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
              )}
              aria-current={active ? 'page' : undefined}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}

export default function ContentLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ProtectedRoute requireRoles={['instructor', 'content_editor', 'administrator', 'system_admin']}>
      <div className="flex h-screen overflow-hidden">
        <div className="hidden md:flex">
          <ContentSidebar />
        </div>
        <div className="flex flex-1 flex-col overflow-hidden">
          <ContentHeader />
          <main
            className="flex-1 overflow-y-auto bg-muted/30 p-4 md:p-6"
            id="main-content"
            tabIndex={-1}
          >
            {children}
          </main>
        </div>
      </div>
    </ProtectedRoute>
  )
}

function ContentHeader() {
  const pathname = usePathname()
  const { mobileNavOpen, setMobileNavOpen } = useUIStore()

  const pageTitle = React.useMemo(() => {
    const segments = pathname.split('/').filter(Boolean)
    if (segments.length <= 1) return 'Content'
    const last = segments[segments.length - 1]
    return last ? last.charAt(0).toUpperCase() + last.slice(1) : 'Content'
  }, [pathname])

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={() => setMobileNavOpen(true)}
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </Button>
      <div className="flex-1">
        <span className="text-sm font-semibold">{pageTitle}</span>
      </div>
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-72 p-0">
          <ContentSidebar />
        </SheetContent>
      </Sheet>
    </header>
  )
}
