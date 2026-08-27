import { Box, Typography } from '@mui/material'
import { useState } from 'react'

interface Props {
  src: string | null
  alt: string
  /** Text used for the fallback monogram - normally the brand. */
  fallbackLabel?: string
  /** CSS aspect-ratio; product shots from retailers are portrait-ish. */
  ratio?: string
  rounded?: number
}

/**
 * Product shot with a graceful fallback.
 *
 * Most of the catalog has no image: the synthetic seed data has none at all, and
 * a live listing can lose its image between scrapes. A broken-image icon in a
 * grid looks like a bug, so a missing or failed image degrades to a brand
 * monogram of the same size and the layout never shifts.
 */
export function ProductImage({
  src,
  alt,
  fallbackLabel,
  ratio = '1 / 1',
  rounded = 1.5,
}: Props) {
  const [failed, setFailed] = useState(false)

  const monogram = (fallbackLabel ?? alt)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase()

  const showImage = Boolean(src) && !failed

  return (
    <Box
      sx={{
        aspectRatio: ratio,
        width: '100%',
        borderRadius: rounded,
        overflow: 'hidden',
        bgcolor: 'action.hover',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}
    >
      {showImage ? (
        <Box
          component="img"
          src={src as string}
          alt={alt}
          loading="lazy"
          onError={() => setFailed(true)}
          sx={{
            width: '100%',
            height: '100%',
            // contain, not cover: retailer shots are already framed, and cropping
            // them tends to cut the product off.
            objectFit: 'contain',
            display: 'block',
          }}
        />
      ) : (
        <Typography
          variant="h4"
          component="span"
          aria-hidden
          sx={{ color: 'text.disabled', fontWeight: 600, letterSpacing: 1 }}
        >
          {monogram || '—'}
        </Typography>
      )}
    </Box>
  )
}
