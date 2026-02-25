/**
 * src/pages/Dashboard.tsx
 *
 * Full workspace:
 *  - Left sidebar: document upload/list + chat session list
 *  - Right: active chat with RAG query input
 *
 * Architecture: chat-session-based (POST /rag/chats/<id>/message/)
 * Documents:    standard CRUD   (GET/POST /documents/v1/...)
 */

import {
  useState,
  useEffect,
  useRef,
  useCallback,
  useLayoutEffect,
} from 'react';
import type { KeyboardEvent, MouseEvent } from 'react';
import { useAuth } from '../context/AuthContext';
import { documentsApi } from '../api/documents';
import type { Document as Doc } from '../api/documents';
import { chatApi } from '../api/rag';
import type { ChatSession, ChatMessage, Source } from '../api/rag';
import { ds } from '../styles/dashboard';
import { ui, statusDot, sourceBadgeVariant, fileTypeBadge } from '../styles/ui';

// ── Local UI types ─────────────────────────────────────────────────────────

/** In-memory message used to render the chat — merges user + assistant sides */
interface Message {
  id:       string;
  role:     'user' | 'assistant';
  text:     string;
  source?:  string;
  latency?: number;
  model?:   string | null;
  sources?: Source[];
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
  Plus: () => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <line x1="12" y1="5" x2="12" y2="19"/>
      <line x1="5" y1="12" x2="19" y2="12"/>
    </svg>
  ),
  ChevronRight: () => (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <polyline points="9 18 15 12 9 6"/>
    </svg>
  ),
  Chat: () => (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
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

function uid() { return Math.random().toString(36).slice(2); }

function fmtSize(bytes: number) {
  if (bytes < 1024)        return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function fmtDate(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

// ── ChatMessage → local Message converter ──────────────────────────────────

function fromChatMessage(m: ChatMessage): [Message, Message] {
  return [
    { id: `u-${m.id}`, role: 'user',      text: m.query },
    { id: `a-${m.id}`, role: 'assistant', text: m.response,
      source: m.response_source, sources: m.sources },
  ];
}

// ── Sub-components ─────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className={ds.msgAi}>
      <div className={`${ds.msgAvatar} ${ds.msgAvatarAi}`}>AI</div>
      <div className={ds.typingDots}>
        {[0, 1, 2].map(i => (
          <div key={i} className={ds.typingDot}
               style={{ animation: `bounce 1.2s ${i * 0.2}s infinite` }} />
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
        <span style={{ transform: open ? 'rotate(90deg)' : 'none',
                       transition: 'transform 0.2s', display: 'inline-flex' }}>
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
                <span className={ui.caption}>
                  {(src.similarity_score * 100).toFixed(0)}%
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ChatBubble({ msg, userInitial }: { msg: Message; userInitial: string }) {
  const isUser   = msg.role === 'user';
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
              {msg.latency != null && <span>{msg.latency}ms</span>}
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
  const userInitial = (user?.full_name || user?.email || 'U')[0].toUpperCase();

  // ── Sidebar tab ───────────────────────────────────────────────────────────
  const [tab, setTab] = useState<'docs' | 'chats'>('chats');

  // ── Document state ────────────────────────────────────────────────────────
  const [docs,        setDocs]        = useState<Doc[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [file,        setFile]        = useState<File | null>(null);
  const [title,       setTitle]       = useState('');
  const [secLevel,    setSecLevel]    = useState('LOW');
  const [uploading,   setUploading]   = useState(false);
  const [uploadPct,   setUploadPct]   = useState(0);
  const [uploadMsg,   setUploadMsg]   = useState('');
  const [dragOver,    setDragOver]    = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Chat session state ────────────────────────────────────────────────────
  const [sessions,      setSessions]      = useState<ChatSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [messages,      setMessages]      = useState<Message[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [input,         setInput]         = useState('');
  const [querying,      setQuerying]      = useState(false);
  const [mode,          setMode]          = useState<'quick' | 'detailed'>('quick');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef    = useRef<HTMLTextAreaElement>(null);

  // ── Data fetching ─────────────────────────────────────────────────────────

  const fetchDocs = useCallback(async () => {
    try {
      const { data } = await documentsApi.list();
      setDocs((data as any).results ?? data);
    } catch { /* silent */ }
    finally { setDocsLoading(false); }
  }, []);

  const fetchSessions = useCallback(async () => {
    try {
      const { data } = await chatApi.listSessions();
      setSessions((data as any).results ?? data);
    } catch { /* silent */ }
    finally { setSessionsLoading(false); }
  }, []);

  const loadSessionMessages = useCallback(async (session: ChatSession) => {
    setActiveSession(session);
    setMessages([]);
    setMessagesLoading(true);
    try {
      const { data } = await chatApi.getMessages(session.id);
      const msgs: Message[] = ((data as any).results ?? data)
        .flatMap((m: ChatMessage) => fromChatMessage(m));
      setMessages(msgs);
    } catch { /* silent */ }
    finally { setMessagesLoading(false); }
  }, []);

  useEffect(() => { fetchDocs(); }, [fetchDocs]);
  useEffect(() => { fetchSessions(); }, [fetchSessions]);

  // Poll document status every 8s
  useEffect(() => {
    const id = setInterval(fetchDocs, 8000);
    return () => clearInterval(id);
  }, [fetchDocs]);

  // Auto-scroll chat
  useLayoutEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, querying]);

  // ── Session actions ───────────────────────────────────────────────────────

  async function handleNewChat() {
    try {
      const { data } = await chatApi.createSession();
      setSessions(prev => [data, ...prev]);
      setActiveSession(data);
      setMessages([]);
      setTab('chats');
    } catch { /* silent */ }
  }

  async function handleDeleteSession(id: number, e: MouseEvent) {
    e.stopPropagation();
    if (!confirm('Delete this conversation?')) return;
    try {
      await chatApi.deleteSession(id);
      setSessions(prev => prev.filter(s => s.id !== id));
      if (activeSession?.id === id) {
        setActiveSession(null);
        setMessages([]);
      }
    } catch { /* silent */ }
  }

  // ── Upload handlers ───────────────────────────────────────────────────────

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
      }, 1200);
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

  async function handleDeleteDoc(id: number) {
    if (!confirm('Delete this document and all its chunks?')) return;
    try {
      await documentsApi.delete(id);
      fetchDocs();
    } catch { /* silent */ }
  }

  // ── Send message ──────────────────────────────────────────────────────────

  async function sendMessage() {
    const q = input.trim();
    if (!q || querying) return;

    // Auto-create a session if none is active
    let session = activeSession;
    if (!session) {
      try {
        const { data } = await chatApi.createSession();
        session = data;
        setSessions(prev => [data, ...prev]);
        setActiveSession(data);
      } catch { return; }
    }

    // Optimistically add user bubble
    const userMsgId = uid();
    setMessages(prev => [...prev, { id: userMsgId, role: 'user', text: q }]);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    setQuerying(true);

    try {
      const { data } = await chatApi.sendMessage(session.id, q, mode);

      if (data.success) {
        setMessages(prev => [...prev, {
          id:      uid(),
          role:    'assistant',
          text:    data.answer,
          source:  data.source,
          latency: data.latency_ms,
          model:   data.model,
          sources: data.sources,
        }]);
      } else {
        setMessages(prev => [...prev, {
          id:     uid(),
          role:   'assistant',
          text:   data.error ?? 'Something went wrong.',
          source: 'ERROR',
        }]);
      }

      // Refresh sessions so title + message_count update
      fetchSessions();
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
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }

  function handleTextareaInput(v: string) {
    setInput(v);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height =
        `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <>
      <style>{`
        @keyframes bounce {
          0%,60%,100% { transform:translateY(0);   opacity:0.4; }
          30%          { transform:translateY(-5px); opacity:1;   }
        }
      `}</style>

      <div className={ds.shell}>

        {/* ── Header ──────────────────────────────────────────────────── */}
        <header className={ds.header}>
          <div className={ds.headerBrand}>
            <div className={ds.headerIcon}><Icon.Logo /></div>
            SecureRAG
          </div>
          <div className={ds.headerDiv} />
          <span className={ds.headerTitle}>Knowledge Assistant</span>
          <div className={ds.headerSpacer} />
          <div className={ds.headerUser}>
            <div className={ui.avatar}>{userInitial}</div>
            <span>{user?.email}</span>
            <button onClick={logout} className={ui.btnGhost} title="Sign out">
              <Icon.Logout />
            </button>
          </div>
        </header>

        <div className={ds.content}>

          {/* ── Sidebar ───────────────────────────────────────────────── */}
          <aside className={ds.sidebar}>

            {/* Tab bar */}
            <div className={ds.tabBar}>
              {(['chats', 'docs'] as const).map(t => (
                <button key={t} onClick={() => setTab(t)}
                        className={`${ds.tab} ${tab === t ? ds.tabActive : ds.tabInactive}`}>
                  {t === 'chats' ? 'Chats' : 'Documents'}
                </button>
              ))}
            </div>

            {/* ── Chats tab ─────────────────────────────────────────── */}
            {tab === 'chats' && (
              <>
                <div className="px-4 pt-4 pb-2 flex items-center justify-between">
                  <span className={ui.sectionLabelSm}>Conversations</span>
                  <button onClick={handleNewChat}
                          className={`${ui.btnIcon} w-8 h-8 rounded-lg`}
                          title="New chat">
                    <Icon.Plus />
                  </button>
                </div>

                <div className={ds.historyList}>
                  {sessionsLoading ? (
                    <div className={ds.docEmpty}>Loading…</div>
                  ) : sessions.length === 0 ? (
                    <div className={ds.docEmpty}>
                      No conversations yet.{'\n'}Click + to start one.
                    </div>
                  ) : sessions.map(s => (
                    <div key={s.id}
                         className={`${ds.historyItem} ${activeSession?.id === s.id ? ds.historyItemActive : ''}`}
                         onClick={() => loadSessionMessages(s)}>
                      <div className={ds.historyQ}>
                        {s.title || 'New conversation'}
                      </div>
                      <div className={ds.historyMeta}>
                        <span className={ui.caption}>{fmtDate(s.updated_at)}</span>
                        <span className={`${ds.sourceBadge} ${ui.badgeGrey} ml-auto`}>
                          {s.message_count} msg{s.message_count !== 1 ? 's' : ''}
                        </span>
                        <button
                          className={ds.docDelete}
                          onClick={e => handleDeleteSession(s.id, e)}
                          title="Delete">
                          <Icon.Trash />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* ── Documents tab ─────────────────────────────────────── */}
            {tab === 'docs' && (
              <>
                <div className={ui.sectionLabel}>Upload</div>

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
                  <input ref={fileInputRef} type="file"
                         accept=".pdf,.docx,.doc,.txt" className="hidden"
                         onChange={e => { const f = e.target.files?.[0]; if (f) pickFile(f); }} />
                  <div className={ds.uploadIcon}><Icon.Upload /></div>
                  <div className={ds.uploadLabel}>
                    {file ? file.name : 'Drop file or click to browse'}
                  </div>
                  <div className={ds.uploadHint}>
                    {file ? fmtSize(file.size) : 'PDF · DOCX · DOC · TXT · max 50 MB'}
                  </div>
                </div>

                <div className={ds.controls}>
                  <input type="text" value={title} placeholder="Document title"
                         onChange={e => setTitle(e.target.value)}
                         className={ui.inputSm()} />
                  <select value={secLevel} onChange={e => setSecLevel(e.target.value)}
                          className={ui.select}>
                    <option value="LOW">🔓 Low — Public</option>
                    <option value="MID">🔒 Mid — Internal</option>
                    <option value="HIGH">🔐 High — Confidential</option>
                    <option value="VERY_HIGH">🛡 Very High — Restricted</option>
                  </select>
                  <button onClick={handleUpload}
                          disabled={!file || !title.trim() || uploading}
                          className={ui.btnSm}>
                    {uploading ? 'Uploading…' : 'Upload Document'}
                  </button>
                </div>

                {(uploadPct > 0 || uploadMsg) && (
                  <div className={ds.progressWrap}>
                    {uploadPct > 0 && (
                      <div className={ds.progressTrack}>
                        <div className={ds.progressFill} style={{ width: `${uploadPct}%` }} />
                      </div>
                    )}
                    {uploadMsg && (
                      <div className={uploadMsg.startsWith('Error')
                        ? ds.progressError : ds.progressLabel}>
                        {uploadMsg}
                      </div>
                    )}
                  </div>
                )}

                <div className={ui.sectionLabel}>Your Documents</div>

                <div className={ds.docList}>
                  {docsLoading ? (
                    <div className={ds.docEmpty}>Loading…</div>
                  ) : docs.length === 0 ? (
                    <div className={ds.docEmpty}>
                      No documents yet.{'\n'}Upload one to get started.
                    </div>
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
                        <button className={ds.docDelete} title="Delete"
                                onClick={() => handleDeleteDoc(doc.id)}>
                          <Icon.Trash />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </aside>

          {/* ── Chat area ─────────────────────────────────────────────── */}
          <main className={ds.chatArea}>
            {/* Messages */}
            <div className={ds.messages}>
              {messagesLoading ? (
                <div className={ds.emptyState}>
                  <div className={ui.spinnerTeal} />
                </div>
              ) : messages.length === 0 && !querying ? (
                <div className={ds.emptyState}>
                  <div className={ds.emptyIcon}><Icon.Chat /></div>
                  <h3 className={ds.emptyTitle}>
                    {activeSession
                      ? 'Send a message to start'
                      : 'Start a new conversation'}
                  </h3>
                  <p className={ds.emptySubtitle}>
                    {activeSession
                      ? 'Ask anything about your uploaded documents.'
                      : 'Select a chat from the sidebar or click + to begin.'}
                  </p>
                  {activeSession && (
                    <div className={ds.chipWrap}>
                      {[
                        'Summarise this document',
                        'What are the key points?',
                        'What experience is listed?',
                      ].map(s => (
                        <button key={s} onClick={() => setInput(s)} className={ds.chip}>{s}</button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <>
                  {messages.map(msg => (
                    <ChatBubble key={msg.id} msg={msg} userInitial={userInitial} />
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
                  placeholder={activeSession
                    ? 'Ask a question about your documents…'
                    : 'Type to start a new conversation…'}
                  className={ds.textarea}
                  disabled={querying}
                />
                <select
                  value={mode}
                  onChange={e => setMode(e.target.value as 'quick' | 'detailed')}
                  className={ds.modeSelect}
                  title={mode === 'quick' ? 'Qwen2-0.5B · fast' : 'Qwen2.5-1.5B · thorough'}
                >
                  <option value="quick">⚡ Quick</option>
                  <option value="detailed">🔍 Detailed</option>
                </select>
                <button onClick={sendMessage}
                        disabled={!input.trim() || querying}
                        className={ui.btnIcon}>
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