import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { BookOpen, Code2, Terminal, Server, Shield, Brain, FileText, Wrench } from 'lucide-react'

const SECTIONS = [
  { icon: BookOpen, title: 'Getting Started', desc: 'Quick start guide, installation, and architecture overview.', href: '/docs/getting-started' },
  { icon: Code2, title: 'REST API', desc: 'Complete REST API reference with examples.', href: '/docs/rest-api' },
  { icon: Terminal, title: 'CLI', desc: 'Command-line tool for managing MasteryOS.', href: '/docs/cli' },
  { icon: Server, title: 'SDKs', desc: 'Official SDKs for Python, JavaScript, Go, Java, and C#.', href: '/docs/sdks' },
  { icon: Shield, title: 'Security', desc: 'Authentication, RBAC, audit logging, and compliance.', href: '/docs/security' },
  { icon: Brain, title: 'AI Platform', desc: 'Provider-agnostic AI with safety controls.', href: '/docs/ai' },
  { icon: FileText, title: 'Changelog', desc: 'Version history and release notes.', href: '/changelog' },
  { icon: Wrench, title: 'Troubleshooting', desc: 'Common issues and solutions.', href: '/docs/troubleshooting' },
]

export default function DocsPage() {
  return (
    <div>
      <h1 className="text-4xl font-extrabold tracking-tight">Documentation</h1>
      <p className="mt-2 text-lg text-muted-foreground">Everything you need to build with MasteryOS.</p>
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SECTIONS.map((section) => {
          const Icon = section.icon
          return (
            <Link key={section.title} href={section.href}>
              <Card className="h-full transition-shadow hover:shadow-lg">
                <CardHeader>
                  <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/10">
                    <Icon className="h-5 w-5 text-blue-600" />
                  </div>
                  <CardTitle className="text-lg">{section.title}</CardTitle>
                  <CardDescription>{section.desc}</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
