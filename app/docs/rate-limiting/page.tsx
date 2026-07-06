export const metadata = {
  title: 'Rate Limiting — MasteryOS',
  description: 'API rate limiting policies and configuration for MasteryOS.',
}

export default function RateLimitingPage() {
  return (
    <div className="prose prose-neutral max-w-none dark:prose-invert">
      <h1>Rate Limiting</h1>
      <p className="text-lg text-muted-foreground">
        MasteryOS enforces rate limits to protect against abuse and ensure fair usage.
      </p>

      <h2>Rate Limit Tiers</h2>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-2">Endpoint</th>
            <th className="text-left py-2">Limit</th>
            <th className="text-left py-2">Window</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b"><td><code>/auth/login</code></td><td>10</td><td>per minute</td></tr>
          <tr className="border-b"><td><code>/auth/register</code></td><td>5</td><td>per minute</td></tr>
          <tr className="border-b"><td><code>/auth/forgot-password</code></td><td>3</td><td>per minute</td></tr>
          <tr className="border-b"><td><code>/auth/verify-email</code></td><td>10</td><td>per minute</td></tr>
          <tr className="border-b"><td><code>/auth/resend-verification</code></td><td>3</td><td>per minute</td></tr>
          <tr className="border-b"><td><code>/auth/reset-password</code></td><td>5</td><td>per minute</td></tr>
          <tr className="border-b"><td><code>/auth/refresh</code></td><td>30</td><td>per minute</td></tr>
          <tr className="border-b"><td><code>/questions/*/submit</code></td><td>100</td><td>per minute</td></tr>
          <tr><td>All other endpoints</td><td>60</td><td>per minute</td></tr>
        </tbody>
      </table>

      <h2>Rate Limit Headers</h2>
      <p>Responses include headers indicating rate limit status:</p>
      <ul>
        <li><code>X-RateLimit-Limit</code> — Maximum requests per window</li>
        <li><code>X-RateLimit-Remaining</code> — Remaining requests in current window</li>
        <li><code>X-RateLimit-Reset</code> — Unix timestamp when the window resets</li>
        <li><code>Retry-After</code> — Seconds to wait before retrying (on 429)</li>
      </ul>

      <h2>429 Too Many Requests</h2>
      <p>When rate limited, the API returns:</p>
      <pre className="bg-muted p-4 rounded-lg text-sm">{`HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 60

{
  "detail": {
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "code": "RATE_LIMIT_EXCEEDED"
  }
}`}</pre>

      <h2>Identifier</h2>
      <p>Rate limits are applied per-client, identified by:</p>
      <ol>
        <li>Authenticated user ID (if JWT present)</li>
        <li>IP address (if unauthenticated)</li>
      </ol>

      <h2>Admin Bypass</h2>
      <p>Administrator roles bypass rate limiting. This is intentional for admin operations.</p>

      <h2>Implementation</h2>
      <p>Rate limiting uses a token bucket algorithm. In production, a Redis-backed distributed
      rate limiter is recommended for multi-replica deployments.</p>
    </div>
  )
}
