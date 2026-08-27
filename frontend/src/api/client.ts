import type {
  ChatMessage,
  ChatReply,
  Conflict,
  Dupe,
  FilterOptions,
  PriceHistory,
  ProductDetail,
  ProductPage,
  ProductSummary,
  QuizOptions,
  QuizResponse,
  SkinProfile,
} from './types'

// Vite proxies /api to the FastAPI server in dev, so this stays relative.
const BASE = '/api'

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const body = await response.text().catch(() => '')
    throw new ApiError(response.status, body || response.statusText)
  }
  return response.json() as Promise<T>
}

export interface ProductQuery {
  q?: string
  category?: string
  concern?: string
  brand?: string
  min_price?: number
  max_price?: number
  sort?: string
  page?: number
  page_size?: number
}

function toQueryString(params: object): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  })
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export const api = {
  products: (query: ProductQuery = {}) =>
    request<ProductPage>(`/products${toQueryString(query)}`),

  product: (slug: string) => request<ProductDetail>(`/products/${slug}`),

  priceHistory: (slug: string, days = 90) =>
    request<PriceHistory[]>(`/products/${slug}/prices?days=${days}`),

  dupes: (slug: string) => request<Dupe[]>(`/products/${slug}/dupes`),

  deals: (limit = 8) => request<ProductSummary[]>(`/products/deals?limit=${limit}`),

  filters: () => request<FilterOptions>('/products/filters'),

  quizOptions: () => request<QuizOptions>('/quiz/options'),

  recommend: (profile: SkinProfile & { limit?: number }) =>
    request<QuizResponse>('/quiz/recommend', {
      method: 'POST',
      body: JSON.stringify(profile),
    }),

  chatStatus: () => request<{ enabled: boolean }>('/chat/status'),

  chat: (body: { message: string; history: ChatMessage[]; avoid: string[] }) =>
    request<ChatReply>('/chat', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  conflicts: (productIds: number[]) =>
    request<Conflict[]>('/routine/conflicts', {
      method: 'POST',
      body: JSON.stringify({ product_ids: productIds }),
    }),
}

export { ApiError }
