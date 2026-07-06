import { Shield } from 'lucide-react'

export const metadata = {
  title: 'Architecture Overview — MasteryOS',
  description: 'Understand the Clean Architecture, DDD bounded contexts, and technology stack behind MasteryOS.',
}

export default function ArchitecturePage() {
  return (
    <div className="prose prose-neutral max-w-none dark:prose-invert">
      <h1>Architecture Overview</h1>
      <p className="text-lg text-muted-foreground">
        MasteryOS follows Clean Architecture + Domain-Driven Design with 8 bounded contexts.
      </p>

      <h2>Technology Stack</h2>
      <ul>
        <li><strong>Backend:</strong> FastAPI, Python 3.13, SQLAlchemy 2.x (async), PostgreSQL, Redis</li>
        <li><strong>Frontend:</strong> Next.js 16, React 19, TypeScript, Tailwind CSS, React Query, Zustand</li>
        <li><strong>Auth:</strong> RS256 JWT, Argon2id, TOTP MFA, RBAC with 6 roles</li>
        <li><strong>Infrastructure:</strong> Docker, Railway, Nginx, Prometheus, Grafana, Sentry</li>
        <li><strong>AI:</strong> Ollama (default), OpenAI, Gemini, Anthropic — optional augmentation layer</li>
      </ul>

      <h2>Bounded Contexts</h2>
      <p>The backend is organized into 8 DDD bounded contexts:</p>
      <ol>
        <li><strong>Identity</strong> — Users, profiles, credentials, sessions, MFA</li>
        <li><strong>Content</strong> — Subjects, concepts, templates, explanations</li>
        <li><strong>Assessment</strong> — Question instances, attempts, answers</li>
        <li><strong>Learning</strong> — Enrollments, study sessions, goals</li>
        <li><strong>Mastery</strong> — Mastery scores, reviews, algorithm versions</li>
        <li><strong>Scheduling</strong> — Adaptive queue, daily practice</li>
        <li><strong>Administration</strong> — Notifications, feature flags, audit logs</li>
        <li><strong>Billing</strong> — Subscriptions, invoices, plans</li>
      </ol>

      <h2>Layered Architecture</h2>
      <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
{`┌─────────────────────────────────────────┐
│  Presentation (FastAPI routers, DTOs)    │
├─────────────────────────────────────────┤
│  Application (Commands, Queries, UoW)    │
├─────────────────────────────────────────┤
│  Domain (Entities, Value Objects, Events)│
├─────────────────────────────────────────┤
│  Infrastructure (ORM, Redis, Email)      │
└─────────────────────────────────────────┘`}
      </pre>

      <h2>Learning Loop</h2>
      <p>The heart of the platform — every feature supports this loop:</p>
      <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
{`Adaptive Practice Queue → User Answers → Attempt Recorded →
Mastery Updated → Scheduler Calculates Next Review →
Explanation Displayed → Practice Queue Updated`}
      </pre>

      <h2>Key Architectural Decisions</h2>
      <ul>
        <li><strong>Modular Monolith:</strong> Single deployable, modular boundaries (ADR-0001)</li>
        <li><strong>DDD Bounded Contexts:</strong> 8 contexts with clear ownership (ADR-0006)</li>
        <li><strong>Outbox Pattern:</strong> Transactional event publishing (ADR-0012)</li>
        <li><strong>RS256 JWT:</strong> Asymmetric keys for multi-service validation (ADR-0013)</li>
        <li><strong>API-First:</strong> OpenAPI 3.1 contract drives development (ADR-0014)</li>
      </ul>

      <div className="mt-8 rounded-lg border border-border p-4 bg-muted/50">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold">Security by Design</h3>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          All endpoints require authentication. Admin operations require RBAC role checks.
          Audit logs are immutable. Passwords use Argon2id. JWTs use RS256 with key rotation.
        </p>
      </div>
    </div>
  )
}
