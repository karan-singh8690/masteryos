import type { MetadataRoute } from 'next'

const SITE_URL = 'https://masteryos-production.up.railway.app'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: [
        '/',
        '/q/',          // Public question pages (SEO)
        '/features',
        '/pricing',
        '/security',
        '/blog',
        '/faq',
        '/status',
        '/changelog',
        '/about',
        '/support',
        '/legal/',
      ],
      disallow: [
        '/api/',
        '/admin/',
        '/dashboard',
        '/study',
        '/settings',
        '/profile',
        '/notifications',
        '/materials/',
        '/mastery',
        '/reviews',
        '/recommendations',
        '/achievements',
        '/portal',
        '/forgot-password',
        '/reset-password',
        '/verify-email',
        '/mfa',
        '/recovery-codes',
        '/docs/',
      ],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  }
}
