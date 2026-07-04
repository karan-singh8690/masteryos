import type { Metadata, Viewport } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'

import { Providers } from '@/providers'
import { APP_NAME } from '@/lib/constants'
import '@/styles/globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://masteryos.com'

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: 'MasteryOS — The Operating System for Learning',
    template: `%s | MasteryOS`,
  },
  description:
    'MasteryOS is an adaptive learning platform that determines the single highest-value learning activity for every user based on measurable mastery. Master Python interviews and beyond.',
  applicationName: 'MasteryOS',
  authors: [{ name: 'Mastery Engine Team', url: 'https://masteryos.com' }],
  creator: 'Mastery Engine',
  publisher: 'Mastery Engine',
  keywords: [
    'MasteryOS', 'learning platform', 'adaptive learning', 'mastery tracking',
    'Python interview prep', 'spaced repetition', 'AI tutor', 'learning OS',
    'skill assessment', 'interview preparation', 'programming education',
  ],
  category: 'education',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: SITE_URL,
    siteName: 'MasteryOS',
    title: 'MasteryOS — The Operating System for Learning',
    description:
      'Adaptive learning platform with measurable mastery tracking. Master Python interviews with AI-powered explanations and spaced repetition.',
    images: [
      {
        url: '/brand/og-image.svg',
        width: 1200,
        height: 630,
        alt: 'MasteryOS — The Operating System for Learning',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'MasteryOS — The Operating System for Learning',
    description:
      'Adaptive learning platform with measurable mastery tracking. Master Python interviews with AI-powered explanations and spaced repetition.',
    images: ['/brand/og-image.svg'],
    creator: '@masteryos',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  alternates: {
    canonical: '/',
  },
  manifest: '/manifest.webmanifest',
  icons: {
    icon: [
      { url: '/favicon.svg', type: 'image/svg+xml' },
    ],
    apple: [
      { url: '/brand/logo-mark.svg', type: 'image/svg+xml' },
    ],
  },
}

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0f172a' },
  ],
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrainsMono.variable} min-h-screen bg-background text-foreground antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
