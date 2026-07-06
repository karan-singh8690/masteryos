'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Moon, Sun, Menu, X, Github, Twitter, Linkedin } from 'lucide-react'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/cn'

const NAV_LINKS = [
  { label: 'Features', href: '/features' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'Security', href: '/security' },
  { label: 'Docs', href: '/docs' },
  { label: 'Blog', href: '/blog' },
]

const SOCIAL_LINKS = [
  { label: 'GitHub', href: 'https://github.com', icon: Github },
  { label: 'Twitter', href: 'https://twitter.com', icon: Twitter },
  { label: 'LinkedIn', href: 'https://linkedin.com', icon: Linkedin },
]

const FOOTER_LINKS = {
  Product: [
    { label: 'Features', href: '/features' },
    { label: 'Pricing', href: '/pricing' },
    { label: 'Security', href: '/security' },
    { label: 'Changelog', href: '/changelog' },
    { label: 'Roadmap', href: '/roadmap' },
  ],
  Resources: [
    { label: 'Documentation', href: '/docs' },
    { label: 'SDKs', href: '/sdk' },
    { label: 'Blog', href: '/blog' },
    { label: 'API Explorer', href: '/api-explorer' },
    { label: 'Status', href: '/status' },
  ],
  Company: [
    { label: 'About', href: '/about' },
    { label: 'Careers', href: '/careers' },
    { label: 'Contact', href: '/contact' },
    { label: 'Support', href: '/support' },
  ],
  Legal: [
    { label: 'Privacy Policy', href: '/legal/privacy' },
    { label: 'Terms of Service', href: '/legal/terms' },
    { label: 'Cookie Policy', href: '/legal/privacy' },
  ],
} as const

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2" aria-label="MasteryOS home">
      <img src="/brand/logo-mark.svg" alt="" className="h-8 w-8" />
      <span className="text-xl font-bold tracking-tight">
        Mastery
        <span className="gradient-emerald-text">OS</span>
      </span>
    </Link>
  )
}

function Header() {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const [mobileOpen, setMobileOpen] = React.useState(false)

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/60 bg-background/70 backdrop-blur-xl">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <Logo />

        <nav
          className="hidden items-center gap-1 md:flex"
          aria-label="Main navigation"
        >
          {NAV_LINKS.map((link) => {
            const active = pathname === link.href || pathname.startsWith(`${link.href}/`)
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  'rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  active
                    ? 'text-emerald-500 dark:text-emerald-400'
                    : 'text-muted-foreground hover:text-emerald-500 dark:hover:text-emerald-400',
                )}
              >
                {link.label}
              </Link>
            )
          })}
        </nav>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label="Toggle theme"
          >
            <Sun className="h-5 w-5 dark:hidden" />
            <Moon className="hidden h-5 w-5 dark:block" />
          </Button>
          <Button variant="ghost" asChild className="hidden sm:flex">
            <Link href="/login">Sign In</Link>
          </Button>
          <Button
            asChild
            className="gradient-emerald border-0 font-semibold text-white shadow-sm shadow-emerald-500/20 hover:shadow-emerald-500/30"
          >
            <Link href="/register">Get Started</Link>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {mobileOpen && (
        <nav
          className="border-t border-border/60 bg-background px-4 py-2 md:hidden"
          aria-label="Mobile navigation"
        >
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="block rounded-md px-3 py-2.5 text-sm font-medium text-muted-foreground hover:bg-emerald-500/10 hover:text-emerald-500 dark:hover:text-emerald-400"
              onClick={() => setMobileOpen(false)}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  )
}

function Footer() {
  return (
    <footer className="mt-auto border-t border-border/60 bg-muted/20">
      <div className="container mx-auto px-4 py-14">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-6">
          <div className="col-span-2 md:col-span-2">
            <Logo />
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
              The Operating System for Learning. Adaptive mastery tracking for Python interview
              prep and beyond.
            </p>
            <div className="mt-5 flex items-center gap-2">
              {SOCIAL_LINKS.map((social) => {
                const Icon = social.icon
                return (
                  <a
                    key={social.label}
                    href={social.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={social.label}
                    className="flex h-9 w-9 items-center justify-center rounded-lg border border-border/60 text-muted-foreground transition-colors hover:border-emerald-500/40 hover:text-emerald-500 dark:hover:text-emerald-400"
                  >
                    <Icon className="h-4 w-4" />
                  </a>
                )
              })}
            </div>
          </div>

          {Object.entries(FOOTER_LINKS).map(([category, links]) => (
            <div key={category}>
              <h3 className="mb-4 text-sm font-semibold text-foreground">{category}</h3>
              <ul className="space-y-2.5">
                {links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-emerald-500 dark:hover:text-emerald-400"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-border/60 pt-6 text-sm text-muted-foreground sm:flex-row">
          <p>© 2026 Mastery Engine. All rights reserved.</p>
          <p>MasteryOS™ is a trademark of Mastery Engine.</p>
        </div>
      </div>
    </footer>
  )
}

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  // The landing page (/) has its own full-screen hero with nav + footer.
  // Skip the marketing header/footer for it to avoid duplicate navigation.
  const isLandingPage = pathname === '/'

  if (isLandingPage) {
    return (
      <div className="flex min-h-screen flex-col">
        <main className="flex-1">{children}</main>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  )
}
