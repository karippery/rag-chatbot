/**
 * src/styles/tokens.ts
 */

export const colors = {
  // Backgrounds
  bg:       '#FCFCFC',
  surface:  '#FFFFFF',
  surface2: '#F4FAFA',   // tinted input/hover bg
  surface3: '#E0F5F5',   // active / selected

  // Borders
  border:   '#C8E6E6',
  border2:  '#0DABAB',   // accent border / focus ring

  // Text
  text:     '#042A2B',   // primary — near-black teal
  text2:    '#2D7070',   // secondary
  text3:    '#5EB1BF',   // placeholder / muted

  // Brand
  accent:    '#0DABAB',  // primary teal
  accentDim: '#E0F5F5',  // teal wash (button hover bg, active state)
  accentAlt: '#5EB1BF',  // softer teal

  // Highlight
  highlight:    '#F6E879',
  highlightDim: '#FEFAC8',

  // Status
  success: '#15803D',
  warning: '#B45309',
  danger:  '#DC2626',
} as const;

export const font = {
  mono: "'DM Mono', monospace",
  sans: "'DM Sans', sans-serif",
} as const;

export const strengthLevels = [
  { label: 'Very weak',   color: colors.danger,    pct: '20%' },
  { label: 'Weak',        color: colors.warning,   pct: '40%' },
  { label: 'Fair',        color: colors.highlight, pct: '60%' },
  { label: 'Strong',      color: colors.accentAlt, pct: '80%' },
  { label: 'Very strong', color: colors.success,   pct: '100%' },
] as const;