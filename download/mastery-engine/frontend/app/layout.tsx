import type { Metadata } from 'next'
import { Providers } from '@/providers'
import '@/styles/globals.css'

export const metadata: Metadata = {
  title: {
    default: 'Mastery Engine',
    template: '%s | Mastery Engine',
  },
  description:
    'A Learning Operating System that determines the single highest-value learning activity for every user based on measurable mastery.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
