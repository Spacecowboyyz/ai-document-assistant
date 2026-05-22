export default function ChatLoading() {
  return (
    <div className="flex h-screen flex-col animate-pulse">
      <div className="h-14 border-b border-border bg-surface" />
      <div className="flex-1 space-y-4 p-6">
        <div className="ml-auto h-16 w-2/3 rounded-2xl bg-surface" />
        <div className="h-24 w-3/4 rounded-2xl bg-surface" />
      </div>
      <div className="h-24 border-t border-border bg-surface" />
    </div>
  )
}
