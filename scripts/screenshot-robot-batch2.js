#!/usr/bin/env node
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE_URL = 'https://masteryos-production.up.railway.app'
const SCREENSHOT_DIR = '/home/z/my-project/download/screenshots'

// Pages 18-93 (auth + docs + learner + admin + portal + content)
const PAGES = [
  { path: '/register', name: '18-register' },
  { path: '/forgot-password', name: '19-forgot-password' },
  { path: '/docs', name: '20-docs' },
  { path: '/docs/getting-started', name: '21-docs-getting-started' },
  { path: '/docs/architecture', name: '23-docs-architecture' },
  { path: '/docs/rest-api', name: '24-docs-rest-api' },
  { path: '/docs/ai', name: '28-docs-ai' },
  { path: '/docs/deployment', name: '29-docs-deployment' },
  { path: '/docs/faq', name: '35-docs-faq' },
  // Auth required
  { path: '/dashboard', name: '42-learner-dashboard', auth: true },
  { path: '/subjects', name: '43-learner-subjects', auth: true },
  { path: '/study/start', name: '44-learner-study-start', auth: true },
  { path: '/mastery', name: '45-learner-mastery', auth: true },
  { path: '/reviews', name: '46-learner-reviews', auth: true },
  { path: '/recommendations', name: '47-learner-recommendations', auth: true },
  { path: '/achievements', name: '48-learner-achievements', auth: true },
  { path: '/notifications', name: '49-learner-notifications', auth: true },
  { path: '/profile', name: '50-learner-profile', auth: true },
  { path: '/settings', name: '51-learner-settings', auth: true },
  { path: '/search', name: '52-learner-search', auth: true },
  { path: '/welcome', name: '53-learner-welcome', auth: true },
  // Admin
  { path: '/admin', name: '54-admin-dashboard', auth: true },
  { path: '/admin/users', name: '55-admin-users', auth: true },
  { path: '/admin/feature-flags', name: '58-admin-feature-flags', auth: true },
  { path: '/admin/workers', name: '59-admin-workers', auth: true },
  { path: '/admin/outbox', name: '60-admin-outbox', auth: true },
  { path: '/admin/invites', name: '71-admin-invites', auth: true },
  // Beta Ops
  { path: '/admin/beta-ops', name: '72-beta-ops-dashboard', auth: true },
  { path: '/admin/beta-ops/feedback', name: '75-beta-ops-feedback', auth: true },
  { path: '/admin/beta-ops/operations', name: '78-beta-ops-operations', auth: true },
  { path: '/admin/beta-ops/releases', name: '79-beta-ops-releases', auth: true },
  // Portal
  { path: '/portal/account', name: '82-portal-account', auth: true },
  { path: '/portal/billing', name: '83-portal-billing', auth: true },
  { path: '/portal/api-keys', name: '84-portal-api-keys', auth: true },
  { path: '/portal/sessions', name: '85-portal-sessions', auth: true },
  { path: '/portal/usage', name: '86-portal-usage', auth: true },
  { path: '/portal/organizations', name: '87-portal-organizations', auth: true },
  { path: '/portal/invitations', name: '88-portal-invitations', auth: true },
  // Content
  { path: '/content', name: '89-content-dashboard', auth: true },
  { path: '/content/subjects', name: '90-content-subjects', auth: true },
]

async function main() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true })
  const browser = await chromium.launch({ headless: true })
  
  const authContext = await browser.newContext({ viewport: { width: 1280, height: 800 }, ignoreHTTPSErrors: true })
  
  // Login
  console.log('Logging in...')
  const loginPage = await authContext.newPage()
  await loginPage.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 10000 })
  await loginPage.fill('input[type="email"]', 'krn129110@gmail.com')
  await loginPage.fill('input[type="password"]', '8690Gmkaran@_123')
  await loginPage.click('button[type="submit"]')
  await loginPage.waitForTimeout(3000)
  await authContext.addCookies([
    { name: 'mastery-authenticated', value: 'true', domain: 'masteryos-production.up.railway.app', path: '/' },
    { name: 'mastery-role', value: 'administrator', domain: 'masteryos-production.up.railway.app', path: '/' },
  ])
  await loginPage.close()
  console.log('Logged in\n')
  
  const publicContext = await browser.newContext({ viewport: { width: 1280, height: 800 }, ignoreHTTPSErrors: true })
  
  for (const page of PAGES) {
    const ctx = page.auth ? authContext : publicContext
    const p = await ctx.newPage()
    try {
      await p.goto(`${BASE_URL}${page.path}`, { waitUntil: 'domcontentloaded', timeout: 8000 })
      await p.waitForTimeout(1500)
      await p.screenshot({ path: path.join(SCREENSHOT_DIR, `${page.name}.png`) })
      console.log(`✅ ${page.name}.png`)
    } catch (err) {
      try { await p.screenshot({ path: path.join(SCREENSHOT_DIR, `${page.name}-ERROR.png`) }) } catch {}
      console.log(`❌ ${page.name} — ${err.message.substring(0, 50)}`)
    } finally {
      await p.close()
    }
  }
  
  await browser.close()
  console.log(`\nDone! ${PAGES.length} pages processed.`)
}

main().catch(console.error)
