'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  BookOpen,
  GraduationCap,
  Calendar,
  Lightbulb,
  Trophy,
  Search,
  Settings,
  type LucideIcon,
} from 'lucide-react'

import { AppLayout } from '@/components/layout/app-layout'
import { ProtectedRoute } from '@/components/layout/route-protection'
import { Sidebar } from '@/components/layout/sidebar'
import { BetaBanner } from '@/components/beta/beta-banner'
import { BetaFeedbackButton } from '@/components/beta/feedback-button'
import { cn } from '@/lib/cn'
import { ROUTES } from '@/lib/constants'

interface NavItem {
  label: string
  href: string
  icon: LucideIcon
}

const LEARNER_NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Subjects', href: '/subjects', icon: BookOpen },
  { label: 'Study', href: '/study/start', icon: GraduationCap },
  { label: 'Reviews', href: '/reviews', icon: Calendar },
  { label: 'Recommendations', href: '/recommendations', icon: Lightbulb },
  { label: 'Achievements', href: '/achievements', icon: Trophy },
]

interface LearnerSidebarProps {
  className?: string
}

function LearnerSidebar({ className }: LearnerSidebarProps) {
  const pathname = usePathname()

  return (
    <aside
      className={cn('flex h-full w-64 flex-col border-r bg-card', className)}
      aria-label="Learner navigation"
    >
      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Main">
        <div className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Learn
        </div>
        {LEARNER_NAV_ITEMS.map((item) => {
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

        <div className="mb-2 mt-6 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Account
        </div>
        <Link
          href="/profile"
          className={cn(
            'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
            pathname === '/profile'
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
          )}
        >
          <Settings className="h-4 w-4" aria-hidden="true" />
          Profile
        </Link>
      </nav>

      <div className="border-t p-3">
        <Link
          href="/search"
          className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        >
          <Search className="h-4 w-4" aria-hidden="true" />
          Search
          <kbd className="ml-auto rounded border bg-muted px-1.5 py-0.5 text-xs">⌘K</kbd>
        </Link>
      </div>
    </aside>
  )
}

export default function LearnerLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ProtectedRoute>
      <div className="flex h-screen overflow-hidden">
        {/* Desktop sidebar */}
        <div className="hidden md:flex">
          <LearnerSidebar />
        </div>

        {/* Main content */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Reuse the header from AppLayout but with our learner sidebar */}
          <LearnerHeader />
          <BetaBanner />
          <main
            className="flex-1 overflow-y-auto bg-muted/30 p-4 md:p-6"
            id="main-content"
            tabIndex={-1}
          >
            {children}
          </main>
        </div>
      </div>
      <BetaFeedbackButton />
    </ProtectedRoute>
  )
}

// Import header separately to avoid circular dep
function LearnerHeader() {
  const [HeaderModule, setHeaderModule] = React.useState<any>(null)

  React.useEffect(() => {
    import('@/components/layout/header').then((mod) => {
      // The header uses the mobile nav from ui-store, which works fine
      // We just need to ensure it renders
      setHeaderModule(mod)
    })
  }, [])

  if (!HeaderModule) return null
  const Header = HeaderModule.Header
  return <Header />
}
