import { Brain } from 'lucide-react'

export const metadata = {
  title: 'AI Platform — MasteryOS',
  description: 'Optional AI augmentation layer with provider abstraction, safety, and audit trail.',
}

export default function AiPage() {
  return (
    <div className="prose prose-neutral max-w-none dark:prose-invert">
      <h1>AI Intelligence Platform</h1>
      <p className="text-lg text-muted-foreground">
        MasteryOS uses AI as an optional augmentation layer — not for runtime decisions.
        Human-authored content remains the source of truth.
      </p>

      <h2>Providers</h2>
      <p>The AI platform supports 5 providers via a unified interface:</p>
      <ul>
        <li><strong>Mock</strong> — Testing only, no external calls</li>
        <li><strong>Ollama</strong> — Local LLM (default, Qwen 2.5:7B)</li>
        <li><strong>OpenAI</strong> — GPT-4o-mini</li>
        <li><strong>Gemini</strong> — Google Gemini 1.5 Flash</li>
        <li><strong>Anthropic</strong> — Claude 3.5 Sonnet</li>
      </ul>

      <h2>AI Gateway</h2>
      <p>The <code>AIGateway</code> provides:</p>
      <ul>
        <li>Request validation + prompt construction</li>
        <li>Provider selection + fallback routing</li>
        <li>Timeouts + retries with exponential backoff</li>
        <li>Response validation + token/cost accounting</li>
        <li>Rate limiting (per-user, per-provider)</li>
      </ul>

      <h2>Safety Layer</h2>
      <div className="rounded-lg border border-border p-4 bg-muted/50">
        <div className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold">SafetyValidator</h3>
        </div>
        <ul className="mt-2 text-sm">
          <li>Prompt injection protection</li>
          <li>PII detection + removal</li>
          <li>Toxicity detection</li>
          <li>Hallucination confidence scoring</li>
          <li>Output length limits</li>
          <li>Code injection prevention</li>
        </ul>
      </div>

      <h2>Capabilities</h2>
      <ol>
        <li><strong>AI Explanations</strong> — Beginner, Interview, Detailed, Simple, Analogy variants</li>
        <li><strong>Study Coach</strong> — Daily/weekly plans, motivation, study tips</li>
        <li><strong>Predictive Analytics</strong> — Dropout risk, completion forecast, interview readiness</li>
        <li><strong>Instructor Intelligence</strong> — Class weaknesses, concept heatmaps, misconception trends</li>
        <li><strong>Content Intelligence</strong> — Duplicate detection, weak distractors, coverage gaps</li>
        <li><strong>Recommendation Enhancer</strong> — Natural language rewriting of recommendations</li>
        <li><strong>Weekly Reports</strong> — Student, instructor, and org-level summaries</li>
      </ol>

      <h2>Human Review Workflow</h2>
      <p>AI-generated explanations follow a review pipeline:</p>
      <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
{`Draft → Content Editor Review → Approve → Published → Student Visible`}
      </pre>

      <h2>API Endpoints</h2>
      <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
{`GET  /api/v1/ai/status              — Check AI availability
PATCH /api/v1/ai/config              — Update AI config (admin)
POST /api/v1/ai/explanations/generate — Generate explanation
POST /api/v1/ai/coach/plan           — Get study plan
POST /api/v1/ai/analytics/forecast   — Predictive analytics
POST /api/v1/ai/content/analyze      — Content intelligence
POST /api/v1/ai/recommendations/enhance — Enhance recommendations
POST /api/v1/ai/reports/weekly       — Generate weekly report
POST /api/v1/ai/instructor/insights  — Instructor analytics
GET  /api/v1/ai/prompts              — List prompts
GET  /api/v1/ai/prompts/{type}       — Get prompt by type
GET  /api/v1/ai/audit                — AI audit trail
GET  /api/v1/ai/metrics              — AI usage metrics`}
      </pre>

      <h2>Configuration</h2>
      <p>AI is disabled by default. Enable via environment variables:</p>
      <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
{`AI_ENABLED=true
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b`}
      </pre>
    </div>
  )
}
