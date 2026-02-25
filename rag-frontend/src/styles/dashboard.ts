/**
 * src/styles/dashboard.ts  —  Dashboard layout only
 *
 * Shared primitives (inputs, buttons, badges, alerts) live in ui.ts.
 * This file contains ONLY what is unique to the dashboard layout:
 * shell, header, sidebar, chat area, message bubbles.
 */

export const ds = {

  // ── App shell ──────────────────────────────────────────────────────────
  shell:   'h-screen flex flex-col bg-[#FCFCFC] overflow-hidden',
  content: 'flex flex-1 overflow-hidden',

  // ── Header ─────────────────────────────────────────────────────────────
  header:       'flex items-center gap-3 px-6 h-16 bg-white border-b border-[#C8E6E6] shrink-0 shadow-sm',
  headerBrand:  'flex items-center gap-3 font-mono text-base font-bold text-[#042A2B] tracking-widest',
  headerDiv:    'w-px h-6 bg-[#C8E6E6] mx-2',
  headerTitle:  'text-sm text-[#5EB1BF] font-mono',
  headerSpacer: 'flex-1',
  headerUser:   'flex items-center gap-3 text-sm text-[#2D7070] font-mono',
  headerIcon:   'w-9 h-9 rounded-xl bg-[#0DABAB] flex items-center justify-center text-white shadow-sm shrink-0',

  // ── Sidebar ────────────────────────────────────────────────────────────
  sectionLabel: 'px-4 pt-5 pb-2 text-xs font-mono font-bold text-[#0DABAB] tracking-[0.12em] uppercase',
  sidebar: 'w-80 flex flex-col bg-white border-r border-[#C8E6E6] shrink-0',

  // ── Tab nav ────────────────────────────────────────────────────────────
  tabBar:     'flex gap-1.5 px-4 py-3 border-b border-[#C8E6E6] bg-[#F4FAFA]',
  tab:        'flex-1 py-2 rounded-lg text-sm font-mono font-semibold text-center cursor-pointer transition-all',
  tabActive:  'bg-[#0DABAB] text-white shadow-sm',
  tabInactive:'text-[#5EB1BF] hover:text-[#042A2B] hover:bg-[#E0F5F5]',

  // ── Upload zone ────────────────────────────────────────────────────────
  uploadZone:       'mx-4 mt-4 border-2 border-dashed border-[#C8E6E6] rounded-xl p-6 text-center cursor-pointer transition-all hover:border-[#0DABAB] hover:bg-[#F4FAFA]',
  uploadZoneActive: 'border-[#0DABAB] bg-[#F4FAFA]',
  uploadIcon:       'text-[#0DABAB] mb-3 flex justify-center',
  uploadLabel:      'text-sm text-[#2D7070] leading-relaxed font-medium',
  uploadHint:       'text-xs font-mono text-[#5EB1BF] mt-1',

  // ── Upload controls ────────────────────────────────────────────────────
  controls: 'px-4 pb-4 flex flex-col gap-2.5',

  // ── Progress bar ───────────────────────────────────────────────────────
  progressWrap:  'mx-4 mb-3',
  progressTrack: 'h-1.5 bg-[#E0F5F5] rounded-full overflow-hidden',
  progressFill:  'h-full bg-[#0DABAB] rounded-full transition-all duration-300',
  progressLabel: 'text-xs font-mono text-[#5EB1BF] mt-1.5',
  progressError: 'text-xs font-mono text-red-500 mt-1.5',

  // ── Document list ──────────────────────────────────────────────────────
  docList:   'flex-1 overflow-y-auto px-3 pb-4 space-y-1 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:bg-[#C8E6E6] [&::-webkit-scrollbar-thumb]:rounded-full',
  docItem:   'flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-default transition-colors hover:bg-[#F4FAFA] group',
  docIcon:   'w-9 h-9 rounded-lg flex items-center justify-center text-xs font-mono font-bold shrink-0',
  docMeta:   'flex-1 min-w-0',
  docName:   'text-sm font-semibold text-[#042A2B] truncate',
  docSub:    'text-xs font-mono text-[#5EB1BF] mt-0.5',
  docDelete: 'opacity-0 group-hover:opacity-100 text-[#5EB1BF] hover:text-red-500 transition-all p-1.5 rounded-lg hover:bg-red-50',
  docDot:    'w-2.5 h-2.5 rounded-full shrink-0',
  docEmpty:  'px-4 py-12 text-center text-sm font-mono text-[#5EB1BF] leading-loose',

  // ── History list ───────────────────────────────────────────────────────
  historyList: 'flex-1 overflow-y-auto px-3 py-2 space-y-1 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:bg-[#C8E6E6] [&::-webkit-scrollbar-thumb]:rounded-full',
  historyItem:        'px-3 py-3 rounded-xl cursor-pointer transition-colors hover:bg-[#F4FAFA] border border-transparent hover:border-[#C8E6E6]',
  historyItemActive:  'bg-[#E0F5F5] border-[#C8E6E6]',
  historyQ:    'text-sm font-medium text-[#042A2B] truncate',
  historyMeta:  'flex items-center gap-2 mt-1.5',
  sourceBadge:  'inline-flex items-center text-[11px] font-mono font-semibold px-2 py-0.5 rounded-full',

  // ── Chat area ──────────────────────────────────────────────────────────
  chatArea: 'flex-1 flex flex-col overflow-hidden bg-[#FCFCFC]',

  // Messages scroll area
  messages: 'flex-1 overflow-y-auto px-6 py-6 space-y-6 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:bg-[#C8E6E6] [&::-webkit-scrollbar-thumb]:rounded-full',

  // ── Message bubbles ────────────────────────────────────────────────────
  msgUser:    'flex gap-3 flex-row-reverse items-end',
  msgAi:      'flex gap-3 items-end',
  msgAvatar:     'w-9 h-9 rounded-full flex items-center justify-center text-sm font-mono font-bold shrink-0',
  msgAvatarUser: 'bg-[#0DABAB] text-white',
  msgAvatarAi:   'bg-[#F4FAFA] border border-[#C8E6E6] text-[#5EB1BF]',
  docDotFallback:'bg-[#C8E6E6]',
  msgBody:    'max-w-[72%] flex flex-col gap-1.5',
  bubbleUser: 'px-4 py-3 rounded-2xl rounded-br-sm bg-[#0DABAB] text-white text-sm leading-relaxed shadow-sm',
  bubbleAi:   'px-4 py-3 rounded-2xl rounded-bl-sm bg-white border border-[#C8E6E6] text-[#042A2B] text-sm leading-relaxed shadow-sm',
  msgMeta:    'flex items-center gap-2 text-xs font-mono text-[#5EB1BF] px-1',

  // ── Sources accordion ──────────────────────────────────────────────────
  sourcesBtn:  'flex items-center gap-1.5 text-xs font-mono text-[#5EB1BF] hover:text-[#0DABAB] transition-colors px-1 mt-1',
  sourcesList: 'flex flex-col gap-1.5 mt-1.5',
  sourceItem:  'flex items-center gap-2.5 px-3 py-2 bg-[#F4FAFA] border border-[#C8E6E6] rounded-lg text-xs font-mono text-[#2D7070]',
  sourceNum:   'w-5 h-5 rounded-full bg-[#0DABAB] text-white flex items-center justify-center text-[10px] font-bold shrink-0',

  // ── Empty state ────────────────────────────────────────────────────────
  emptyState:    'flex-1 flex flex-col items-center justify-center gap-5 text-center p-12',
  emptyIcon:     'w-18 h-18 rounded-2xl bg-[#E0F5F5] border border-[#C8E6E6] flex items-center justify-center text-[#0DABAB]',
  emptyTitle:    'text-lg font-bold text-[#042A2B]',
  emptySubtitle: 'text-sm text-[#5EB1BF] max-w-xs leading-relaxed',
  chipWrap:      'flex flex-wrap gap-2 justify-center mt-2',
  chip:          'px-4 py-2 rounded-full border border-[#C8E6E6] text-sm font-mono text-[#2D7070] hover:border-[#0DABAB] hover:text-[#0DABAB] hover:bg-[#F4FAFA] cursor-pointer transition-all',

  // ── Typing indicator ──────────────────────────────────────────────────
  typingDots: 'flex gap-2 px-5 py-3.5 bg-white border border-[#C8E6E6] rounded-2xl rounded-bl-sm w-fit shadow-sm',
  typingDot:  'w-2.5 h-2.5 rounded-full bg-[#0DABAB]',

  // ── Input area ────────────────────────────────────────────────────────
  inputArea: 'px-6 py-5 bg-white border-t border-[#C8E6E6] shrink-0',
  inputRow:  'flex items-end gap-3 bg-[#F4FAFA] border border-[#C8E6E6] rounded-2xl px-5 py-4 focus-within:border-[#0DABAB] focus-within:ring-2 focus-within:ring-[#0DABAB]/15 transition-all',
  textarea:  'flex-1 bg-transparent text-sm text-[#042A2B] placeholder-[#5EB1BF] resize-none outline-none min-h-7 max-h-40 leading-relaxed',
  inputHint: 'text-xs font-mono text-[#5EB1BF] text-center mt-2',

  // ── Mode dropdown (inside input row) ─────────────────────────────────
  modeSelect:      'appearance-none bg-transparent text-xs font-mono font-semibold text-[#5EB1BF] hover:text-[#0DABAB] border border-[#C8E6E6] hover:border-[#0DABAB] rounded-lg px-2.5 py-1.5 cursor-pointer focus:outline-none transition-all shrink-0',

} as const;