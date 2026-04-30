import { useEffect, useState } from 'react'

interface MemoryData {
  memory_systems: {
    semantic: { count: number; status: string }
    episodic: { count: number; status: string }
    muninn: { count: number; status: string; vaults?: string[] }
  }
  total_memories: number
}

export function MemoryStats() {
  const [data, setData] = useState<MemoryData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchMemory = async () => {
      try {
        const res = await fetch('/api/asgard/memory/stats')
        if (res.ok) {
          const data = await res.json()
          setData(data)
        }
      } catch (err) {
        console.error('Failed to fetch memory stats:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchMemory()
    const interval = setInterval(fetchMemory, 10000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="card">
        <h2 className="text-xl font-bold text-asgard-gold mb-4">🧠 Memoria</h2>
        <div className="loading text-gray-400">Cargando...</div>
      </div>
    )
  }

  const memoryTypes = [
    {
      name: 'Semántica',
      key: 'semantic',
      icon: '📚',
      color: 'bg-blue-500',
      description: 'Hechos y conocimiento',
    },
    {
      name: 'Episódica',
      key: 'episodic',
      icon: '🎬',
      color: 'bg-purple-500',
      description: 'Eventos y experiencias',
    },
    {
      name: 'MuninnDB',
      key: 'muninn',
      icon: '🗄️',
      color: 'bg-green-500',
      description: 'Vaults cognitivos',
    },
  ]

  return (
    <div className="card">
      <h2 className="text-xl font-bold text-asgard-gold mb-4">🧠 Sistemas de Memoria</h2>

      <div className="space-y-3">
        {memoryTypes.map((type) => {
          const system = data?.memory_systems[type.key as keyof typeof data.memory_systems]
          const count = system?.count || 0
          const total = data?.total_memories || 1
          const percentage = total > 0 ? (count / total) * 100 : 0

          return (
            <div key={type.key} className="p-3 rounded-lg bg-gray-800/50">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{type.icon}</span>
                  <div>
                    <div className="font-medium">{type.name}</div>
                    <div className="text-xs text-gray-500">{type.description}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold">{count.toLocaleString()}</div>
                  <div className={`text-xs ${
                    system?.status === 'active' ? 'text-green-400' : 'text-gray-500'
                  }`}>
                    {system?.status === 'active' ? '● Activo' : '○ Inactivo'}
                  </div>
                </div>
              </div>

              {/* Progress bar */}
              <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full ${type.color} transition-all duration-500`}
                  style={{ width: `${percentage}%` }}
                />
              </div>

              {/* Vaults for Muninn */}
              {type.key === 'muninn' && system && 'vaults' in system && (system as any).vaults && (system as any).vaults.length > 0 && (
                <div className="mt-2 text-xs text-gray-400">
                  Vaults: {(system as any).vaults.join(', ')}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Total */}
      <div className="mt-4 pt-4 border-t border-gray-700">
        <div className="flex items-center justify-between">
          <span className="text-gray-400">Total de memorias:</span>
          <span className="text-2xl font-bold text-asgard-gold">
            {data?.total_memories.toLocaleString() || 0}
          </span>
        </div>
      </div>
    </div>
  )
}
