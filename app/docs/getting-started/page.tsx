'use client'
import { Badge } from '@/components/ui/badge'

export default function GettingStartedPage() {
  return (
    <div className="prose prose-slate max-w-none dark:prose-invert">
      <h1>Getting Started</h1>
      <p>Welcome to MasteryOS! This guide will get you up and running in minutes.</p>

      <h2>Prerequisites</h2>
      <ul>
        <li>A MasteryOS account (<a href="/register">register here</a>)</li>
        <li>Your API key (found in <a href="/portal/api-keys">API Keys settings</a>)</li>
        <li>Python 3.11+ or Node.js 18+ (for SDK usage)</li>
      </ul>

      <h2>Quick Start</h2>
      <p>The fastest way to start is with our Python SDK:</p>
      <pre className="rounded-lg bg-muted p-4"><code className="text-sm font-mono">{`pip install masteryos

from masteryos import MasteryOS

client = MasteryOS(api_key="your-api-key")

# Get your dashboard
dashboard = client.learning.get_dashboard()
print(f"Concepts mastered: {dashboard.mastered_count}")

# Start a study session
session = client.learning.start_session(subject="python-interview-prep")
print(f"Session started: {session.id}")`}</code></pre>

      <h2>Authentication</h2>
      <p>All API requests require an API key passed in the <code>Authorization</code> header:</p>
      <pre className="rounded-lg bg-muted p-4"><code className="text-sm font-mono">{`curl -H "Authorization: Bearer your-api-key" \\
     https://api.masteryos.com/api/v1/learning/dashboard`}</code></pre>

      <h2>Next Steps</h2>
      <ul>
        <li><a href="/docs/rest-api">REST API Reference</a> — complete endpoint documentation</li>
        <li><a href="/docs/sdks">SDK Guide</a> — install and use official SDKs</li>
        <li><a href="/docs/cli">CLI Reference</a> — manage MasteryOS from the command line</li>
        <li><a href="/api-explorer">API Explorer</a> — try API calls in your browser</li>
      </ul>

      <div className="mt-8 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-950">
        <h3 className="mb-1 flex items-center gap-2 text-blue-700 dark:text-blue-300">
          <Badge>Tip</Badge> Join the Closed Beta
        </h3>
        <p className="text-sm text-blue-600 dark:text-blue-400">
          MasteryOS is currently in Closed Beta. <a href="/register" className="underline">Request an invite</a> to get started.
        </p>
      </div>
    </div>
  )
}
