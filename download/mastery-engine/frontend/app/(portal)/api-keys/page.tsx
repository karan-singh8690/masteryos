'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { KeyRound, Plus, Copy, Trash2 } from 'lucide-react'

const KEYS = [
  { id: 'key_1', name: 'Production', prefix: 'mos_prod_a1b2...', created: '2026-06-15', lastUsed: '2026-07-03' },
  { id: 'key_2', name: 'Development', prefix: 'mos_dev_c3d4...', created: '2026-06-20', lastUsed: '2026-07-02' },
]

export default function ApiKeysPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">API Keys</h1>
        <Button><Plus className="mr-2 h-4 w-4" /> Create Key</Button>
      </div>
      <div className="space-y-4">
        {KEYS.map((key) => (
          <Card key={key.id}>
            <CardContent className="flex items-center justify-between pt-6">
              <div>
                <div className="flex items-center gap-2">
                  <KeyRound className="h-4 w-4 text-blue-600" />
                  <span className="font-semibold">{key.name}</span>
                </div>
                <p className="mt-1 font-mono text-sm text-muted-foreground">{key.prefix}</p>
                <p className="mt-1 text-xs text-muted-foreground">Created {key.created} · Last used {key.lastUsed}</p>
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" size="icon"><Copy className="h-4 w-4" /></Button>
                <Button variant="ghost" size="icon" className="text-red-600"><Trash2 className="h-4 w-4" /></Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950">
        <CardContent className="pt-6">
          <h3 className="flex items-center gap-2 font-semibold text-amber-700 dark:text-amber-300">
            <Badge variant="secondary" className="bg-amber-600 text-white">Warning</Badge> Keep your API keys secure
          </h3>
          <p className="mt-2 text-sm text-amber-600 dark:text-amber-400">
            API keys are shown only once at creation. Store them securely. Never commit them to version control.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
