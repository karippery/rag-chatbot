/**
 * src/styles/ui.ts  —  Global component styles
 *
 * Every reusable UI primitive lives here.
 * Import this anywhere: auth pages, dashboard, future pages.
 *
 * Rules:
 *  - If a style appears in more than one file → it goes here.
 *  - Page-specific layout stays in its own file (auth.ts / dashboard.ts).
 *  - All font sizes bumped up one step from the old values for legibility.
 *
 * Text scale used throughout:
 *   body copy     → text-sm   (14px)
 *   labels/mono   → text-xs   (12px)  ← was text-[10px]/text-[11px]
 *   captions/meta → text-[11px]       ← was text-[9px]/text-[10px]
 *   headings      → text-xl / text-lg
 */

// ── Colour aliases (keep in sync with tokens.ts) ──────────────────────────
const C = {
  text:         '#042A2B',
  text2:        '#2D7070',
  text3:        '#5EB1BF',
  bg:           '#FCFCFC',
  surface:      '#FFFFFF',
  surface2:     '#F4FAFA',
  surface3:     '#E0F5F5',
  border:       '#C8E6E6',
  border2:      '#0DABAB',
  accent:       '#0DABAB',
  accentHover:  '#0c9999',
  accentActive: '#0a8888',
  highlight:    '#F6E879',
  highlightDim: '#FEFAC8',
} as const;

export const ui = {

  // ── Typography ────────────────────────────────────────────────────────
  // Use these instead of raw Tailwind text-* classes so scaling is central.
  h1:      `text-2xl font-bold   text-[${C.text}]  leading-tight`,
  h2:      `text-xl  font-bold   text-[${C.text}]  leading-tight`,
  h3:      `text-lg  font-semibold text-[${C.text}]`,
  h4:      `text-base font-semibold text-[${C.text}]`,
  body:    `text-sm  text-[${C.text}]  leading-relaxed`,
  bodyMd:  `text-base text-[${C.text}] leading-relaxed`,
  label:   `text-xs  font-mono font-semibold text-[${C.text2}] tracking-wide uppercase`,
  caption: `text-[11px] font-mono text-[${C.text3}]`,
  mono:    `text-xs  font-mono text-[${C.text2}]`,

  // ── Inputs ────────────────────────────────────────────────────────────
  // All inputs: comfortable height, clear focus ring, readable text
  input: (hasError = false) => [
    `w-full px-4 py-3 rounded-xl text-sm text-[${C.text}]`,
    `bg-[${C.surface2}] placeholder-[${C.text3}]`,
    'focus:outline-none transition-all',
    hasError
      ? 'border-2 border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-100'
      : `border border-[${C.border}] focus:border-[${C.border2}] focus:ring-2 focus:ring-[${C.border2}]/15 focus:bg-white`,
  ].join(' '),

  // Password input — extra right padding for show/hide toggle
  inputPw: (hasError = false) => [
    `w-full px-4 py-3 pr-12 rounded-xl text-sm text-[${C.text}]`,
    `bg-[${C.surface2}] placeholder-[${C.text3}]`,
    'focus:outline-none transition-all',
    hasError
      ? 'border-2 border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-100'
      : `border border-[${C.border}] focus:border-[${C.border2}] focus:ring-2 focus:ring-[${C.border2}]/15 focus:bg-white`,
  ].join(' '),

  // Compact input — for sidebar controls (title field, select)
  inputSm: (hasError = false) => [
    `w-full px-3 py-2.5 rounded-lg text-sm text-[${C.text}]`,
    `bg-[${C.surface2}] placeholder-[${C.text3}]`,
    'focus:outline-none transition-all',
    hasError
      ? 'border border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-100'
      : `border border-[${C.border}] focus:border-[${C.border2}] focus:ring-2 focus:ring-[${C.border2}]/15`,
  ].join(' '),

  select: `w-full px-3 py-2.5 rounded-lg text-sm text-[${C.text}] bg-[${C.surface2}] border border-[${C.border}] focus:outline-none focus:border-[${C.border2}] cursor-pointer transition-all`,

  pwWrap:      'relative',
  pwToggleBtn: `absolute right-3.5 top-1/2 -translate-y-1/2 text-[${C.text3}] hover:text-[${C.accent}] transition-colors`,

  // ── Buttons ───────────────────────────────────────────────────────────
  // Primary — solid teal
  btnPrimary: [
    'w-full py-3 rounded-xl',
    `bg-[${C.accent}] hover:bg-[${C.accentHover}] active:bg-[${C.accentActive}] disabled:opacity-40`,
    'text-white text-sm font-semibold tracking-wide',
    'transition-colors flex items-center justify-center gap-2 shadow-sm',
  ].join(' '),

  // Secondary — outlined
  btnSecondary: [
    'py-2.5 px-4 rounded-xl',
    `border border-[${C.border}] hover:border-[${C.accent}] hover:bg-[${C.surface2}]`,
    `text-sm font-medium text-[${C.text2}] hover:text-[${C.accent}]`,
    'transition-all flex items-center justify-center gap-2',
  ].join(' '),

  // Compact — for sidebar actions
  btnSm: [
    'py-2.5 px-3 rounded-lg',
    `bg-[${C.accent}] hover:bg-[${C.accentHover}] disabled:opacity-40`,
    'text-white text-sm font-semibold tracking-wide',
    'transition-colors flex items-center justify-center gap-2 shadow-sm w-full',
  ].join(' '),

  // Icon button — square, used for send button etc.
  btnIcon: [
    'w-10 h-10 rounded-xl flex items-center justify-center',
    `bg-[${C.accent}] hover:bg-[${C.accentHover}] disabled:opacity-30`,
    'text-white transition-colors shadow-sm shrink-0',
  ].join(' '),

  // Ghost — text only, for logout / cancel
  btnGhost: `text-sm text-[${C.text3}] hover:text-red-500 transition-colors flex items-center gap-1.5`,

  spinner:      'w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin',
  spinnerTeal:  'w-6 h-6 border-2 border-[#C8E6E6] border-t-[#0DABAB] rounded-full animate-spin',

  // ── Badges ────────────────────────────────────────────────────────────
  // Base — combine with colour variant below
  badge:        'inline-flex items-center text-[11px] font-mono font-semibold px-2 py-0.5 rounded-full',
  badgeTeal:    `bg-[${C.surface3}] text-[${C.accent}]`,
  badgeYellow:  `bg-[${C.highlightDim}] text-amber-700`,
  badgeGrey:    `bg-[${C.surface2}] text-[${C.text3}]`,
  badgeRed:     'bg-red-50 text-red-600',
  badgeGreen:   'bg-green-50 text-green-700',

  // ── Status dots ───────────────────────────────────────────────────────
  dot:            'w-2.5 h-2.5 rounded-full shrink-0',
  dotIndexed:     'bg-green-500',
  dotProcessing:  'bg-amber-400',
  dotPending:     'bg-amber-400',
  dotFailed:      'bg-red-500',

  // ── Alerts / feedback ─────────────────────────────────────────────────
  alertError: [
    'flex items-start gap-2.5 px-4 py-3 rounded-xl',
    'bg-red-50 border border-red-200 text-red-700 text-sm',
  ].join(' '),

  alertSuccess: 'flex flex-col items-center gap-3 py-6 text-center',

  alertSuccessIcon: [
    'w-14 h-14 rounded-2xl',
    `bg-[${C.surface3}] border-2 border-[${C.accent}]/30`,
    `flex items-center justify-center text-[${C.accent}] text-2xl`,
  ].join(' '),

  alertInfo: [
    'flex items-start gap-2.5 px-4 py-3 rounded-xl',
    `bg-[${C.surface3}] border border-[${C.border}] text-[${C.text2}] text-sm`,
  ].join(' '),

  // ── Links ─────────────────────────────────────────────────────────────
  link:   `text-[${C.accent}] hover:text-[${C.accentHover}] font-medium underline-offset-2 hover:underline transition-colors`,
  linkSm: `text-xs font-mono text-[${C.accent}] hover:text-[${C.accentHover}] transition-colors`,

  // ── Dividers ──────────────────────────────────────────────────────────
  divider:   `border-t border-[${C.border}]`,
  dividerV:  `border-l border-[${C.border}]`,

  // ── Surfaces ──────────────────────────────────────────────────────────
  card:   `bg-white border border-[${C.border}] rounded-2xl shadow-sm`,
  panel:  `bg-white border border-[${C.border}] rounded-xl`,
  tinted: `bg-[${C.surface2}] border border-[${C.border}] rounded-xl`,

  // ── Password strength bar ─────────────────────────────────────────────
  strengthWrap:  'flex flex-col gap-1.5 mt-1.5',
  strengthTrack: `h-1.5 rounded-full bg-[${C.surface3}] overflow-hidden`,
  strengthFill:  'h-full rounded-full transition-all duration-300',
  strengthLabel: 'text-xs font-mono font-medium',

  // ── Scrollbar (apply to scroll containers) ────────────────────────────
  // Add this class alongside overflow-y-auto for styled scrollbars
  scrollbar: [
    '[&::-webkit-scrollbar]:w-1.5',
    `[&::-webkit-scrollbar-track]:bg-[${C.surface2}]`,
    `[&::-webkit-scrollbar-thumb]:bg-[${C.border}]`,
    '[&::-webkit-scrollbar-thumb]:rounded-full',
    `[&::-webkit-scrollbar-thumb:hover]:bg-[${C.accent}]`,
  ].join(' '),

  // ── Avatar ────────────────────────────────────────────────────────────
  avatar: `w-9 h-9 rounded-full bg-[${C.accent}] flex items-center justify-center text-white text-sm font-bold font-mono`,
  avatarSm: `w-7 h-7 rounded-full bg-[${C.accent}] flex items-center justify-center text-white text-xs font-bold font-mono`,

  // ── Brand ─────────────────────────────────────────────────────────────
  brandIcon: `w-10 h-10 rounded-xl bg-[${C.accent}] flex items-center justify-center text-white shadow-sm`,
  brandIconSm: `w-8 h-8 rounded-lg bg-[${C.accent}] flex items-center justify-center text-white`,

  // ── Section label (sidebar headings) ─────────────────────────────────
  sectionLabel:    `px-4 pt-5 pb-2 text-xs font-mono font-bold text-[${C.accent}] tracking-[0.12em] uppercase`,
  sectionLabelSm:  `text-xs font-mono font-bold text-[${C.accent}] tracking-[0.12em] uppercase`,  // inline, no padding

  // ── Form field wrapper ────────────────────────────────────────────────
  fieldWrap:  'flex flex-col gap-2',
  fieldRow:   'flex items-center justify-between',
  fieldError: 'text-xs font-mono text-red-600 mt-0.5',

} as const;

// ── Source badge map ───────────────────────────────────────────────────────
// Maps response_source values → badge classes (uses ui.badge + variant)
export const sourceBadgeVariant: Record<string, string> = {
  LLM:         ui.badgeTeal,
  EXTRACTIVE:  ui.badgeYellow,
  NOT_IN_DOCS: ui.badgeGrey,
  NO_RESULTS:  ui.badgeGrey,
  ERROR:       ui.badgeRed,
};

// ── File type badge map ────────────────────────────────────────────────────
export const fileTypeBadge: Record<string, string> = {
  pdf:  ui.badgeRed,
  docx: ui.badgeTeal,
  doc:  ui.badgeTeal,
  txt:  ui.badgeYellow,
};

// ── Status dot map ─────────────────────────────────────────────────────────
export const statusDot: Record<string, string> = {
  indexed:    ui.dotIndexed,
  processing: ui.dotProcessing,
  pending:    ui.dotPending,
  failed:     ui.dotFailed,
};