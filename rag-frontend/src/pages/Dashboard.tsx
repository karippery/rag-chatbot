/**
 * src/pages/Dashboard.tsx
 *
 * Main workspace: document sidebar (left) + RAG chat (right).
 * All API calls go through src/api/documents.ts and src/api/rag.ts.
 */

import {
  useState,
  useEffect,
  useRef,
  useCallback,
  useLayoutEffect,
} from 'react';
import type { KeyboardEvent } from 'react';
import { useAuth } from '../context/AuthContext';
import { documentsApi } from '../api/documents';
import type { Document as Doc } from '../api/documents';
import { ragApi } from '../api/rag';
import type { HistoryItem, Source } from '../api/rag';
import { ds } from '../styles/dashboard';
import { ui, statusDot, sourceBadgeVariant, fileTypeBadge } from '../styles/ui';

// ── Types ──────────────────────────────────────────────────────────────────

interface Message {
  id:        string;
  role:      'user' | 'assistant';
  text:      string;
  source?:   string;
  latency?:  number;
  model?:    string | null;
  sources?:  Source[];
}

// ── Icons ──────────────────────────────────────────────────────────────────

const Icon = {
  Logo: () => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2L2 7l10 5 10-5-10-5z"/>
      <path d="M2 17l10 5 10-5"/>
      <path d="M2 12l10 5 10-5"/>
    </svg>
  ),
  Upload: () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="17 8 12 3 7 8"/>
      <line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
  ),
  Trash: () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="3 6 5 6 21 6"/>
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
      <path d="M10 11v6"/><path d="M14 11v6"/>
      <path d="M9 6V4h6v2"/>
    </svg>
  ),
  Send: () => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <line x1="22" y1="2" x2="11" y2="13"/>
      <polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>
  ),
  ChevronRight: () => (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <polyline points="9 18 15 12 9 6"/>
    </svg>
  ),
  Inbox: () => (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
      <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>
      <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>
    </svg>
  ),
  Logout: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
      <polyline points="16 17 21 12 16 7"/>
      <line x1="21" y1="12" x2="9" y2="12"/>
    </svg>
  ),
};

// ── Helpers ────────────────────────────────────────────────────────────────

function uid() {
  return Math.random().toString(36).slice(2);
}

function fmtSize(bytes: number) {
  if (bytes < 1024)        return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

// ── Sub-components ─────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className={ds.msgAi}>
      <div className={`${ds.msgAvatar} ${ds.msgAvatarAi}`}>AI</div>
      <div className={ds.typingDots}>
        {[0, 1, 2].map(i => (
          <div
            key={i}
            className={ds.typingDot}
            style={{ animation: `bounce 1.2s ${i * 0.2}s infinite` }}
          />
        ))}
      </div>
    </div>
  );
}

function SourcesAccordion({ sources }: { sources: Source[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button className={ds.sourcesBtn} onClick={() => setOpen(v => !v)}>
        <span style={{ transform: open ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s', display: 'inline-flex' }}>
          <Icon.ChevronRight />
        </span>
        {sources.length} source{sources.length > 1 ? 's' : ''}
      </button>
      {open && (
        <div className={ds.sourcesList}>
          {sources.map((src, i) => (
            <div key={i} className={ds.sourceItem}>
              <div className={ds.sourceNum}>{i + 1}</div>
              <span className={`flex-1 ${ui.mono} truncate`}>{src.document_title}</span>
              {src.similarity_score != null && (
                <span className={ui.caption}>{(src.similarity_score * 100).toFixed(0)}%</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ChatMessage({ msg, userInitial }: { msg: Message; userInitial: string }) {
  const isUser = msg.role === 'user';
  const badgeCls = sourceBadgeVariant[msg.source ?? ''] ?? sourceBadgeVariant.NO_RESULTS;

  return (
    <div className={isUser ? ds.msgUser : ds.msgAi}>
      <div className={`${ds.msgAvatar} ${isUser ? ds.msgAvatarUser : ds.msgAvatarAi}`}>
        {isUser ? userInitial : 'AI'}
      </div>
      <div className={`${ds.msgBody} ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={isUser ? ds.bubbleUser : ds.bubbleAi}>{msg.text}</div>
        {!isUser && (
          <>
            <div className={ds.msgMeta}>
              {msg.source  && <span className={`${ds.sourceBadge} ${badgeCls}`}>{msg.source}</span>}
              {msg.latency  != null && <span>{msg.latency}ms</span>}
              {msg.model   && <span>{msg.model.split('/').pop()}</span>}
            </div>
            {msg.sources && msg.sources.length > 0 && (
              <SourcesAccordion sources={msg.sources} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────

export default function Dashboard() {
  const { user, logout } = useAuth();

  // ── Document state ───────────────────────────────────────────────────────
  const [docs,        setDocs]        = useState<Doc[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [tab,         setTab]         = useState<'docs' | 'history'>('docs');

  // Upload state
  const [file,         setFile]         = useState<File | null>(null);
  const [title,        setTitle]        = useState('');
  const [secLevel,     setSecLevel]     = useState('LOW');
  const [uploading,    setUploading]    = useState(false);
  const [uploadPct,    setUploadPct]    = useState(0);
  const [uploadMsg,    setUploadMsg]    = useState('');
  const [dragOver,     setDragOver]     = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Chat state ───────────────────────────────────────────────────────────
  const [messages,   setMessages]   = useState<Message[]>([]);
  const [history,    setHistory]    = useState<HistoryItem[]>([]);
  const [input,      setInput]      = useState('');
  const [querying,   setQuerying]   = useState(false);
  const [mode,       setMode]       = useState<'quick' | 'detailed'>('quick');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef    = useRef<HTMLTextAreaElement>(null);

  const userInitial = (user?.full_name || user?.email || 'U')[0].toUpperCase();

  // ── Data fetching ────────────────────────────────────────────────────────

  const fetchDocs = useCallback(async () => {
    try {
      const { data } = await documentsApi.list();
      setDocs(data.results ?? data as any);
    } catch { /* silent */ }
    finally { setDocsLoading(false); }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const { data } = await ragApi.history();
      setHistory(data.results ?? data as any);
    } catch { /* silent */ }
  }, []);

  useEffect(() => { fetchDocs(); }, [fetchDocs]);
  useEffect(() => { if (tab === 'history') fetchHistory(); }, [tab, fetchHistory]);

  // Poll document status every 8s to catch indexing completion
  useEffect(() => {
    const id = setInterval(fetchDocs, 8000);
    return () => clearInterval(id);
  }, [fetchDocs]);

  // Auto-scroll chat
  useLayoutEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, querying]);

  // ── Upload handlers ──────────────────────────────────────────────────────

  function pickFile(f: File) {
    setFile(f);
    if (!title) setTitle(f.name.replace(/\.[^.]+$/, ''));
  }

  async function handleUpload() {
    if (!file || !title.trim() || uploading) return;
    setUploading(true);
    setUploadPct(10);
    setUploadMsg('Uploading…');

    const ticker = setInterval(() => {
      setUploadPct(p => p < 80 ? p + 8 : p);
    }, 400);

    try {
      await documentsApi.upload({ file, title: title.trim(), security_level: secLevel });
      clearInterval(ticker);
      setUploadPct(100);
      setUploadMsg('Queued for indexing');
      setTimeout(() => {
        setFile(null); setTitle(''); setUploadPct(0); setUploadMsg('');
        if (fileInputRef.current) fileInputRef.current.value = '';
        fetchDocs();
      }, 1000);
    } catch (err: any) {
      clearInterval(ticker);
      const msg = err.response?.data?.file?.[0]
        || err.response?.data?.title?.[0]
        || err.response?.data?.detail
        || 'Upload failed.';
      setUploadMsg(`Error: ${msg}`);
      setUploadPct(0);
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Delete this document and all its chunks?')) return;
    try {
      await documentsApi.delete(id);
      fetchDocs();
    } catch { /* silent */ }
  }

  // ── Chat handlers ────────────────────────────────────────────────────────

  async function sendMessage() {
    const q = input.trim();
    if (!q || querying) return;

    setMessages(prev => [...prev, { id: uid(), role: 'user', text: q }]);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    setQuerying(true);

    try {
      const { data } = await ragApi.query(q, mode);
      setMessages(prev => [...prev, {
        id:      uid(),
        role:    'assistant',
        text:    data.answer,
        source:  data.source,
        latency: data.latency_ms,
        model:   data.model,
        sources: data.sources,
      }]);
      fetchHistory();
    } catch (err: any) {
      setMessages(prev => [...prev, {
        id:     uid(),
        role:   'assistant',
        text:   err.response?.data?.error || 'Something went wrong.',
        source: 'ERROR',
      }]);
    } finally {
      setQuerying(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function handleTextareaInput(v: string) {
    setInput(v);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }

  function loadHistoryItem(item: HistoryItem) {
    setMessages(prev => [
      ...prev,
      { id: uid(), role: 'user',      text: item.query },
      { id: uid(), role: 'assistant', text: item.response,
        source: item.response_source, sources: item.sources },
    ]);
    setTab('docs');
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <>
      {/* Bounce animation for typing dots */}
      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
          30%            { transform: translateY(-4px); opacity: 1; }
        }
      `}</style>

      <div className={ds.shell}>

        {/* ── Header ────────────────────────────────────────────────── */}
        <header className={ds.header}>
          <div className={ds.headerBrand}>
            <div className={ds.headerIcon}><Icon.Logo /></div>
            <Icon.Logo />
            RAG
          </div>
          <div className={ds.headerDiv} />
          <span className={ds.headerTitle}>Knowledge Assistant</span>
          <div className={ds.headerSpacer} />
          <div className={ds.headerUser}>
            <div className={ui.avatar}>{userInitial}</div>
            <span>{user?.email}</span>
            <button
              onClick={logout}
              className={ui.btnGhost}
              title="Sign out"
            >
              <Icon.Logout />
            </button>
          </div>
        </header>

        <div className={ds.content}>

          {/* ── Sidebar ─────────────────────────────────────────────── */}
          <aside className={ds.sidebar}>

            {/* Tab nav */}
            <div className={ds.tabBar}>
              {(['docs', 'history'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`${ds.tab} ${tab === t ? ds.tabActive : ds.tabInactive}`}
                >
                  {t === 'docs' ? 'Documents' : 'History'}
                </button>
              ))}
            </div>

            {/* ── Documents tab ──────────────────────────────────────── */}
            {tab === 'docs' && (
              <>
                <div className={ds.sectionLabel}>Upload</div>

                {/* Drop zone */}
                <div
                  className={`${ds.uploadZone} ${dragOver ? ds.uploadZoneActive : ''}`}
                  onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={e => {
                    e.preventDefault(); setDragOver(false);
                    const f = e.dataTransfer.files[0];
                    if (f) pickFile(f);
                  }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.doc,.txt"
                    className="hidden"
                    onChange={e => { const f = e.target.files?.[0]; if (f) pickFile(f); }}
                  />
                  <div className={ds.uploadIcon}><Icon.Upload /></div>
                  <div className={ds.uploadLabel}>
                    {file ? file.name : 'Drop file here or click to browse'}
                  </div>
                  <div className={ds.uploadHint}>
                    {file ? fmtSize(file.size) : 'PDF · DOCX · DOC · TXT · max 50 MB'}
                  </div>
                </div>

                {/* Title + security level + upload button */}
                <div className={`${ds.controls} mt-2`}>
                  <input
                    type="text"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    placeholder="Document title"
                    className={ui.inputSm()}
                  />
                  <select
                    value={secLevel}
                    onChange={e => setSecLevel(e.target.value)}
                    className={ui.select}
                  >
                    <option value="LOW">🔓 Low — Public</option>
                    <option value="MID">🔒 Mid — Internal</option>
                    <option value="HIGH">🔐 High — Confidential</option>
                    <option value="VERY_HIGH">🛡 Very High — Restricted</option>
                  </select>
                  <button
                    onClick={handleUpload}
                    disabled={!file || !title.trim() || uploading}
                    className={ui.btnSm}
                  >
                    {uploading ? 'Uploading…' : 'Upload Document'}
                  </button>
                </div>

                {/* Progress */}
                {(uploadPct > 0 || uploadMsg) && (
                  <div className={`${ds.progressWrap} px-3`}>
                    {uploadPct > 0 && (
                      <div className={ds.progressTrack}>
                        <div className={ds.progressFill} style={{ width: `${uploadPct}%` }} />
                      </div>
                    )}
                    {uploadMsg && (
                      <div className={`${ds.progressLabel} ${uploadMsg.startsWith('Error') ? 'text-red-400' : ''}`}>
                        {uploadMsg}
                      </div>
                    )}
                  </div>
                )}

                <div className={ds.sectionLabel}>Your Documents</div>

                {/* Document list */}
                <div className={ds.docList}>
                  {docsLoading ? (
                    <div className={ds.docEmpty}>Loading…</div>
                  ) : docs.length === 0 ? (
                    <div className={ds.docEmpty}>No documents yet.{'\n'}Upload one to get started.</div>
                  ) : docs.map(doc => {
                    const ext = doc.file_type?.toLowerCase() ?? 'txt';
                    return (
                      <div key={doc.id} className={ds.docItem}>
                        <div className={`${ds.docIcon} ${fileTypeBadge[ext] ?? fileTypeBadge.txt}`}>
                          {ext.toUpperCase()}
                        </div>
                        <div className={ds.docMeta}>
                          <div className={ds.docName} title={doc.title}>{doc.title}</div>
                          <div className={ds.docSub}>
                            {doc.chunk_count ?? '—'} chunks · {doc.security_level}
                          </div>
                        </div>
                        <div className={`${ds.docDot} ${statusDot[doc.status] ?? ds.docDotFallback}`}
                             title={doc.status} />
                        <button
                          className={ds.docDelete}
                          onClick={() => handleDelete(doc.id)}
                          title="Delete"
                        >
                          <Icon.Trash />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </>
            )}

            {/* ── History tab ────────────────────────────────────────── */}
            {tab === 'history' && (
              <div className={ds.historyList}>
                {history.length === 0 ? (
                  <div className={ds.docEmpty}>No queries yet.</div>
                ) : history.map(item => {
                  const badgeCls = sourceBadgeVariant[item.response_source] ?? sourceBadgeVariant.NO_RESULTS;
                  return (
                    <div
                      key={item.id}
                      className={ds.historyItem}
                      onClick={() => loadHistoryItem(item)}
                    >
                      <div className={ds.historyQ}>{item.query}</div>
                      <div className={ds.historyMeta}>
                        <span className={`${ds.sourceBadge} ${badgeCls}`}>
                          {item.response_source}
                        </span>
                        <span className={ui.caption}>
                          {new Date(item.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

          </aside>

          {/* ── Chat area ───────────────────────────────────────────── */}
          <main className={ds.chatArea}>

            {/* Mode bar */}
            <div className={ds.modeBar}>
              <span className={ds.modeLabel}>model</span>
              {(['quick', 'detailed'] as const).map(m => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`${ds.modeBtn} ${mode === m ? ds.modeBtnOn : ds.modeBtnOff}`}
                >
                  {m}
                </button>
              ))}
              <span className={ds.modeHint}>
                {mode === 'quick' ? 'Qwen2-0.5B · fast' : 'Qwen2.5-1.5B · thorough'}
              </span>
            </div>

            {/* Messages */}
            <div className={ds.messages}>
              {messages.length === 0 && !querying ? (
                <div className={ds.emptyState}>
                  <div className={ds.emptyIcon}><Icon.Inbox /></div>
                  <h3 className={ds.emptyTitle}>
                    Ask anything about your documents
                  </h3>
                  <p className={ds.emptySubtitle}>
                    Upload a document on the left, then ask questions.
                    Answers are grounded in your files only.
                  </p>
                  <div className={ds.chipWrap}>
                    {[
                      'Summarise this document',
                      'What are the key skills listed?',
                      'What experience does this person have?',
                    ].map(s => (
                      <button
                        key={s}
                        onClick={() => setInput(s)}
                        className={ds.chip}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <>
                  {messages.map(msg => (
                    <ChatMessage key={msg.id} msg={msg} userInitial={userInitial} />
                  ))}
                  {querying && <TypingIndicator />}
                </>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className={ds.inputArea}>
              <div className={ds.inputRow}>
                <textarea
                  ref={textareaRef}
                  rows={1}
                  value={input}
                  onChange={e => handleTextareaInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about your documents…"
                  className={ds.textarea}
                  disabled={querying}
                />
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() || querying}
                  className={ui.btnIcon}
                >
                  <Icon.Send />
                </button>
              </div>
              <div className={ds.inputHint}>Enter to send · Shift+Enter for new line</div>
            </div>

          </main>
        </div>
      </div>
    </>
  );
}