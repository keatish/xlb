import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline'
import CloseIcon from '@mui/icons-material/Close'
import RestartAltIcon from '@mui/icons-material/RestartAlt'
import SendIcon from '@mui/icons-material/Send'
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Divider,
  Fab,
  IconButton,
  Paper,
  Slide,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'
import { useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useChat } from '../hooks/useChat'

/** Openers that show what the assistant is actually for, including the allergy path. */
const STARTERS = [
  'What should I use for dry, sensitive skin?',
  'I am allergic to fragrance and essential oils.',
  'Where is the CeraVe cleanser cheapest?',
  'Can I use a retinol and an AHA together?',
]

const PANEL_WIDTH = 384

export function ChatWidget() {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const reduceMotion = useMediaQuery('(prefers-reduced-motion: reduce)')

  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')

  const { messages, avoid, pending, error, send, removeAvoid, reset } = useChat()

  const fabRef = useRef<HTMLButtonElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const logEndRef = useRef<HTMLDivElement>(null)

  // Hide the widget entirely when the server has no LLM configured, rather than
  // offering a button that can only fail.
  const { data: status } = useQuery({
    queryKey: ['chat-status'],
    queryFn: api.chatStatus,
    staleTime: 5 * 60 * 1000,
    retry: false,
  })

  const close = useCallback(() => {
    setOpen(false)
    // Return focus to the trigger so keyboard users are not dropped at the top.
    fabRef.current?.focus()
  }, [])

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, close])

  useEffect(() => {
    if (open) {
      const id = window.setTimeout(() => inputRef.current?.focus(), reduceMotion ? 0 : 180)
      return () => window.clearTimeout(id)
    }
  }, [open, reduceMotion])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth' })
  }, [messages, pending, reduceMotion])

  const submit = useCallback(() => {
    if (!draft.trim() || pending) return
    void send(draft)
    setDraft('')
  }, [draft, pending, send])

  if (status && !status.enabled) return null

  return (
    <>
      <Fab
        ref={fabRef}
        color="primary"
        aria-label={open ? 'Close the skincare assistant' : 'Ask the skincare assistant'}
        aria-expanded={open}
        onClick={() => (open ? close() : setOpen(true))}
        sx={{
          position: 'fixed',
          // Sit clear of the iOS home indicator and Android nav bar.
          bottom: 'calc(24px + env(safe-area-inset-bottom, 0px))',
          right: 'calc(24px + env(safe-area-inset-right, 0px))',
          zIndex: theme.zIndex.tooltip,
        }}
      >
        {open ? <CloseIcon /> : <ChatBubbleOutlineIcon />}
      </Fab>

      <Slide
        direction="up"
        in={open}
        mountOnEnter
        unmountOnExit
        timeout={reduceMotion ? 0 : 220}
      >
        <Paper
          elevation={8}
          role="dialog"
          aria-label="Skincare assistant"
          sx={{
            position: 'fixed',
            zIndex: theme.zIndex.tooltip - 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            border: 1,
            borderColor: 'divider',
            ...(isMobile
              ? { inset: 0, borderRadius: 0 }
              : {
                  bottom: 'calc(96px + env(safe-area-inset-bottom, 0px))',
                  right: 'calc(24px + env(safe-area-inset-right, 0px))',
                  width: PANEL_WIDTH,
                  maxWidth: 'calc(100vw - 48px)',
                  height: 'min(620px, calc(100vh - 140px))',
                }),
          }}
        >
          <Stack
            direction="row"
            alignItems="center"
            spacing={1}
            sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}
          >
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h6" sx={{ lineHeight: 1.2 }}>
                Skincare assistant
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Ingredients, prices and recommendations
              </Typography>
            </Box>

            {messages.length > 0 && (
              <Tooltip title="Start a new conversation">
                <IconButton size="small" onClick={reset} aria-label="Start a new conversation">
                  <RestartAltIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
            <IconButton size="small" onClick={close} aria-label="Close the assistant">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Stack>

          {avoid.length > 0 && (
            <Box sx={{ px: 2, py: 1.25, bgcolor: 'action.hover' }}>
              <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                Avoiding — products containing these are filtered out
              </Typography>
              <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
                {avoid.map((term) => (
                  <Chip
                    key={term}
                    label={term}
                    size="small"
                    onDelete={() => removeAvoid(term)}
                    sx={{ maxWidth: '100%' }}
                  />
                ))}
              </Stack>
            </Box>
          )}

          <Box
            aria-live="polite"
            aria-atomic="false"
            sx={{ flexGrow: 1, overflowY: 'auto', px: 2, py: 2 }}
          >
            {messages.length === 0 ? (
              <Stack spacing={1.5}>
                <Typography variant="body2" color="text.secondary">
                  Ask about a product, compare prices, or tell me what your skin
                  reacts to and I will leave those products out.
                </Typography>
                <Stack spacing={0.75} alignItems="flex-start">
                  {STARTERS.map((starter) => (
                    <Chip
                      key={starter}
                      label={starter}
                      variant="outlined"
                      size="small"
                      onClick={() => void send(starter)}
                      sx={{ height: 'auto', py: 0.5, '& .MuiChip-label': { whiteSpace: 'normal' } }}
                    />
                  ))}
                </Stack>
              </Stack>
            ) : (
              <Stack spacing={1.5}>
                {messages.map((message, index) => (
                  <Box
                    key={`${index}-${message.role}`}
                    sx={{
                      alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
                      maxWidth: '85%',
                      px: 1.5,
                      py: 1,
                      borderRadius: 2,
                      bgcolor: message.role === 'user' ? 'primary.main' : 'action.hover',
                      color: message.role === 'user' ? 'primary.contrastText' : 'text.primary',
                    }}
                  >
                    {/* Rendered as plain text - model output is never treated as markup. */}
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                      {message.content}
                    </Typography>
                  </Box>
                ))}
              </Stack>
            )}

            {pending && (
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1.5 }}>
                <CircularProgress size={14} />
                <Typography variant="caption" color="text.secondary">
                  Checking the catalogue…
                </Typography>
              </Stack>
            )}

            {error && (
              <Alert severity="error" sx={{ mt: 1.5 }}>
                {error}
              </Alert>
            )}

            <div ref={logEndRef} />
          </Box>

          <Divider />

          <Stack direction="row" spacing={1} alignItems="flex-end" sx={{ p: 1.5 }}>
            <TextField
              inputRef={inputRef}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                // Enter sends; Shift+Enter starts a new line.
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  submit()
                }
              }}
              placeholder="Ask about a product or ingredient"
              size="small"
              fullWidth
              multiline
              maxRows={4}
              disabled={pending}
              inputProps={{ 'aria-label': 'Message the skincare assistant', maxLength: 2000 }}
            />
            <IconButton
              color="primary"
              onClick={submit}
              disabled={pending || !draft.trim()}
              aria-label="Send message"
            >
              <SendIcon fontSize="small" />
            </IconButton>
          </Stack>

          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ px: 2, pb: 1.5, display: 'block' }}
          >
            Educational information, not medical advice. For a persistent skin
            condition, see a dermatologist.
          </Typography>
        </Paper>
      </Slide>
    </>
  )
}
