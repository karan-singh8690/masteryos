import { test, expect } from '@playwright/test'

test.describe('Authentication flow', () => {
  test('login page loads', async ({ page }) => {
    await page.goto('/login')
    await expect(page).toHaveTitle(/Mastery Engine/i)
    await expect(page.getByRole('heading', { name: /welcome back/i })).toBeVisible()
    await expect(page.getByLabel(/email/i)).toBeVisible()
    await expect(page.getByLabel(/password/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
  })

  test('register page loads', async ({ page }) => {
    await page.goto('/register')
    await expect(page.getByRole('heading', { name: /create your account/i })).toBeVisible()
    await expect(page.getByLabel(/email/i)).toBeVisible()
    await expect(page.getByLabel(/display name/i)).toBeVisible()
    await expect(page.getByLabel(/^password$/i)).toBeVisible()
  })

  test('forgot password page loads', async ({ page }) => {
    await page.goto('/forgot-password')
    await expect(page.getByRole('heading', { name: /forgot password/i })).toBeVisible()
  })

  test('shows validation error for invalid email', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel(/email/i).fill('not-an-email')
    await page.getByLabel(/password/i).fill('password')
    await page.getByRole('button', { name: /sign in/i }).click()
    // Should show validation error
    await expect(page.getByText(/valid email/i)).toBeVisible()
  })
})

test.describe('Theme switching', () => {
  test('theme toggle is visible', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('button', { name: /toggle theme/i })).toBeVisible()
  })
})

test.describe('Navigation', () => {
  test('home page has CTA buttons', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('link', { name: /get started free/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /sign in/i })).toBeVisible()
  })

  test('404 page shows for unknown routes', async ({ page }) => {
    await page.goto('/nonexistent-page')
    await expect(page.getByText('404')).toBeVisible()
  })
})

test.describe('Responsive design', () => {
  test('mobile viewport renders correctly', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  })

  test('desktop viewport renders correctly', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 })
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  })
})
