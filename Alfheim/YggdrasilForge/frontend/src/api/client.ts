/** YggdrasilForge API client */

export type AIProvider = 'hunyuan3d' | 'rodin' | 'polyhaven' | 'sketchfab' | 'blender_local'

const API_BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// ── Generation API ──────────────────────────────────────────────────────

export interface Generation {
  id: string
  type: string
  provider: string
  status: string
  prompt?: string | null
  input_image?: string | null
  result_object?: string | null
  result_path?: string | null
  error?: string | null
  provider_job_id?: string | null
  provider_data?: Record<string, unknown> | null
  created_at: string
  completed_at?: string | null
}

export interface TextTo3DPayload {
  prompt: string
  provider: AIProvider
  bbox_condition?: number[]
}

export interface ImageTo3DPayload {
  image_url?: string
  prompt?: string
  provider: AIProvider
  bbox_condition?: number[]
}

// ── Asset search result ─────────────────────────────────────────────────

export interface AssetSearchResult {
  name: string
  description?: string
  thumbnail?: string
  source: string
  vertex_count?: string
}

// ── API Object ──────────────────────────────────────────────────────────

export const api = {
  // Health
  health: () => request<Record<string, unknown>>('/health'),

  // Generation
  generateTextTo3D: (payload: TextTo3DPayload) =>
    request<Generation>('/generation/text-to-3d', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  generateImageTo3D: (payload: ImageTo3DPayload) =>
    request<Generation>('/generation/image-to-3d', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getGeneration: (id: string) =>
    request<Generation>(`/generation/${id}`),

  listGenerations: (params?: { status?: string; provider?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams()
    if (params?.status) qs.set('status', params.status)
    if (params?.provider) qs.set('provider', params.provider)
    if (params?.limit) qs.set('limit', String(params.limit))
    if (params?.offset) qs.set('offset', String(params.offset))
    const query = qs.toString() ? `?${qs.toString()}` : ''
    return request<{ items: Generation[]; total: number }>(`/generation/${query}`)
  },

  // Assets — PolyHaven
  polyhavenStatus: () => request<Record<string, unknown>>('/assets/polyhaven/status'),
  polyhavenCategories: (type = 'hdris') => request<Record<string, unknown>>(`/assets/polyhaven/categories?asset_type=${type}`),
  searchPolyhaven: (data: { asset_type?: string; categories?: string }) =>
    request<{ results: unknown }>('/assets/polyhaven/search', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  downloadPolyhaven: (data: { asset_id: string; asset_type: string; resolution?: string }) =>
    request<Record<string, unknown>>('/assets/polyhaven/download', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Assets — Sketchfab
  sketchfabStatus: () => request<Record<string, unknown>>('/assets/sketchfab/status'),
  searchSketchfab: (data: { query: string; categories?: string; count?: number }) =>
    request<{ results: unknown }>('/assets/sketchfab/search', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  downloadSketchfab: (data: { uid: string; target_size?: number }) =>
    request<Record<string, unknown>>('/assets/sketchfab/download', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  previewSketchfab: (uid: string) => request<Record<string, unknown>>(`/assets/sketchfab/preview/${uid}`),

  // Asset history
  listAssets: (params?: Record<string, string>) => {
    const qs = new URLSearchParams(params).toString()
    return request<{ items: unknown[]; total: number }>(`/assets/history${qs ? `?${qs}` : ''}`)
  },

  // Blender
  blenderStatus: () => request<Record<string, unknown>>('/blender/status'),
  getScene: () => request<Record<string, unknown>>('/blender/scene'),
  getObject: (name: string) => request<Record<string, unknown>>(`/blender/object/${name}`),
  getScreenshot: (maxSize = 1000) => request<Record<string, unknown>>(`/blender/screenshot?max_size=${maxSize}`),
  executeCode: (code: string) =>
    request<Record<string, unknown>>('/blender/execute', {
      method: 'POST',
      body: JSON.stringify({ code }),
    }),

  // Render
  render: (data: { engine?: string; resolution_x?: number; resolution_y?: number; output_path?: string }) =>
    request<Record<string, unknown>>('/render/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}
