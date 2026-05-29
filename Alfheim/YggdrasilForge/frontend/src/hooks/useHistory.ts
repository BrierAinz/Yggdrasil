import { useState, useEffect } from 'react'
import { api, type Generation } from '../api/client'

export function useGenerations() {
  const [generations, setGenerations] = useState<Generation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await api.listGenerations({ limit: 50 })
        setGenerations(data.items)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load generations')
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [])

  return { generations, loading, error }
}
