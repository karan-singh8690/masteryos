export default function AdminLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0A0A0B]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-emerald-500/20 border-t-emerald-500" />
        <p className="text-sm text-zinc-400">Loading admin panel...</p>
      </div>
    </div>
  )
}
