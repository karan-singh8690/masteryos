import { notFound } from 'next/navigation'
import Link from 'next/link'
import { ArrowRight, BookOpen, CheckCircle2, Sparkles, Brain, Shield } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// SSR: Fetch question data at build/request time for SEO
async function getQuestion(code: string) {
  try {
    const res = await fetch(`${API_URL}/api/v1/seo/questions/${code}`, {
      next: { revalidate: 3600 }, // Revalidate every hour
    })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

// Generate static metadata for SEO
export async function generateMetadata({ params }: { params: { code: string } }) {
  const question = await getQuestion(params.code)
  if (!question || question.error) {
    return {
      title: 'Question Not Found — MasteryOS',
      description: 'Practice Python interview questions with adaptive mastery tracking.',
    }
  }

  const title = question.meta_title || `${question.prompt?.slice(0, 60)} — MasteryOS`
  const description = question.meta_description || `Practice: ${question.prompt?.slice(0, 120)}`

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: 'article',
      url: `https://masteryos-production.up.railway.app/q/${params.code}`,
      siteName: 'MasteryOS',
      images: [{ url: 'https://masteryos-production.up.railway.app/brand/logo-mark.svg' }],
    },
    twitter: {
      card: 'summary',
      title,
      description,
    },
    alternates: {
      canonical: `https://masteryos-production.up.railway.app/q/${params.code}`,
    },
    keywords: [
      'python', 'interview', 'python interview', question.subject_name,
      ...question.concepts?.map((c: any) => c.name || c),
      question.pyq_exam, 'coding interview', 'data structures',
      'algorithms', 'masteryos', 'practice questions',
    ].filter(Boolean),
  }
}

// JSON-LD structured data for Google rich snippets
function generateJsonLd(question: any) {
  return {
    "@context": "https://schema.org",
    "@type": "QAPage",
    "mainEntity": {
      "@type": "Question",
      "name": question.prompt,
      "text": question.prompt,
      "answerCount": "1",
      "suggestedAnswer": {
        "@type": "Answer",
        "text": "Sign up on MasteryOS to see the full explanation and practice this question with adaptive mastery tracking.",
        "upvoteCount": 0,
      },
      "about": question.concepts?.map((c: any) => ({
        "@type": "Thing",
        "name": c.name || c,
      })),
      "educationalLevel": question.difficulty,
      "learningResourceType": "Quiz",
    },
    "isPartOf": {
      "@type": "Course",
      "name": question.subject_name,
      "description": question.subject_description,
    },
  }
}

export default async function PublicQuestionPage({ params }: { params: { code: string } }) {
  const question = await getQuestion(params.code)

  if (!question || question.error) {
    notFound()
  }

  return (
    <div className="min-h-screen bg-[#08080A] text-white">
      {/* Background glow */}
      <div className="pointer-events-none fixed inset-0 glow-emerald opacity-20" />

      {/* Nav */}
      <nav className="relative z-50 flex items-center justify-between px-6 py-5 md:px-12">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 text-sm font-bold text-black shadow-lg shadow-emerald-500/20">
            M
          </span>
          <span className="text-lg font-bold tracking-tight text-white">
            Mastery<span className="gradient-emerald-text">OS</span>
          </span>
        </Link>
        <Link href="/register">
          <button className="btn-glow rounded-lg gradient-emerald px-4 py-2 text-sm font-semibold text-black shadow-lg shadow-emerald-500/30">
            Sign Up Free
          </button>
        </Link>
      </nav>

      <div className="relative mx-auto max-w-3xl px-4 py-12">
        {/* Breadcrumb */}
        <div className="mb-6 flex items-center gap-2 text-sm text-zinc-500">
          <Link href="/" className="hover:text-emerald-400 transition-colors">Home</Link>
          <span>/</span>
          <span className="text-zinc-400">{question.subject_name}</span>
          <span>/</span>
          <span className="text-emerald-400">Question</span>
        </div>

        {/* Question card */}
        <div className="glass-card rounded-2xl p-8">
          {/* Tags */}
          <div className="mb-6 flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
              {question.question_type?.replace(/_/g, ' ')}
            </span>
            <span className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-zinc-400 capitalize">
              {question.difficulty}
            </span>
            {question.pyq_exam && (
              <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-300">
                {question.pyq_exam}{question.pyq_year ? ` ${question.pyq_year}` : ''}
              </span>
            )}
            {question.concepts?.map((c: any) => (
              <span key={c.name || c} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-zinc-500">
                {c.name || c}
              </span>
            ))}
          </div>

          {/* Question text */}
          <h1 className="text-2xl font-bold leading-snug text-white md:text-3xl">
            {question.prompt}
          </h1>

          {/* Choices (if multiple choice) — no correct answer indicated */}
          {question.choices && question.choices.length > 0 && (
            <div className="mt-6 space-y-3">
              {question.choices.map((choice: any, i: number) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-4"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10 text-sm font-bold text-zinc-400">
                    {choice.id || String.fromCharCode(65 + i)}
                  </span>
                  <span className="text-sm text-zinc-300">{choice.text}</span>
                </div>
              ))}
            </div>
          )}

          {/* Locked answer section */}
          <div className="mt-8 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-6 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 ring-1 ring-inset ring-emerald-500/20">
              <Brain className="h-6 w-6 text-emerald-400" />
            </div>
            <h3 className="text-lg font-bold text-white">Want to see the answer?</h3>
            <p className="mt-1 text-sm text-zinc-400">
              Sign up free to see the full explanation, practice with adaptive questions,
              and track your mastery score.
            </p>
            <Link href="/register">
              <button className="btn-glow mt-4 inline-flex items-center gap-2 rounded-lg gradient-emerald px-6 py-2.5 text-sm font-semibold text-black shadow-lg shadow-emerald-500/30 transition-all hover:scale-105">
                Sign Up to See Answer
                <ArrowRight className="h-4 w-4" />
              </button>
            </Link>
            {question.explanation_preview && (
              <p className="mt-4 text-xs text-zinc-600">
                Preview: {question.explanation_preview}
              </p>
            )}
          </div>
        </div>

        {/* SEO content — subject description */}
        <div className="mt-8 glass-card rounded-2xl p-6">
          <h2 className="mb-2 flex items-center gap-2 text-lg font-bold text-white">
            <BookOpen className="h-5 w-5 text-emerald-400" />
            About {question.subject_name}
          </h2>
          <p className="text-sm leading-relaxed text-zinc-400">
            {question.subject_description || 'Master Python technical interviews with adaptive practice on data structures, algorithms, OOP, Python internals, and system design.'}
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link href="/register">
              <button className="text-sm font-medium text-emerald-400 hover:text-emerald-300 transition-colors">
                Start practicing free →
              </button>
            </Link>
            <Link href="/features">
              <button className="text-sm font-medium text-zinc-500 hover:text-zinc-300 transition-colors">
                Learn more about MasteryOS
              </button>
            </Link>
          </div>
        </div>

        {/* Features highlights */}
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          {[
            { icon: Brain, title: 'Adaptive Practice', desc: 'Questions adapt to your level' },
            { icon: Sparkles, title: 'AI Explanations', desc: 'Understand every answer deeply' },
            { icon: Shield, title: 'Spaced Repetition', desc: 'Review at optimal intervals' },
          ].map((f) => (
            <div key={f.title} className="glass-card rounded-xl p-4 text-center">
              <f.icon className="mx-auto h-6 w-6 text-emerald-400" />
              <h4 className="mt-2 text-sm font-semibold text-white">{f.title}</h4>
              <p className="mt-1 text-xs text-zinc-500">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* JSON-LD structured data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(generateJsonLd(question)) }}
      />
    </div>
  )
}
