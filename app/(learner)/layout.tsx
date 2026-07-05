'use client'

import * as React from 'react'
import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { useTheme } from 'next-themes'
import {
  LayoutDashboard,
  BookOpen,
  GraduationCap,
  Calendar,
  Lightbulb,
  Trophy,
  Settings,
  Search,
  Menu,
  Moon,
  Sun,
  Monitor,
  LogOut,
  User as UserIcon,
  Shield,
  ChevronDown,
  Command,
  type LucideIcon,
} from 'lucide-react'

import { ProtectedRoute } from '@/components/layout/route-protection'
import { BetaBanner } from '@/components/beta/beta-banner'
import { BetaFeedbackButton } from '@/components/beta/feedback-button'
import { NotificationMenu } from '@/components/layout/notification-menu'
import { cn } from '@/lib/cn'
import { ROUTES } from '@/lib/constants'
import { getInitials } from '@/lib/format'
import { getAvatarGradient } from '@/lib/avatar'
import { useAuth } from '@/providers/auth-provider'
import { useUIStore } from '@/stores/ui-store'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
} from '@/components/ui/sheet'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface NavItem {
  label: string
  href: string
  icon: LucideIcon
  description?: string
}

const LEARNER_NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, description: 'Overview & stats' },
  { label: 'Subjects', href: '/subjects', icon: BookOpen, description: 'Browse curriculum' },
  { label: 'Study', href: '/study/start', icon: GraduationCap, description: 'Start a session' },
  { label: 'Reviews', href: '/reviews', icon: Calendar, description: 'Spaced repetition' },
  { label: 'Recommendations', href: '/recommendations', icon: Lightbulb, description: 'AI suggestions' },
  { label: 'Achievements', href: '/achievements', icon: Trophy, description: 'Your milestones' },
]

const ACCOUNT_NAV_ITEMS: NavItem[] = [
  { label: 'Profile', href: '/profile', icon: UserIcon },
  { label: 'Security', href: '/settings/security', icon: Shield },
  { label: 'Settings', href: '/settings', icon: Settings },
]

// ============================================================
// Sidebar — dark (#0A0A0B) with emerald active states
// ============================================================

interface LearnerSidebarProps {
  className?: string
  onNavigate?: () => void
}

function LearnerSidebar({ className, onNavigate }: LearnerSidebarProps) {
  const pathname = usePathname()

  return (
    <aside
      className={cn(
        'flex h-full w-64 flex-col bg-[#0A0A0B] text-zinc-300',
        className,
      )}
      aria-label="Learner navigation"
    >
      {/* Brand */}
      <div className="flex h-16 items-center gap-2.5 border-b border-white/5 px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg shadow-emerald-500/20">
          <img src="/brand/logo-mark.svg" alt="" className="h-6 w-6" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-bold tracking-tight text-white">MasteryOS</span>
          <span className="text-[10px] font-medium uppercase tracking-wider text-emerald-400/80">
            Learner
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-6 overflow-y-auto p-4" aria-label="Main">
        <div>
          <div className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500">
            Learn
          </div>
          <ul className="space-y-0.5">
            {LEARNER_NAV_ITEMS.map((item) => {
              const Icon = item.icon
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`)
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    className={cn(
                      'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all',
                      active
                        ? 'bg-emerald-500/10 text-white'
                        : 'text-zinc-400 hover:bg-white/5 hover:text-white',
                    )}
                    aria-current={active ? 'page' : undefined}
                  >
                    {/* Active left accent */}
                    {active && (
                      <span
                        className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-emerald-400"
                        aria-hidden="true"
                      />
                    )}
                    <Icon
                      className={cn(
                        'h-4 w-4 shrink-0 transition-colors',
                        active
                          ? 'text-emerald-400'
                          : 'text-zinc-500 group-hover:text-zinc-300',
                      )}
                      aria-hidden="true"
                    />
                    <span className="flex-1">{item.label}</span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>

        <div>
          <div className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500">
            Account
          </div>
          <ul className="space-y-0.5">
            {ACCOUNT_NAV_ITEMS.map((item) => {
              const Icon = item.icon
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`)
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    className={cn(
                      'group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all',
                      active
                        ? 'bg-emerald-500/10 text-white'
                        : 'text-zinc-400 hover:bg-white/5 hover:text-white',
                    )}
                    aria-current={active ? 'page' : undefined}
                  >
                    {active && (
                      <span
                        className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r-full bg-emerald-400"
                        aria-hidden="true"
                      />
                    )}
                    <Icon
                      className={cn(
                        'h-4 w-4 shrink-0 transition-colors',
                        active
                          ? 'text-emerald-400'
                          : 'text-zinc-500 group-hover:text-zinc-300',
                      )}
                      aria-hidden="true"
                    />
                    <span className="flex-1">{item.label}</span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      </nav>

      {/* Upgrade card */}
      <div className="border-t border-white/5 p-4">
        <div className="rounded-xl bg-gradient-to-br from-emerald-500/10 to-teal-500/5 p-4 ring-1 ring-inset ring-emerald-500/20">
          <p className="text-xs font-semibold text-white">Upgrade to Pro</p>
          <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">
            Unlock unlimited study sessions & AI explanations.
          </p>
          <button
            type="button"
            className="mt-3 w-full rounded-md bg-gradient-to-r from-emerald-500 to-teal-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition-all hover:from-emerald-600 hover:to-teal-600"
          >
            Upgrade
          </button>
        </div>
      </div>
    </aside>
  )
}

// ============================================================
// Header — clean, minimal, with search + theme + bell + avatar
// ============================================================

function LearnerHeader() {
  const { theme, setTheme } = useTheme()
  const { user, logout } = useAuth()
  const router = useRouter()
  const [mounted, setMounted] = React.useState(false)
  const { mobileNavOpen, setMobileNavOpen } = useUIStore()

  React.useEffect(() => {
    setMounted(true)
  }, [])

  const displayName = user?.profile.display_name || 'Learner'
  const avatarSeed = user?.user.id || user?.user.email || displayName
  const gradientClass = getAvatarGradient(avatarSeed)
  const avatarUrl = user?.profile.avatar_url

  const handleLogout = async () => {
    await logout(false)
  }

  const handleLogoutAll = async () => {
    await logout(true)
  }

  return (
    <header
      className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur-md sm:px-6"
      role="banner"
    >
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="icon"
        className="text-muted-foreground hover:bg-accent md:hidden"
        onClick={() => setMobileNavOpen(true)}
        aria-label="Open navigation menu"
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* Search bar */}
      <div className="flex flex-1 items-center">
        <Link
          href="/search"
          className="group flex w-full max-w-md items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <Search className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span className="flex-1 text-left">
            <span className="text-muted-foreground/80">Search concepts, subjects…</span>
          </span>
          <kbd
            className="hidden items-center gap-0.5 rounded border bg-background px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground sm:inline-flex"
            aria-hidden="true"
          >
            <Command className="h-2.5 w-2.5" />
            K
          </kbd>
        </Link>
      </div>

      {/* Right side actions */}
      <div className="flex items-center gap-1.5">
        {/* Theme toggle */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="text-muted-foreground hover:bg-accent hover:text-foreground"
              aria-label="Toggle theme"
            >
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

        {/* Notifications */}
        <NotificationMenu />

        {/* Profile menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="ml-1 flex items-center gap-2 rounded-full p-0.5 pr-2 transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              aria-label="Open profile menu"
            >
              <div
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br text-xs font-bold text-white',
                  gradientClass,
                )}
              >
                {avatarUrl ? (
                  <img
                    src={avatarUrl}
                    alt={displayName}
                    className="h-full w-full rounded-full object-cover"
                  />
                ) : (
                  getInitials(displayName)
                )}
              </div>
              <span className="hidden text-sm font-medium sm:inline-block">{displayName}</span>
              <ChevronDown className="hidden h-4 w-4 text-muted-foreground sm:inline-block" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="flex flex-col gap-1">
              <span className="font-medium">{displayName}</span>
              {user?.user.email && (
                <span className="text-xs text-muted-foreground">{user.user.email}</span>
              )}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => router.push(ROUTES.PROFILE)}>
              <UserIcon className="mr-2 h-4 w-4" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push('/settings/security')}>
              <Shield className="mr-2 h-4 w-4" />
              Security
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(ROUTES.SETTINGS)}>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} className="text-destructive">
              <LogOut className="mr-2 h-4 w-4" />
              Log out
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleLogoutAll} className="text-destructive">
              <LogOut className="mr-2 h-4 w-4" />
              Log out all devices
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}

// ============================================================
// Layout
// ============================================================

export default function LearnerLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { mobileNavOpen, setMobileNavOpen } = useUIStore()

  return (
    <ProtectedRoute>
      <div className="flex h-screen overflow-hidden bg-background">
        {/* Desktop sidebar */}
        <div className="hidden md:flex md:shrink-0">
          <LearnerSidebar />
        </div>

        {/* Main content */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <LearnerHeader />
          <BetaBanner />
          <main
            className="flex-1 overflow-y-auto bg-muted/30 p-4 md:p-6 lg:p-8"
            id="main-content"
            tabIndex={-1}
          >
            <div className="mx-auto max-w-7xl">{children}</div>
          </main>
        </div>
      </div>

      {/* Mobile sidebar */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-72 border-none p-0">
          <LearnerSidebar onNavigate={() => setMobileNavOpen(false)} />
        </SheetContent>
      </Sheet>

      <BetaFeedbackButton />
    </ProtectedRoute>
  )
}
