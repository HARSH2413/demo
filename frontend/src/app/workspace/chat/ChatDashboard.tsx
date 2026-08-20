"use client";

import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  MessageSquare, Plus, FileText, Send, Paperclip, X,
  Loader2, Info, Database, History, CheckCircle2,
  AlertCircle, RefreshCw, XCircle, Cloud, Search, FileUp, ArrowUpDown, Pencil, Trash2
} from 'lucide-react';
import { API_URL } from '@/lib/config';
import { createClient } from '@/lib/supabase/client';

// ── Types ──

interface Citation {
  filename: string;
  content: string;
  similarity: number;
}

interface ChatMessage {
  role: 'user' | 'ai';
  content: string;
  citations?: Citation[];
  key_takeaways?: string[];
  related_questions?: string[];
  error?: boolean;
}

interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'warning';
}

interface DocumentRecord {
  filename: string;
  file_hash?: string;
  created_at?: string;
  status?: 'processing' | 'indexed' | 'failed';
  size?: number;
}

interface ChatSession {
  id: string;
  title: string;
  created_at?: string;
}

// ── Inline Toast Component ──

function ToastContainer({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  return (
    <div className="fixed top-6 right-6 z-50 space-y-3">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-center gap-3 px-5 py-3.5 rounded-2xl shadow-2xl text-sm font-semibold backdrop-blur-md animate-slide-in max-w-sm ${toast.type === 'success' ? 'bg-emerald-600/95 text-white' :
            toast.type === 'error' ? 'bg-red-600/95 text-white' :
              'bg-amber-500/95 text-white'
            }`}
        >
          {toast.type === 'success' && <CheckCircle2 size={16} />}
          {toast.type === 'error' && <XCircle size={16} />}
          {toast.type === 'warning' && <AlertCircle size={16} />}
          <span className="flex-1">{toast.message}</span>
          <button onClick={() => onDismiss(toast.id)} className="opacity-70 hover:opacity-100">
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}

// ── Knowledge Base View Component ──
// NOTE: For maintainability, this would typically be in its own file (e.g., `components/KnowledgeBaseView.tsx`)
function KnowledgeBaseView({
  documents,
  isSyncing,
  isUploading,
  onUploadClick,
  onDriveSync,
  onForceResync,
  onDeleteFile, onFilesSelected,
}: {
  documents: DocumentRecord[];
  isSyncing: boolean;
  isUploading: boolean;
  onUploadClick: () => void;
  onDriveSync: () => void;
  onForceResync: () => void;
  onDeleteFile: (filename: string) => void;
  onFilesSelected: (files: FileList | File[]) => void;
}) {
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<'newest' | 'name'>('newest');
  const [dragging, setDragging] = useState(false);
  const visibleDocuments = documents
    .filter((document) => document.filename.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => sort === 'name'
      ? a.filename.localeCompare(b.filename)
      : new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
  const fileType = (filename: string) => filename.split('.').pop()?.toUpperCase() || 'FILE';

  return (
    <div className="p-10 bg-slate-50 flex-1 overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-slate-800">Knowledge Base</h2>
        <div className="flex gap-3">
          <button onClick={onForceResync} disabled={isSyncing} className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-white text-sm font-bold rounded-xl hover:bg-amber-600 transition-all disabled:opacity-50 shadow-md shadow-amber-100">
            {isSyncing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Force Re-sync
          </button>
          <button onClick={onDriveSync} disabled={isSyncing} className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white text-sm font-bold rounded-xl hover:bg-emerald-700 transition-all disabled:opacity-50 shadow-md shadow-emerald-100">
            {isSyncing ? <Loader2 size={14} className="animate-spin" /> : <Cloud size={14} />}
            Sync Drive
          </button>
          <button onClick={onUploadClick} disabled={isUploading} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-bold rounded-xl hover:bg-indigo-700 transition-all disabled:opacity-50 shadow-md shadow-indigo-100">
            {isUploading ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            Upload Document
          </button>
        </div>
      </div>
      <div
        onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => { event.preventDefault(); setDragging(false); onFilesSelected(event.dataTransfer.files); }}
        onClick={onUploadClick}
        className={`mb-6 cursor-pointer rounded-3xl border-2 border-dashed p-7 text-center transition-all ${dragging ? 'border-indigo-500 bg-indigo-50' : 'border-slate-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/30'}`}
      >
        <FileUp className="mx-auto mb-2 text-indigo-600" size={28} />
        <p className="font-bold text-slate-700">Drop documents here, or click to upload</p>
        <p className="mt-1 text-xs text-slate-500">PDF, DOCX, TXT, CSV, XLSX · up to 25 MB each · multiple files supported</p>
      </div>

      <div className="mb-5 flex flex-wrap gap-3">
        <label className="relative min-w-64 flex-1">
          <Search size={16} className="absolute left-3 top-3 text-slate-400" />
          <input aria-label="Search documents" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search documents..." className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm outline-none focus:border-indigo-500" />
        </label>
        <button onClick={() => setSort(sort === 'newest' ? 'name' : 'newest')} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-600 hover:border-indigo-300">
          <ArrowUpDown size={15} /> {sort === 'newest' ? 'Newest first' : 'Name'}
        </button>
      </div>

      {visibleDocuments.length === 0 ? (
        <div className="text-center p-12 border border-slate-200 rounded-3xl bg-white text-slate-500">
          <Database size={40} className="mx-auto mb-4 opacity-20" />
          <p>{documents.length ? 'No documents match your search.' : 'Your knowledge base is empty.'}</p>
          {!documents.length && <p className="text-xs mt-2">Upload a document or sync your Google Drive folder to get started.</p>}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {visibleDocuments.map((document) => (
            <div key={document.filename} className="p-6 bg-white border border-slate-200 rounded-3xl hover:border-indigo-500 hover:shadow-xl transition-all group flex flex-col justify-between min-h-36 relative">
              <div className="flex items-start justify-between">
                <FileText className="text-indigo-600 group-hover:scale-110 transition-transform" size={28} />
                <button aria-label={`Delete ${document.filename}`} onClick={(e) => { e.stopPropagation(); onDeleteFile(document.filename); }} className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all">
                  <X size={14} />
                </button>
              </div>
              <div>
                <h4 className="font-bold text-sm truncate text-slate-800">{document.filename}</h4>
                <p className="text-[10px] text-slate-400 mt-1">{fileType(document.filename)}{document.size ? ` · ${(document.size / 1024 / 1024).toFixed(1)} MB` : ''}{document.created_at ? ` · ${new Date(document.created_at).toLocaleDateString()}` : ''}</p>
                <p className={`text-[10px] font-bold mt-2 uppercase tracking-tighter flex items-center gap-1 ${document.status === 'processing' ? 'text-amber-600' : document.status === 'failed' ? 'text-red-600' : 'text-emerald-600'}`}>
                  {document.status === 'processing' ? <Loader2 size={10} className="animate-spin" /> : <CheckCircle2 size={10} />} {document.status === 'processing' ? 'Indexing' : document.status === 'failed' ? 'Failed' : 'Indexed'}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main Dashboard ──

export default function SecureBrainDashboard({ tenantId }: { tenantId: string }) {
  const [activeDoc, setActiveDoc] = useState<{ title: string, content: string, fileUrl?: string } | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [currentView, setCurrentView] = useState<'chat' | 'documents'>('chat');
  const [localFiles, setLocalFiles] = useState<Record<string, string>>({});
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [recentChats, setRecentChats] = useState<ChatSession[]>([]);
  const [toasts, setToasts] = useState<Toast[]>([]);

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
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    
    const headers = new Headers(options?.headers);
    if (session?.access_token) {
      headers.set('Authorization', `Bearer ${session.access_token}`);
    }

    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({ detail: "Unknown error" }));
      if (res.status === 429) {
        showToast("Rate limited — please wait a moment and try again", "warning");
        throw new Error("rate_limited");
      }
      if (res.status === 409) {
        showToast(data.detail || "Duplicate file detected", "warning");
        throw new Error("duplicate");
      }
      showToast(data.detail || "Something went wrong", "error");
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }, [showToast]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const fetchDocuments = useCallback(async () => {
    try {
      const data = await apiFetch(`/api/v1/documents/?tenant_id=${tenantId}`);
      if (data.documents) {
        setDocuments((previous) => {
          const indexed = data.documents.map((document: DocumentRecord) => ({ ...document, status: 'indexed' as const }));
          const pending = previous.filter((document) => document.status === 'processing' && !indexed.some((item: DocumentRecord) => item.filename === document.filename));
          return [...pending, ...indexed];
        });
      } else if (data.files) {
        setDocuments(data.files.map((filename: string) => ({ filename, status: 'indexed' })));
      }
    } catch {
      // apiFetch already displays a helpful error.
    }
  }, [apiFetch, tenantId]);

  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);

  const fetchChatSessions = useCallback(async () => {
    try {
      const data = await apiFetch(`/api/v1/chat/sessions?tenant_id=${tenantId}`);
      setRecentChats(data.sessions || []);
    } catch {
      // apiFetch already displays a helpful error.
    }
  }, [apiFetch, tenantId]);

  useEffect(() => { fetchChatSessions(); }, [fetchChatSessions]);

  useEffect(() => {
    if (!sessionId) return;
    const loadHistory = async () => {
      try {
        const data = await apiFetch(`/api/v1/chat/sessions/${sessionId}?tenant_id=${tenantId}`);
        setMessages(data.history.map((m: { role: string; content: string }) => ({
          role: m.role === 'assistant' ? 'ai' : 'user',
          content: m.content
        })));
      } catch {
        showToast("Failed to load chat history", "error");
      }
    };
    loadHistory();
  }, [sessionId, apiFetch, showToast]);

  const uploadFiles = async (fileList: FileList | File[]) => {
    const files = Array.from(fileList);
    if (!files.length) return;
    const supportedExtensions = new Set(['pdf', 'txt', 'docx', 'csv', 'xlsx']);
    const validFiles = files.filter((file) => supportedExtensions.has(file.name.split('.').pop()?.toLowerCase() || ''));
    if (validFiles.length !== files.length) showToast('Only PDF, DOCX, TXT, CSV, and XLSX files are supported.', 'warning');
    if (!validFiles.length) return;

    setIsUploading(true);
    setDocuments((previous) => [
      ...validFiles.filter((file) => !previous.some((document) => document.filename === file.name)).map((file) => ({ filename: file.name, size: file.size, status: 'processing' as const })),
      ...previous,
    ]);

    await Promise.all(validFiles.map(async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('tenant_id', tenantId);
      try {
        const data = await apiFetch('/api/v1/upload/', { method: 'POST', body: formData });
        showToast(data.message, 'success');
      } catch {
        setDocuments((previous) => previous.map((document) => document.filename === file.name ? { ...document, status: 'failed' } : document));
      }
    }));

    if (fileInputRef.current) fileInputRef.current.value = '';
    setIsUploading(false);
    window.setTimeout(fetchDocuments, 4000);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => uploadFiles(event.target.files || []);

  const handleRenameChat = async (chat: ChatSession) => {
    const title = window.prompt('Rename conversation', chat.title)?.trim();
    if (!title || title === chat.title) return;
    try {
      await apiFetch(`/api/v1/chat/sessions/${chat.id}?tenant_id=${tenantId}`, {
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
      await apiFetch(`/api/v1/chat/sessions/${chat.id}?tenant_id=${tenantId}`, { method: 'DELETE' });
      setRecentChats(previous => previous.filter(item => item.id !== chat.id));
      if (sessionId === chat.id) {
        setSessionId(null);
        setMessages([]);
      }
      showToast('Conversation deleted', 'success');
    } catch { }
  };

  const handleDriveSync = async (forceResync: boolean = false) => {
    setIsSyncing(true);
    const formData = new FormData();
    formData.append("tenant_id", tenantId);
    if (forceResync) {
      formData.append("force_resync", "true");
    }

    try {
      showToast(forceResync ? "Force re-syncing all files..." : "Scanning Google Drive folder...", "warning");
      const data = await apiFetch("/api/v1/drive/sync", {
        method: "POST",
        body: formData,
      });
      showToast(data.message, "success");
      if (data.queued_files && data.queued_files.length > 0) {
        setDocuments(prev => [
          ...data.queued_files.filter((filename: string) => !prev.some(document => document.filename === filename)).map((filename: string) => ({ filename, status: 'processing' as const })),
          ...prev,
        ]);
        window.setTimeout(fetchDocuments, 4000);
      }
    } catch (err) {
      // Errors handled by apiFetch
    } finally {
      setIsSyncing(false);
    }
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
          body: JSON.stringify({ tenant_id: tenantId, title: userQuery.slice(0, 30) })
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
        body: JSON.stringify({ question: userQuery, tenant_id: tenantId, session_id: currentSid })
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

  const handleDeleteFile = async (filename: string) => {
    try {
      await apiFetch(`/api/v1/documents/?filename=${encodeURIComponent(filename)}&tenant_id=${tenantId}`, { method: "DELETE" });
      setDocuments(prev => prev.filter(document => document.filename !== filename));
      showToast(`Deleted "${filename}"`, "success");
    } catch { }
  };

  const getFileUrl = (name: string) => {
    const key = Object.keys(localFiles).find(k => k.toLowerCase() === name.toLowerCase());
    return key ? localFiles[key] : undefined;
  };

  return (
    <div className="flex h-screen bg-[#F8FAFC] font-sans text-slate-900 overflow-hidden">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <aside className="w-72 border-r border-slate-200 flex flex-col bg-white shrink-0">
        <div className="p-6 flex items-center gap-3">
          <div className="bg-indigo-600 p-2 rounded-xl shadow-lg shadow-indigo-100">
            <Database className="text-white w-5 h-5" />
          </div>
          <span className="font-bold text-xl tracking-tight text-slate-800">ActionRAG</span>
        </div>

        <button onClick={() => { setMessages([]); setSessionId(null); setCurrentView('chat'); }} className="mx-6 mb-8 flex items-center justify-center gap-2 py-3 rounded-xl font-bold transition-all bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-100">
          <Plus size={18} /> New Investigation
        </button>

        <nav className="flex-1 overflow-y-auto px-4 space-y-8">
          <div>
            <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.2em] px-2 mb-3">Library</h3>
            <div onClick={() => setCurrentView('documents')} className={`flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-all ${currentView === 'documents' ? 'bg-indigo-50 text-indigo-700 font-bold' : 'text-slate-500 hover:bg-slate-50'}`}>
              <FileText size={18} /> <span className="text-sm">Knowledge Base</span>
            </div>
          </div>

          {recentChats.length > 0 && (
            <div>
              <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.2em] px-2 mb-3">Recent Inquiries</h3>
              <div className="space-y-1">
                {recentChats.map((chat) => (
                  <div key={chat.id} onClick={() => { setSessionId(chat.id); setCurrentView('chat'); }} className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-xs truncate transition-all ${sessionId === chat.id ? 'bg-slate-100 text-indigo-600 font-bold border-l-4 border-indigo-600 rounded-l-none' : 'text-slate-500 hover:bg-slate-50'}`}>
                    <History size={14} className="shrink-0" />
                    <span className="min-w-0 flex-1 truncate">{chat.title}</span>
                    <button aria-label={`Rename ${chat.title}`} onClick={(event) => { event.stopPropagation(); handleRenameChat(chat); }} className="hidden p-1 hover:text-indigo-700 group-hover:block"><Pencil size={12} /></button>
                    <button aria-label={`Delete ${chat.title}`} onClick={(event) => { event.stopPropagation(); handleDeleteChat(chat); }} className="hidden p-1 hover:text-red-600 group-hover:block"><Trash2 size={12} /></button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </nav>

        <div className="p-4 border-t border-slate-200">
           <form action={async () => {
             // In a real client component, you'd import logout from actions and call it here.
             // But since this is a client component passing server actions can be tricky unless passed as props or imported directly.
             // We will just do a simple window.location redirect for now or we can use the Next.js router.
             // Actually, we can import logout from '@/app/auth/actions'.
           }}>
             <button
               onClick={(e) => {
                  e.preventDefault();
                  fetch('/auth/logout', { method: 'POST' }).then(() => window.location.href = '/login')
               }}
               className="w-full flex items-center justify-center gap-2 py-2 rounded-lg text-sm text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
             >
               Sign Out
             </button>
           </form>
        </div>
      </aside>

      <main className={`flex-1 flex flex-col min-w-0 bg-white transition-all duration-500 ease-in-out ${activeDoc ? 'max-w-[50%] border-r border-slate-200' : 'max-w-full'}`}>
        <header className="h-16 border-b border-slate-100 flex items-center justify-between px-8 shrink-0 bg-white/80 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <h2 className="font-bold text-sm text-slate-700 uppercase tracking-widest">
              {currentView === 'chat' ? 'Neural Search Active' : 'Document Index'}
            </h2>
          </div>
          <div className="flex items-center gap-3">
            {isSyncing && <span className="text-xs text-emerald-600 font-bold flex items-center gap-2"><Loader2 className="w-3 h-3 animate-spin" /> Syncing Drive...</span>}
            {isUploading && <span className="text-xs text-indigo-600 font-bold flex items-center gap-2"><Loader2 className="w-3 h-3 animate-spin" /> Indexing Document...</span>}
            {isProcessing && <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />}
          </div>
        </header>

        {currentView === 'chat' ? (
          <>
            <div className="flex-1 overflow-y-auto p-10 space-y-10 scroll-smooth bg-slate-50">
              {messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-center space-y-6">
                  <div className="w-20 h-20 bg-indigo-50 rounded-3xl flex items-center justify-center">
                    <MessageSquare size={40} className="text-indigo-600 opacity-40" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-xl font-bold text-slate-800">Enterprise Contextual AI</h3>
                    <p className="text-sm text-slate-400 max-w-sm">Ask a question to retrieve insights from your uploaded technical or legal documentation.</p>
                  </div>
                </div>
              )}
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start gap-4'}`}>

                  {msg.role === 'ai' && (
                    <div className={`w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-lg mt-1 ${msg.error ? 'bg-red-500 shadow-red-100' : 'bg-indigo-600 shadow-indigo-100'
                      }`}>
                      {msg.error ? <AlertCircle className="text-white w-4 h-4" /> : <span className="text-white text-xs font-black italic">AI</span>}
                    </div>
                  )}

                  <div className={`flex flex-col space-y-3 max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    {msg.role === 'ai' && !msg.error && msg.key_takeaways && msg.key_takeaways.length > 0 && (
                      <div className="w-full bg-amber-50 border-l-4 border-amber-400 p-4 rounded-lg animate-in fade-in">
                        <p className="text-xs font-bold text-amber-900 uppercase tracking-wide mb-2.5 flex items-center gap-2">
                          <span className="text-lg">📌</span> Key Takeaways
                        </p>
                        <ul className="text-sm text-amber-800 space-y-1.5">
                          {msg.key_takeaways.map((point, pIdx) => (
                            <li key={pIdx} className="flex items-start gap-2">
                              <span className="text-amber-400 font-bold mt-0.5">•</span>
                              <span className="leading-relaxed">{point}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className={`p-6 text-[15px] leading-relaxed shadow-sm transition-all ${msg.role === 'user'
                      ? 'bg-slate-900 text-white rounded-3xl rounded-tr-sm'
                      : msg.error
                        ? 'bg-red-50 border border-red-200 text-red-700 rounded-3xl rounded-tl-sm'
                        : 'bg-white border border-slate-200 text-slate-800 rounded-3xl rounded-tl-sm'
                      }`}>
                      <div className={`prose prose-sm max-w-none ${msg.role === 'user' ? 'prose-invert' : msg.error ? '' : 'prose-indigo'}`}>
                        <ReactMarkdown>
                          {msg.content}
                        </ReactMarkdown>
                      </div>

                      {msg.error && (
                        <button onClick={() => { const lastUserMsg = messages.slice(0, idx).reverse().find(m => m.role === 'user'); if (lastUserMsg) handleSendMessage(lastUserMsg.content); }} className="mt-3 flex items-center gap-2 text-xs font-bold text-red-600 hover:text-red-800 transition-colors">
                          <RefreshCw size={12} /> Retry
                        </button>
                      )}
                    </div>

                    {msg.role === 'ai' && !msg.error && msg.citations && msg.citations.length > 0 && (
                      <div className="flex flex-wrap gap-2 animate-in fade-in pt-1 pl-2">
                        {Array.from(new Set(msg.citations.map(c => c.filename))).map((filename, cIdx) => (
                          <button key={cIdx} onClick={() => { const cite = msg.citations?.find(c => c.filename === filename); setActiveDoc({ title: filename, content: cite?.content || "", fileUrl: getFileUrl(filename) }); }} className="group flex items-center gap-1.5 bg-indigo-50 border border-indigo-100 px-3 py-1.5 rounded-full text-[11px] font-bold text-indigo-700 hover:bg-indigo-600 hover:text-white transition-all duration-200">
                            <CheckCircle2 size={12} className="text-indigo-400 group-hover:text-white" />
                            {filename}
                          </button>
                        ))}
                      </div>
                    )}

                    {msg.role === 'ai' && !msg.error && msg.related_questions && msg.related_questions.length > 0 && (
                      <div className="w-full mt-3 pt-3 border-t border-slate-200">
                        <p className="text-xs font-bold text-slate-600 uppercase tracking-wide mb-2.5">💡 Related Questions</p>
                        <div className="space-y-2">
                          {msg.related_questions.map((q, qIdx) => (
                            <button
                              key={qIdx}
                              onClick={() => { setInputText(q); handleSendMessage(q); }}
                              className="w-full text-left text-sm px-3 py-2 rounded-lg hover:bg-indigo-50 transition-colors text-slate-700 hover:text-indigo-700 font-medium flex items-start gap-2"
                            >
                              <span className="text-indigo-500 mt-0.5 flex-shrink-0">→</span>
                              <span className="leading-relaxed">{q}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <div className="p-6 border-t border-slate-200 bg-white">
              <div className="max-w-4xl mx-auto relative group flex items-center">
                <button onClick={() => fileInputRef.current?.click()} disabled={isUploading} className="absolute left-4 z-10 p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all disabled:opacity-50">
                  {isUploading ? <Loader2 size={20} className="animate-spin" /> : <Paperclip size={20} />}
                </button>
                <input className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-4 pl-16 pr-16 text-sm focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-50 transition-all" placeholder="Query your internal knowledge base..." value={inputText} onChange={(e) => setInputText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()} />
                <button onClick={() => handleSendMessage()} disabled={isProcessing || !inputText.trim()} className="absolute right-3 bg-indigo-600 p-2.5 rounded-xl text-white hover:bg-indigo-700 shadow-md shadow-indigo-100 transition-all disabled:opacity-50">
                  <Send size={18} />
                </button>
                <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".pdf,.txt,.docx,.csv,.xlsx" multiple />
              </div>
            </div>
          </>
        ) : (
          <>
            <KnowledgeBaseView
              documents={documents}
              isSyncing={isSyncing}
              isUploading={isUploading}
              onUploadClick={() => fileInputRef.current?.click()}
              onDriveSync={() => handleDriveSync(false)}
              onForceResync={() => handleDriveSync(true)}
              onDeleteFile={handleDeleteFile}
              onFilesSelected={uploadFiles}
            />
            <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".pdf,.txt,.docx,.csv,.xlsx" multiple />
          </>
        )}
      </main>

      {activeDoc && (
        <aside className="w-1/2 bg-slate-50 flex flex-col shrink-0 animate-in slide-in-from-right duration-500 ease-out z-20 shadow-2xl border-l border-slate-200">
          <header className="h-16 border-b border-slate-200 bg-white flex items-center justify-between px-6 shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-indigo-50 rounded-lg flex items-center justify-center text-indigo-600">
                <FileText size={18} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-800 truncate max-w-[250px]">{activeDoc.title}</h3>
                <span className="text-[9px] font-black text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full uppercase tracking-widest flex items-center gap-1 w-fit mt-1">
                  <CheckCircle2 size={10} /> Source Authenticated
                </span>
              </div>
            </div>
            <button onClick={() => setActiveDoc(null)} className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-400 hover:text-slate-900">
              <X size={20} />
            </button>
          </header>

          <div className="flex-1 overflow-hidden relative">
            {activeDoc.fileUrl ? (
              <iframe
                src={`${activeDoc.fileUrl}#toolbar=0&navpanes=0&view=FitH`}
                className="w-full h-full border-0"
              />
            ) : (
              <div className="h-full p-12 overflow-y-auto">
                <div className="max-w-2xl mx-auto space-y-8">
                  <div className="bg-white p-10 rounded-3xl shadow-sm border border-slate-200 relative">
                    <div className="absolute -top-3 -left-3 bg-indigo-600 text-white p-2 rounded-xl shadow-lg">
                      <Info size={16} />
                    </div>
                    <h4 className="text-[11px] font-black text-indigo-600 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                      Exact Knowledge Fragment
                    </h4>
                    <p className="text-[15px] leading-[1.8] text-slate-700 font-medium whitespace-pre-wrap">
                      {activeDoc.content}
                    </p>
                  </div>

                  <div className="bg-slate-100 p-6 rounded-2xl border border-slate-200">
                    <p className="text-[11px] text-slate-500 font-bold leading-relaxed">
                      The AI extracted this specific paragraph from the source document to formulate your answer. The original file is stored securely in your vector database.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </aside>
      )}
    </div>
  );
}
