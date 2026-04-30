import { useEffect, useState } from 'react'

interface AutoModeTask {
  task_id: string
  title: string
  status: string
  created_at?: string
}

export function AutoModeTasks() {
  const [tasks, setTasks] = useState<AutoModeTask[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const res = await fetch('/api/asgard/automode/tasks')
        if (res.ok) {
          const data = await res.json()
          setTasks(data.active_tasks || [])
        }
      } catch (err) {
        console.error('Failed to fetch automode tasks:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchTasks()
    const interval = setInterval(fetchTasks, 5000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="card">
        <h2 className="text-xl font-bold text-asgard-gold mb-4">🔥 Auto-Mode</h2>
        <div className="loading text-gray-400">Cargando...</div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-asgard-gold">
          🔥 Auto-Mode Tasks
        </h2>
        <span className="text-sm text-gray-400">
          {tasks.length} activas
        </span>
      </div>

      {tasks.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <div className="text-4xl mb-2">🔥</div>
          <p>No hay tareas autónomas activas</p>
          <p className="text-xs mt-2">
            Usa <code className="bg-gray-800 px-2 py-1 rounded">/automode</code> en Discord
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => (
            <div
              key={task.task_id}
              className="p-3 rounded-lg bg-gray-800/50 border border-gray-700 hover:border-orange-500/50 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-medium text-orange-400">{task.title}</div>
                  <div className="text-xs text-gray-500 font-mono">{task.task_id}</div>
                </div>
                <span className="badge badge-active text-xs">{task.status}</span>
              </div>

              {task.created_at && (
                <div className="mt-2 text-xs text-gray-500">
                  Creada: {new Date(task.created_at).toLocaleString()}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Info */}
      <div className="mt-4 pt-4 border-t border-gray-700 text-xs text-gray-500">
        <p>
          Auto-Mode ejecuta tareas de forma autónoma con checkpointing y
          reportes automáticos.
        </p>
      </div>
    </div>
  )
}
