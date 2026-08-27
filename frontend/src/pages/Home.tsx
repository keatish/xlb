import SearchIcon from '@mui/icons-material/Search'
import {
  Box,
  Button,
  Chip,
  Container,
  Grid,
  InputAdornment,
  Skeleton,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link as RouterLink, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { ProductCard } from '../components/ProductCard'
import { CATEGORY_LABELS } from '../format'
import { useSkinProfile } from '../hooks/useSkinProfile'

export function Home() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const { hasProfile } = useSkinProfile()

  const { data: filters } = useQuery({ queryKey: ['filters'], queryFn: api.filters })
  const { data: deals, isLoading } = useQuery({
    queryKey: ['deals'],
    queryFn: () => api.deals(8),
  })

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    navigate(`/search?q=${encodeURIComponent(query.trim())}`)
  }

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 5, md: 8 } }}>
      <Stack spacing={2.5} sx={{ maxWidth: 720, mb: 7 }}>
        <Typography variant="h1">
          Know what is in it.
          <Box component="span" sx={{ color: 'primary.main' }}> Pay less for it.</Box>
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ fontSize: '1.1rem' }}>
          Compare the same skincare product across retailers, read the full ingredient
          list with the actives and irritants called out, and get recommendations built
          around your skin — not around what is on offer this week.
        </Typography>

        <Box component="form" onSubmit={submit}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
            <TextField
              fullWidth
              placeholder="Search a product, brand or ingredient"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              }}
            />
            <Button type="submit" variant="contained" size="large" sx={{ px: 4 }}>
              Search
            </Button>
          </Stack>
        </Box>

        <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" useFlexGap>
          <Button component={RouterLink} to="/quiz" variant="outlined" size="large">
            {hasProfile ? 'Retake the skin quiz' : 'Take the skin quiz'}
          </Button>
          {hasProfile && (
            <Button component={RouterLink} to="/results" size="large">
              See my recommendations
            </Button>
          )}
        </Stack>
      </Stack>

      {filters && filters.categories.length > 0 && (
        <Box sx={{ mb: 7 }}>
          <Typography variant="h4" sx={{ mb: 2 }}>
            Browse by category
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {filters.categories.map((category) => (
              <Chip
                key={category.key}
                component={RouterLink}
                to={`/search?category=${category.key}`}
                clickable
                label={`${CATEGORY_LABELS[category.key] ?? category.label} (${category.count})`}
                sx={{ px: 0.5 }}
              />
            ))}
          </Stack>
        </Box>
      )}

      <Box>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          justifyContent="space-between"
          alignItems={{ sm: 'baseline' }}
          spacing={0.5}
          sx={{ mb: 2.5 }}
        >
          <Typography variant="h4">Biggest price gaps</Typography>
          <Typography variant="body2" color="text.secondary">
            Same product, very different prices depending on where you buy
          </Typography>
        </Stack>

        <Grid container spacing={2.5}>
          {isLoading &&
            Array.from({ length: 8 }).map((_, index) => (
              <Grid item xs={12} sm={6} md={3} key={index}>
                <Skeleton variant="rounded" height={210} />
              </Grid>
            ))}

          {deals?.map((product) => (
            <Grid item xs={12} sm={6} md={3} key={product.id}>
              <ProductCard product={product} />
            </Grid>
          ))}
        </Grid>
      </Box>
    </Container>
  )
}
