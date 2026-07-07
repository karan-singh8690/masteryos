import type { MetadataRoute } from 'next'

const SITE_URL = 'https://masteryos-production.up.railway.app'
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Fetch all question codes for sitemap
async function getQuestionUrls(): Promise<MetadataRoute.Sitemap> {
  try {
    const res = await fetch(`${API_URL}/api/v1/seo/sitemap`, {
      next: { revalidate: 3600 }, // Revalidate every hour
    })
    if (!res.ok) return []
    const data = await res.json()

    const questionUrls: MetadataRoute.Sitemap = (data.questions || []).map((url: string) => ({
      url: `${SITE_URL}${url}`,
      lastModified: new Date(),
      changeFrequency: 'monthly' as const,
      priority: 0.8,
    }))

    const subjectUrls: MetadataRoute.Sitemap = (data.subjects || []).map((url: string) => ({
      url: `${SITE_URL}${url}`,
      lastModified: new Date(),
      changeFrequency: 'weekly' as const,
      priority: 0.7,
    }))

    return [...questionUrls, ...subjectUrls]
  } catch {
    return []
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date()

  const staticRoutes = [
    { url: '', priority: 1.0, changeFrequency: 'weekly' as const },
    { url: '/features', priority: 0.9, changeFrequency: 'monthly' as const },
    { url: '/pricing', priority: 0.9, changeFrequency: 'monthly' as const },
    { url: '/security', priority: 0.8, changeFrequency: 'monthly' as const },
    { url: '/faq', priority: 0.6, changeFrequency: 'monthly' as const },
    { url: '/status', priority: 0.7, changeFrequency: 'daily' as const },
    { url: '/changelog', priority: 0.8, changeFrequency: 'weekly' as const },
    { url: '/blog', priority: 0.8, changeFrequency: 'weekly' as const },
    { url: '/about', priority: 0.6, changeFrequency: 'monthly' as const },
    { url: '/support', priority: 0.7, changeFrequency: 'monthly' as const },
    { url: '/legal/privacy', priority: 0.4, changeFrequency: 'yearly' as const },
    { url: '/legal/terms', priority: 0.4, changeFrequency: 'yearly' as const },
    { url: '/login', priority: 0.5, changeFrequency: 'monthly' as const },
    { url: '/register', priority: 0.6, changeFrequency: 'monthly' as const },
  ]

  const staticSitemap: MetadataRoute.Sitemap = staticRoutes.map((route) => ({
    url: `${SITE_URL}${route.url}`,
    lastModified: now,
    changeFrequency: route.changeFrequency,
    priority: route.priority,
  }))

  // Fetch dynamic question + subject URLs
  const dynamicSitemap = await getQuestionUrls()

  return [...staticSitemap, ...dynamicSitemap]
}
