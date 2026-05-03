import { useState } from 'react'

interface AgentData {
  status: string
  total_calls: number
  success_rate: number
  avg_latency_ms: number
}

interface PantheonControlProps {
  agents: Record<string, AgentData>
  onlineCount: number
}

const AGENT_EMOJIS: Record<string, string> = {
  eva: '👁️',
  adan: '🔧',
  odin: '🧠',
  lucifer: '🔥',
  crystal: '💎',
  shalltear: '🩸',
  archivero: '📚',
}

const AGENT_DESCRIPTIONS: Record<string, string> = {
  eva: 'Análisis e investigación',
  adan: 'Código y refactor',
  odin: 'Arquitectura y diseño',
  lucifer: 'Creativo y conversacional',
  crystal: 'Discord y Telegram',
  shalltear: 'Creatividad NSFW',
  archivero: 'Documentación y RAG',
}

export function PantheonControl({ agents, onlineCount }: PantheonControlProps) {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)

  const agentList = Object.entries(agents).map(([name, data]) => ({
    name,
    emoji: AGENT_EMOJIS[name] || '🤖',
    description: AGENT_DESCRIPTIONS[name] || 'Agente especializado',
    ...data,
  }))

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'online':
        return <span className="badge badge-online">Online</span>
      case 'standby':
        return <span className="badge badge-standby">Standby</span>
      case 'offline':
        return <span className="badge badge-offline">Offline</span>
      default:
        return <span className="badge badge-standby">{status}</span>
    }
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-asgard-gold">
          🏛️ Panteón de Agentes
        </h2>
        <span className="text-sm text-gray-400">
          {onlineCount}/{agentList.length} online
        </span>
      </div>

      <div className="space-y-3">
        {agentList.map((agent) => (
          <div
            key={agent.name}
            className={`p-3 rounded-lg border border-gray-700 cursor-pointer transition-all hover:border-asgard-gold ${
              selectedAgent === agent.name ? 'bg-gray-800 border-asgard-gold' : ''
            }`}
            onClick={() => setSelectedAgent(selectedAgent === agent.name ? null : agent.name)}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{agent.emoji}</span>
                <div>
                  <div className="font-semibold capitalize flex items-center gap-2">
                    {agent.name}
                    {getStatusBadge(agent.status)}
                  </div>
                  <div className="text-xs text-gray-500">{agent.description}</div>
                </div>
              </div>

              <div className="text-right text-sm">
                <div className="text-gray-400">
                  {agent.total_calls.toLocaleString()} calls
                </div>
                <div className="text-xs text-gray-500">
                  {(agent.success_rate * 100).toFixed(1)}% éxito
                </div>
              </div>
            </div>

            {/* Expanded details */}
            {selectedAgent === agent.name && (
              <div className="mt-3 pt-3 border-t border-gray-700 text-sm">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-gray-500">Latencia media:</span>
                    <span className="ml-2 font-mono">
                      {agent.avg_latency_ms.toFixed(0)}ms
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Tasa de éxito:</span>
                    <span className={`ml-2 font-mono ${
                      agent.success_rate > 0.9 ? 'text-green-400' :
                      agent.success_rate > 0.7 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {(agent.success_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* Action buttons */}
                <div className="mt-3 flex gap-2">
                  <button
                    className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 rounded transition-colors"
                    disabled={agent.status !== 'online'}
                  >
                    Test
                  </button>
                  <button
                    className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-700 rounded transition-colors"
                    disabled
                  >
                    Config
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="mt-4 pt-4 border-t border-gray-700 text-xs text-gray-500">
        <p>Los agentes del Panteón son especialistas que Lilith puede delegar.</p>
      </div>
    </div>
  )
}
