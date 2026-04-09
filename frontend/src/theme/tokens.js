// theme/tokens.js — Design system tokens

export const colors = {
  bg:      '#0a0a0f',
  surface: '#141419',
  border:  '#1e1e2a',
  cyan:    '#00d4ff',
  amber:   '#ff9f43',
  green:   '#00c853',
  red:     '#ff4444',
  text:    '#e0e0e8',
  muted:   '#6b6b7e',
  white:   '#ffffff',
}

// Recharts-friendly chart color series
export const chartColors = {
  primary:   '#00d4ff',
  secondary: '#ff9f43',
  tertiary:  '#00c853',
  danger:    '#ff4444',
  purple:    '#b388ff',
  teal:      '#00bcd4',
  series: [
    '#00d4ff', '#ff9f43', '#00c853', '#ff4444',
    '#b388ff', '#00bcd4', '#ffd740', '#ff80ab',
    '#69f0ae', '#ff6d00', '#40c4ff', '#ea80fc',
  ],
}

// Regime colors
export const regimeColors = {
  bull: '#00c853',
  bear: '#ff4444',
  neutral: '#ff9f43',
}

// Percentile band colors for fan chart
export const fanColors = {
  p5_p95:  'rgba(0, 212, 255, 0.08)',
  p25_p75: 'rgba(0, 212, 255, 0.18)',
  p50:     '#00d4ff',
}

export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  '2xl': '48px',
}
