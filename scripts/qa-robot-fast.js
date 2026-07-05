#!/usr/bin/env node
/**
 * MasteryOS QA Robot — Fast Version
 * Tests API endpoints + key pages only (no browser needed for API tests)
 */

const BASE_URL = 'https://masteryos-production.up.railway.app'
const API_URL = 'https://trustworthy-adventure-production-a9cc.up.railway.app'

const API_ENDPOINTS = [
  ['GET', '/api/v1/health', false],
  ['GET', '/api/v1/health/ready', false],
  ['GET', '/api/v1/health/live', false],
  ['GET', '/api/v1/beta/status', false],
  ['GET', '/metrics', false],
  ['GET', '/', false],
  ['GET', '/api/v1/admin/feature-flags', true],
  ['GET', '/api/v1/feature-flags', true],
  ['GET', '/api/v1/users/me', true],
  ['GET', '/api/v1/questions/dashboard', true],
  ['GET', '/api/v1/enrollments', true],
  ['GET', '/api/v1/notifications', true],
  ['GET', '/api/v1/recommendations', true],
  ['GET', '/api/v1/achievements', true],
  ['GET', '/api/v1/admin/beta/invites', true],
  ['GET', '/api/v1/admin/beta-ops/dashboard', true],
  ['GET', '/api/v1/admin/beta-ops/operations', true],
  ['GET', '/api/v1/admin/bg/workers', true],
  ['GET', '/api/v1/admin/bg/outbox', true],
  ['GET', '/api/v1/ai/status', false],
  ['GET', '/api/v1/ai/metrics', true],
  ['POST', '/api/v1/auth/login', false],
  ['POST', '/api/v1/auth/register', false],
]

const PAGES = [
  '/', '/login', '/register', '/dashboard', '/admin', '/admin/invites',
  '/admin/beta-ops', '/docs', '/blog', '/pricing', '/status', '/support',
  '/features', '/about', '/contact', '/api-explorer', '/privacy', '/terms',
]

const passed = []
const failed = []
const warnings = []

function log(type, msg, detail = '') {
  const icon = type === 'PASS' ? '✅' : type === 'FAIL' ? '❌' : '⚠️'
  console.log(`${icon} [${type}] ${msg}${detail ? ' — ' + detail : ''}`)
  if (type === 'PASS') passed.push(msg)
  else if (type === 'FAIL') failed.push(msg + ': ' + detail)
  else warnings.push(msg + ': ' + detail)
}

async function testAPIs() {
  console.log('\n🔧 Testing API Endpoints\n')
  
  // First login to get token
  let token = null
  try {
    const loginRes = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'krn129110@gmail.com',
        password: '8690Gmkaran@_123',
      }),
    })
    if (loginRes.ok) {
      const data = await loginRes.json()
      token = data.access_token
      log('PASS', 'Admin Login', 'Token received')
    } else {
      log('FAIL', 'Admin Login', `${loginRes.status}`)
    }
  } catch (err) {
    log('FAIL', 'Admin Login', err.message)
  }

  for (const [method, path, needsAuth] of API_ENDPOINTS) {
    try {
      const headers = {}
      if (needsAuth && token) headers.Authorization = `Bearer ${token}`
      
      let body = null
      if (method === 'POST' && path.includes('login')) {
        headers['Content-Type'] = 'application/json'
        body = JSON.stringify({ email: 'test@test.com', password: 'test' })
      } else if (method === 'POST' && path.includes('register')) {
        headers['Content-Type'] = 'application/json'
        body = JSON.stringify({ email: 'test@test.com', password: 'testtest123', display_name: 'Test' })
      }
      
      const res = await fetch(`${API_URL}${path}`, { method, headers, body })
      const status = res.status
      
      if (status === 200) log('PASS', `${method} ${path}`, `${status}`)
      else if (status === 401 || status === 403) log('PASS', `${method} ${path}`, `${status} (auth required — expected)`)
      else if (status === 404) log('FAIL', `${method} ${path}`, `${status} — NOT FOUND`)
      else if (status === 422) log('WARN', `${method} ${path}`, `${status} — validation error`)
      else if (status >= 500) log('FAIL', `${method} ${path}`, `${status} — SERVER ERROR`)
      else log('WARN', `${method} ${path}`, `${status}`)
    } catch (err) {
      log('FAIL', `${method} ${path}`, err.message)
    }
  }
}

async function testPages() {
  console.log('\n🌐 Testing Frontend Pages\n')
  
  const { chromium } = require('playwright')
  const browser = await chromium.launch({ headless: true })
  
  for (const page of PAGES) {
    const ctx = await browser.newContext({ ignoreHTTPSErrors: true })
    const p = await ctx.newPage()
    
    try {
      const res = await p.goto(`${BASE_URL}${page}`, { waitUntil: 'domcontentloaded', timeout: 10000 })
      const status = res?.status() || 0
      const finalUrl = p.url()
      
      if (status === 200) {
        if (finalUrl.includes('/login') && !page.includes('/login')) {
          log('PASS', `Page ${page}`, '200 → login redirect (auth required)')
        } else {
          log('PASS', `Page ${page}`, '200')
        }
      } else if (status === 404) {
        log('FAIL', `Page ${page}`, '404 — NOT FOUND')
      } else if (status === 500) {
        log('FAIL', `Page ${page}`, '500 — SERVER ERROR')
      } else {
        log('WARN', `Page ${page}`, `${status}`)
      }
    } catch (err) {
      log('FAIL', `Page ${page}`, err.message.substring(0, 60))
    } finally {
      await p.close()
      await ctx.close()
    }
  }
  
  await browser.close()
}

async function main() {
  console.log('╔══════════════════════════════════════════════════════╗')
  console.log('║       MasteryOS QA Robot — Fast Scan                 ║')
  console.log(`║  Site: ${BASE_URL.substring(0, 44).padEnd(44)}║`)
  console.log(`║  API:  ${API_URL.substring(0, 44).padEnd(44)}║`)
  console.log('╚══════════════════════════════════════════════════════╝')

  await testAPIs()
  await testPages()

  const total = passed.length + failed.length + warnings.length
  const pct = total > 0 ? Math.round((passed.length / total) * 100) : 0

  console.log('\n╔══════════════════════════════════════════════════════╗')
  console.log('║              QA Report — Summary                     ║')
  console.log('╠══════════════════════════════════════════════════════╣')
  console.log(`║  Total:      ${String(total).padEnd(42)}║`)
  console.log(`║  ✅ Passed:  ${String(passed.length).padEnd(42)}║`)
  console.log(`║  ❌ Failed:  ${String(failed.length).padEnd(42)}║`)
  console.log(`║  ⚠️  Warnings: ${String(warnings.length).padEnd(42)}║`)
  console.log(`║  Success:    ${String(pct + '%').padEnd(42)}║`)
  console.log('╚══════════════════════════════════════════════════════╝')

  if (failed.length > 0) {
    console.log('\n❌ FAILED:')
    failed.forEach(f => console.log(`   • ${f}`))
  }
  
  if (warnings.length > 0) {
    console.log('\n⚠️  WARNINGS:')
    warnings.forEach(w => console.log(`   • ${w}`))
  }
  
  process.exit(failed.length > 0 ? 1 : 0)
}

main().catch(console.error)
