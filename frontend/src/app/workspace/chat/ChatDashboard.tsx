"use client";

import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import Link from 'next/link';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import {
  MessageSquare, Plus, FileText, Send, Paperclip, X,
  Loader2, Info, Database, History, CheckCircle2,
  AlertCircle, RefreshCw, Pencil, Trash2
} from 'lucide-react';
import { apiFetch as sharedApiFetch, ApiError } from '@/lib/api';
import { ToastContainer, Toast } from '@/components/chat/ToastContainer';
import { KnowledgeBaseView, DocumentRecord } from '@/components/chat/KnowledgeBaseView';
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



interface ChatSession {
  id: string;
  title: string;
  created_at?: string;
}



export default function SecureBrainDashboard({ boxId, boxName }: { boxId: string, boxName: string }) {
  const [activeDoc, setActiveDoc] = useState<{ title: string, content: string, fileUrl?: string } | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const viewParam = searchParams.get('view');
  const currentView = viewParam === 'documents' ? 'documents' : 'chat';

  const setCurrentView = (view: 'chat' | 'documents') => {
    const params = new URLSearchParams(searchParams.toString());
    if (view === 'chat') {
      params.delete('view'); // cleaner URL for default
    } else {
      params.set('view', view);
    }
    router.push(`${pathname}?${params.toString()}`);
  };

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
    try {
      return await sharedApiFetch(path, options);
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 429) {
          showToast("Rate limited — please wait a moment and try again", "warning");
          throw new Error("rate_limited");
        }
        if (err.status === 409) {
          showToast(err.detail || "Duplicate file detected", "warning");
          throw new Error("duplicate");
        }
        showToast(err.detail || "Something went wrong", "error");
        throw new Error(err.detail || `HTTP ${err.status}`);
      }
      showToast(err.message || "Something went wrong", "error");
      throw err;
    }
  }, [showToast]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const fetchDocuments = useCallback(async () => {
    try {
      const data = await apiFetch(`/api/v1/documents/?box_id=${boxId}`);
      if (data.documents) {
        setDocuments(data.documents);
      } else if (data.files) {
        // Fallback for older API versions without document objects
        setDocuments(data.files.map((filename: string) => ({ filename, status: 'completed' as const })));
      }
    } catch {
      // apiFetch already displays a helpful error.
    }
  }, [apiFetch, boxId]);

  // Initial fetch and polling effect
  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Polling for processing documents
  useEffect(() => {
    const hasProcessing = documents.some(doc => doc.status === 'processing');
    let timeoutId: number;

    if (hasProcessing) {
      timeoutId = window.setTimeout(() => {
        fetchDocuments();
      }, 3000);
    }

    return () => {
      if (timeoutId) window.clearTimeout(timeoutId);
    };
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
    setDocuments((previous) => [
      ...validFiles.filter((file) => !previous.some((document) => document.filename === file.name)).map((file) => ({ filename: file.name, size: file.size, status: 'processing' as const })),
      ...previous,
    ]);

    await Promise.all(validFiles.map(async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('box_id', boxId);
      try {
        const data = await apiFetch('/api/v1/upload/box', { method: 'POST', body: formData });
        showToast(data.message, 'success');
      } catch {
        setDocuments((previous) => previous.map((document) => document.filename === file.name ? { ...document, status: 'failed' } : document));
      }
    }));

    if (fileInputRef.current) fileInputRef.current.value = '';
    setIsUploading(false);
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

  const handleDriveSync = async (forceResync: boolean = false) => {
    setIsSyncing(true);
    const formData = new FormData();
    formData.append("box_id", boxId);
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
      }
    } catch {
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

  const handleDeleteFile = async (filename: string) => {
    try {
      await apiFetch(`/api/v1/documents/?filename=${encodeURIComponent(filename)}&box_id=${boxId}`, { method: "DELETE" });
      setDocuments(prev => prev.filter(document => document.filename !== filename));
      showToast(`Deleted "${filename}"`, "success");
    } catch { }
  };

  const getFileUrl = (name: string) => {
    const localFiles: Record<string, string> = {};
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

        <div className="px-6 mb-6">
          <label className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-2 block">Active Box</label>
          <div className="w-full bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-xl block p-2.5 font-semibold">
            {boxName}
          </div>
          <Link href="/boxes" className="mt-3 inline-block text-xs font-bold text-indigo-600 hover:text-indigo-800 transition-colors">
            ← Back to Boxes
          </Link>
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
