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
  FlaskConical, ClipboardList, LineChart,
  Bell, Menu, X,
} from 'lucide-react'

import { ProtectedRoute } from '@/components/layout/route-protection'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { useAuth } from '@/providers/auth-provider'
import { UserAvatar } from '@/components/ui/avatar'
import { cn } from '@/lib/cn'
import { useUIStore } from '@/stores/ui-store'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'

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

function BrandMark() {
  return (
    <Link href="/admin/dashboard" className="flex items-center gap-2.5" aria-label="MasteryOS admin home">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 text-sm font-bold text-black shadow-lg shadow-emerald-500/20">
        M
      </span>
      <span className="text-[17px] font-bold tracking-tight text-white">
        Mastery<span className="text-emerald-400">OS</span>
      </span>
    </Link>
  )
}

function NavLink({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const pathname = usePathname()
  const Icon = item.icon
  const active = pathname === item.href || pathname.startsWith(`${item.href}/`)
  return (
    <Link
      key={item.href}
      href={item.href}
      onClick={onNavigate}
      className={cn(
        'group relative flex items-center gap-3 rounded-lg border-l-2 px-3 py-2 text-[13px] font-medium transition-all duration-150',
        active
          ? 'border-emerald-500 bg-emerald-500/10 text-white'
          : 'border-transparent text-slate-400 hover:bg-white/[0.04] hover:text-white',
      )}
      aria-current={active ? 'page' : undefined}
    >
      <Icon
        className={cn(
          'h-4 w-4 shrink-0 transition-colors',
          active ? 'text-emerald-400' : 'text-slate-500 group-hover:text-slate-300',
        )}
        aria-hidden="true"
      />
      <span className="truncate">{item.label}</span>
    </Link>
  )
}

function SectionLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600', className)}>
      {children}
    </div>
  )
}

function AdminSidebar({ className, onNavigate }: { className?: string; onNavigate?: () => void }) {
  return (
    <aside
      className={cn('flex h-full w-64 flex-col bg-[#0A0A0B] text-slate-300', className)}
      aria-label="Admin navigation"
    >
      {/* Brand */}
      <div className="flex h-16 shrink-0 items-center border-b border-white/[0.06] px-5">
        <BrandMark />
      </div>

      {/* Nav */}
      <nav
        className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4 admin-scroll"
        aria-label="Main"
      >
        <SectionLabel>Administration</SectionLabel>
        {ADMIN_NAV.map((item) => (
          <NavLink key={item.href} item={item} onNavigate={onNavigate} />
        ))}

        <SectionLabel className="mt-6">Beta Operations</SectionLabel>
        {BETA_OPS_NAV.map((item) => (
          <NavLink key={item.href} item={item} onNavigate={onNavigate} />
        ))}
      </nav>

      {/* Footer status */}
      <div className="shrink-0 border-t border-white/[0.06] px-5 py-4">
        <div className="flex items-center gap-2 text-[11px] text-slate-500">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          All systems operational
        </div>
        <p className="mt-1 text-[11px] text-slate-600">v1.0 · Admin Console</p>
      </div>
    </aside>
  )
}

function HeaderSearchTrigger() {
  const { setCommandPaletteOpen } = useUIStore()
  return (
    <button
      type="button"
      onClick={() => setCommandPaletteOpen(true)}
      className="hidden w-full max-w-xs items-center gap-2 rounded-lg border border-border/70 bg-muted/40 px-3 py-1.5 text-left text-sm text-muted-foreground transition-colors hover:border-border hover:bg-muted md:flex lg:max-w-sm"
      aria-label="Open search"
    >
      <Search className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span className="flex-1 truncate">Search admin…</span>
      <kbd className="hidden shrink-0 rounded border border-border/60 bg-background px-1.5 py-0.5 font-mono text-[10px] font-medium text-muted-foreground lg:inline-block">
        ⌘K
      </kbd>
    </button>
  )
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { mobileNavOpen, setMobileNavOpen } = useUIStore()
  const { user } = useAuth()
  const pathname = usePathname()
  const pageTitle = React.useMemo(() => {
    const segments = pathname.split('/').filter(Boolean)
    if (segments.length <= 1) return 'Admin'
    const last = segments[segments.length - 1]
    return last ? last.charAt(0).toUpperCase() + last.slice(1) : 'Admin'
  }, [pathname])

  return (
    <ProtectedRoute requireRoles={['administrator', 'system_admin']}>
      <div className="flex h-screen overflow-hidden bg-background dark:bg-[#0A0A0B]">
        {/* Desktop sidebar */}
        <div className="hidden md:flex md:shrink-0">
          <AdminSidebar />
        </div>

        {/* Main column */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-3 border-b border-border/60 bg-background/80 px-4 backdrop-blur-md md:px-6">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setMobileNavOpen(true)}
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </Button>

            <div className="flex flex-col">
              <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Admin
              </span>
              <span className="text-sm font-semibold leading-none text-foreground">{pageTitle}</span>
            </div>

            {/* Right cluster */}
            <div className="ml-auto flex items-center gap-1.5 md:gap-2">
              <HeaderSearchTrigger />

              <ThemeToggle />

              <Button
                variant="ghost"
                size="icon"
                className="relative"
                aria-label="Notifications"
              >
                <Bell className="h-5 w-5" />
                <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-background" />
              </Button>

              <div className="ml-1">
                <UserAvatar
                  name={user?.user?.email ?? 'Admin User'}
                  size="sm"
                  className="ring-2 ring-emerald-500/30"
                />
              </div>
            </div>
          </header>

          <main
            className="flex-1 overflow-y-auto bg-background p-4 md:p-6 lg:p-8 dark:bg-[#0A0A0B]"
            id="main-content"
            tabIndex={-1}
          >
            {children}
          </main>
        </div>
      </div>

      {/* Mobile drawer */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-72 border-0 p-0">
          <div className="flex h-full flex-col bg-[#0A0A0B]">
            <div className="flex h-16 items-center justify-between border-b border-white/[0.06] px-5">
              <BrandMark />
              <Button
                variant="ghost"
                size="icon"
                className="text-slate-400 hover:bg-white/5 hover:text-white"
                onClick={() => setMobileNavOpen(false)}
                aria-label="Close menu"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
            <AdminSidebar className="flex-1" onNavigate={() => setMobileNavOpen(false)} />
          </div>
        </SheetContent>
      </Sheet>
    </ProtectedRoute>
  )
}
