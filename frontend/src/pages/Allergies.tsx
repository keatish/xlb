import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline'
import {
  Alert,
  AlertTitle,
  Button,
  Container,
  Paper,
  Stack,
  Typography,
} from '@mui/material'
import { Link as RouterLink } from 'react-router-dom'
import { AllergyPicker } from '../components/AllergyPicker'
import { emptyProfile, useSkinProfile } from '../hooks/useSkinProfile'

/**
 * A standing home for the avoid-list, reachable from every page.
 *
 * The same input also sits inside the quiz, but an allergy is not a one-off
 * questionnaire answer - it is a permanent fact about someone that they need to
 * be able to set, check and correct without retaking a four-step quiz.
 */
export function Allergies() {
  const { profile, setProfile } = useSkinProfile()
  const avoiding = profile?.avoid_ingredients ?? []

  const clear = () => setProfile({ ...(profile ?? emptyProfile), avoid_ingredients: [] })

  return (
    <Container maxWidth="md" sx={{ py: 6 }}>
      <Typography variant="h1" sx={{ fontSize: { xs: '2rem', md: '2.4rem' }, mb: 1 }}>
        Ingredients you avoid
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Tell us what you react to and we will check every ingredient list against it — on product
        pages, in search results, and when recommending a routine.
      </Typography>

      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        <AllergyPicker autoFocus label="Allergies and ingredients to avoid" />

      </Paper>

      {avoiding.length > 0 ? (
        <Alert severity="success" variant="outlined" sx={{ mb: 3 }}>
          <AlertTitle>Screening is on</AlertTitle>
          We are checking every product against {avoiding.length} entr
          {avoiding.length === 1 ? 'y' : 'ies'}. Products containing them are flagged on the
          product page, badged in search, and left out of quiz recommendations entirely.
          <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
            <Button component={RouterLink} to="/search" size="small" variant="outlined">
              Browse screened products
            </Button>
            <Button size="small" color="inherit" onClick={clear}>
              Clear list
            </Button>
          </Stack>
        </Alert>
      ) : (
        <Alert severity="info" variant="outlined" icon={<ErrorOutlineIcon fontSize="inherit" />} sx={{ mb: 3 }}>
          Nothing listed yet, so nothing is being screened.
        </Alert>
      )}

      <Typography variant="caption" color="text.secondary">
        Choosing a group catches the whole family: “fragrance” also finds Linalool, Limonene and
        the rest of the 26 components the EU requires to be declared by name — the ones that
        appear on labels that never say “Parfum”. Screening compares your list against published
        ingredient lists only; it cannot account for reformulation, cross-contamination or “may
        contain” traces, so check the pack if you react severely.
      </Typography>
    </Container>
  )
}
