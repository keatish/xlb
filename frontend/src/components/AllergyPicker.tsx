import { Autocomplete, Box, Chip, Stack, TextField, Tooltip, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { emptyProfile, useSkinProfile } from '../hooks/useSkinProfile'

interface Props {
  /**
   * Controlled mode, for the quiz: it holds a draft profile and only commits on
   * finish. Left undefined, the picker reads and writes the saved profile
   * directly, which is what the front page and the allergies page want - there
   * is no "save" step to wait for.
   */
  value?: string[]
  onChange?: (next: string[]) => void
  /** Hide the group chips, for tighter placements. */
  compact?: boolean
  autoFocus?: boolean
  label?: string
}

export function AllergyPicker({ value, onChange, compact = false, autoFocus, label }: Props) {
  const { profile, setProfile } = useSkinProfile()
  const { data: groups } = useQuery({ queryKey: ['allergens'], queryFn: api.allergens })

  const controlled = value !== undefined
  const avoiding = controlled ? value : (profile?.avoid_ingredients ?? [])

  const save = (next: string[]) => {
    const clean = next.map((entry) => entry.trim()).filter(Boolean)
    if (controlled) {
      onChange?.(clean)
    } else {
      setProfile({ ...(profile ?? emptyProfile), avoid_ingredients: clean })
    }
  }

  const options = (groups ?? []).map((group) => group.label)
  const notes = new Map(
    (groups ?? []).map((group) => [
      group.label,
      `${group.members.length} ingredient${group.members.length === 1 ? '' : 's'} · ${group.product_matches} product${group.product_matches === 1 ? '' : 's'} in our catalogue · ${group.note ?? ''}`,
    ]),
  )

  return (
    <Stack spacing={compact ? 1.5 : 3}>
      <Autocomplete
        multiple
        freeSolo
        options={options}
        value={avoiding}
        onChange={(_, next) => save(next)}
        ChipProps={{ color: 'error', variant: 'outlined', size: 'small' }}
        renderOption={(props, option) => {
          const { key, ...rest } = props as typeof props & { key: string }
          return (
            <Box component="li" key={key} {...rest}>
              <Stack spacing={0.25}>
                <Typography variant="body2">{option}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {notes.get(option)}
                </Typography>
              </Stack>
            </Box>
          )
        }}
        renderInput={(params) => (
          <TextField
            {...params}
            autoFocus={autoFocus}
            label={label}
            placeholder={avoiding.length ? 'Add another' : 'e.g. fragrance, lanolin, nut oils'}
            helperText="Pick a group or type any ingredient, then press Enter."
          />
        )}
      />

      {!compact && options.length > 0 && (
        <Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            Common groups — each covers a whole family of ingredients. The number is how many
            products we currently list contain it:
          </Typography>
          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
            {(groups ?? []).map((group) => {
              const active = avoiding.includes(group.label)
              return (
                <Tooltip
                  key={group.key}
                  title={
                    group.product_matches === 0
                      ? `${group.members.length} ingredients — none appear in any product we currently list`
                      : `${group.members.length} ingredients · matches ${group.product_matches} product${group.product_matches === 1 ? '' : 's'} we list`
                  }
                >
                  <Chip
                    label={`${group.label} · ${group.product_matches}`}
                    size="small"
                    color={active ? 'error' : 'default'}
                    variant={active ? 'filled' : 'outlined'}
                    // Dimmed rather than hidden: an allergy that matches nothing
                    // today still needs recording, so it applies as the
                    // catalogue grows.
                    sx={{ opacity: group.product_matches === 0 && !active ? 0.5 : 1 }}
                    onClick={() =>
                      save(
                        active
                          ? avoiding.filter((entry) => entry !== group.label)
                          : [...avoiding, group.label],
                      )
                    }
                  />
                </Tooltip>
              )
            })}
          </Stack>
        </Box>
      )}
    </Stack>
  )
}
