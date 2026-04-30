import { useEffect, useRef, useState } from 'react'

interface LogEntry {
  timestamp: string
  level: string
  source: string
  message: string
}

export function LiveLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [connected, setConnected] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const logContainerRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    // Connect to WebSocket
    const connectWebSocket = () => {
      const ws = new WebSocket('ws://localhost:8000/api/asgard/ws/logs')
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        console.log('[LiveLogs] WebSocket connected')
      }

      ws.onmessage = (event) => {
        try {
          const log = JSON.parse(event.data)
          setLogs((prev) => {
            const newLogs = [...prev, log]
            // Keep only last 100 logs
            return newLogs.slice(-100)
          })
        } catch (err) {
          console.error('Failed to parse log:', err)
        }
      }

      ws.onclose = () => {
        setConnected(false)
        console.log('[LiveLogs] WebSocket disconnected')
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000)
      }

      ws.onerror = (error) => {
        console.error('[LiveLogs] WebSocket error:', error)
        setConnected(false)
      }
    }

    connectWebSocket()

    // Also fetch recent logs via HTTP
    const fetchRecentLogs = async () => {
      try {
        const res = await fetch('/api/asgard/logs/recent?limit=20')
        if (res.ok) {
          const data = await res.json()
          if (data.logs && data.logs.length > 0) {
            setLogs((prev) => {
              const combined = [...data.logs, ...prev]
              return combined.slice(-100)
            })
          }
        }
      } catch (err) {
        console.error('Failed to fetch recent logs:', err)
      }
    }

    fetchRecentLogs()

    return () => {
      wsRef.current?.close()
    }
  }, [])

  // Auto-scroll
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs, autoScroll])

  const getLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return 'text-red-400'
      case 'WARN':
      case 'WARNING':
        return 'text-yellow-400'
      case 'INFO':
        return 'text-blue-400'
      case 'DEBUG':
        return 'text-gray-500'
      default:
        return 'text-gray-400'
    }
  }

  const clearLogs = () => {
    setLogs([])
  }

  return (
    <div className="card col-span-2">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-asgard-gold">
          📜 Logs en Vivo
        </h2>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded border-gray-600"
            />
            Auto-scroll
          </label>
          <button
            onClick={clearLogs}
            className="text-xs px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
          >
            Clear
          </button>
          <div
            className={`w-2 h-2 rounded-full ${
              connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
            }`}
            title={connected ? 'Connected' : 'Disconnected'}
          />
        </div>
      </div>

      <div
        ref={logContainerRef}
        className="h-64 overflow-y-auto font-mono text-xs bg-gray-900 rounded-lg p-3"
      >
        {logs.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            Esperando logs...
          </div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="mb-1 hover:bg-gray-800/50">
              <span className="text-gray-500">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>{' '}
              <span className={getLevelColor(log.level)}>[{log.level}]</span>{' '}
              <span className="text-gray-600">{log.source}:</span>{' '}
              <span className="text-gray-300">{log.message}</span>
            </div>
          ))
        )}
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
        <span>{logs.length} entradas</span>
        <span>{connected ? 'Conectado' : 'Desconectado'}</span>
      </div>
    </div>
  )
}
