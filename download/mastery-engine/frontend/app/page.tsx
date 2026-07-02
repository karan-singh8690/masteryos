import Link from 'next/link'

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col items-center justify-center px-6">
      <div className="space-y-6 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
          Mastery Engine
        </h1>
        <p className="max-w-2xl text-lg text-gray-600">
          A Learning Operating System that determines the single highest-value learning activity
          for every user based on measurable mastery.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
          <Link
            href="/health"
            className="rounded-lg bg-brand-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700"
          >
            Health Check
          </Link>
          <a
            href="/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg border border-gray-300 px-6 py-3 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50"
          >
            API Docs
          </a>
        </div>
        <div className="pt-8 text-sm text-gray-400">
          <p>Status: Scaffold ready for feature implementation.</p>
          <p className="pt-1">Version: 0.1.0</p>
        </div>
      </div>
    </main>
  )
}
