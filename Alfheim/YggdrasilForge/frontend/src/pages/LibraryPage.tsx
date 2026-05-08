import { useState } from 'react'
import { useSearchAssets } from '../hooks/useAssets'

type AssetSource = 'polyhaven' | 'sketchfab'
type AssetType = 'models' | 'textures' | 'hdris'

export function LibraryPage() {
  const [source, setSource] = useState<AssetSource>('sketchfab')
  const [query, setQuery] = useState('')
  const [assetType, setAssetType] = useState<AssetType>('models')
  const [categories, setCategories] = useState('')
  const { search, results, loading, error } = useSearchAssets()

  const handleSearch = () => {
    if (!query.trim()) return
    search({ source, query, assetType, categories })
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h2 className="text-2xl font-bold text-rune-100 mb-1">Asset Library</h2>
      <p className="text-rune-400 mb-6">Browse PolyHaven & Sketchfab free assets</p>

      {/* Search Bar */}
      <div className="forge-card mb-6">
        <div className="flex flex-wrap gap-3 items-end">
          {/* Source toggle */}
          <div>
            <label className="block text-xs font-medium text-rune-400 mb-1">Source</label>
            <div className="flex gap-1">
              <button
                className={`px-3 py-1.5 rounded text-sm ${source === 'sketchfab' ? 'bg-fjord text-white' : 'bg-rune-800 text-rune-300'}`}
                onClick={() => setSource('sketchfab')}
              >
                Sketchfab
              </button>
              <button
                className={`px-3 py-1.5 rounded text-sm ${source === 'polyhaven' ? 'bg-yggdrasil-green text-white' : 'bg-rune-800 text-rune-300'}`}
                onClick={() => setSource('polyhaven')}
              >
                PolyHaven
              </button>
            </div>
          </div>

          {/* Asset Type */}
          <div>
            <label className="block text-xs font-medium text-rune-400 mb-1">Type</label>
            <select
              className="forge-select text-sm"
              value={assetType}
              onChange={(e) => setAssetType(e.target.value as AssetType)}
            >
              <option value="models">Models</option>
              <option value="textures">Textures</option>
              <option value="hdris">HDRIs</option>
            </select>
          </div>

          {/* Query */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs font-medium text-rune-400 mb-1">Search</label>
            <input
              className="forge-input text-sm"
              placeholder="Search assets..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>

          {/* Categories (optional) */}
          <div className="w-40">
            <label className="block text-xs font-medium text-rune-400 mb-1">Categories</label>
            <input
              className="forge-input text-sm"
              placeholder="e.g. furniture, nature"
              value={categories}
              onChange={(e) => setCategories(e.target.value)}
            />
          </div>

          <button
            className="forge-btn-fjord"
            onClick={handleSearch}
            disabled={loading}
          >
            {loading ? 'Searching...' : '🔍 Search'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 mb-4 rounded-lg bg-ember/10 border border-ember/30 text-ember text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {results.map((item, i) => (
          <div key={i} className="forge-card hover:border-rune-500 transition-colors">
            {/* Thumbnail */}
            {item.thumbnail && (
              <div className="aspect-video bg-rune-800 rounded-lg mb-3 overflow-hidden">
                <img
                  src={item.thumbnail}
                  alt={item.name}
                  className="w-full h-full object-cover"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                />
              </div>
            )}
            <h3 className="font-medium text-rune-100 truncate">{item.name}</h3>
            <p className="text-xs text-rune-400 mt-1 line-clamp-2">{item.description}</p>
            <div className="flex items-center gap-2 mt-2">
              <span className="forge-badge forge-badge-queued">{item.source}</span>
              {item.vertex_count && (
                <span className="text-xs text-rune-500">{item.vertex_count} verts</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {results.length === 0 && !loading && !error && (
        <div className="text-center text-rune-500 py-16">
          <div className="text-4xl mb-2">📚</div>
          <p>Search for assets to get started</p>
        </div>
      )}
    </div>
  )
}
