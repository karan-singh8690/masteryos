'use client'
import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { User, CreditCard, KeyRound, Monitor, BarChart3, Building2, Mail, LifeBuoy, Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/cn'

const NAV = [
  { label: 'Account', href: '/portal/account', icon: User },
  { label: 'Billing', href: '/portal/billing', icon: CreditCard },
  { label: 'API Keys', href: '/portal/api-keys', icon: KeyRound },
  { label: 'Sessions', href: '/portal/sessions', icon: Monitor },
  { label: 'Usage', href: '/portal/usage', icon: BarChart3 },
  { label: 'Organizations', href: '/portal/organizations', icon: Building2 },
  { label: 'Invitations', href: '/portal/invitations', icon: Mail },
  { label: 'Support', href: '/support', icon: LifeBuoy },
]

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 border-r bg-muted/30 md:flex md:flex-col">
        <div className="p-4">
          <Link href="/" className="flex items-center gap-2">
            <img src="/brand/logo-mark.svg" alt="" className="h-8 w-8" />
            <span className="font-bold">Mastery<span className="text-blue-600">OS</span></span>
          </Link>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV.map((item) => {
            const Icon = item.icon
            const active = pathname.startsWith(item.href)
            return (
              <Link key={item.href} href={item.href}
                className={cn('flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  active ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-accent')}>
                <Icon className="h-4 w-4" /> {item.label}
              </Link>
            )
          })}
        </nav>
        <div className="p-3">
          <Button variant="ghost" size="sm" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} className="w-full">
            <Sun className="mr-2 h-4 w-4 dark:hidden" /><Moon className="mr-2 hidden h-4 w-4 dark:block" /> Toggle Theme
          </Button>
        </div>
      </aside>
      <main className="flex-1 p-4 lg:p-8">{children}</main>
    </div>
  )
}
