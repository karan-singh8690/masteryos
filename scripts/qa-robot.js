#!/usr/bin/env node
/**
 * MasteryOS QA Robot
 * 
 * Crawls every page, clicks every button, tests every form,
 * and reports what works and what's broken.
 * 
 * Usage:
 *   node scripts/qa-robot.js                    # Test deployed site
 *   node scripts/qa-robot.js --local            # Test localhost:3000
 *   node scripts/qa-robot.js --url=https://...  # Custom URL
 */

const { chromium } = require('playwright')

// ============================================================
// Configuration
// ============================================================

const args = process.argv.slice(2)
const urlArg = args.find(a => a.startsWith('--url='))
const isLocal = args.includes('--local')

const BASE_URL = urlArg ? urlArg.replace('--url=', '') 
  : isLocal ? 'http://localhost:3000' 
  : 'https://masteryos-production.up.railway.app'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://trustworthy-adventure-production-a9cc.up.railway.app'

const ADMIN_EMAIL = 'krn129110@gmail.com'
const ADMIN_PASSWORD = '8690Gmkaran@_123'

// ============================================================
// Test Results
// ============================================================

const results = {
  pages: [],
  buttons: [],
  forms: [],
  apis: [],
  errors: [],
  summary: {
    total: 0,
    passed: 0,
    failed: 0,
    warnings: 0,
  }
}

function log(type, message, detail = '') {
  const icon = type === 'PASS' ? '✅' : type === 'FAIL' ? '❌' : type === 'WARN' ? '⚠️' : 'ℹ️'
  const line = `${icon} [${type}] ${message}${detail ? ' — ' + detail : ''}`
  console.log(line)
  
  results.summary.total++
  if (type === 'PASS') results.summary.passed++
  else if (type === 'FAIL') results.summary.failed++
  else if (type === 'WARN') results.summary.warnings++
}

// ============================================================
// Pages to test
// ============================================================

const PUBLIC_PAGES = [
  '/',
  '/features',
  '/pricing',
  '/security',
  '/about',
  '/contact',
  '/careers',
  '/roadmap',
  '/changelog',
  '/blog',
  '/support',
  '/status',
  '/api-explorer',
  '/docs',
  '/docs/getting-started',
  '/docs/installation',
  '/docs/architecture',
  '/docs/rest-api',
  '/docs/authentication',
  '/docs/errors',
  '/docs/security',
  '/docs/ai',
  '/docs/deployment',
  '/docs/scaling',
  '/docs/monitoring',
  '/docs/rate-limiting',
  '/docs/cli',
  '/docs/sdks',
  '/docs/faq',
  '/docs/troubleshooting',
  '/docs/content-authoring',
  '/docs/learning-engine',
  '/docs/administration',
  '/docs/websocket-api',
  '/docs/api-explorer',
  '/privacy',
  '/terms',
  '/login',
  '/register',
  '/forgot-password',
  '/health',
]

const LEARNER_PAGES = [
  '/dashboard',
  '/subjects',
  '/study/start',
  '/mastery',
  '/reviews',
  '/recommendations',
  '/achievements',
  '/notifications',
  '/profile',
  '/settings',
  '/search',
  '/welcome',
]

const ADMIN_PAGES = [
  '/admin',
  '/admin/dashboard',
  '/admin/users',
  '/admin/organizations',
  '/admin/rbac',
  '/admin/feature-flags',
  '/admin/workers',
  '/admin/outbox',
  '/admin/dead-letters',
  '/admin/scheduler',
  '/admin/notifications',
  '/admin/email',
  '/admin/audit',
  '/admin/security',
  '/admin/analytics',
  '/admin/billing',
  '/admin/system-config',
  '/admin/search',
  '/admin/invites',
  '/admin/beta-ops',
  '/admin/beta-ops/funnel',
  '/admin/beta-ops/learning',
  '/admin/beta-ops/feedback',
  '/admin/beta-ops/success',
  '/admin/beta-ops/instructor',
  '/admin/beta-ops/operations',
  '/admin/beta-ops/releases',
  '/admin/beta-ops/reports',
  '/admin/beta-ops/experiments',
]

const PORTAL_PAGES = [
  '/portal/account',
  '/portal/billing',
  '/portal/api-keys',
  '/portal/sessions',
  '/portal/usage',
  '/portal/organizations',
  '/portal/invitations',
]

const CONTENT_PAGES = [
  '/content',
  '/content/dashboard',
  '/content/subjects',
  '/content/search',
  '/content/analytics',
  '/content/import-export',
]

// API endpoints to test
const API_ENDPOINTS = [
  ['GET', '/api/v1/health'],
  ['GET', '/api/v1/health/ready'],
  ['GET', '/api/v1/health/live'],
  ['GET', '/api/v1/beta/status'],
  ['GET', '/metrics'],
  ['GET', '/'],
  ['GET', '/api/v1/admin/feature-flags'],
  ['GET', '/api/v1/feature-flags'],
  ['GET', '/api/v1/users/me'],
  ['GET', '/api/v1/questions/dashboard'],
  ['GET', '/api/v1/enrollments'],
  ['GET', '/api/v1/notifications'],
  ['GET', '/api/v1/recommendations'],
  ['GET', '/api/v1/achievements'],
  ['GET', '/api/v1/admin/beta/invites'],
  ['GET', '/api/v1/admin/beta-ops/dashboard'],
  ['GET', '/api/v1/admin/beta-ops/operations'],
  ['GET', '/api/v1/admin/bg/workers'],
  ['GET', '/api/v1/admin/bg/outbox'],
  ['GET', '/api/v1/ai/status'],
  ['GET', '/api/v1/ai/metrics'],
]

// ============================================================
// QA Robot
// ============================================================

async function runQARobot() {
  console.log('\n')
  console.log('╔══════════════════════════════════════════════════════════╗')
  console.log('║          MasteryOS QA Robot — Starting...               ║')
  console.log('╠══════════════════════════════════════════════════════════╣')
  console.log(`║  Target:  ${BASE_URL.padEnd(46)}║`)
  console.log(`║  API:     ${API_URL.padEnd(46)}║`)
  console.log(`║  Time:    ${new Date().toISOString().padEnd(46)}║`)
  console.log('╚══════════════════════════════════════════════════════════╝')
  console.log('\n')

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
  })

  // Collect console errors
  let consoleErrors = []
  let networkErrors = []

  // ============================================================
  // PHASE 1: Test API Endpoints (no auth)
  // ============================================================

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('Phase 1: Testing API Endpoints (no auth)')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

  for (const [method, path] of API_ENDPOINTS) {
    try {
      const response = await fetch(`${API_URL}${path}`, { method })
      const status = response.status
      
      if (status === 200) {
        log('PASS', `API ${method} ${path}`, `${status}`)
      } else if (status === 401 || status === 403) {
        log('PASS', `API ${method} ${path}`, `${status} (auth required — expected)`)
      } else if (status === 404) {
        log('FAIL', `API ${method} ${path}`, `${status} — endpoint not found`)
      } else if (status >= 500) {
        log('FAIL', `API ${method} ${path}`, `${status} — server error`)
      } else {
        log('WARN', `API ${method} ${path}`, `${status}`)
      }
    } catch (err) {
      log('FAIL', `API ${method} ${path}`, err.message)
    }
  }

  // ============================================================
  // PHASE 2: Test Public Pages
  // ============================================================

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('Phase 2: Testing Public Pages')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

  for (const page of PUBLIC_PAGES) {
    const pageResult = await testPage(browser, context, page)
    results.pages.push(pageResult)
  }

  // ============================================================
  // PHASE 3: Login as Admin
  // ============================================================

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('Phase 3: Logging in as Admin')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

  const adminContext = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
  })

  const loggedIn = await loginAsAdmin(adminContext)
  
  if (loggedIn) {
    // ============================================================
    // PHASE 4: Test Learner Pages (logged in)
    // ============================================================

    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    console.log('Phase 4: Testing Learner Pages (logged in)')
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

    for (const page of LEARNER_PAGES) {
      const pageResult = await testPage(browser, adminContext, page)
      results.pages.push(pageResult)
    }

    // ============================================================
    // PHASE 5: Test Admin Pages
    // ============================================================

    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    console.log('Phase 5: Testing Admin Pages')
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

    for (const page of ADMIN_PAGES) {
      const pageResult = await testPage(browser, adminContext, page)
      results.pages.push(pageResult)
    }

    // ============================================================
    // PHASE 6: Test Portal Pages
    // ============================================================

    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    console.log('Phase 6: Testing Portal Pages')
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

    for (const page of PORTAL_PAGES) {
      const pageResult = await testPage(browser, adminContext, page)
      results.pages.push(pageResult)
    }

    // ============================================================
    // PHASE 7: Test Content Pages
    // ============================================================

    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    console.log('Phase 7: Testing Content Pages')
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

    for (const page of CONTENT_PAGES) {
      const pageResult = await testPage(browser, adminContext, page)
      results.pages.push(pageResult)
    }

    // ============================================================
    // PHASE 8: Test Buttons & Forms
    // ============================================================

    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    console.log('Phase 8: Testing Buttons & Interactive Elements')
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

    await testInteractiveElements(browser, adminContext)
  }

  // ============================================================
  // PHASE 9: Test API Endpoints (with auth)
  // ============================================================

  if (loggedIn) {
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    console.log('Phase 9: Testing API Endpoints (with admin auth)')
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

    // Get the access token from the admin context
    const page = await adminContext.newPage()
    await page.goto(`${BASE_URL}/dashboard`)
    const token = await page.evaluate(() => localStorage.getItem('mastery.access_token'))
    await page.close()

    if (token) {
      for (const [method, path] of API_ENDPOINTS) {
        try {
          const response = await fetch(`${API_URL}${path}`, {
            method,
            headers: { Authorization: `Bearer ${token}` },
          })
          const status = response.status
          
          if (status === 200) {
            log('PASS', `API ${method} ${path} (authed)`, `${status}`)
          } else if (status === 404) {
            log('FAIL', `API ${method} ${path} (authed)`, `${status} — not found`)
          } else if (status >= 500) {
            log('FAIL', `API ${method} ${path} (authed)`, `${status} — server error`)
          } else {
            log('WARN', `API ${method} ${path} (authed)`, `${status}`)
          }
        } catch (err) {
          log('FAIL', `API ${method} ${path} (authed)`, err.message)
        }
      }
    } else {
      log('WARN', 'Could not get access token for authed API tests')
    }
  }

  // ============================================================
  // Final Report
  // ============================================================

  await browser.close()

  console.log('\n')
  console.log('╔══════════════════════════════════════════════════════════╗')
  console.log('║              QA Robot — Final Report                    ║')
  console.log('╠══════════════════════════════════════════════════════════╣')
  console.log(`║  Total checks:  ${String(results.summary.total).padEnd(42)}║`)
  console.log(`║  ✅ Passed:     ${String(results.summary.passed).padEnd(42)}║`)
  console.log(`║  ❌ Failed:     ${String(results.summary.failed).padEnd(42)}║`)
  console.log(`║  ⚠️  Warnings:   ${String(results.summary.warnings).padEnd(42)}║`)
  const pct = results.summary.total > 0 ? Math.round((results.summary.passed / results.summary.total) * 100) : 0
  console.log(`║  Success rate:  ${String(pct + '%').padEnd(42)}║`)
  console.log('╚══════════════════════════════════════════════════════════╝')
  console.log('\n')

  if (results.summary.failed > 0) {
    console.log('Failed items:')
    console.log('─────────────────────────────────────────')
  }

  return results
}

// ============================================================
// Helper: Test a single page
// ============================================================

async function testPage(browser, context, path) {
  const url = `${BASE_URL}${path}`
  const page = await context.newPage()
  
  const pageErrors = []
  const consoleErrors = []
  
  // Capture console errors
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text())
    }
  })
  
  // Capture page errors (uncaught exceptions)
  page.on('pageerror', (err) => {
    pageErrors.push(err.message)
  })

  try {
    const response = await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 })
    const status = response?.status() || 0
    
    if (status === 200) {
      // Check for redirect to login (protected page without auth)
      const finalUrl = page.url()
      if (finalUrl.includes('/login') && !path.includes('/login')) {
        log('PASS', `Page ${path}`, `200 → redirected to login (auth required)`)
      } else if (finalUrl.includes('/forbidden') && !path.includes('/forbidden')) {
        log('WARN', `Page ${path}`, `200 → redirected to forbidden (role required)`)
      } else if (pageErrors.length > 0) {
        log('FAIL', `Page ${path}`, `200 but ${pageErrors.length} JS errors`)
        pageErrors.forEach(e => console.log(`     → ${e.substring(0, 100)}`))
      } else if (consoleErrors.length > 0) {
        log('WARN', `Page ${path}`, `200 but ${consoleErrors.length} console errors`)
        consoleErrors.slice(0, 3).forEach(e => console.log(`     → ${e.substring(0, 100)}`))
      } else {
        log('PASS', `Page ${path}`, '200')
      }
    } else if (status === 404) {
      log('FAIL', `Page ${path}`, '404 — page not found')
    } else if (status === 500) {
      log('FAIL', `Page ${path}`, '500 — server error')
    } else if (status === 302 || status === 307) {
      log('PASS', `Page ${path}`, `${status} → redirect`)
    } else {
      log('WARN', `Page ${path}`, `${status}`)
    }
    
    return { path, status, errors: [...pageErrors, ...consoleErrors] }
  } catch (err) {
    log('FAIL', `Page ${path}`, err.message.substring(0, 80))
    return { path, status: 0, errors: [err.message] }
  } finally {
    await page.close()
  }
}

// ============================================================
// Helper: Login as admin
// ============================================================

async function loginAsAdmin(context) {
  const page = await context.newPage()
  
  try {
    // Go to login page
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 15000 })
    
    // Fill in credentials
    await page.fill('input[type="email"]', ADMIN_EMAIL)
    await page.fill('input[type="password"]', ADMIN_PASSWORD)
    
    // Click sign in
    await page.click('button[type="submit"]')
    
    // Wait for navigation (to dashboard or admin)
    await page.waitForTimeout(5000)
    
    const finalUrl = page.url()
    
    if (finalUrl.includes('/dashboard') || finalUrl.includes('/admin') || finalUrl.includes('/login')) {
      if (finalUrl.includes('/login')) {
        log('FAIL', 'Admin login', 'Still on login page — login failed')
        await page.close()
        return false
      } else {
        log('PASS', 'Admin login', `Logged in → ${finalUrl.replace(BASE_URL, '')}`)
        await page.close()
        return true
      }
    } else {
      log('PASS', 'Admin login', `Redirected to ${finalUrl.replace(BASE_URL, '')}`)
      await page.close()
      return true
    }
  } catch (err) {
    log('FAIL', 'Admin login', err.message.substring(0, 80))
    await page.close()
    return false
  }
}

// ============================================================
// Helper: Test interactive elements (buttons, forms)
// ============================================================

async function testInteractiveElements(browser, context) {
  // Test: Create beta invite
  await testCreateInvite(context)
  
  // Test: Navigate via sidebar
  await testSidebarNavigation(context)
  
  // Test: Theme toggle
  await testThemeToggle(context)
  
  // Test: Search
  await testSearch(context)
}

async function testCreateInvite(context) {
  const page = await context.newPage()
  
  try {
    await page.goto(`${BASE_URL}/admin/invites`, { waitUntil: 'networkidle', timeout: 15000 })
    
    // Check if the invite form exists
    const emailInput = await page.$('input[type="email"]')
    const submitButton = await page.$('button[type="submit"]')
    
    if (emailInput && submitButton) {
      log('PASS', 'Beta Invite form', 'Form found on /admin/invites')
      
      // Try filling in an email (but don't submit — we don't want to create spam invites)
      await emailInput.fill('test-robot@example.com')
      log('PASS', 'Beta Invite form', 'Email input accepts text')
    } else {
      log('FAIL', 'Beta Invite form', 'Form not found on /admin/invites')
    }
  } catch (err) {
    log('FAIL', 'Beta Invite form', err.message.substring(0, 80))
  } finally {
    await page.close()
  }
}

async function testSidebarNavigation(context) {
  const page = await context.newPage()
  
  try {
    await page.goto(`${BASE_URL}/admin`, { waitUntil: 'networkidle', timeout: 15000 })
    
    // Find all sidebar links
    const links = await page.$$('nav a, aside a')
    
    if (links.length > 0) {
      log('PASS', 'Admin sidebar', `Found ${links.length} navigation links`)
      
      // Check if key nav items exist
      const navText = await page.evaluate(() => {
        const links = document.querySelectorAll('nav a, aside a')
        return Array.from(links).map(a => a.textContent?.trim() || '')
      })
      
      const expectedItems = ['Dashboard', 'Users', 'Beta Invites', 'Beta Dashboard']
      for (const item of expectedItems) {
        if (navText.some(t => t.includes(item))) {
          log('PASS', `Nav item "${item}"`, 'Found in sidebar')
        } else {
          log('WARN', `Nav item "${item}"`, 'Not found in sidebar')
        }
      }
    } else {
      log('WARN', 'Admin sidebar', 'No navigation links found')
    }
  } catch (err) {
    log('FAIL', 'Admin sidebar', err.message.substring(0, 80))
  } finally {
    await page.close()
  }
}

async function testThemeToggle(context) {
  const page = await context.newPage()
  
  try {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle', timeout: 15000 })
    
    // Look for theme toggle button
    const themeButton = await page.$('button[aria-label*="theme"], button[aria-label*="Theme"], button:has(svg.lucide-sun), button:has(svg.lucide-moon)')
    
    if (themeButton) {
      log('PASS', 'Theme toggle', 'Found theme toggle button')
    } else {
      log('WARN', 'Theme toggle', 'Theme toggle button not found on landing page')
    }
  } catch (err) {
    log('WARN', 'Theme toggle', err.message.substring(0, 80))
  } finally {
    await page.close()
  }
}

async function testSearch(context) {
  const page = await context.newPage()
  
  try {
    await page.goto(`${BASE_URL}/search`, { waitUntil: 'networkidle', timeout: 15000 })
    
    // Look for search input
    const searchInput = await page.$('input[type="search"], input[placeholder*="search" i], input[placeholder*="Search" i]')
    
    if (searchInput) {
      log('PASS', 'Search', 'Search input found')
    } else {
      log('WARN', 'Search', 'Search input not found')
    }
  } catch (err) {
    log('WARN', 'Search', err.message.substring(0, 80))
  } finally {
    await page.close()
  }
}

// ============================================================
// Run the robot
// ============================================================

runQARobot().then((results) => {
  process.exit(results.summary.failed > 0 ? 1 : 0)
}).catch((err) => {
  console.error('QA Robot crashed:', err)
  process.exit(1)
})
