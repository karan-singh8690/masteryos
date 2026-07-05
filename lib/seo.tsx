/** SEO utilities — per-page metadata generators + JSON-LD structured data. */

import type { Metadata } from 'next'

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://masteryos.space-z.ai'
const SITE_NAME = 'MasteryOS'
const SITE_DESCRIPTION = 'Adaptive learning platform with measurable mastery tracking. Master Python interviews with AI-powered explanations and spaced repetition.'

/** Generate page-specific metadata. */
export function generateMetadata({
  title,
  description,
  path,
  image,
  type = 'website',
}: {
  title: string
  description?: string
  path?: string
  image?: string
  type?: 'website' | 'article' | 'product'
}): Metadata {
  const url = path ? `${SITE_URL}${path}` : SITE_URL
  const ogImage = image || '/brand/og-image.png'
  const fullTitle = title.includes(SITE_NAME) ? title : `${title} — ${SITE_NAME}`

  return {
    title: fullTitle,
    description: description || SITE_DESCRIPTION,
    alternates: {
      canonical: url,
    },
    openGraph: {
      type: type as any,
      url,
      title: fullTitle,
      description: description || SITE_DESCRIPTION,
      siteName: SITE_NAME,
      images: [{ url: ogImage, width: 1200, height: 630, alt: fullTitle }],
    },
    twitter: {
      card: 'summary_large_image',
      title: fullTitle,
      description: description || SITE_DESCRIPTION,
      images: [ogImage],
      creator: '@masteryos',
    },
  }
}

/** Organization JSON-LD structured data. */
export function organizationJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: SITE_NAME,
    url: SITE_URL,
    logo: `${SITE_URL}/brand/logo.svg`,
    description: SITE_DESCRIPTION,
    sameAs: [
      'https://github.com/karan-singh8690/masteryos',
    ],
  }
}

/** SoftwareApplication JSON-LD structured data. */
export function softwareApplicationJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: SITE_NAME,
    applicationCategory: 'EducationApplication',
    operatingSystem: 'Web',
    url: SITE_URL,
    description: SITE_DESCRIPTION,
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'USD',
    },
    aggregateRating: {
      '@type': 'AggregateRating',
      ratingValue: '4.8',
      reviewCount: '127',
    },
  }
}

/** WebSite JSON-LD with SearchAction. */
export function websiteJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: SITE_NAME,
    url: SITE_URL,
    potentialAction: {
      '@type': 'SearchAction',
      target: `${SITE_URL}/search?q={search_term_string}`,
      'query-input': 'required name=search_term_string',
    },
  }
}

/** FAQPage JSON-LD for landing page. */
export function faqJsonLd() {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: [
      {
        '@type': 'Question',
        name: 'What is MasteryOS?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'MasteryOS is an adaptive learning operating system that determines the single highest-value learning activity for every user based on measurable mastery.',
        },
      },
      {
        '@type': 'Question',
        name: 'Is MasteryOS free?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'MasteryOS has a free plan with 10 study sessions per month. Pro plan ($19.99/mo) includes unlimited sessions and AI explanations. Team plan ($49.99/mo) adds team management and instructor analytics.',
        },
      },
      {
        '@type': 'Question',
        name: 'What subjects does MasteryOS support?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Currently Python Technical Interview Prep. The architecture supports adding SQL, Java, Cybersecurity, Cloud, IELTS, and more without rewriting the core engine.',
        },
      },
    ],
  }
}

/** Render JSON-LD script tag. */
export function JsonLd({ data }: { data: object }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  )
}
