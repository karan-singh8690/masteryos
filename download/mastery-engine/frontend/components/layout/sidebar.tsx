'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  BookOpen,
  Trophy,
  Calendar,
  Settings,
  Shield,
  Home,
  type LucideIcon,
} from 'lucide-react'

import { cn } from '@/lib/cn'
import { ROUTES } from '@/lib/constants'
import { Button } from '@/components/ui/button'

interface NavItem {
  label: string
  href: string
  icon: LucideIcon
  roles?: string[]
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: ROUTES.DASHBOARD, icon: LayoutDashboard },
  { label: 'Learn', href: '/learn', icon: BookOpen },
  { label: 'Achievements', href: '/achievements', icon: Trophy },
  { label: 'Schedule', href: '/schedule', icon: Calendar },
]

const SECONDARY_NAV_ITEMS: NavItem[] = [
  { label: 'Profile', href: ROUTES.PROFILE, icon: Home },
  { label: 'Security', href: ROUTES.SECURITY, icon: Shield },
  { label: 'Settings', href: ROUTES.SETTINGS, icon: Settings },
]

interface SidebarProps {
  className?: string
}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname()

  return (
    <aside
      className={cn(
        'flex h-full w-64 flex-col border-r bg-card',
        className,
      )}
      aria-label="Main navigation"
    >
      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Main">
        <div className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Menu
        </div>
        {NAV_ITEMS.map((item) => (
          <SidebarLink key={item.href} item={item} active={isActive(pathname, item.href)} />
        ))}

        <div className="mb-2 mt-6 px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Account
        </div>
        {SECONDARY_NAV_ITEMS.map((item) => (
          <SidebarLink key={item.href} item={item} active={isActive(pathname, item.href)} />
        ))}
      </nav>

      <div className="border-t p-3">
        <Button variant="outline" className="w-full" asChild>
          <Link href={ROUTES.HOME}>Back to home</Link>
        </Button>
      </div>
    </aside>
  )
}

function SidebarLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon
  return (
    <Link
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
}

function isActive(pathname: string, href: string): boolean {
  if (href === ROUTES.DASHBOARD) return pathname === href
  return pathname === href || pathname.startsWith(`${href}/`)
}
