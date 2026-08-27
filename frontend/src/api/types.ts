export interface ProductSummary {
  id: number
  slug: string
  name: string
  brand: string
  category: string
  size_label: string | null
  image_url: string | null
  best_price: number | null
  highest_price: number | null
  retailer_count: number
  on_sale: boolean
  concerns: string[]
  key_actives: string[]
}

export interface Ingredient {
  position: number
  inci_name: string
  common_name: string | null
  function: string | null
  is_active: boolean
  is_irritant: boolean
  comedogenic_rating: number | null
  active_group: string | null
  description: string | null
  known: boolean
  is_prominent: boolean
}

export interface RetailerPrice {
  retailer: string
  retailer_slug: string
  url: string
  price: number | null
  was_price: number | null
  currency: string
  in_stock: boolean
  last_scraped_at: string | null
  is_stale: boolean
  is_best: boolean
}

export interface ProductAnalysis {
  active_groups: string[]
  max_comedogenic: number
  has_fragrance: boolean
  has_alcohol: boolean
  has_essential_oil: boolean
  known_count: number
  unknown_count: number
}

export interface ProductDetail extends ProductSummary {
  description: string | null
  upc: string | null
  ingredients: Ingredient[]
  analysis: ProductAnalysis
  prices: RetailerPrice[]
  lowest_90d: number | null
  highest_90d: number | null
}

export interface ProductPage {
  items: ProductSummary[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface PricePoint {
  date: string
  price: number
}

export interface PriceHistory {
  retailer: string
  retailer_slug: string
  points: PricePoint[]
}

export interface Dupe {
  product: ProductSummary
  similarity: number
  shared_actives: string[]
  savings: number | null
}

export interface Concern {
  key: string
  label: string
  description: string | null
}

export interface FilterOptions {
  categories: { key: string; label: string; count: number }[]
  concerns: Concern[]
  brands: { id: number; name: string; slug: string }[]
  price_range: { min: number; max: number }
}

export interface QuizOptions {
  skin_types: { key: string; label: string; description: string }[]
  concerns: Concern[]
  categories: { key: string; label: string }[]
  budgets: { key: number; label: string }[]
}

export interface SkinProfile {
  skin_type: string
  concerns: string[]
  sensitive: boolean
  acne_prone: boolean
  fragrance_free: boolean
  budget_max: number | null
  categories: string[]
}

export interface Recommendation {
  product: ProductSummary
  score: number
  reasons: string[]
  warnings: string[]
}

export interface Conflict {
  id: string
  severity: 'high' | 'medium' | 'low'
  title: string
  explanation: string
  guidance: string
  products: string[]
}

export interface QuizResponse {
  recommendations: Recommendation[]
  routine: { am: ProductSummary[]; pm: ProductSummary[] }
  conflicts: Conflict[]
}
