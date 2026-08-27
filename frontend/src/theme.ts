import { createTheme } from '@mui/material/styles'

// Editorial rather than clinical: warm neutral ground, a single muted accent,
// generous whitespace. Ingredient data is dense enough that the chrome around it
// should stay quiet.
export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#3f6f5f', light: '#5c8d7c', dark: '#2c4f43' },
    secondary: { main: '#b4674f' },
    success: { main: '#2f7d5c' },
    warning: { main: '#b07d2b' },
    error: { main: '#b4453a' },
    background: { default: '#faf8f5', paper: '#ffffff' },
    text: { primary: '#1f2421', secondary: '#5f6b64' },
    divider: 'rgba(31, 36, 33, 0.10)',
  },
  typography: {
    fontFamily: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'].join(','),
    h1: { fontSize: '2.6rem', fontWeight: 700, letterSpacing: '-0.025em' },
    h2: { fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.02em' },
    h3: { fontSize: '1.5rem', fontWeight: 650, letterSpacing: '-0.015em' },
    h4: { fontSize: '1.2rem', fontWeight: 600 },
    h5: { fontSize: '1.05rem', fontWeight: 600 },
    h6: { fontSize: '0.95rem', fontWeight: 600 },
    body2: { lineHeight: 1.6 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          border: '1px solid rgba(31, 36, 33, 0.09)',
          boxShadow: 'none',
          transition: 'border-color 160ms ease, transform 160ms ease',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 500 },
        sizeSmall: { fontSize: '0.72rem' },
      },
    },
    MuiButton: {
      styleOverrides: { root: { borderRadius: 10 } },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(250, 248, 245, 0.85)',
          backdropFilter: 'blur(8px)',
          color: '#1f2421',
          boxShadow: 'none',
          borderBottom: '1px solid rgba(31, 36, 33, 0.09)',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: { fontWeight: 600, fontSize: '0.8rem', color: '#5f6b64' },
      },
    },
  },
})
