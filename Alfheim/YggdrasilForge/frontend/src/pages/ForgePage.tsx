import { useState } from 'react'
import { useGenerate } from '../hooks/useGenerations'
import type { AIProvider } from '../api/client'

const PROVIDERS = [
  { value: 'hunyuan3d', label: 'Hunyuan3D', description: 'Free text/image to 3D' },
  { value: 'rodin', label: 'Hyper3D Rodin', description: 'Free trial text/image to 3D' },
] as const

export function ForgePage() {
  const [prompt, setPrompt] = useState('')
  const [provider, setProvider] = useState<AIProvider>('hunyuan3d')
  const [mode, setMode] = useState<'text' | 'image'>('text')
  const [imageUrl, setImageUrl] = useState('')
  const { generate, status, error } = useGenerate()

  const handleSubmit = async () => {
    if (!prompt && mode === 'text') return
    await generate({
      prompt: mode === 'text' ? prompt : prompt || undefined,
      provider,
      mode,
      imageUrl: mode === 'image' ? imageUrl : undefined,
    })
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-rune-100 mb-1">The Forge</h2>
      <p className="text-rune-400 mb-6">Shape 3D models from words and images</p>

      <div className="forge-card space-y-6">
        {/* Mode Toggle */}
        <div className="flex gap-2">
          <button
            className={`forge-btn ${mode === 'text' ? 'forge-btn-primary' : 'forge-btn-secondary'}`}
            onClick={() => setMode('text')}
          >
            📝 Text to 3D
          </button>
          <button
            className={`forge-btn ${mode === 'image' ? 'forge-btn-primary' : 'forge-btn-secondary'}`}
            onClick={() => setMode('image')}
          >
            🖼️ Image to 3D
          </button>
        </div>

        {/* Provider Selection */}
        <div>
          <label className="block text-sm font-medium text-rune-300 mb-2">AI Provider</label>
          <div className="grid grid-cols-2 gap-3">
            {PROVIDERS.map((p) => (
              <button
                key={p.value}
                onClick={() => setProvider(p.value as AIProvider)}
                className={`p-3 rounded-lg border text-left transition-all ${
                  provider === p.value
                    ? 'border-ember bg-ember/10 text-ember-light'
                    : 'border-rune-700 bg-rune-800 text-rune-300 hover:border-rune-500'
                }`}
              >
                <div className="font-medium">{p.label}</div>
                <div className="text-xs opacity-70">{p.description}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Prompt Input */}
        <div>
          <label className="block text-sm font-medium text-rune-300 mb-1">
            {mode === 'text' ? 'Describe your 3D model' : 'Text prompt (optional)'}
          </label>
          <textarea
            className="forge-input h-24 resize-none"
            placeholder={mode === 'text'
              ? 'A detailed description of what you want to create...'
              : 'Optional text prompt alongside the image...'
            }
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </div>

        {/* Image URL (image mode only) */}
        {mode === 'image' && (
          <div>
            <label className="block text-sm font-medium text-rune-300 mb-1">Image URL</label>
            <input
              type="url"
              className="forge-input"
              placeholder="https://example.com/reference.jpg"
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
            />
          </div>
        )}

        {/* Generate Button */}
        <button
          className="forge-btn-primary w-full py-3 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={handleSubmit}
          disabled={status === 'loading'}
        >
          {status === 'loading' ? '⚒️ Forging...' : '⚒️ Forge 3D Model'}
        </button>

        {/* Error */}
        {error && (
          <div className="p-3 rounded-lg bg-ember/10 border border-ember/30 text-ember text-sm">
            {error}
          </div>
        )}
      </div>
    </div>
  )
}
