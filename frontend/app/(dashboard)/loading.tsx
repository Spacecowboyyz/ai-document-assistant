export default function DashboardLoading() {
  return (
    <div className="mx-auto max-w-4xl animate-pulse p-4 md:p-8">
      <div className="mb-8 h-8 w-48 rounded-lg bg-surface" />
      <div className="mb-8 h-32 rounded-xl bg-surface" />
      <div className="space-y-3">
        <div className="h-20 rounded-xl bg-surface" />
        <div className="h-20 rounded-xl bg-surface" />
        <div className="h-20 rounded-xl bg-surface" />
      </div>
    </div>
  )
}
