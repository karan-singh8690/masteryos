import type { MetadataRoute } from 'next'

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://masteryos.com'

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date()

  const staticRoutes = [
    { url: '', priority: 1.0, changeFrequency: 'weekly' as const },
    { url: '/features', priority: 0.9, changeFrequency: 'monthly' as const },
    { url: '/pricing', priority: 0.9, changeFrequency: 'monthly' as const },
    { url: '/security', priority: 0.8, changeFrequency: 'monthly' as const },
    { url: '/docs', priority: 0.9, changeFrequency: 'weekly' as const },
    { url: '/docs/getting-started', priority: 0.9, changeFrequency: 'weekly' as const },
    { url: '/docs/rest-api', priority: 0.8, changeFrequency: 'weekly' as const },
    { url: '/docs/websocket-api', priority: 0.7, changeFrequency: 'monthly' as const },
    { url: '/docs/authentication', priority: 0.8, changeFrequency: 'monthly' as const },
    { url: '/docs/sdks', priority: 0.8, changeFrequency: 'monthly' as const },
    { url: '/docs/cli', priority: 0.7, changeFrequency: 'monthly' as const },
    { url: '/docs/deployment', priority: 0.7, changeFrequency: 'monthly' as const },
    { url: '/docs/architecture', priority: 0.6, changeFrequency: 'monthly' as const },
    { url: '/docs/security', priority: 0.7, changeFrequency: 'monthly' as const },
    { url: '/docs/ai', priority: 0.7, changeFrequency: 'monthly' as const },
    { url: '/docs/learning-engine', priority: 0.7, changeFrequency: 'monthly' as const },
    { url: '/docs/troubleshooting', priority: 0.6, changeFrequency: 'monthly' as const },
    { url: '/docs/faq', priority: 0.6, changeFrequency: 'monthly' as const },
    { url: '/api-explorer', priority: 0.8, changeFrequency: 'weekly' as const },
    { url: '/status', priority: 0.7, changeFrequency: 'daily' as const },
    { url: '/roadmap', priority: 0.8, changeFrequency: 'weekly' as const },
    { url: '/changelog', priority: 0.8, changeFrequency: 'weekly' as const },
    { url: '/blog', priority: 0.8, changeFrequency: 'weekly' as const },
    { url: '/about', priority: 0.6, changeFrequency: 'monthly' as const },
    { url: '/contact', priority: 0.6, changeFrequency: 'monthly' as const },
    { url: '/careers', priority: 0.6, changeFrequency: 'weekly' as const },
    { url: '/support', priority: 0.7, changeFrequency: 'monthly' as const },
    { url: '/legal/privacy', priority: 0.4, changeFrequency: 'yearly' as const },
    { url: '/legal/terms', priority: 0.4, changeFrequency: 'yearly' as const },
  ]

  return staticRoutes.map((route) => ({
    url: `${SITE_URL}${route.url}`,
    lastModified: now,
    changeFrequency: route.changeFrequency,
    priority: route.priority,
  }))
}
