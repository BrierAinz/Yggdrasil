import { useMemo } from 'react'

interface ReinoData {
  status: string
  file_count: number
  dir_count: number
  has_rules: boolean
}

interface YggdrasilMapProps {
  reinos: Record<string, ReinoData>
  totalFiles: number
}

const REINO_EMOJIS: Record<string, string> = {
  asgard: '🏛️',
  alfheim: '🎨',
  midgard: '🌍',
  svartalfheim: '📚',
  vanaheim: '🌿',
  jotunheim: '🏔️',
  muspelheim: '🔥',
  niflheim: '🌫️',
  helheim: '⚰️',
}

const REINO_NAMES: Record<string, string> = {
  asgard: 'Asgard',
  alfheim: 'Alfheim',
  midgard: 'Midgard',
  svartalfheim: 'Svartalfheim',
  vanaheim: 'Vanaheim',
  jotunheim: 'Jotunheim',
  muspelheim: 'Muspelheim',
  niflheim: 'Niflheim',
  helheim: 'Helheim',
}

export function YggdrasilMap({ reinos, totalFiles }: YggdrasilMapProps) {
  const reinoList = useMemo(() => {
    return Object.entries(reinos).map(([name, data]) => ({
      name,
      displayName: REINO_NAMES[name] || name,
      emoji: REINO_EMOJIS[name] || '📁',
      ...data,
    }))
  }, [reinos])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-500/20 border-green-500/50 text-green-400'
      case 'initialized':
        return 'bg-blue-500/20 border-blue-500/50 text-blue-400'
      case 'empty':
        return 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400'
      case 'not_created':
        return 'bg-gray-500/20 border-gray-500/50 text-gray-400'
      default:
        return 'bg-red-500/20 border-red-500/50 text-red-400'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'active':
        return 'Activo'
      case 'initialized':
        return 'Inicializado'
      case 'empty':
        return 'Vacío'
      case 'not_created':
        return 'No creado'
      default:
        return status
    }
  }

  return (
    <div className="card col-span-2">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-asgard-gold">
          🌳 Yggdrasil - Los 9 Reinos
        </h2>
        <span className="text-sm text-gray-400">
          {totalFiles.toLocaleString()} archivos totales
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {reinoList.map((reino) => (
          <div
            key={reino.name}
            className={`p-3 rounded-lg border ${getStatusColor(reino.status)} transition-all hover:scale-105`}
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">{reino.emoji}</span>
              <span className="font-semibold capitalize">{reino.displayName}</span>
            </div>

            <div className="text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-gray-400">Estado:</span>
                <span className="font-medium">{getStatusLabel(reino.status)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Archivos:</span>
                <span className="font-medium">{reino.file_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Dirs:</span>
                <span className="font-medium">{reino.dir_count}</span>
              </div>
            </div>

            {reino.has_rules && (
              <div className="mt-2 text-xs text-asgard-gold">
                📜 Tiene reglas
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Leyenda */}
      <div className="mt-4 pt-4 border-t border-gray-700 flex flex-wrap gap-4 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <span className="text-gray-400">Activo</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-500"></div>
          <span className="text-gray-400">Inicializado</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
          <span className="text-gray-400">Vacío</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-gray-500"></div>
          <span className="text-gray-400">No creado</span>
        </div>
      </div>
    </div>
  )
}
