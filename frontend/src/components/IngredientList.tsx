import ScienceIcon from '@mui/icons-material/Science'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import {
  Alert,
  Box,
  Chip,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import type { Ingredient, ProductAnalysis } from '../api/types'
import { ACTIVE_GROUP_LABELS } from '../format'

interface Props {
  ingredients: Ingredient[]
  analysis: ProductAnalysis
}

export function IngredientList({ ingredients, analysis }: Props) {
  if (ingredients.length === 0) {
    return (
      <Alert severity="info" variant="outlined">
        No ingredient list available for this product yet.
      </Alert>
    )
  }

  const flags: string[] = []
  if (analysis.has_fragrance) flags.push('Contains fragrance')
  if (analysis.has_alcohol) flags.push('Contains denatured alcohol')
  if (analysis.has_essential_oil) flags.push('Contains essential oils')
  if (analysis.max_comedogenic >= 3) {
    flags.push(`Comedogenic ingredient rated ${analysis.max_comedogenic}/5`)
  }

  return (
    <Stack spacing={2}>
      {analysis.active_groups.length > 0 && (
        <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap alignItems="center">
          <ScienceIcon sx={{ fontSize: 18, color: 'primary.main' }} />
          <Typography variant="body2" color="text.secondary" sx={{ mr: 0.5 }}>
            Actives:
          </Typography>
          {analysis.active_groups.map((group) => (
            <Chip
              key={group}
              label={ACTIVE_GROUP_LABELS[group] ?? group}
              size="small"
              color="primary"
              variant="outlined"
            />
          ))}
        </Stack>
      )}

      {flags.length > 0 && (
        <Alert
          severity="warning"
          variant="outlined"
          icon={<WarningAmberIcon fontSize="inherit" />}
        >
          {flags.join(' · ')}
        </Alert>
      )}

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
          Listed in INCI order — ingredients near the top are present at the highest
          concentrations.
        </Typography>

        <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
          {ingredients.map((ingredient) => {
            const label = ingredient.common_name ?? ingredient.inci_name
            const detail = [
              ingredient.function,
              ingredient.comedogenic_rating
                ? `comedogenic ${ingredient.comedogenic_rating}/5`
                : null,
              ingredient.description,
            ]
              .filter(Boolean)
              .join(' — ')

            return (
              <Tooltip key={`${ingredient.position}-${ingredient.inci_name}`} title={detail || ''}>
                <Chip
                  label={label}
                  size="small"
                  variant={ingredient.is_active ? 'filled' : 'outlined'}
                  color={
                    ingredient.is_active
                      ? 'primary'
                      : ingredient.is_irritant
                        ? 'warning'
                        : 'default'
                  }
                  sx={{
                    opacity: ingredient.is_prominent || ingredient.is_active ? 1 : 0.72,
                    borderStyle: ingredient.known ? 'solid' : 'dashed',
                  }}
                />
              </Tooltip>
            )
          })}
        </Stack>

        {analysis.unknown_count > 0 && (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
            {analysis.unknown_count} ingredient{analysis.unknown_count === 1 ? '' : 's'} not in our
            database (shown with a dashed border).
          </Typography>
        )}
      </Paper>

      <Box>
        <Typography variant="caption" color="text.secondary">
          Filled chips are actives · amber are common irritants · hover any ingredient for
          detail.
        </Typography>
      </Box>
    </Stack>
  )
}
