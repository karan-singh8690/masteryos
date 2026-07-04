'use client'
import { Badge } from '@/components/ui/badge'

const ENDPOINT_GROUPS = [
  { group: 'Authentication', endpoints: [
    { method: 'POST', path: '/api/v1/auth/register', desc: 'Register a new user (requires invite token during beta)' },
    { method: 'POST', path: '/api/v1/auth/login', desc: 'Login with email + password' },
    { method: 'POST', path: '/api/v1/auth/refresh', desc: 'Refresh access token' },
    { method: 'POST', path: '/api/v1/auth/logout', desc: 'Logout (revoke refresh token)' },
    { method: 'POST', path: '/api/v1/auth/verify-email', desc: 'Verify email with token' },
    { method: 'POST', path: '/api/v1/auth/forgot-password', desc: 'Request password reset' },
    { method: 'POST', path: '/api/v1/auth/reset-password', desc: 'Reset password with token' },
    { method: 'POST', path: '/api/v1/auth/mfa/setup', desc: 'Setup MFA (TOTP)' },
    { method: 'POST', path: '/api/v1/auth/mfa/verify', desc: 'Verify MFA code' },
  ]},
  { group: 'Learning', endpoints: [
    { method: 'GET', path: '/api/v1/learning/dashboard', desc: 'Get learner dashboard' },
    { method: 'POST', path: '/api/v1/learning/sessions', desc: 'Start a study session' },
    { method: 'GET', path: '/api/v1/learning/sessions/{id}', desc: 'Get session details' },
    { method: 'POST', path: '/api/v1/learning/sessions/{id}/answers', desc: 'Submit an answer' },
    { method: 'GET', path: '/api/v1/learning/mastery', desc: 'Get mastery scores' },
    { method: 'GET', path: '/api/v1/learning/recommendations', desc: 'Get study recommendations' },
  ]},
  { group: 'Beta Operations', endpoints: [
    { method: 'GET', path: '/api/v1/admin/beta-ops/dashboard', desc: 'Beta ops dashboard (admin)' },
    { method: 'GET', path: '/api/v1/admin/beta-ops/analytics/funnel', desc: 'Registration funnel' },
    { method: 'GET', path: '/api/v1/admin/beta-ops/learning', desc: 'Learning effectiveness' },
    { method: 'GET', path: '/api/v1/admin/beta-ops/success', desc: 'User success report' },
    { method: 'GET', path: '/api/v1/admin/beta-ops/experiments', desc: 'List experiments' },
  ]},
]

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-teal-600', POST: 'bg-blue-600', PATCH: 'bg-amber-600', DELETE: 'bg-red-600', PUT: 'bg-purple-600',
}

export default function RestApiPage() {
  return (
    <div className="prose prose-slate max-w-none dark:prose-invert">
      <h1>REST API Reference</h1>
      <p>The MasteryOS REST API is organized around REST, returns JSON, uses standard HTTP response codes, and accepts JSON request bodies.</p>

      <h2>Base URL</h2>
      <pre className="rounded-lg bg-muted p-4"><code className="text-sm font-mono">https://api.masteryos.com/api/v1</code></pre>

      <h2>Authentication</h2>
      <p>Pass your API key in the <code>Authorization</code> header as a Bearer token:</p>
      <pre className="rounded-lg bg-muted p-4"><code className="text-sm font-mono">{`Authorization: Bearer your-api-key`}</code></pre>

      <h2>Rate Limiting</h2>
      <p>Rate limits are per-IP and per-endpoint:</p>
      <ul>
        <li><strong>Auth endpoints:</strong> 10 requests/minute</li>
        <li><strong>API endpoints:</strong> 60 requests/minute</li>
        <li><strong>AI endpoints:</strong> 20 requests/minute</li>
        <li><strong>Question submission:</strong> 30 requests/minute</li>
      </ul>
      <p>Rate-limited responses return <code>429 Too Many Requests</code> with a <code>Retry-After</code> header.</p>

      <h2>Endpoints</h2>
      {ENDPOINT_GROUPS.map((group) => (
        <div key={group.group} className="mt-8">
          <h3>{group.group}</h3>
          <div className="space-y-2">
            {group.endpoints.map((ep) => (
              <div key={ep.path + ep.method} className="flex items-center gap-3 rounded-lg border p-3">
                <Badge className={`${METHOD_COLORS[ep.method]} w-16 justify-center`}>{ep.method}</Badge>
                <code className="text-sm font-mono">{ep.path}</code>
                <span className="ml-auto text-sm text-muted-foreground">{ep.desc}</span>
              </div>
            ))}
          </div>
        </div>
      ))}

      <h2>Example Request</h2>
      <pre className="rounded-lg bg-muted p-4"><code className="text-sm font-mono">{`curl -X POST https://api.masteryos.com/api/v1/learning/sessions \\
  -H "Authorization: Bearer your-api-key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "subject_id": "python-interview-prep",
    "intent": "mixed",
    "target_question_count": 10
  }'`}</code></pre>

      <h2>Example Response</h2>
      <pre className="rounded-lg bg-muted p-4"><code className="text-sm font-mono">{`{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "intent": "mixed",
  "started_at": "2026-07-03T12:00:00Z",
  "questions": [...]
}`}</code></pre>
    </div>
  )
}
