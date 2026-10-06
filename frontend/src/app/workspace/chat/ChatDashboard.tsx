"use client";

import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import {
  MessageSquare, Plus, FileText, Send, Paperclip, X,
  Loader2, CheckCircle2, AlertCircle, RefreshCw, Pencil, Trash2, FolderOpen
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
  const [activeDoc, setActiveDoc] = useState<{ title: string, content: string, fileUrl?: string } | null>(null);
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

      {/* ── Main Workspace: Chat + Source Panel ── */}
      {/* Matches Stitch: docintel_minimal_box_workspace_chat_light */}
      {currentView === 'chat' && (
      <div className="flex-1 flex flex-col h-full min-w-0 bg-white">
        {/* Clean Workspace Header — matches Stitch exactly */}
        <header className="h-14 border-b border-slate-200 bg-white px-4 md:px-6 flex items-center justify-between shrink-0 z-20">
          <div className="flex items-center gap-3 md:gap-4 min-w-0">
            <div className="flex items-center gap-2">
              <FolderOpen className="text-slate-400 w-5 h-5 shrink-0" />
              <h1 className="text-sm font-semibold text-slate-900 truncate tracking-tight font-headline">
                {boxName}
              </h1>
            </div>
            <span className="h-4 w-[1px] bg-slate-200 hidden sm:block" />
            {/* Subtle document count indicator */}
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 text-xs font-medium text-emerald-700 border border-emerald-200/60">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span>{activeDocCount} documents active</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentView('documents')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
            >
              <FileText className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Documents</span>
            </button>
            {(
              <button
                onClick={() => {
                  if (activeDoc) {
                    setActiveDoc(null);
                    setShowSourcePanel(false);
                  } else {
                    setShowSourcePanel(!showSourcePanel);
                  }
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium transition-colors ${showSourcePanel || activeDoc ? 'bg-slate-100 text-slate-900' : 'bg-slate-50 text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
                <span className="hidden sm:inline">Source Panel</span>
              </button>
            )}
          </div>
        </header>

        {/* Body */}
        <main className="flex-1 flex overflow-hidden relative">
          {/* Chat / Documents Area */}
          <section className={`flex-1 flex flex-col h-full min-w-0 bg-white relative ${activeDoc ? 'max-w-[55%]' : ''}`}>
            {currentView === 'chat' ? (
              <>
                {/* Scrollable Chat */}
                <div className="flex-1 overflow-y-auto px-4 md:px-6 py-8 bg-white">
                  <div className="max-w-3xl mx-auto space-y-8 pb-8">
                    {messages.length === 0 && (
                      <div className="h-full flex flex-col items-center justify-center text-center pt-20 space-y-4">
                        <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center">
                          <MessageSquare size={28} className="text-indigo-600 opacity-60" />
                        </div>
                        <div className="space-y-2">
                          <h3 className="text-lg font-semibold text-slate-900 font-headline">Ask a question</h3>
                          <p className="text-sm text-slate-500 max-w-sm">
                            Ask a question about documents in this Box to retrieve grounded, cited answers.
                          </p>
                        </div>
                        {/* New Chat + History buttons on mobile */}
                        <div className="flex items-center gap-2 md:hidden mt-4">
                          <button onClick={() => { setMessages([]); setSessionId(null); }} className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 text-slate-600">
                            <Plus size={14} className="inline mr-1" /> New Chat
                          </button>
                        </div>
                      </div>
                    )}

                    {messages.map((msg, idx) => (
                      <div key={idx} className="flex gap-4 items-start">
                        {/* Avatar */}
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                          msg.role === 'user'
                            ? 'bg-slate-100 border border-slate-200'
                            : msg.error
                              ? 'bg-red-50 border border-red-200'
                              : 'bg-indigo-50 border border-indigo-100'
                        }`}>
                          {msg.role === 'user' ? (
                            <span className="text-xs font-semibold text-slate-600">You</span>
                          ) : msg.error ? (
                            <AlertCircle className="w-4 h-4 text-red-500" />
                          ) : (
                            <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                          )}
                        </div>

                        {/* Content */}
                        <div className="flex-1 space-y-3">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-slate-500 tracking-tight">{msg.role === 'user' ? 'You' : 'DocIntel Synthesizer'}</span>
                            {msg.role === 'ai' && !msg.error && (
                              <span className="text-[10px] text-emerald-700 font-medium px-2 py-0.5 rounded-md bg-emerald-50 border border-emerald-200">
                                Verified against {activeDocCount} files
                              </span>
                            )}
                          </div>

                          <div className={`text-[15px] leading-relaxed ${msg.error ? 'text-red-700' : 'text-slate-800'}`}>
                            <div className={`prose prose-sm max-w-none ${msg.error ? '' : 'prose-slate'}`}>
                              <ReactMarkdown>{msg.content}</ReactMarkdown>
                            </div>
                          </div>

                          {msg.error && (
                            <button
                              onClick={() => { const lastUserMsg = messages.slice(0, idx).reverse().find(m => m.role === 'user'); if (lastUserMsg) handleSendMessage(lastUserMsg.content); }}
                              className="flex items-center gap-2 text-xs font-medium text-red-600 hover:text-red-800 transition-colors"
                            >
                              <RefreshCw size={12} /> Retry
                            </button>
                          )}

                          {/* Citations — styled as Stitch source link buttons */}
                          {msg.role === 'ai' && !msg.error && msg.citations && msg.citations.length > 0 && (
                            <div className="flex flex-wrap gap-2 pt-1">
                              {Array.from(new Set(msg.citations.map(c => c.filename))).map((filename, cIdx) => (
                                <button
                                  key={cIdx}
                                  onClick={() => {
                                    const cite = msg.citations?.find(c => c.filename === filename);
                                    setActiveDoc({ title: filename, content: cite?.content || "" });
                                    setShowSourcePanel(true);
                                  }}
                                  className="inline-flex items-center gap-1.5 text-xs text-slate-600 hover:text-indigo-600 transition-colors bg-white px-2 py-1 rounded-md border border-slate-200 shadow-xs"
                                >
                                  <svg className="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>
                                  <span>{filename}</span>
                                </button>
                              ))}
                            </div>
                          )}

                          {/* Related questions */}
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
                    <div ref={messagesEndRef} />
                  </div>
                </div>

                {/* Input Area — matches Stitch bottom-docked input */}
                <div className="p-4 bg-white border-t border-slate-200">
                  <div className="max-w-3xl mx-auto">
                    <div className="relative flex items-center bg-white border border-slate-200 rounded-xl focus-within:border-indigo-600 focus-within:ring-2 focus-within:ring-indigo-100 transition-all shadow-xs">
                      <button onClick={() => fileInputRef.current?.click()} disabled={isUploading} className="p-3 text-slate-400 hover:text-slate-700 transition-colors" title="Attach Document">
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
                        <button
                          onClick={() => handleSendMessage()}
                          disabled={isProcessing || !inputText.trim()}
                          className="p-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition-colors flex items-center justify-center shadow-xs disabled:opacity-50"
                        >
                          {isProcessing ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".pdf,.txt,.docx,.csv,.xlsx" multiple />
              </>
            ) : null}
          </section>

          {/* Source Panel — matches Stitch collapsible panel */}
          {activeDoc && (
            <aside className="w-[420px] shrink-0 border-l border-slate-200 bg-white flex flex-col h-full transition-all duration-200 ease-in-out hidden md:flex">
              {/* Source Header */}
              <div className="h-14 px-4 border-b border-slate-200 flex items-center justify-between shrink-0 bg-slate-50/50">
                <div className="flex items-center gap-2 truncate">
                  <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
                  <span className="text-xs font-semibold text-slate-900 tracking-tight truncate font-headline">{activeDoc.title}</span>
                </div>
                <button onClick={() => { setActiveDoc(null); setShowSourcePanel(false); }} className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors" title="Close Panel">
                  <X size={16} />
                </button>
              </div>

              {/* Document Viewer Body */}
              <div className="flex-1 overflow-y-auto p-5 text-xs leading-relaxed space-y-6 select-text text-slate-600 bg-white font-mono">
                <div className="p-3.5 rounded-lg border border-indigo-200 bg-indigo-50/50 relative">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-indigo-700 font-semibold text-[11px]">Source Citation</span>
                    <span className="text-[9px] text-indigo-700 uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-indigo-100 border border-indigo-200">Active Citation</span>
                  </div>
                  <p className="text-slate-900 leading-normal font-mono text-xs whitespace-pre-wrap">
                    {activeDoc.content}
                  </p>
                </div>
              </div>

              {/* Source Footer */}
              <div className="p-3 border-t border-slate-200 bg-slate-50/50 text-[11px] text-slate-500 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  <span>Source verified</span>
                </div>
              </div>
            </aside>
          )}
        </main>
      </div>
      )}
    </div>
  );
}
