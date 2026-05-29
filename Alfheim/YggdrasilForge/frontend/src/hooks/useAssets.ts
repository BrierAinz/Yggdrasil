import { useState, useCallback } from 'react'
import { api, type AssetSearchResult } from '../api/client'

interface SearchParams {
  source: 'polyhaven' | 'sketchfab'
  query: string
  assetType: string
  categories?: string
}

export function useSearchAssets() {
  const [results, setResults] = useState<AssetSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const search = useCallback(async (params: SearchParams) => {
    setLoading(true)
    setError(null)

    try {
      let data: { results: unknown }

      if (params.source === 'sketchfab') {
        data = await api.searchSketchfab({
          query: params.query,
          categories: params.categories || undefined,
          count: 20,
        })
      } else {
        data = await api.searchPolyhaven({
          asset_type: params.assetType,
          categories: params.categories || undefined,
        })
      }

      // Parse results — the exact shape depends on MCP response
      const raw = data.results
      if (typeof raw === 'object' && raw !== null) {
        // Try to normalize MCP results into our format
        const items = Array.isArray(raw) ? raw : [raw]
        setResults(items.map((item: unknown) => {
          const obj = item as Record<string, unknown>
          return {
            name: String(obj.name || obj.title || 'Unknown'),
            description: String(obj.description || obj.thumbnail || ''),
            thumbnail: String(obj.thumbnail || obj.image || ''),
            source: params.source,
            vertex_count: String(obj.vertex_count || obj.vertexCount || ''),
          } satisfies AssetSearchResult
        }))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }, [])

  return { search, results, loading, error }
}
