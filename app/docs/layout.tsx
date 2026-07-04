'use client'
import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Search, Menu, X, Moon, Sun } from 'lucide-react'
import { useTheme } from 'next-themes'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
    <Link href="/" className="flex items-center gap-2" aria-label="MasteryOS home">
      <img src="/brand/logo-mark.svg" alt="" className="h-8 w-8" />
      <span className="text-lg font-bold">Mastery<span className="text-blue-600">OS</span></span>
    </Link>
  )
}

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const [sidebarOpen, setSidebarOpen] = React.useState(false)
  const [search, setSearch] = React.useState('')

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-md">
        <div className="flex h-14 items-center gap-4 px-4">
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setSidebarOpen(!sidebarOpen)}>
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
          <Logo />
          <div className="relative ml-4 hidden flex-1 max-w-md sm:block">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search docs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label="Toggle theme">
              <Sun className="h-5 w-5 dark:hidden" />
              <Moon className="hidden h-5 w-5 dark:block" />
            </Button>
            <Button variant="ghost" asChild className="hidden sm:flex"><Link href="/">← Back to site</Link></Button>
          </div>
        </div>
      </header>
      <div className="flex flex-1">
        <aside className={cn(
          'fixed inset-y-0 left-0 top-14 z-40 w-64 overflow-y-auto border-r bg-background p-4 transition-transform lg:static lg:top-0 lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}>
          {search && <p className="mb-4 text-sm text-muted-foreground">Filtering for: "{search}"</p>}
          {DOC_SECTIONS.map((section) => {
            const filteredItems = search
              ? section.items.filter((item) => item.label.toLowerCase().includes(search.toLowerCase()))
              : section.items
            if (search && filteredItems.length === 0) return null
            return (
              <div key={section.title} className="mb-6">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">{section.title}</h3>
                <ul className="space-y-1">
                  {filteredItems.map((item) => {
                    const href = `/docs/${item.slug}`
                    const active = pathname === href
                    return (
                      <li key={item.slug}>
                        <Link
                          href={href}
                          className={cn(
                            'block rounded-md px-3 py-1.5 text-sm transition-colors',
                            active ? 'bg-blue-600/10 font-medium text-blue-600' : 'text-muted-foreground hover:text-foreground'
                          )}
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
        <main className="flex-1 overflow-x-hidden p-4 lg:p-8">
          <div className="mx-auto max-w-3xl">{children}</div>
        </main>
      </div>
    </div>
  )
}
