#!/usr/bin/env node
/**
 * MasteryOS Screenshot Robot
 * 
 * Captures a screenshot of EVERY page on the platform.
 * Saves to /home/z/my-project/download/screenshots/
 * 
 * Run: node scripts/screenshot-robot.js
 */

const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE_URL = 'https://masteryos-production.up.railway.app'
const API_URL = 'https://trustworthy-adventure-production-a9cc.up.railway.app'
const SCREENSHOT_DIR = '/home/z/my-project/download/screenshots'

const ADMIN_EMAIL = 'krn129110@gmail.com'
const ADMIN_PASSWORD = '8690Gmkaran@_123'

// All pages to screenshot
const ALL_PAGES = [
  // Public
  { path: '/', name: '01-landing' },
  { path: '/features', name: '02-features' },
  { path: '/pricing', name: '03-pricing' },
  { path: '/security', name: '04-security' },
  { path: '/about', name: '05-about' },
  { path: '/contact', name: '06-contact' },
  { path: '/careers', name: '07-careers' },
  { path: '/roadmap', name: '08-roadmap' },
  { path: '/changelog', name: '09-changelog' },
  { path: '/blog', name: '10-blog' },
  { path: '/support', name: '11-support' },
  { path: '/status', name: '12-status' },
  { path: '/api-explorer', name: '13-api-explorer' },
  { path: '/privacy', name: '14-privacy' },
  { path: '/terms', name: '15-terms' },
  { path: '/health', name: '16-health' },
  
  // Auth
  { path: '/login', name: '17-login' },
  { path: '/register', name: '18-register' },
  { path: '/forgot-password', name: '19-forgot-password' },
  
  // Docs
  { path: '/docs', name: '20-docs' },
  { path: '/docs/getting-started', name: '21-docs-getting-started' },
  { path: '/docs/installation', name: '22-docs-installation' },
  { path: '/docs/architecture', name: '23-docs-architecture' },
  { path: '/docs/rest-api', name: '24-docs-rest-api' },
  { path: '/docs/authentication', name: '25-docs-authentication' },
  { path: '/docs/errors', name: '26-docs-errors' },
  { path: '/docs/security', name: '27-docs-security' },
  { path: '/docs/ai', name: '28-docs-ai' },
  { path: '/docs/deployment', name: '29-docs-deployment' },
  { path: '/docs/scaling', name: '30-docs-scaling' },
  { path: '/docs/monitoring', name: '31-docs-monitoring' },
  { path: '/docs/rate-limiting', name: '32-docs-rate-limiting' },
  { path: '/docs/cli', name: '33-docs-cli' },
  { path: '/docs/sdks', name: '34-docs-sdks' },
  { path: '/docs/faq', name: '35-docs-faq' },
  { path: '/docs/troubleshooting', name: '36-docs-troubleshooting' },
  { path: '/docs/content-authoring', name: '37-docs-content-authoring' },
  { path: '/docs/learning-engine', name: '38-docs-learning-engine' },
  { path: '/docs/administration', name: '39-docs-administration' },
  { path: '/docs/websocket-api', name: '40-docs-websocket-api' },
  { path: '/docs/api-explorer', name: '41-docs-api-explorer' },
  
  // Learner (requires login)
  { path: '/dashboard', name: '42-learner-dashboard', needsAuth: true },
  { path: '/subjects', name: '43-learner-subjects', needsAuth: true },
  { path: '/study/start', name: '44-learner-study-start', needsAuth: true },
  { path: '/mastery', name: '45-learner-mastery', needsAuth: true },
  { path: '/reviews', name: '46-learner-reviews', needsAuth: true },
  { path: '/recommendations', name: '47-learner-recommendations', needsAuth: true },
  { path: '/achievements', name: '48-learner-achievements', needsAuth: true },
  { path: '/notifications', name: '49-learner-notifications', needsAuth: true },
  { path: '/profile', name: '50-learner-profile', needsAuth: true },
  { path: '/settings', name: '51-learner-settings', needsAuth: true },
  { path: '/search', name: '52-learner-search', needsAuth: true },
  { path: '/welcome', name: '53-learner-welcome', needsAuth: true },
  
  // Admin (requires login)
  { path: '/admin', name: '54-admin-dashboard', needsAuth: true },
  { path: '/admin/users', name: '55-admin-users', needsAuth: true },
  { path: '/admin/organizations', name: '56-admin-organizations', needsAuth: true },
  { path: '/admin/rbac', name: '57-admin-rbac', needsAuth: true },
  { path: '/admin/feature-flags', name: '58-admin-feature-flags', needsAuth: true },
  { path: '/admin/workers', name: '59-admin-workers', needsAuth: true },
  { path: '/admin/outbox', name: '60-admin-outbox', needsAuth: true },
  { path: '/admin/dead-letters', name: '61-admin-dead-letters', needsAuth: true },
  { path: '/admin/scheduler', name: '62-admin-scheduler', needsAuth: true },
  { path: '/admin/notifications', name: '63-admin-notifications', needsAuth: true },
  { path: '/admin/email', name: '64-admin-email', needsAuth: true },
  { path: '/admin/audit', name: '65-admin-audit', needsAuth: true },
  { path: '/admin/security', name: '66-admin-security', needsAuth: true },
  { path: '/admin/analytics', name: '67-admin-analytics', needsAuth: true },
  { path: '/admin/billing', name: '68-admin-billing', needsAuth: true },
  { path: '/admin/system-config', name: '69-admin-system-config', needsAuth: true },
  { path: '/admin/search', name: '70-admin-search', needsAuth: true },
  { path: '/admin/invites', name: '71-admin-invites', needsAuth: true },
  
  // Beta Ops
  { path: '/admin/beta-ops', name: '72-beta-ops-dashboard', needsAuth: true },
  { path: '/admin/beta-ops/funnel', name: '73-beta-ops-funnel', needsAuth: true },
  { path: '/admin/beta-ops/learning', name: '74-beta-ops-learning', needsAuth: true },
  { path: '/admin/beta-ops/feedback', name: '75-beta-ops-feedback', needsAuth: true },
  { path: '/admin/beta-ops/success', name: '76-beta-ops-success', needsAuth: true },
  { path: '/admin/beta-ops/instructor', name: '77-beta-ops-instructor', needsAuth: true },
  { path: '/admin/beta-ops/operations', name: '78-beta-ops-operations', needsAuth: true },
  { path: '/admin/beta-ops/releases', name: '79-beta-ops-releases', needsAuth: true },
  { path: '/admin/beta-ops/reports', name: '80-beta-ops-reports', needsAuth: true },
  { path: '/admin/beta-ops/experiments', name: '81-beta-ops-experiments', needsAuth: true },
  
  // Portal
  { path: '/portal/account', name: '82-portal-account', needsAuth: true },
  { path: '/portal/billing', name: '83-portal-billing', needsAuth: true },
  { path: '/portal/api-keys', name: '84-portal-api-keys', needsAuth: true },
  { path: '/portal/sessions', name: '85-portal-sessions', needsAuth: true },
  { path: '/portal/usage', name: '86-portal-usage', needsAuth: true },
  { path: '/portal/organizations', name: '87-portal-organizations', needsAuth: true },
  { path: '/portal/invitations', name: '88-portal-invitations', needsAuth: true },
  
  // Content
  { path: '/content', name: '89-content-dashboard', needsAuth: true },
  { path: '/content/subjects', name: '90-content-subjects', needsAuth: true },
  { path: '/content/search', name: '91-content-search', needsAuth: true },
  { path: '/content/analytics', name: '92-content-analytics', needsAuth: true },
  { path: '/content/import-export', name: '93-content-import-export', needsAuth: true },
]

async function main() {
  // Create screenshot directory
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true })
  
  console.log('\n╔══════════════════════════════════════════════════════╗')
  console.log('║    MasteryOS Screenshot Robot — Starting...         ║')
  console.log(`║    ${ALL_PAGES.length} pages to capture                    ║`)
  console.log(`║    Saving to: download/screenshots/                  ║`)
  console.log('╚══════════════════════════════════════════════════════╝\n')
  
  const browser = await chromium.launch({ headless: true })
  
  // Create contexts
  const publicContext = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    ignoreHTTPSErrors: true,
  })
  
  // Auth context (will login)
  const authContext = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    ignoreHTTPSErrors: true,
  })
  
  // Login
  console.log('🔐 Logging in as admin...')
  const loginPage = await authContext.newPage()
  await loginPage.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 15000 })
  await loginPage.fill('input[type="email"]', ADMIN_EMAIL)
  await loginPage.fill('input[type="password"]', ADMIN_PASSWORD)
  await loginPage.click('button[type="submit"]')
  await loginPage.waitForTimeout(3000)
  
  // Set auth cookie (in case login page didn't)
  await authContext.addCookies([{
    name: 'mastery-authenticated',
    value: 'true',
    domain: 'masteryos-production.up.railway.app',
    path: '/',
  }])
  await authContext.addCookies([{
    name: 'mastery-role',
    value: 'administrator',
    domain: 'masteryos-production.up.railway.app',
    path: '/',
  }])
  
  await loginPage.close()
  console.log('✅ Logged in\n')
  
  let captured = 0
  let failed = 0
  
  for (const page of ALL_PAGES) {
    const context = page.needsAuth ? authContext : publicContext
    const p = await context.newPage()
    
    try {
      await p.goto(`${BASE_URL}${page.path}`, { waitUntil: 'domcontentloaded', timeout: 10000 })
      await p.waitForTimeout(1500) // Wait for content to render
      
      const filename = `${page.name}.png`
      await p.screenshot({ path: path.join(SCREENSHOT_DIR, filename), fullPage: false })
      
      console.log(`✅ ${page.name}.png (${page.path})`)
      captured++
    } catch (err) {
      // Try to screenshot the error page
      try {
        await p.screenshot({ path: path.join(SCREENSHOT_DIR, `${page.name}-ERROR.png`), fullPage: false })
      } catch {}
      console.log(`❌ ${page.name} (${page.path}) — ${err.message.substring(0, 50)}`)
      failed++
    } finally {
      await p.close()
    }
  }
  
  await browser.close()
  
  console.log('\n╔══════════════════════════════════════════════════════╗')
  console.log('║         Screenshot Robot — Complete!                 ║')
  console.log('╠══════════════════════════════════════════════════════╣')
  console.log(`║  ✅ Captured:  ${String(captured).padEnd(38)}║`)
  console.log(`║  ❌ Failed:    ${String(failed).padEnd(38)}║`)
  console.log(`║  📁 Location:  download/screenshots/                 ║`)
  console.log('╚══════════════════════════════════════════════════════╝')
}

main().catch(console.error)
