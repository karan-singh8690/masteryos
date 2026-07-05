import { generateMetadata, JsonLd, organizationJsonLd, softwareApplicationJsonLd, faqJsonLd } from '@/lib/seo'

export const metadata = generateMetadata({
  title: 'MasteryOS — The Operating System for Learning',
  description: 'Adaptive learning platform with measurable mastery tracking. Master Python interviews with AI-powered explanations and spaced repetition.',
  path: '/',
})

export default function LandingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <JsonLd data={organizationJsonLd()} />
      <JsonLd data={softwareApplicationJsonLd()} />
      <JsonLd data={faqJsonLd()} />
      {children}
    </>
  )
}
