import {
  Box,
  Button,
  Chip,
  Container,
  Divider,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Pagination,
  Paper,
  Select,
  Skeleton,
  Stack,
  Typography,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import { ProductCard } from '../components/ProductCard'
import { CATEGORY_LABELS } from '../format'

export function Search() {
  const [params, setParams] = useSearchParams()

  const q = params.get('q') ?? ''
  const category = params.get('category') ?? ''
  const concern = params.get('concern') ?? ''
  const brand = params.get('brand') ?? ''
  const sort = params.get('sort') ?? 'relevance'
  const page = Number(params.get('page') ?? 1)

  const update = (key: string, value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    // Any filter change invalidates the current page number.
    if (key !== 'page') next.delete('page')
    setParams(next)
  }

  const { data: filters } = useQuery({ queryKey: ['filters'], queryFn: api.filters })
  const { data, isLoading } = useQuery({
    queryKey: ['products', q, category, concern, brand, sort, page],
    queryFn: () =>
      api.products({
        q: q || undefined,
        category: category || undefined,
        concern: concern || undefined,
        brand: brand || undefined,
        sort,
        page,
        page_size: 24,
      }),
  })

  const activeFilters = [
    category && { key: 'category', label: CATEGORY_LABELS[category] ?? category },
    concern && {
      key: 'concern',
      label: filters?.concerns.find((c) => c.key === concern)?.label ?? concern,
    },
    brand && {
      key: 'brand',
      label: filters?.brands.find((b) => b.slug === brand)?.name ?? brand,
    },
  ].filter(Boolean) as { key: string; label: string }[]

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 4, md: 6 } }}>
      <Grid container spacing={4}>
        <Grid item xs={12} md={3}>
          <Paper variant="outlined" sx={{ p: 2.5, position: { md: 'sticky' }, top: 88 }}>
            <Typography variant="h5" sx={{ mb: 2 }}>
              Filters
            </Typography>

            <Stack spacing={2.5}>
              <FormControl fullWidth size="small">
                <InputLabel>Category</InputLabel>
                <Select
                  label="Category"
                  value={category}
                  onChange={(event) => update('category', event.target.value)}
                >
                  <MenuItem value="">All categories</MenuItem>
                  {filters?.categories.map((item) => (
                    <MenuItem key={item.key} value={item.key}>
                      {CATEGORY_LABELS[item.key] ?? item.label} ({item.count})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth size="small">
                <InputLabel>Skin concern</InputLabel>
                <Select
                  label="Skin concern"
                  value={concern}
                  onChange={(event) => update('concern', event.target.value)}
                >
                  <MenuItem value="">Any concern</MenuItem>
                  {filters?.concerns.map((item) => (
                    <MenuItem key={item.key} value={item.key}>
                      {item.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth size="small">
                <InputLabel>Brand</InputLabel>
                <Select
                  label="Brand"
                  value={brand}
                  onChange={(event) => update('brand', event.target.value)}
                >
                  <MenuItem value="">All brands</MenuItem>
                  {filters?.brands.map((item) => (
                    <MenuItem key={item.slug} value={item.slug}>
                      {item.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Divider />

              <FormControl fullWidth size="small">
                <InputLabel>Sort by</InputLabel>
                <Select
                  label="Sort by"
                  value={sort}
                  onChange={(event) => update('sort', event.target.value)}
                >
                  <MenuItem value="relevance">Relevance</MenuItem>
                  <MenuItem value="price_asc">Price: low to high</MenuItem>
                  <MenuItem value="price_desc">Price: high to low</MenuItem>
                  <MenuItem value="name">Name</MenuItem>
                </Select>
              </FormControl>

              {activeFilters.length > 0 && (
                <Button size="small" onClick={() => setParams(q ? { q } : {})}>
                  Clear filters
                </Button>
              )}
            </Stack>
          </Paper>
        </Grid>

        <Grid item xs={12} md={9}>
          <Stack spacing={0.5} sx={{ mb: 3 }}>
            <Typography variant="h2">
              {q ? `Results for "${q}"` : 'All products'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {isLoading ? 'Searching…' : `${data?.total ?? 0} products`}
            </Typography>
            {activeFilters.length > 0 && (
              <Stack direction="row" spacing={1} sx={{ pt: 1 }} flexWrap="wrap" useFlexGap>
                {activeFilters.map((filter) => (
                  <Chip
                    key={filter.key}
                    label={filter.label}
                    size="small"
                    onDelete={() => update(filter.key, '')}
                  />
                ))}
              </Stack>
            )}
          </Stack>

          <Grid container spacing={2.5}>
            {isLoading &&
              Array.from({ length: 6 }).map((_, index) => (
                <Grid item xs={12} sm={6} lg={4} key={index}>
                  <Skeleton variant="rounded" height={210} />
                </Grid>
              ))}

            {data?.items.map((product) => (
              <Grid item xs={12} sm={6} lg={4} key={product.id}>
                <ProductCard product={product} />
              </Grid>
            ))}
          </Grid>

          {!isLoading && data && data.items.length === 0 && (
            <Paper variant="outlined" sx={{ p: 5, textAlign: 'center' }}>
              <Typography variant="h5" sx={{ mb: 1 }}>
                Nothing matched
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Try a broader search or clear a filter.
              </Typography>
            </Paper>
          )}

          {data && data.pages > 1 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', pt: 4 }}>
              <Pagination
                count={data.pages}
                page={page}
                onChange={(_, value) => update('page', String(value))}
                color="primary"
              />
            </Box>
          )}
        </Grid>
      </Grid>
    </Container>
  )
}
