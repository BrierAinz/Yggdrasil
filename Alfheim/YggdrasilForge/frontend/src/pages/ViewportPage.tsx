import { useState, useEffect } from 'react'
import { api } from '../api/client'

export function ViewportPage() {
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null)
  const [sceneInfo, setSceneInfo] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchScene = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getScene()
      setSceneInfo(data.scene)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch scene')
    } finally {
      setLoading(false)
    }
  }

  const fetchScreenshot = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getScreenshot()
      setScreenshotUrl(data.screenshot)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to capture screenshot')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchScene()
  }, [])

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h2 className="text-2xl font-bold text-rune-100 mb-1">Viewport</h2>
      <p className="text-rune-400 mb-6">Blender scene info & viewport preview</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Scene Info */}
        <div className="forge-card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium text-rune-100">Scene Info</h3>
            <button className="forge-btn-secondary text-xs" onClick={fetchScene}>
              🔄 Refresh
            </button>
          </div>

          {loading && !sceneInfo && <div className="text-rune-400">Loading...</div>}
          {error && <div className="text-ember text-sm">{error}</div>}

          {sceneInfo && (
            <pre className="text-xs text-rune-300 bg-rune-950 rounded-lg p-3 overflow-auto max-h-80 font-mono">
              {JSON.stringify(sceneInfo, null, 2)}
            </pre>
          )}

          {!sceneInfo && !loading && !error && (
            <div className="text-rune-500 text-center py-8">
              Blender not connected. Open Blender with MCP addon.
            </div>
          )}
        </div>

        {/* Viewport Screenshot */}
        <div className="forge-card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium text-rune-100">Viewport</h3>
            <button className="forge-btn-fjord text-xs" onClick={fetchScreenshot} disabled={loading}>
              📸 Capture
            </button>
          </div>

          <div className="aspect-video bg-rune-950 rounded-lg overflow-hidden flex items-center justify-center">
            {screenshotUrl ? (
              <img src={screenshotUrl} alt="Blender Viewport" className="w-full h-full object-contain" />
            ) : (
              <div className="text-rune-600 text-center">
                <div className="text-4xl mb-2">🖥️</div>
                <p className="text-sm">Click "Capture" to take a viewport screenshot</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
