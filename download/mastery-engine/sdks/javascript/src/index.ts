/**
 * MasteryOS JavaScript/TypeScript SDK — official client library.
 *
 * @example
 * import { MasteryOS } from '@masteryos/sdk';
 * const client = new MasteryOS({ apiKey: 'your-api-key' });
 * const dashboard = await client.learning.getDashboard();
 */

export class APIError extends Error {
  constructor(public statusCode: number, message: string, public code?: string) {
    super(`[${statusCode}] ${message}`)
    this.name = 'APIError'
  }
}

export class RateLimitError extends APIError {
  constructor(public retryAfter?: number) {
    super(429, 'Rate limited', 'RATE_LIMITED')
    this.name = 'RateLimitError'
  }
}

export interface MasteryOSConfig {
  apiKey: string
  baseUrl?: string
  timeout?: number
  maxRetries?: number
}

const DEFAULT_BASE_URL = 'https://api.masteryos.com'
const VERSION = '1.0.0'

export class MasteryOS {
  private apiKey: string
  private baseUrl: string
  private timeout: number
  private maxRetries: number

  public learning: LearningResource
  public auth: AuthResource
  public betaOps: BetaOpsResource

  constructor(config: MasteryOSConfig) {
    this.apiKey = config.apiKey
    this.baseUrl = (config.baseUrl || DEFAULT_BASE_URL).replace(/\/$/, '')
    this.timeout = config.timeout ?? 30000
    this.maxRetries = config.maxRetries ?? 3

    this.learning = new LearningResource(this)
    this.auth = new AuthResource(this)
    this.betaOps = new BetaOpsResource(this)
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const url = `${this.baseUrl}${path}`
    let lastError: Error | null = null

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), this.timeout)

        const response = await fetch(url, {
          method,
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json',
            'User-Agent': `masteryos-js/${VERSION}`,
          },
          body: body ? JSON.stringify(body) : undefined,
          signal: controller.signal,
        })
        clearTimeout(timeoutId)

        if (response.status === 429) {
          const retryAfter = response.headers.get('Retry-After')
          throw new RateLimitError(retryAfter ? parseInt(retryAfter) : undefined)
        }

        if (response.status >= 500 && attempt < this.maxRetries) {
          await new Promise((r) => setTimeout(r, Math.pow(2, attempt) * 1000))
          continue
        }

        const data = await response.json().catch(() => ({ detail: response.statusText }))

        if (response.status >= 400) {
          throw new APIError(response.status, data.detail || response.statusText, data.code)
        }

        return data as T
      } catch (error) {
        if (error instanceof APIError) throw error
        lastError = error as Error
        if (attempt < this.maxRetries) {
          await new Promise((r) => setTimeout(r, Math.pow(2, attempt) * 1000))
          continue
        }
      }
    }
    throw lastError || new Error('Request failed')
  }

  async get<T>(path: string): Promise<T> { return this.request<T>('GET', path) }
  async post<T>(path: string, body?: unknown): Promise<T> { return this.request<T>('POST', path, body) }
  async patch<T>(path: string, body?: unknown): Promise<T> { return this.request<T>('PATCH', path, body) }
  async delete<T>(path: string): Promise<T> { return this.request<T>('DELETE', path) }
}

class LearningResource {
  constructor(private client: MasteryOS) {}

  async getDashboard() { return this.client.get('/api/v1/learning/dashboard') }
  async startSession(subjectId: string, intent = 'mixed', targetCount = 10) {
    return this.client.post('/api/v1/learning/sessions', { subject_id: subjectId, intent, target_question_count: targetCount })
  }
  async getSession(sessionId: string) { return this.client.get(`/api/v1/learning/sessions/${sessionId}`) }
  async submitAnswer(sessionId: string, questionId: string, answer: unknown) {
    return this.client.post(`/api/v1/learning/sessions/${sessionId}/answers`, { question_id: questionId, answer })
  }
  async getMastery() { return this.client.get('/api/v1/learning/mastery') }
  async getRecommendations() { return this.client.get('/api/v1/learning/recommendations') }
}

class AuthResource {
  constructor(private client: MasteryOS) {}

  async login(email: string, password: string) { return this.client.post('/api/v1/auth/login', { email, password }) }
  async register(email: string, password: string, displayName: string, inviteToken?: string) {
    const payload: Record<string, string> = { email, password, display_name: displayName }
    if (inviteToken) payload.invite_token = inviteToken
    return this.client.post('/api/v1/auth/register', payload)
  }
  async refresh(refreshToken: string) { return this.client.post('/api/v1/auth/refresh', { refresh_token: refreshToken }) }
  async logout() { return this.client.post('/api/v1/auth/logout') }
}

class BetaOpsResource {
  constructor(private client: MasteryOS) {}

  async getDashboard() { return this.client.get('/api/v1/admin/beta-ops/dashboard') }
  async getFunnel(days = 30) { return this.client.get(`/api/v1/admin/beta-ops/analytics/funnel?days=${days}`) }
  async getRetention(weeks = 8) { return this.client.get(`/api/v1/admin/beta-ops/analytics/retention?weeks=${weeks}`) }
  async getLearning() { return this.client.get('/api/v1/admin/beta-ops/learning') }
  async getFeedback(limit = 100) { return this.client.get(`/api/v1/admin/beta-ops/feedback?limit=${limit}`) }
  async getUserSuccess() { return this.client.get('/api/v1/admin/beta-ops/success') }
  async getInstructor() { return this.client.get('/api/v1/admin/beta-ops/instructor') }
  async getOperations() { return this.client.get('/api/v1/admin/beta-ops/operations') }
  async getReleases() { return this.client.get('/api/v1/admin/beta-ops/releases') }
  async getReport(period: 'daily' | 'weekly' | 'monthly' = 'weekly') { return this.client.get(`/api/v1/admin/beta-ops/reports/${period}`) }
  async listExperiments() { return this.client.get('/api/v1/admin/beta-ops/experiments') }
}

export default MasteryOS
