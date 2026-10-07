"use client";

import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import {
  MessageSquare, Plus, FileText, Send, Paperclip, X,
  Loader2, CheckCircle2, AlertCircle, RefreshCw, Pencil, Trash2, FolderOpen,
  PanelLeftClose, PanelRightClose, History, BookOpen, Link2, Sparkles
} from 'lucide-react';
import { apiFetch as sharedApiFetch, ApiError } from '@/lib/api';
import { ToastContainer, Toast } from '@/components/chat/ToastContainer';
import { KnowledgeBaseView, DocumentRecord } from '@/components/chat/KnowledgeBaseView';
import UploadProgressModal, { UploadFileItem } from '@/components/chat/UploadProgressModal';

// ── Types ──

interface Citation {
  evidence_id?: string;
  document_id?: string;
  filename: string;
  chunk_index?: number;
  page_start?: number;
  page_end?: number;
  section_title?: string;
  content: string;
  embedding_score?: number;
  lexical_score?: number;
  rrf_score?: number;
  rerank_score?: number;
}

interface ChatMessage {
  role: 'user' | 'ai';
  content: string;
  citations?: Citation[];
  key_takeaways?: string[];
  related_questions?: string[];
  error?: boolean;
}

interface ChatSession {
  id: string;
  title: string;
  created_at?: string;
}

export default function SecureBrainDashboard({ boxId, boxName }: { boxId: string, boxName: string }) {
  const [activeSource, setActiveSource] = useState<{ citations: Citation[], focusIdx: number } | null>(null);
  const [historyOpen, setHistoryOpen] = useState(true);
  const [historyWidth, setHistoryWidth] = useState(256);
  const [sourceWidth, setSourceWidth] = useState(420);
  const resizingRef = useRef<null | 'history' | 'source'>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const viewParam = searchParams.get('view');
  const currentView = viewParam === 'chat' ? 'chat' : 'documents';

  const setCurrentView = (view: 'chat' | 'documents') => {
    const params = new URLSearchParams(searchParams.toString());
    if (view === 'documents') {
      params.delete('view');
    } else {
      params.set('view', view);
    }
    router.push(`${pathname}?${params.toString()}`);
  };

  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [recentChats, setRecentChats] = useState<ChatSession[]>([]);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [showSourcePanel, setShowSourcePanel] = useState(false);
  const [uploadFileItems, setUploadFileItems] = useState<UploadFileItem[]>([]);
  const [showUploadModal, setShowUploadModal] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const showToast = useCallback((message: string, type: 'success' | 'error' | 'warning') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const apiFetch = useCallback(async (path: string, options?: RequestInit) => {
    try {
      return await sharedApiFetch(path, options);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 429) {
          showToast("Rate limited — please wait a moment and try again", "warning");
          throw new Error("rate_limited");
        }
        if (err.status === 409) {
          showToast(err.detail as string || "Duplicate file detected", "warning");
          throw new Error("duplicate");
        }
        showToast(err.detail as string || "Something went wrong", "error");
        throw new Error(err.detail as string || `HTTP ${err.status}`);
      }
      showToast(err instanceof Error ? err.message : "Something went wrong", "error");
      throw err;
    }
  }, [showToast]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Panel layout persistence ──
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('docintel.panels') || '{}');
      if (typeof saved.historyOpen === 'boolean') setHistoryOpen(saved.historyOpen);
      if (typeof saved.sourceOpen === 'boolean') setShowSourcePanel(saved.sourceOpen);
      if (typeof saved.historyWidth === 'number') setHistoryWidth(saved.historyWidth);
      if (typeof saved.sourceWidth === 'number') setSourceWidth(saved.sourceWidth);
    } catch { }
  }, []);

  useEffect(() => {
    localStorage.setItem('docintel.panels', JSON.stringify({ historyOpen, sourceOpen: showSourcePanel, historyWidth, sourceWidth }));
  }, [historyOpen, showSourcePanel, historyWidth, sourceWidth]);

  // ── Drag-to-resize ──
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (resizingRef.current === 'history') {
        setHistoryWidth(Math.min(420, Math.max(200, e.clientX - (document.getElementById('chat-main')?.getBoundingClientRect().left || 0))));
      } else if (resizingRef.current === 'source') {
        setSourceWidth(Math.min(760, Math.max(300, window.innerWidth - e.clientX)));
      }
    };
    const onUp = () => {
      if (resizingRef.current) {
        resizingRef.current = null;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, []);

  const startResize = (side: 'history' | 'source') => (e: React.MouseEvent) => {
    e.preventDefault();
    resizingRef.current = side;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

  const citationLabel = (c: Citation) => {
    let label = c.filename;
    if (c.page_start) label += ` • p.${c.page_start}${c.page_end && c.page_end !== c.page_start ? `–${c.page_end}` : ''}`;
    if (c.section_title) label += `, ${c.section_title}`;
    return label;
  };

  const openCitation = (citations: Citation[], focusIdx: number) => {
    setActiveSource({ citations, focusIdx });
    setShowSourcePanel(true);
    setTimeout(() => {
      document.getElementById(`cite-${focusIdx}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 80);
  };

  const fetchDocuments = useCallback(async () => {
    try {
      const data = await apiFetch(`/api/v1/documents/?box_id=${boxId}`);
      if (data.data) {
        setDocuments(data.data);
      } else if (data.documents) {
        setDocuments(data.documents);
      } else if (data.files) {
        setDocuments(data.files.map((filename: string) => ({ filename, status: 'completed' as const })));
      }
    } catch {
      // apiFetch already displays a helpful error.
    }
  }, [apiFetch, boxId]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Polling for processing documents
  useEffect(() => {
    const hasProcessing = documents.some(doc => doc.status === 'processing');
    let timeoutId: number;
    if (hasProcessing) {
      timeoutId = window.setTimeout(() => { fetchDocuments(); }, 3000);
    }
    return () => { if (timeoutId) window.clearTimeout(timeoutId); };
  }, [documents, fetchDocuments]);

  const fetchChatSessions = useCallback(async () => {
    try {
      const data = await apiFetch(`/api/v1/chat/sessions?box_id=${boxId}`);
      setRecentChats(data.sessions || []);
    } catch {
      // apiFetch already displays a helpful error.
    }
  }, [apiFetch, boxId]);

  useEffect(() => { fetchChatSessions(); }, [fetchChatSessions]);

  useEffect(() => {
    if (!sessionId) return;
    const loadHistory = async () => {
      try {
        const data = await apiFetch(`/api/v1/chat/sessions/${sessionId}?box_id=${boxId}`);
        setMessages(data.history.map((m: { role: string; content: string }) => ({
          role: m.role === 'assistant' ? 'ai' : 'user',
          content: m.content
        })));
      } catch {
        showToast("Failed to load chat history", "error");
      }
    };
    loadHistory();
  }, [sessionId, boxId, apiFetch, showToast]);

  const uploadFiles = async (fileList: FileList | File[]) => {
    const files = Array.from(fileList);
    if (!files.length) return;
    const supportedExtensions = new Set(['pdf', 'txt', 'docx', 'csv', 'xlsx']);
    const validFiles = files.filter((file) => supportedExtensions.has(file.name.split('.').pop()?.toLowerCase() || ''));
    if (validFiles.length !== files.length) showToast('Only PDF, DOCX, TXT, CSV, and XLSX files are supported.', 'warning');
    if (!validFiles.length) return;

    setIsUploading(true);

    // Build modal items for each file
    const newItems: UploadFileItem[] = validFiles.map(f => ({
      filename: f.name,
      size: f.size,
      status: 'queued' as const,
      progress: 0,
    }));
    setUploadFileItems(newItems);
    setShowUploadModal(true);

    setDocuments((previous) => [
      ...validFiles.filter((file) => !previous.some((document) => document.filename === file.name)).map((file) => ({ filename: file.name, size: file.size, status: 'processing' as const })),
      ...previous,
    ]);

    await Promise.all(validFiles.map(async (file, idx) => {
      // Mark as processing
      setUploadFileItems(prev => prev.map((item, i) =>
        i === idx ? { ...item, status: 'processing' as const, progress: 15, statusMessage: 'Uploading file...' } : item
      ));

      const formData = new FormData();
      formData.append('file', file);
      formData.append('box_id', boxId);
      try {
        // Simulate progress steps
        setUploadFileItems(prev => prev.map((item, i) =>
          i === idx ? { ...item, progress: 45, statusMessage: 'Extracting content' } : item
        ));
        const data = await apiFetch('/api/v1/upload/box', { method: 'POST', body: formData });
        setUploadFileItems(prev => prev.map((item, i) =>
          i === idx ? { ...item, status: 'indexing' as const, progress: 72, statusMessage: 'Generating vectors' } : item
        ));
        // Brief delay for visual feedback, then mark ready
        await new Promise(resolve => setTimeout(resolve, 600));
        setUploadFileItems(prev => prev.map((item, i) =>
          i === idx ? { ...item, status: 'ready' as const, progress: 100, statusMessage: data.message || 'Indexed and ready' } : item
        ));
      } catch {
        setUploadFileItems(prev => prev.map((item, i) =>
          i === idx ? { ...item, status: 'failed' as const, progress: 0, statusMessage: 'Processing failed' } : item
        ));
        setDocuments((previous) => previous.map((document) => document.filename === file.name ? { ...document, status: 'failed' } : document));
      }
    }));

    if (fileInputRef.current) fileInputRef.current.value = '';
    setIsUploading(false);
    // Refresh documents list after batch completes
    fetchDocuments();
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => uploadFiles(event.target.files || []);

  const handleRenameChat = async (chat: ChatSession) => {
    const title = window.prompt('Rename conversation', chat.title)?.trim();
    if (!title || title === chat.title) return;
    try {
      await apiFetch(`/api/v1/chat/sessions/${chat.id}?box_id=${boxId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      setRecentChats(previous => previous.map(item => item.id === chat.id ? { ...item, title } : item));
      showToast('Conversation renamed', 'success');
    } catch { }
  };

  const handleDeleteChat = async (chat: ChatSession) => {
    if (!window.confirm(`Delete "${chat.title}"? This cannot be undone.`)) return;
    try {
      await apiFetch(`/api/v1/chat/sessions/${chat.id}?box_id=${boxId}`, { method: 'DELETE' });
      setRecentChats(previous => previous.filter(item => item.id !== chat.id));
      if (sessionId === chat.id) {
        setSessionId(null);
        setMessages([]);
      }
      showToast('Conversation deleted', 'success');
    } catch { }
  };

  const handleSendMessage = async (retryContent?: string) => {
    const userQuery = retryContent || inputText.trim();
    if (!userQuery || isProcessing) return;

    if (!retryContent) {
      setInputText("");
      setMessages(prev => [...prev, { role: 'user', content: userQuery }]);
    }
    setIsProcessing(true);

    let currentSid = sessionId;
    if (!currentSid) {
      try {
        const data = await apiFetch("/api/v1/chat/sessions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ box_id: boxId, title: userQuery.slice(0, 30) })
        });
        currentSid = data.session_id;
        setSessionId(currentSid);
        setRecentChats(prev => [{ id: data.session_id, title: userQuery.slice(0, 30) || 'New Conversation' }, ...prev]);
      } catch {
        showToast("Failed to create chat session", "error");
        setIsProcessing(false);
        return;
      }
    }

    try {
      const data = await apiFetch("/api/v1/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: userQuery, box_id: boxId, session_id: currentSid })
      });
      setMessages(prev => {
        const filtered = retryContent ? prev.filter(m => !(m.error && m.role === 'ai')) : prev;
        return [...filtered, { role: 'ai', content: data.answer, citations: data.citations }];
      });
    } catch {
      setMessages(prev => [...prev, { role: 'ai', content: "I couldn't reach the server. Click retry or try again in a moment.", error: true }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDeleteFile = async (documentId: string) => {
    try {
      await apiFetch(`/api/v1/documents/${documentId}?box_id=${boxId}`, { method: "DELETE" });
      setDocuments(prev => prev.filter(document => document.id !== documentId));
      showToast(`Deleted document`, "success");
    } catch { }
  };

  const activeDocCount = documents.filter(d => d.status !== 'failed').length;

  return (
    <div className="flex h-full bg-white text-slate-900 overflow-hidden relative">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      {/* Upload Progress Modal — matches Stitch design */}
      <UploadProgressModal
        isOpen={showUploadModal}
        boxName={boxName}
        files={uploadFileItems}
        onClose={() => setShowUploadModal(false)}
        onCancelAll={() => {
          setShowUploadModal(false);
          setUploadFileItems([]);
        }}
        onRemoveFile={(filename) => {
          setUploadFileItems(prev => prev.filter(f => f.filename !== filename));
        }}
      />

      {currentView === 'documents' && (
        <>
          <KnowledgeBaseView
            boxId={boxId}
            boxName={boxName}
            documents={documents}
            isUploading={isUploading}
            onUploadClick={() => fileInputRef.current?.click()}
            onDeleteFile={handleDeleteFile}
            onFilesSelected={uploadFiles}
            onOpenChat={() => setCurrentView('chat')}
          />
          <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".pdf,.txt,.docx,.csv,.xlsx" multiple />
        </>
      )}

      {/* ── Main Workspace: History + Chat + Source Panel ── */}
      {currentView === 'chat' && (
        <div className="flex-1 flex flex-col h-full min-w-0 bg-white">
          <header className="h-14 border-b border-slate-200 bg-white px-4 md:px-6 flex items-center justify-between shrink-0 z-20">
            <div className="flex items-center gap-3 md:gap-4 min-w-0">
              <div className="flex items-center gap-2 min-w-0">
                <FolderOpen className="text-slate-400 w-5 h-5 shrink-0" />
                <h1 className="text-sm font-semibold text-slate-900 truncate tracking-tight font-headline">{boxName}</h1>
              </div>
              <span className="h-4 w-[1px] bg-slate-200 hidden sm:block" />
              <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 text-xs font-medium text-emerald-700 border border-emerald-200/60">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span>{activeDocCount} documents active</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                id="toggle-history-btn"
                onClick={() => setHistoryOpen(o => !o)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium transition-colors ${historyOpen ? 'bg-slate-100 text-slate-900' : 'bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}
                title="Toggle Chat History"
              >
                <History className="w-3.5 h-3.5 text-slate-500" />
                <span className="hidden sm:inline">History</span>
                <span className="px-1.5 rounded-full bg-white text-[10px] text-slate-600 font-mono border border-slate-200">{recentChats.length}</span>
              </button>
              <button
                onClick={() => setCurrentView('documents')}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
              >
                <FileText className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Manage Documents</span>
              </button>
              <button
                id="toggle-source-btn"
                onClick={() => setShowSourcePanel(o => !o)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium transition-colors ${showSourcePanel ? 'bg-slate-100 text-slate-900' : 'bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}
                title="Toggle Document Inspection Panel"
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Source Panel</span>
              </button>
            </div>
          </header>

          <main id="chat-main" className="flex-1 flex overflow-hidden relative">
            {/* ── Chat History Sidebar (resizable / collapsible to icon rail) ── */}
            {historyOpen ? (
              <aside id="chat-history-sidebar" style={{ width: historyWidth }} className="relative shrink-0 border-r border-slate-200 bg-slate-50/50 hidden md:flex flex-col h-full">
                <div className="h-12 px-4 border-b border-slate-200 flex items-center justify-between shrink-0 bg-slate-50/80">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-slate-500" />
                    <span className="text-xs font-semibold text-slate-900 tracking-tight font-headline">Chat History</span>
                  </div>
                  <button onClick={() => setHistoryOpen(false)} className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors" title="Collapse">
                    <PanelLeftClose size={15} />
                  </button>
                </div>
                <div className="p-3 border-b border-slate-200/80">
                  <button onClick={() => { setSessionId(null); setMessages([]); setActiveSource(null); }} className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 text-xs font-medium transition-colors shadow-xs group">
                    <Plus size={14} className="text-indigo-600 group-hover:scale-110 transition-transform" />
                    New Chat
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                  <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider px-2 pt-2 pb-1 font-mono">Recent Threads</div>
                  {recentChats.map(chat => {
                    const active = sessionId === chat.id;
                    return (
                      <div key={chat.id} onClick={() => { setSessionId(chat.id); setActiveSource(null); }}
                        className={`group p-2.5 rounded-lg cursor-pointer transition-all border ${active ? 'bg-indigo-50/80 border-indigo-100 shadow-xs' : 'border-transparent hover:bg-white hover:border-slate-200'}`}>
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className={`text-xs truncate tracking-tight ${active ? 'font-semibold text-indigo-900' : 'font-medium text-slate-900'}`}>{chat.title}</span>
                          {active && <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 shrink-0 group-hover:hidden" />}
                          <div className="hidden group-hover:flex items-center gap-0.5 shrink-0">
                            <button onClick={(e) => { e.stopPropagation(); handleRenameChat(chat); }} className="p-0.5 rounded text-slate-400 hover:text-indigo-600" title="Rename"><Pencil size={11} /></button>
                            <button onClick={(e) => { e.stopPropagation(); handleDeleteChat(chat); }} className="p-0.5 rounded text-slate-400 hover:text-red-600" title="Delete"><Trash2 size={11} /></button>
                          </div>
                        </div>
                        <div className={`text-[11px] ${active ? 'text-indigo-600/80' : 'text-slate-400'}`}>
                          {active ? 'Active session' : chat.created_at ? new Date(chat.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''}
                        </div>
                      </div>
                    );
                  })}
                  {recentChats.length === 0 && <div className="text-xs text-slate-400 text-center mt-6">No conversations yet</div>}
                </div>
                <div className="p-3 border-t border-slate-200 bg-slate-50/80 text-[11px] text-slate-500">
                  Total {recentChats.length} conversation{recentChats.length === 1 ? '' : 's'}
                </div>
                {/* Resize handle */}
                <div onMouseDown={startResize('history')} className="absolute top-0 -right-1 w-2 h-full cursor-col-resize z-10 group">
                  <div className="mx-auto w-[2px] h-full bg-transparent group-hover:bg-indigo-400 transition-colors" />
                </div>
              </aside>
            ) : (
              <aside className="w-12 shrink-0 border-r border-slate-200 bg-slate-50/50 hidden md:flex flex-col items-center py-3 gap-2">
                <button onClick={() => setHistoryOpen(true)} className="p-2 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-white border border-transparent hover:border-slate-200 transition-colors" title="Show Chat History">
                  <History size={18} />
                </button>
                <button onClick={() => { setSessionId(null); setMessages([]); setActiveSource(null); }} className="p-2 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-white border border-transparent hover:border-slate-200 transition-colors" title="New Chat">
                  <Plus size={18} />
                </button>
              </aside>
            )}

            {/* ── Chat ── */}
            <section className="flex-1 flex flex-col h-full min-w-0 bg-white relative">
              <div className="flex-1 overflow-y-auto px-4 md:px-6 py-8 bg-white">
                <div className="max-w-3xl mx-auto space-y-8 pb-8">
                  {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-center pt-20 space-y-4">
                      <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center">
                        <Sparkles size={26} className="text-indigo-600 opacity-70" />
                      </div>
                      <div className="space-y-2">
                        <h3 className="text-lg font-semibold text-slate-900 font-headline">Ask a question</h3>
                        <p className="text-sm text-slate-500 max-w-sm">Ask a question about documents in this Box to retrieve grounded, cited answers.</p>
                      </div>
                    </div>
                  )}

                  {messages.map((msg, idx) => (
                    <div key={idx} className="flex gap-4 items-start">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${msg.role === 'user' ? 'bg-slate-100 border border-slate-200' : msg.error ? 'bg-red-50 border border-red-200' : 'bg-indigo-50 border border-indigo-100'}`}>
                        {msg.role === 'user' ? <span className="text-[10px] font-semibold text-slate-600">You</span>
                          : msg.error ? <AlertCircle className="w-4 h-4 text-red-500" />
                            : <Sparkles className="w-4 h-4 text-indigo-600" />}
                      </div>
                      <div className="flex-1 min-w-0 space-y-3">
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-semibold tracking-tight ${msg.role === 'user' ? 'text-slate-500' : 'text-slate-900 font-headline'}`}>{msg.role === 'user' ? 'You' : 'DocIntel Synthesizer'}</span>
                          {msg.role === 'ai' && !msg.error && (
                            <span className="text-[10px] text-emerald-700 font-medium px-2 py-0.5 rounded-md bg-emerald-50 border border-emerald-200">Verified against {activeDocCount} files</span>
                          )}
                        </div>
                        <div className={`text-[15px] leading-relaxed ${msg.error ? 'text-red-700' : 'text-slate-800'}`}>
                          <div className={`prose prose-sm max-w-none ${msg.error ? '' : 'prose-slate'}`}>
                            <ReactMarkdown
                              components={{
                                a: ({ node, ...props }) => {
                                  if (props.href?.startsWith('#cite-')) {
                                    const cIdx = parseInt(props.href.replace('#cite-', ''));
                                    if (!isNaN(cIdx) && msg.citations) {
                                      return (
                                        <button
                                          onClick={(e) => { 
                                            e.preventDefault(); 
                                            const clickedCitation = msg.citations![cIdx];
                                            const filteredCitations = msg.citations!.filter(orig => (orig.evidence_id || orig.filename) === (clickedCitation.evidence_id || clickedCitation.filename));
                                            const newFocusIdx = filteredCitations.findIndex(orig => orig === clickedCitation);
                                            openCitation(filteredCitations, newFocusIdx === -1 ? 0 : newFocusIdx); 
                                          }}
                                          className="inline-flex items-center justify-center px-1.5 py-0.5 rounded bg-indigo-50 border border-indigo-200 text-indigo-700 hover:bg-indigo-100 font-mono text-[10px] font-bold mx-0.5 align-baseline transition-colors"
                                          title={msg.citations[cIdx]?.filename}
                                        >
                                          {props.children}
                                        </button>
                                      );
                                    }
                                  }
                                  return <a {...props} />;
                                }
                              }}
                            >
                              {msg.content.replace(/(?:\[|【)(E?\d+)(?:\]|】)/g, (match, p1) => {
                                if (!msg.citations) return match;
                                const searchId = p1.startsWith('E') ? p1 : `E${p1}`;
                                let idx = msg.citations.findIndex(c => c.evidence_id === searchId);
                                if (idx === -1) {
                                  const num = parseInt(p1.replace('E', ''));
                                  if (!isNaN(num) && num > 0 && num <= msg.citations.length) idx = num - 1;
                                }
                                if (idx !== -1) return `[${match}](#cite-${idx})`;
                                return match;
                              })}
                            </ReactMarkdown>
                          </div>
                        </div>

                        {msg.error && (
                          <button onClick={() => { const lastUserMsg = messages.slice(0, idx).reverse().find(m => m.role === 'user'); if (lastUserMsg) handleSendMessage(lastUserMsg.content); }}
                            className="flex items-center gap-2 text-xs font-medium text-red-600 hover:text-red-800 transition-colors">
                            <RefreshCw size={12} /> Retry
                          </button>
                        )}

                        {/* Citation cards */}
                        {msg.role === 'ai' && !msg.error && msg.citations && msg.citations.length > 0 && (
                          <div className="space-y-2 pt-1">
                            {Array.from(new Map(msg.citations.map(c => [c.evidence_id || c.filename, c])).values()).map((c, cIdx) => (
                              <div key={cIdx} className="p-3 rounded-xl bg-slate-50/80 border border-slate-200/90 hover:border-indigo-200 transition-colors">
                                <div className="flex items-center justify-between gap-2">
                                  <span className="text-xs font-semibold text-indigo-600 tracking-tight font-headline shrink-0">{c.evidence_id ? c.evidence_id : `[E${cIdx + 1}]`}</span>
                                  <button onClick={() => {
                                      const filtered = msg.citations!.filter(orig => (orig.evidence_id || orig.filename) === (c.evidence_id || c.filename));
                                      openCitation(filtered, 0);
                                    }}
                                    className="inline-flex items-center gap-1.5 text-xs text-slate-600 hover:text-indigo-600 transition-colors bg-white px-2 py-1 rounded-md border border-slate-200 shadow-xs min-w-0">
                                    <Link2 size={12} className="text-slate-400 shrink-0" />
                                    <span className="truncate">{citationLabel(c)}</span>
                                  </button>
                                </div>
                                <p className="text-sm text-slate-600 leading-relaxed mt-2 line-clamp-2">{c.content}</p>
                              </div>
                            ))}
                          </div>
                        )}

                        {msg.role === 'ai' && !msg.error && msg.related_questions && msg.related_questions.length > 0 && (
                          <div className="pt-3 mt-3 border-t border-slate-100">
                            <p className="text-xs font-semibold text-slate-500 mb-2">Related Questions</p>
                            <div className="space-y-1.5">
                              {msg.related_questions.map((q, qIdx) => (
                                <button key={qIdx} onClick={() => { setInputText(q); handleSendMessage(q); }}
                                  className="w-full text-left text-sm px-3 py-2 rounded-lg hover:bg-slate-50 transition-colors text-slate-600 hover:text-indigo-600 font-medium flex items-start gap-2">
                                  <span className="text-indigo-500 mt-0.5">→</span>
                                  <span className="leading-relaxed">{q}</span>
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {isProcessing && (
                    <div className="flex gap-4 items-center text-sm text-slate-500">
                      <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center"><Loader2 className="w-4 h-4 text-indigo-600 animate-spin" /></div>
                      Searching your documents…
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              <div className="p-4 bg-white border-t border-slate-200">
                <div className="max-w-3xl mx-auto">
                  <div className="relative flex items-center bg-white border border-slate-200 rounded-xl focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-100 transition-all shadow-xs">
                    <button onClick={() => fileInputRef.current?.click()} disabled={isUploading} className="p-3 text-slate-400 hover:text-slate-700 transition-colors" title="Attach Document to Box">
                      {isUploading ? <Loader2 size={20} className="animate-spin" /> : <Paperclip size={20} />}
                    </button>
                    <input
                      className="flex-1 bg-transparent border-0 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-0 py-3.5 px-1"
                      placeholder="Ask a question about documents in this Box..."
                      value={inputText}
                      onChange={e => setInputText(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                    />
                    <div className="flex items-center gap-1.5 pr-2">
                      <button onClick={() => handleSendMessage()} disabled={isProcessing || !inputText.trim()}
                        className="p-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors flex items-center justify-center shadow-xs disabled:opacity-50">
                        {isProcessing ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".pdf,.txt,.docx,.csv,.xlsx" multiple />
            </section>

            {/* ── Source Panel (resizable / collapsible to icon rail) ── */}
            {showSourcePanel ? (
              <aside id="source-panel" style={{ width: sourceWidth }} className="relative shrink-0 border-l border-slate-200 bg-white hidden md:flex flex-col h-full">
                <div onMouseDown={startResize('source')} className="absolute top-0 -left-1 w-2 h-full cursor-col-resize z-10 group">
                  <div className="mx-auto w-[2px] h-full bg-transparent group-hover:bg-indigo-400 transition-colors" />
                </div>
                <div className="h-12 px-4 border-b border-slate-200 flex items-center justify-between shrink-0 bg-slate-50/50">
                  <div className="flex items-center gap-2 truncate">
                    <BookOpen className="w-4 h-4 text-indigo-600 shrink-0" />
                    <span className="text-xs font-semibold text-slate-900 tracking-tight truncate font-headline">
                      {activeSource ? activeSource.citations[activeSource.focusIdx]?.filename : 'Source Inspector'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {activeSource && (
                      <span className="text-[11px] font-mono text-slate-600 px-2 py-0.5 rounded bg-white border border-slate-200">
                        {activeSource.focusIdx + 1} / {activeSource.citations.length}
                      </span>
                    )}
                    <button onClick={() => setShowSourcePanel(false)} className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors" title="Collapse">
                      <PanelRightClose size={15} />
                    </button>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-5 font-mono text-xs leading-relaxed space-y-4 select-text text-slate-600">
                  {!activeSource && (
                    <div className="text-center text-slate-400 font-sans text-sm pt-16 space-y-2">
                      <BookOpen className="w-8 h-8 mx-auto opacity-40" />
                      <p>Click a citation in an answer to inspect the source passage.</p>
                    </div>
                  )}
                  {activeSource?.citations.map((c, i) => {
                    const focused = i === activeSource.focusIdx;
                    return (
                      <div key={i} id={`cite-${i}`} onClick={() => setActiveSource({ ...activeSource, focusIdx: i })}
                        className={`p-3.5 rounded-lg border cursor-pointer transition-all ${focused ? 'border-indigo-200 bg-indigo-50/50 ring-1 ring-indigo-200/50' : 'border-slate-200 bg-slate-50/70 opacity-60 hover:opacity-100'}`}>
                        <div className="flex items-center justify-between mb-1.5 gap-2 font-sans">
                          <span className={`font-semibold text-[11px] truncate ${focused ? 'text-indigo-700' : 'text-slate-700'}`}>
                            [{c.evidence_id || `E${i + 1}`}] {c.section_title || c.filename}{c.page_start ? ` · p.${c.page_start}` : ''}
                          </span>
                          {focused && <span className="text-[9px] text-indigo-700 uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-indigo-100 border border-indigo-200 shrink-0">Active Citation</span>}
                        </div>
                        <p className="text-slate-900 leading-normal whitespace-pre-wrap">{c.content}</p>
                        {c.rerank_score != null && (
                          <div className="mt-2 text-[10px] text-slate-400">relevance {c.rerank_score.toFixed(3)}</div>
                        )}
                      </div>
                    );
                  })}
                </div>

                <div className="p-3 border-t border-slate-200 bg-slate-50/50 text-[11px] text-slate-500 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  {activeSource ? `${activeSource.citations.length} grounded passage(s)` : 'No source selected'}
                </div>
              </aside>
            ) : (
              <aside className="w-12 shrink-0 border-l border-slate-200 bg-slate-50/50 hidden md:flex flex-col items-center py-3 gap-2">
                <button onClick={() => setShowSourcePanel(true)} className="relative p-2 rounded-lg text-slate-500 hover:text-indigo-600 hover:bg-white border border-transparent hover:border-slate-200 transition-colors" title="Show Source Panel">
                  <BookOpen size={18} />
                  {activeSource && <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-indigo-600" />}
                </button>
              </aside>
            )}
          </main>
        </div>
      )}
    </div>
  );
}
