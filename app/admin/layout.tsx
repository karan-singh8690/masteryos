'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Users, Building2, Shield, Flag, Server,
  Mail, Clock, FileText, AlertTriangle, BarChart3, CreditCard,
  Settings, Search, type LucideIcon,
  Activity, HeartHandshake, GraduationCap, Wrench, Rocket,
  UserPlus,
  FlaskConical, ClipboardList, LineChart, type LucideIcon as LucideIcon2,
} from 'lucide-react'

import { ProtectedRoute } from '@/components/layout/route-protection'
import { cn } from '@/lib/cn'
import { useUIStore } from '@/stores/ui-store'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Menu } from 'lucide-react'

interface NavItem { label: string; href: string; icon: LucideIcon }

const ADMIN_NAV: NavItem[] = [
  { label: 'Dashboard', href: '/admin/dashboard', icon: LayoutDashboard },
  { label: 'Users', href: '/admin/users', icon: Users },
  { label: 'Organizations', href: '/admin/organizations', icon: Building2 },
  { label: 'RBAC', href: '/admin/rbac', icon: Shield },
  { label: 'Feature Flags', href: '/admin/feature-flags', icon: Flag },
  { label: 'Workers', href: '/admin/workers', icon: Server },
  { label: 'Outbox', href: '/admin/outbox', icon: FileText },
  { label: 'Dead Letters', href: '/admin/dead-letters', icon: AlertTriangle },
  { label: 'Scheduler', href: '/admin/scheduler', icon: Clock },
  { label: 'Notifications', href: '/admin/notifications', icon: Mail },
  { label: 'Email', href: '/admin/email', icon: Mail },
  { label: 'Audit Logs', href: '/admin/audit', icon: FileText },
  { label: 'Security', href: '/admin/security', icon: AlertTriangle },
  { label: 'Analytics', href: '/admin/analytics', icon: BarChart3 },
  { label: 'Billing', href: '/admin/billing', icon: CreditCard },
  { label: 'System Config', href: '/admin/system-config', icon: Settings },
  { label: 'Search', href: '/admin/search', icon: Search },
]

// Task 026: Closed Beta Operations Platform nav section.
const BETA_OPS_NAV: NavItem[] = [
  { label: 'Beta Dashboard', href: '/admin/beta-ops', icon: Activity },
  { label: 'Beta Invites', href: '/admin/invites', icon: UserPlus },
  { label: 'Funnel & Retention', href: '/admin/beta-ops/funnel', icon: LineChart },
  { label: 'Learning Insights', href: '/admin/beta-ops/learning', icon: GraduationCap },
  { label: 'Feedback Review', href: '/admin/beta-ops/feedback', icon: ClipboardList },
  { label: 'User Success', href: '/admin/beta-ops/success', icon: HeartHandshake },
  { label: 'Instructor', href: '/admin/beta-ops/instructor', icon: GraduationCap },
  { label: 'Operations', href: '/admin/beta-ops/operations', icon: Wrench },
  { label: 'Releases', href: '/admin/beta-ops/releases', icon: Rocket },
  { label: 'Reports', href: '/admin/beta-ops/reports', icon: FileText },
  { label: 'Experiments', href: '/admin/beta-ops/experiments', icon: FlaskConical },
]

function AdminSidebar({ className }: { className?: string }) {
  const pathname = usePathname()
  return (
    <aside className={cn('flex h-full w-64 flex-col border-r bg-card', className)} aria-label="Admin navigation">
      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Main">
        <div className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Administration</div>
        {ADMIN_NAV.map((item) => {
          const Icon = item.icon
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`)
          return (
            <Link key={item.href} href={item.href}
              className={cn('flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                active ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground')}
              aria-current={active ? 'page' : undefined}>
              <Icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
            </Link>
          )
        })}
        {/* Task 026: Beta Operations section */}
        <div className="mt-4 mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Beta Operations</div>
        {BETA_OPS_NAV.map((item) => {
          const Icon = item.icon
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`)
          return (
            <Link key={item.href} href={item.href}
              className={cn('flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                active ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground')}
              aria-current={active ? 'page' : undefined}>
              <Icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { mobileNavOpen, setMobileNavOpen } = useUIStore()
  const pathname = usePathname()
  const pageTitle = React.useMemo(() => {
    const segments = pathname.split('/').filter(Boolean)
    if (segments.length <= 1) return 'Admin'
    const last = segments[segments.length - 1]
    return last ? last.charAt(0).toUpperCase() + last.slice(1) : 'Admin'
  }, [pathname])

  return (
    <ProtectedRoute requireRoles={['administrator', 'system_admin']}>
      <div className="flex h-screen overflow-hidden">
        <div className="hidden md:flex"><AdminSidebar /></div>
        <div className="flex flex-1 flex-col overflow-hidden">
          <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setMobileNavOpen(true)} aria-label="Open menu">
              <Menu className="h-5 w-5" />
            </Button>
            <div className="flex-1"><span className="text-sm font-semibold">{pageTitle}</span></div>
          </header>
          <main className="flex-1 overflow-y-auto bg-muted/30 p-4 md:p-6" id="main-content" tabIndex={-1}>
            {children}
          </main>
        </div>
      </div>
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-72 p-0"><AdminSidebar /></SheetContent>
      </Sheet>
    </ProtectedRoute>
  )
}
