import { useState, useCallback } from 'react'
import { api, type Generation, type AIProvider } from '../api/client'

interface GenerateParams {
  prompt: string
  provider: AIProvider
  mode: 'text' | 'image'
  imageUrl?: string
  bboxCondition?: number[]
}

export function useGenerate() {
  const [currentGeneration, setCurrentGeneration] = useState<Generation | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  const generate = useCallback(async (params: GenerateParams) => {
    setStatus('loading')
    setError(null)

    try {
      let gen: Generation
      if (params.mode === 'text') {
        gen = await api.generateTextTo3D({
          prompt: params.prompt,
          provider: params.provider,
          bbox_condition: params.bboxCondition,
        })
      } else {
        gen = await api.generateImageTo3D({
          image_url: params.imageUrl,
          prompt: params.prompt || undefined,
          provider: params.provider,
          bbox_condition: params.bboxCondition,
        })
      }

      setCurrentGeneration(gen)
      setStatus('success')

      // Poll for updates
      if (gen.id && (gen.status === 'queued' || gen.status === 'processing')) {
        pollGeneration(gen.id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
      setStatus('error')
    }
  }, [])

  const pollGeneration = async (genId: string) => {
    const maxAttempts = 120 // 10 minutes at 5s intervals
    let attempts = 0

    const poll = async () => {
      try {
        const gen = await api.getGeneration(genId)
        setCurrentGeneration(gen)

        if (gen.status === 'completed' || gen.status === 'failed') {
          return
        }

        attempts++
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000)
        }
      } catch {
        // Don't fail on poll errors, just stop polling
      }
    }

    setTimeout(poll, 5000)
  }

  return { generate, currentGeneration, status, error }
}
