/**
 * src/styles/auth.ts  —  Auth page layout only
 *
 * Shared primitives (inputs, buttons, badges, alerts, links) live in ui.ts.
 * This file contains ONLY what is unique to auth pages:
 * the page shell, card structure, and brand mark.
 *
 * Usage:
 *   import { authStyles as s } from '../styles/auth';
 *   import { ui } from '../styles/ui';
 *
 *   <div className={s.page}>
 *   <input className={ui.input(hasError)} />
 *   <button className={ui.btnPrimary}>
 */

export const authStyles = {

  // ── Page shell ─────────────────────────────────────────────────────────
  // Soft teal radial dot-grid. Suggests data / security without being heavy.
  page: [
    'min-h-screen flex flex-col items-center justify-center px-4 bg-[#FCFCFC]',
    '[background-image:radial-gradient(circle,#0DABAB20_1px,transparent_1px)]',
    '[background-size:32px_32px]',
  ].join(' '),

  // ── Brand mark ─────────────────────────────────────────────────────────
  brand:        'flex items-center gap-3 mb-10',
  brandName:    'font-mono text-base font-bold text-[#042A2B] tracking-widest',
  brandTagline: 'font-mono text-xs text-[#5EB1BF] tracking-wide',

  // ── Card shell ─────────────────────────────────────────────────────────
  card:       'w-full max-w-md bg-white border border-[#C8E6E6] rounded-2xl shadow-sm overflow-hidden',
  cardHeader: 'px-8 pt-8 pb-6 border-b border-[#C8E6E6] bg-[#F4FAFA]',
  cardTitle:  'text-xl font-bold text-[#042A2B]',
  cardSub:    'text-sm text-[#5EB1BF] mt-1.5',
  cardBody:   'px-8 py-7 flex flex-col gap-5 bg-white',
  cardFooter: 'px-8 py-5 border-t border-[#C8E6E6] text-center text-sm text-[#5EB1BF] bg-[#F4FAFA]',

} as const;