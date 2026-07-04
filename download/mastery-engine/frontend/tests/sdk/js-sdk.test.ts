/**
 * Tests for the MasteryOS JavaScript SDK (Task 027).
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { join } from 'path'

const SDK_PATH = join(__dirname, '..', '..', '..', 'sdks', 'javascript', 'src', 'index.ts')
const SDK_SOURCE = readFileSync(SDK_PATH, 'utf-8')

describe('MasteryOS JavaScript SDK', () => {
  describe('Structure', () => {
    it('exports MasteryOS class', () => expect(SDK_SOURCE).toContain('export class MasteryOS'))
    it('exports APIError class', () => expect(SDK_SOURCE).toContain('export class APIError'))
    it('exports RateLimitError class', () => expect(SDK_SOURCE).toContain('export class RateLimitError'))
    it('exports MasteryOSConfig interface', () => expect(SDK_SOURCE).toContain('export interface MasteryOSConfig'))
    it('has default export', () => expect(SDK_SOURCE).toContain('export default MasteryOS'))
  })

  describe('Learning Resource', () => {
    it('has LearningResource class', () => expect(SDK_SOURCE).toContain('class LearningResource'))
    it('has getDashboard method', () => expect(SDK_SOURCE).toContain('getDashboard'))
    it('has startSession method', () => expect(SDK_SOURCE).toContain('startSession'))
    it('has getSession method', () => expect(SDK_SOURCE).toContain('getSession'))
    it('has submitAnswer method', () => expect(SDK_SOURCE).toContain('submitAnswer'))
    it('has getMastery method', () => expect(SDK_SOURCE).toContain('getMastery'))
    it('has getRecommendations method', () => expect(SDK_SOURCE).toContain('getRecommendations'))
  })

  describe('Auth Resource', () => {
    it('has AuthResource class', () => expect(SDK_SOURCE).toContain('class AuthResource'))
    it('has login method', () => expect(SDK_SOURCE).toMatch(/login\(/))
    it('has register method', () => expect(SDK_SOURCE).toMatch(/register\(/))
    it('has refresh method', () => expect(SDK_SOURCE).toMatch(/refresh\(/))
    it('has logout method', () => expect(SDK_SOURCE).toMatch(/logout\(/))
  })

  describe('BetaOps Resource', () => {
    it('has BetaOpsResource class', () => expect(SDK_SOURCE).toContain('class BetaOpsResource'))
    it('has getFunnel method', () => expect(SDK_SOURCE).toContain('getFunnel'))
    it('has getRetention method', () => expect(SDK_SOURCE).toContain('getRetention'))
    it('has getLearning method', () => expect(SDK_SOURCE).toContain('getLearning'))
    it('has getFeedback method', () => expect(SDK_SOURCE).toContain('getFeedback'))
    it('has getUserSuccess method', () => expect(SDK_SOURCE).toContain('getUserSuccess'))
    it('has getInstructor method', () => expect(SDK_SOURCE).toContain('getInstructor'))
    it('has getOperations method', () => expect(SDK_SOURCE).toContain('getOperations'))
    it('has getReleases method', () => expect(SDK_SOURCE).toContain('getReleases'))
    it('has getReport method', () => expect(SDK_SOURCE).toContain('getReport'))
    it('has listExperiments method', () => expect(SDK_SOURCE).toContain('listExperiments'))
  })

  describe('HTTP Methods', () => {
    it('has get method', () => expect(SDK_SOURCE).toMatch(/async get</))
    it('has post method', () => expect(SDK_SOURCE).toMatch(/async post</))
    it('has patch method', () => expect(SDK_SOURCE).toMatch(/async patch</))
    it('has delete method', () => expect(SDK_SOURCE).toMatch(/async delete</))
  })

  describe('Retry Logic', () => {
    it('has maxRetries config', () => expect(SDK_SOURCE).toContain('maxRetries'))
    it('has exponential backoff', () => expect(SDK_SOURCE).toContain('Math.pow(2'))
  })

  describe('Rate Limiting', () => {
    it('handles 429 status', () => expect(SDK_SOURCE).toContain('429'))
    it('reads Retry-After header', () => expect(SDK_SOURCE).toContain('Retry-After'))
  })

  describe('Authentication', () => {
    it('sends Bearer token', () => expect(SDK_SOURCE).toContain('Bearer'))
    it('sends Authorization header', () => expect(SDK_SOURCE).toContain('Authorization'))
  })

  describe('Configuration', () => {
    it('has VERSION constant', () => expect(SDK_SOURCE).toContain('VERSION'))
    it('sends User-Agent header', () => expect(SDK_SOURCE).toContain('User-Agent'))
    it('has DEFAULT_BASE_URL', () => expect(SDK_SOURCE).toContain('DEFAULT_BASE_URL'))
    it('defaults to api.masteryos.com', () => expect(SDK_SOURCE).toContain('https://api.masteryos.com'))
    it('has default timeout', () => expect(SDK_SOURCE).toContain('30000'))
  })
})

describe('SDK package.json', () => {
  const PKG_PATH = join(__dirname, '..', '..', '..', 'sdks', 'javascript', 'package.json')
  const pkg = JSON.parse(readFileSync(PKG_PATH, 'utf-8'))

  it('has correct package name', () => expect(pkg.name).toBe('@masteryos/sdk'))
  it('has version 1.0.0', () => expect(pkg.version).toBe('1.0.0'))
  it('has MIT license', () => expect(pkg.license).toBe('MIT'))
  it('has build script', () => expect(pkg.scripts.build).toBeDefined())
  it('has test script', () => expect(pkg.scripts.test).toBeDefined())
  it('has homepage', () => expect(pkg.homepage).toContain('masteryos'))
})
