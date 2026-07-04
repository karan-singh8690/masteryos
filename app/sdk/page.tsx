'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Terminal, Package, Code2 } from 'lucide-react'

const SDKS = [
  { lang: 'Python', install: 'pip install masteryos', icon: '🐍', example: `from masteryos import MasteryOS\n\nclient = MasteryOS(api_key="your-key")\ndashboard = client.learning.get_dashboard()` },
  { lang: 'JavaScript', install: 'npm install @masteryos/sdk', icon: '📜', example: `import { MasteryOS } from '@masteryos/sdk';\n\nconst client = new MasteryOS({ apiKey: 'your-key' });\nconst dashboard = await client.learning.getDashboard();` },
  { lang: 'TypeScript', install: 'npm install @masteryos/sdk', icon: '📘', example: `import { MasteryOS } from '@masteryos/sdk';\n\nconst client = new MasteryOS({ apiKey: 'your-key' });\nconst dashboard = await client.learning.getDashboard();` },
  { lang: 'Go', install: 'go get github.com/masteryos/go-sdk', icon: '🐹', example: `client := masteryos.New("your-key")\ndashboard, err := client.Learning.GetDashboard()` },
  { lang: 'Java', install: "implementation 'com.masteryos:sdk:1.0.0'", icon: '☕', example: `MasteryOS client = new MasteryOS.Builder()\n    .apiKey("your-key")\n    .build();\nDashboard dashboard = client.learning().getDashboard();` },
  { lang: 'C#', install: 'dotnet add package MasteryOS.SDK', icon: '🔷', example: `var client = new MasteryOSClient("your-key");\nvar dashboard = await client.Learning.GetDashboardAsync();` },
]

export default function SdkPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto mb-16 max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">SDKs</h1>
        <p className="mt-4 text-lg text-muted-foreground">Official SDKs for 5 languages. Typed models, retries, pagination, and streaming built in.</p>
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {SDKS.map((sdk) => (
          <Card key={sdk.lang}>
            <CardHeader>
              <div className="flex items-center gap-3">
                <span className="text-3xl">{sdk.icon}</span>
                <div>
                  <CardTitle>{sdk.lang}</CardTitle>
                  <Badge variant="secondary" className="mt-1">v1.0.0</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-3">
                <p className="mb-1 text-xs font-semibold text-muted-foreground">Install</p>
                <pre className="rounded bg-muted p-2 text-xs"><code className="font-mono">{sdk.install}</code></pre>
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold text-muted-foreground">Quick Start</p>
                <pre className="rounded bg-muted p-2 text-xs"><code className="font-mono whitespace-pre-wrap">{sdk.example}</code></pre>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card className="mx-auto mt-12 max-w-3xl">
        <CardHeader><CardTitle className="flex items-center gap-2"><Package className="h-5 w-5" /> All SDKs include</CardTitle></CardHeader>
        <CardContent>
          <ul className="grid gap-2 sm:grid-cols-2">
            {['Authentication (Bearer token)', 'Automatic retries with backoff', 'Pagination helpers', 'WebSocket streaming', 'File upload/download', 'Typed request/response models', 'Error handling with typed exceptions', 'Rate limit awareness'].map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm"><Code2 className="h-4 w-4 text-blue-600" /> {f}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
