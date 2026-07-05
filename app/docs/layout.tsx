'use client'
import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Search, Menu, X, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { cn } from '@/lib/cn'

const DOC_SECTIONS = [
  { title: 'Getting Started', items: [
    { slug: 'getting-started', label: 'Quick Start' },
    { slug: 'installation', label: 'Installation' },
    { slug: 'architecture', label: 'Architecture Overview' },
  ]},
  { title: 'API Reference', items: [
    { slug: 'rest-api', label: 'REST API' },
    { slug: 'websocket-api', label: 'WebSocket API' },
    { slug: 'authentication', label: 'Authentication' },
    { slug: 'errors', label: 'Error Catalog' },
    { slug: 'rate-limiting', label: 'Rate Limiting' },
  ]},
  { title: 'Developer Tools', items: [
    { slug: 'sdks', label: 'SDKs' },
    { slug: 'cli', label: 'CLI' },
    { slug: 'api-explorer', label: 'API Explorer' },
  ]},
  { title: 'Platform', items: [
    { slug: 'deployment', label: 'Deployment' },
    { slug: 'scaling', label: 'Scaling' },
    { slug: 'monitoring', label: 'Monitoring' },
    { slug: 'security', label: 'Security' },
  ]},
  { title: 'Features', items: [
    { slug: 'ai', label: 'AI Platform' },
    { slug: 'learning-engine', label: 'Learning Engine' },
    { slug: 'content-authoring', label: 'Content Authoring' },
    { slug: 'administration', label: 'Administration' },
  ]},
  { title: 'Reference', items: [
    { slug: 'troubleshooting', label: 'Troubleshooting' },
    { slug: 'faq', label: 'FAQ' },
  ]},
]

function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5" aria-label="MasteryOS home">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-400 to-emerald-600 text-sm font-bold text-black shadow-sm">
        M
      </span>
      <span className="text-lg font-bold tracking-tight text-foreground">
        Mastery<span className="text-emerald-500">OS</span>
      </span>
    </Link>
  )
}

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [sidebarOpen, setSidebarOpen] = React.useState(false)
  const [search, setSearch] = React.useState('')

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground dark:bg-[#0A0A0B]">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur-md dark:bg-[#0A0A0B]/80">
        <div className="flex h-16 items-center gap-3 px-4 md:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle navigation"
          >
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>

          <Logo />

          {/* Search */}
          <div className="relative ml-4 hidden flex-1 max-w-md sm:block">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <Input
              type="search"
              placeholder="Search docs…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-9 rounded-lg border-border/60 bg-muted/40 pl-9 pr-12 text-sm"
              aria-label="Search documentation"
            />
            <kbd className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-border/60 bg-background px-1.5 py-0.5 font-mono text-[10px] font-medium text-muted-foreground md:inline-block">
              ⌘K
            </kbd>
          </div>

          <div className="ml-auto flex items-center gap-1.5">
            <ThemeToggle />
            <Button
              variant="outline"
              size="sm"
              asChild
              className="hidden h-9 gap-1.5 rounded-lg border-border/60 sm:flex"
            >
              <Link href="/">
                <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
                Back to site
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <div className="flex flex-1">
        {/* Sidebar */}
        <aside
          className={cn(
            'fixed inset-y-0 left-0 top-16 z-40 w-72 overflow-y-auto border-r border-border/60 bg-background px-4 py-6 transition-transform duration-200 lg:sticky lg:top-16 lg:z-0 lg:h-[calc(100vh-4rem)] lg:translate-x-0 dark:bg-[#0A0A0B]',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full',
          )}
          aria-label="Documentation navigation"
        >
          {search && (
            <p className="mb-4 rounded-lg bg-emerald-500/10 px-3 py-2 text-xs text-emerald-600 dark:text-emerald-400">
              Filtering for “{search}”
            </p>
          )}
          {DOC_SECTIONS.map((section) => {
            const filteredItems = search
              ? section.items.filter((item) =>
                  item.label.toLowerCase().includes(search.toLowerCase()),
                )
              : section.items
            if (search && filteredItems.length === 0) return null
            return (
              <div key={section.title} className="mb-7">
                <h3 className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  {section.title}
                </h3>
                <ul className="space-y-0.5">
                  {filteredItems.map((item) => {
                    const href = `/docs/${item.slug}`
                    const active = pathname === href
                    return (
                      <li key={item.slug}>
                        <Link
                          href={href}
                          onClick={() => setSidebarOpen(false)}
                          className={cn(
                            'block rounded-lg border-l-2 px-3 py-1.5 text-sm transition-colors',
                            active
                              ? 'border-emerald-500 bg-emerald-500/10 font-medium text-emerald-600 dark:text-emerald-400'
                              : 'border-transparent text-muted-foreground hover:bg-muted/60 hover:text-foreground',
                          )}
                          aria-current={active ? 'page' : undefined}
                        >
                          {item.label}
                        </Link>
                      </li>
                    )
                  })}
                </ul>
              </div>
            )
          })}
        </aside>

        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 top-16 z-30 bg-black/40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* Content */}
        <main className="flex-1 overflow-x-hidden px-4 py-8 lg:px-10 lg:py-12">
          <div className="mx-auto max-w-3xl">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
