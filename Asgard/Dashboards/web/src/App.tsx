import { useEffect, useState } from 'react'
import { YggdrasilMap } from './components/YggdrasilMap'
import { PantheonControl } from './components/PantheonControl'
import { MemoryStats } from './components/MemoryStats'
import { AutoModeTasks } from './components/AutoModeTasks'
import { LiveLogs } from './components/LiveLogs'

// Types
interface EcosystemStatus {
  yggdrasil: {
    reinos: Record<string, {
      status: string
      file_count: number
      dir_count: number
      has_rules: boolean
    }>
    total_files: number
  }
  lilith: {
    backend_running: boolean
    discord_bot: boolean
    telegram_bot: boolean
    version: string
  }
  timestamp: string
}

interface PantheonStatus {
  agents: Record<string, {
    status: string
    total_calls: number
    success_rate: number
    avg_latency_ms: number
  }>
  online_count: number
}

function App() {
  const [ecosystem, setEcosystem] = useState<EcosystemStatus | null>(null)
  const [pantheon, setPantheon] = useState<PantheonStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch ecosystem status
        const ecoRes = await fetch('/api/asgard/ecosystem/status')
        if (!ecoRes.ok) throw new Error('Failed to fetch ecosystem')
        const ecoData = await ecoRes.json()
        setEcosystem(ecoData)

        // Fetch pantheon status
        const panRes = await fetch('/api/asgard/pantheon/status')
        if (!panRes.ok) throw new Error('Failed to fetch pantheon')
        const panData = await panRes.json()
        setPantheon(panData)

        setLoading(false)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
        setLoading(false)
      }
    }

    fetchData()

    // Poll every 5 seconds
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-asgard-dark flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-asgard-gold mb-4">Asgard</h1>
          <p className="text-gray-400 loading">Cargando dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-asgard-dark flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-red-500 mb-4">Error</h1>
          <p className="text-gray-400">{error}</p>
          <p className="text-gray-500 mt-2">Asegúrate de que Lilith esté corriendo en :8000</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-asgard-dark text-white p-6">
      {/* Header */}
      <header className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-asgard-gold">
              🏛️ Asgard Command Center
            </h1>
            <p className="text-gray-400 mt-1">
              Dashboard de telemetría de Yggdrasil
              {ecosystem?.lilith.version && (
                <span className="ml-2 text-asgard-gold">
                  v{ecosystem.lilith.version}
                </span>
              )}
            </p>
          </div>
          <div className="text-right text-sm text-gray-500">
            <p>Última actualización:</p>
            <p>{ecosystem?.timestamp ? new Date(ecosystem.timestamp).toLocaleString() : '-'}</p>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* Yggdrasil Map */}
        {ecosystem && (
          <YggdrasilMap
            reinos={ecosystem.yggdrasil.reinos}
            totalFiles={ecosystem.yggdrasil.total_files}
          />
        )}

        {/* Pantheon Control */}
        {pantheon && (
          <PantheonControl
            agents={pantheon.agents}
            onlineCount={pantheon.online_count}
          />
        )}

        {/* Memory Stats */}
        <MemoryStats />

        {/* AutoMode Tasks */}
        <AutoModeTasks />

        {/* Live Logs */}
        <LiveLogs />
      </div>

      {/* Footer */}
      <footer className="mt-8 pt-4 border-t border-gray-800 text-center text-gray-600 text-sm">
        <p>Yggdrasil Ecosystem Dashboard • {new Date().getFullYear()}</p>
      </footer>
    </div>
  )
}

export default App
