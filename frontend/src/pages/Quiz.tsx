import {
  Box,
  Button,
  Card,
  CardActionArea,
  Chip,
  Container,
  FormControlLabel,
  Grid,
  Paper,
  Stack,
  Step,
  StepLabel,
  Stepper,
  Switch,
  Typography,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { SkinProfile } from '../api/types'
import { emptyProfile, useSkinProfile } from '../hooks/useSkinProfile'

const STEPS = ['Skin type', 'Concerns', 'Sensitivities', 'Budget']

export function Quiz() {
  const navigate = useNavigate()
  const { profile: saved, setProfile } = useSkinProfile()
  const [step, setStep] = useState(0)
  const [draft, setDraft] = useState<SkinProfile>(saved ?? emptyProfile)

  const { data: options } = useQuery({ queryKey: ['quiz-options'], queryFn: api.quizOptions })

  const update = (patch: Partial<SkinProfile>) => setDraft((prev) => ({ ...prev, ...patch }))

  const toggleConcern = (key: string) =>
    update({
      concerns: draft.concerns.includes(key)
        ? draft.concerns.filter((c) => c !== key)
        : [...draft.concerns, key],
    })

  const finish = () => {
    setProfile(draft)
    navigate('/results')
  }

  // Only the concerns step has a real requirement - everything else has a
  // sensible default, and blocking on defaults just adds friction.
  const canAdvance = step !== 1 || draft.concerns.length > 0

  return (
    <Container maxWidth="md" sx={{ py: { xs: 4, md: 6 } }}>
      <Stack spacing={1} sx={{ mb: 4 }}>
        <Typography variant="h1" sx={{ fontSize: { xs: '2rem', md: '2.4rem' } }}>
          Your skin, in four questions
        </Typography>
        <Typography variant="body1" color="text.secondary">
          We match ingredients to what you tell us, and show you exactly why each
          product was picked. Your answers stay in this browser.
        </Typography>
      </Stack>

      <Stepper activeStep={step} sx={{ mb: 5 }} alternativeLabel>
        {STEPS.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      <Paper variant="outlined" sx={{ p: { xs: 2.5, md: 4 }, minHeight: 300 }}>
        {step === 0 && (
          <Stack spacing={2.5}>
            <Typography variant="h4">How does your skin usually behave?</Typography>
            <Grid container spacing={2}>
              {options?.skin_types.map((type) => (
                <Grid item xs={12} sm={6} key={type.key}>
                  <Card
                    sx={{
                      borderColor: draft.skin_type === type.key ? 'primary.main' : undefined,
                      borderWidth: draft.skin_type === type.key ? 2 : 1,
                    }}
                  >
                    <CardActionArea
                      sx={{ p: 2 }}
                      onClick={() => update({ skin_type: type.key })}
                    >
                      <Typography variant="h6">{type.label}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {type.description}
                      </Typography>
                    </CardActionArea>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Stack>
        )}

        {step === 1 && (
          <Stack spacing={2.5}>
            <Box>
              <Typography variant="h4">What would you most like to improve?</Typography>
              <Typography variant="body2" color="text.secondary">
                Pick as many as apply.
              </Typography>
            </Box>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {options?.concerns.map((concern) => (
                <Chip
                  key={concern.key}
                  label={concern.label}
                  onClick={() => toggleConcern(concern.key)}
                  color={draft.concerns.includes(concern.key) ? 'primary' : 'default'}
                  variant={draft.concerns.includes(concern.key) ? 'filled' : 'outlined'}
                  sx={{ py: 2.2, px: 0.5 }}
                />
              ))}
            </Stack>
          </Stack>
        )}

        {step === 2 && (
          <Stack spacing={2}>
            <Typography variant="h4">Anything your skin reacts to?</Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={draft.sensitive}
                  onChange={(event) => update({ sensitive: event.target.checked })}
                />
              }
              label="My skin stings or reddens easily"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={draft.fragrance_free}
                  onChange={(event) => update({ fragrance_free: event.target.checked })}
                />
              }
              label="Avoid added fragrance"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={draft.acne_prone}
                  onChange={(event) => update({ acne_prone: event.target.checked })}
                />
              }
              label="I break out easily (avoid pore-clogging ingredients)"
            />
            <Typography variant="caption" color="text.secondary">
              These act as penalties, not filters — a strong product is still shown, with
              the reason for concern spelled out.
            </Typography>
          </Stack>
        )}

        {step === 3 && (
          <Stack spacing={2.5}>
            <Typography variant="h4">What is your per-product budget?</Typography>
            <Grid container spacing={2}>
              {options?.budgets.map((budget) => {
                const value = budget.key === 0 ? null : budget.key
                const selected = draft.budget_max === value
                return (
                  <Grid item xs={6} sm={3} key={budget.label}>
                    <Card
                      sx={{
                        borderColor: selected ? 'primary.main' : undefined,
                        borderWidth: selected ? 2 : 1,
                      }}
                    >
                      <CardActionArea
                        sx={{ p: 2, textAlign: 'center' }}
                        onClick={() => update({ budget_max: value })}
                      >
                        <Typography variant="h6">{budget.label}</Typography>
                      </CardActionArea>
                    </Card>
                  </Grid>
                )
              })}
            </Grid>
          </Stack>
        )}
      </Paper>

      <Stack direction="row" justifyContent="space-between" sx={{ mt: 3 }}>
        <Button disabled={step === 0} onClick={() => setStep((s) => s - 1)}>
          Back
        </Button>
        {step < STEPS.length - 1 ? (
          <Button variant="contained" disabled={!canAdvance} onClick={() => setStep((s) => s + 1)}>
            Continue
          </Button>
        ) : (
          <Button variant="contained" size="large" onClick={finish}>
            See my recommendations
          </Button>
        )}
      </Stack>
    </Container>
  )
}
