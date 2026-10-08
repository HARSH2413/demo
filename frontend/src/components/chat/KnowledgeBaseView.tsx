'use client';
import React, { useState } from 'react';
import Link from 'next/link';
import {
  Loader2, Upload, Plus, Search, FileText, FileType2, Trash2, Lock,
  ChevronLeft, ChevronRight, MessageSquare, Cloud,
} from 'lucide-react';

export interface DocumentRecord {
  id: string;
  filename: string;
  file_hash?: string;
  created_at?: string;
  status?: 'processing' | 'indexed' | 'failed' | 'completed';
  error_message?: string;
  size?: number;
}

const PAGE_SIZE = 10;

function formatSize(bytes?: number) {
  if (!bytes && bytes !== 0) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value?: string) {
  if (!value) return '—';
  const d = new Date(value);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function StatusBadge({ status }: { status?: DocumentRecord['status'] }) {
  if (status === 'processing') {
    return (
      <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-700 text-[11px] font-medium">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
        <span>Processing</span>
      </div>
    );
  }
  if (status === 'failed') {
    return (
      <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-50 border border-rose-200 text-rose-700 text-[11px] font-medium">
        <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
        <span>Failed</span>
      </div>
    );
  }
  return (
    <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-[11px] font-medium">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
      <span>Ready</span>
    </div>
  );
}

export function KnowledgeBaseView({
  boxId,
  boxName,
  documents,
  isSyncing,
  isUploading,
  onUploadClick,
  onDeleteFile,
  onFilesSelected,
  onOpenChat,
}: {
  boxId?: string;
  boxName?: string;
  documents: DocumentRecord[];
  isSyncing: boolean;
  isUploading: boolean;
  onUploadClick: () => void;
  onDeleteFile: (filename: string) => void;
  onFilesSelected: (files: FileList | File[]) => void;
  onOpenChat?: () => void;
}) {
  const [query, setQuery] = useState('');
  const [dragging, setDragging] = useState(false);
  const [page, setPage] = useState(1);

  const filtered = documents
    .filter((d) => d.filename.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageItems = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
  const totalBytes = documents.reduce((sum, d) => sum + (d.size || 0), 0);
  const fileType = (filename: string) => filename.split('.').pop()?.toUpperCase() || 'FILE';
  const startIdx = filtered.length === 0 ? 0 : (currentPage - 1) * PAGE_SIZE + 1;
  const endIdx = Math.min(currentPage * PAGE_SIZE, filtered.length);

  return (
    <div className="flex-1 flex flex-col min-w-0 h-full overflow-y-auto bg-[#f8fafc]">
      {/* Top header / breadcrumb */}
      <header className="flex justify-between items-center h-14 px-6 w-full bg-white border-b border-[#e2e8f0] sticky top-0 z-30 text-sm tracking-tight text-slate-600 shrink-0">
        <div className="flex items-center gap-2 text-sm text-slate-500 font-medium min-w-0">
          <Link href="/boxes" className="hover:text-slate-900 cursor-pointer transition-colors">My Boxes</Link>
          <span className="text-slate-300">/</span>
          <span className="text-slate-900 font-semibold truncate">{boxName}</span>
          <span className="text-slate-300">/</span>
          <span className="text-[#4f46e5] font-medium">Documents</span>
        </div>
        <div className="flex items-center gap-3">
          {onOpenChat && (
            <button
              onClick={onOpenChat}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#4f46e5] hover:bg-indigo-700 text-white text-xs font-semibold transition-colors shadow-sm"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Chat with Box</span>
            </button>
          )}
        </div>
      </header>

      <main className="flex-1 p-8 max-w-7xl w-full mx-auto space-y-6">
        {/* Title */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="font-headline text-2xl font-bold tracking-tight text-[#0f172a]">Box Documents</h1>
            <p className="text-xs text-[#64748b] mt-1">All files in this Box. Upload documents, then chat with them to get cited answers.</p>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-700 bg-white px-3 py-1.5 rounded-lg border border-[#e2e8f0] shadow-sm">
            <span className={`w-2 h-2 rounded-full ${documents.some(d => d.status === 'processing') ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'}`} />
            <span>{documents.some(d => d.status === 'processing') ? 'Vault Sync: Processing' : 'Vault Sync: Active'}</span>
          </div>
        </div>

        {/* Chat with Box CTA */}
        {onOpenChat && (
          <section className="relative overflow-hidden rounded-xl bg-gradient-to-r from-[#4f46e5] via-indigo-600 to-violet-600 px-6 py-5 flex flex-col md:flex-row md:items-center md:justify-between gap-4 shadow-lg shadow-indigo-200/60">
            <div className="absolute -right-10 -top-10 w-40 h-40 rounded-full bg-white/10 blur-2xl pointer-events-none" />
            <div className="flex items-center gap-4 relative">
              <div className="w-11 h-11 rounded-xl bg-white/15 border border-white/20 flex items-center justify-center text-white shrink-0">
                <MessageSquare className="w-5 h-5" />
              </div>
              <div>
                <h2 className="font-headline text-base font-semibold text-white">Ask questions about your documents</h2>
                <p className="text-xs text-indigo-100 mt-0.5">
                  {documents.filter(d => d.status !== 'failed').length > 0
                    ? `Chat with ${documents.filter(d => d.status !== 'failed').length} document${documents.filter(d => d.status !== 'failed').length === 1 ? '' : 's'} in this Box and get answers with cited sources.`
                    : 'Upload a document, then chat with it to get answers with cited sources.'}
                </p>
              </div>
            </div>
            <button
              onClick={onOpenChat}
              className="relative group flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-white text-[#4f46e5] text-sm font-semibold shadow-sm hover:bg-indigo-50 hover:shadow-md transition-all focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-indigo-600 shrink-0"
            >
              <MessageSquare className="w-4 h-4" />
              <span>Chat with Box</span>
              <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
            </button>
          </section>
        )}

        {/* Compact upload bar */}
        <section
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            if (e.dataTransfer.files?.length) onFilesSelected(e.dataTransfer.files);
          }}
          className={`rounded-lg bg-white border border-dashed px-5 py-3.5 flex flex-col md:flex-row md:items-center md:justify-between gap-3 transition-colors shadow-sm ${dragging ? 'border-indigo-400 bg-indigo-50/40' : 'border-[#e2e8f0] hover:border-indigo-300'}`}
        >
          <div className="flex items-center gap-3.5">
            <div className="w-9 h-9 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-[#4f46e5] shrink-0">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-medium text-slate-900 flex items-center gap-2">
                <span>Drop files here to upload</span>
                <span className="text-xs text-slate-500 font-normal hidden sm:inline">• Ready to chat in moments</span>
              </div>
              <p className="text-xs text-slate-500">PDF, DOCX, TXT, CSV, XLSX up to 25MB</p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={onUploadClick}
              disabled={isUploading}
              className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-[#4f46e5] text-white text-xs font-semibold transition-all hover:bg-indigo-700 focus:ring-2 focus:ring-indigo-500 focus:outline-none shadow-sm disabled:opacity-60"
            >
              {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              <span>Upload Document</span>
            </button>
          </div>
        </section>

        {/* Table container */}
        <section className="rounded-lg bg-white border border-[#e2e8f0] overflow-hidden shadow-sm">
          <div className="px-5 py-3 border-b border-[#e2e8f0] flex flex-col sm:flex-row items-center justify-between gap-3 bg-[#f8fafc]">
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4 pointer-events-none" />
              <input
                value={query}
                onChange={(e) => { setQuery(e.target.value); setPage(1); }}
                className="w-full bg-white border border-[#e2e8f0] rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-[#4f46e5] focus:ring-1 focus:ring-[#4f46e5] transition-all"
                placeholder="Filter documents..."
                type="text"
              />
            </div>
            <div className="text-xs text-slate-500 font-mono shrink-0 flex items-center gap-2">
              <FileText className="w-3.5 h-3.5" />
              <span>{documents.length} document{documents.length === 1 ? '' : 's'}{totalBytes > 0 ? ` • ${formatSize(totalBytes)}` : ''}</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#e2e8f0] text-slate-500 font-medium bg-[#f8fafc] uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-5">Document Name</th>
                  <th className="py-3 px-4 w-28">File Type</th>
                  <th className="py-3 px-4 w-28">Size</th>
                  <th className="py-3 px-4 w-32">Upload Date</th>
                  <th className="py-3 px-4 w-36">Status</th>
                  <th className="py-3 px-5 text-right w-24">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e2e8f0] bg-white">
                {pageItems.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-500">
                      {documents.length === 0 ? 'No documents yet. Upload a file to get started.' : 'No documents match your filter.'}
                    </td>
                  </tr>
                ) : pageItems.map((doc) => {
                  const type = fileType(doc.filename);
                  return (
                    <tr key={doc.filename} className="hover:bg-slate-50/80 transition-colors group">
                      <td className="py-3 px-5">
                        <div className="flex items-center gap-3">
                          {type === 'PDF'
                            ? <FileType2 className="w-5 h-5 text-rose-500 shrink-0" />
                            : <FileText className="w-5 h-5 text-[#4f46e5] shrink-0" />}
                          <div className="flex flex-col">
                            <div className="font-medium text-slate-900 group-hover:text-[#4f46e5] transition-colors truncate max-w-xs md:max-w-md" title={doc.filename}>
                              {doc.filename}
                            </div>
                            {doc.status === 'failed' && doc.error_message && (
                              <div className="text-[11px] text-rose-600 mt-0.5 line-clamp-1" title={doc.error_message}>
                                {doc.error_message}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-slate-600 font-mono">
                        <span className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700 text-[11px] font-medium">{type}</span>
                      </td>
                      <td className="py-3 px-4 text-slate-600 font-mono">{formatSize(doc.size)}</td>
                      <td className="py-3 px-4 text-slate-600">{formatDate(doc.created_at)}</td>
                      <td className="py-3 px-4"><StatusBadge status={doc.status} /></td>
                      <td className="py-3 px-5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {onOpenChat && (
                            <button onClick={onOpenChat} className="px-2 py-1 rounded text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors font-medium text-xs">
                              Chat
                            </button>
                          )}
                          <button
                            onClick={() => { if (confirm(`Delete "${doc.filename}"?`)) onDeleteFile(doc.id); }}
                            className="p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="px-5 py-3 border-t border-[#e2e8f0] flex items-center justify-between text-xs text-slate-500 bg-white">
            <span>Showing {startIdx}-{endIdx} of {filtered.length} documents</span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={currentPage <= 1}
                className="p-1 rounded text-slate-500 hover:bg-slate-100 disabled:text-slate-300 disabled:cursor-not-allowed disabled:hover:bg-transparent"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-mono text-[11px] font-medium border border-slate-200">{currentPage}</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages}
                className="p-1 rounded text-slate-500 hover:bg-slate-100 disabled:text-slate-300 disabled:cursor-not-allowed disabled:hover:bg-transparent"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </section>

        <footer className="pt-2 pb-6 flex items-center justify-between text-xs text-[#64748b] border-t border-[#e2e8f0]">
          <div className="flex items-center gap-2">
            <Lock className="w-3.5 h-3.5 text-slate-400" />
            <span>Encrypted storage{boxId ? <> • Box ID: <code className="font-mono text-slate-800 bg-slate-100 px-1 py-0.5 rounded border border-slate-200">{boxId.slice(0, 8)}</code></> : null}</span>
          </div>
        </footer>
      </main>
    </div>
  );
}
