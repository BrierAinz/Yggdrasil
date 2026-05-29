import { useGenerations } from '../hooks/useGenerations'

export function HistoryPage() {
  const { generations, loading, error } = useGenerations()

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      queued: 'forge-badge-queued',
      processing: 'forge-badge-processing',
      importing: 'forge-badge-processing',
      completed: 'forge-badge-completed',
      failed: 'forge-badge-failed',
    }
    return map[status] || 'forge-badge-queued'
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h2 className="text-2xl font-bold text-rune-100 mb-1">Generation History</h2>
      <p className="text-rune-400 mb-6">Track your 3D model generations</p>

      {error && (
        <div className="p-3 mb-4 rounded-lg bg-ember/10 border border-ember/30 text-ember text-sm">
          {error}
        </div>
      )}

      {loading && <div className="text-rune-400 text-center py-8">Loading history...</div>}

      <div className="space-y-3">
        {generations.map((gen) => (
          <div key={gen.id} className="forge-card flex items-start gap-4">
            {/* Status indicator */}
            <div className="flex-shrink-0 mt-1">
              <div className={`w-3 h-3 rounded-full ${
                gen.status === 'completed' ? 'bg-yggdrasil-green' :
                gen.status === 'failed' ? 'bg-ember' :
                gen.status === 'processing' || gen.status === 'importing' ? 'bg-fjord animate-pulse' :
                'bg-rune-600'
              }`} />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-xs text-rune-500">{gen.id}</span>
                <span className={statusBadge(gen.status)}>{gen.status}</span>
                <span className="text-xs text-rune-500">{gen.provider}</span>
                <span className="text-xs text-rune-500">{gen.type}</span>
              </div>
              {gen.prompt && (
                <p className="text-sm text-rune-200 truncate">{gen.prompt}</p>
              )}
              {gen.error && (
                <p className="text-xs text-ember mt-1">{gen.error}</p>
              )}
              {gen.result_object && (
                <p className="text-xs text-yggdrasil-green mt-1">
                  ✓ {gen.result_object}
                </p>
              )}
            </div>

            {/* Time */}
            <div className="text-xs text-rune-500 flex-shrink-0">
              {new Date(gen.created_at).toLocaleDateString()}
            </div>
          </div>
        ))}
      </div>

      {generations.length === 0 && !loading && !error && (
        <div className="text-center text-rune-500 py-16">
          <div className="text-4xl mb-2">📜</div>
          <p>No generations yet. Start forging!</p>
        </div>
      )}
    </div>
  )
}
