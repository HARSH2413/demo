'use client';
import React, { useState } from 'react';
import { Loader2, RefreshCw, Cloud, Plus, FileUp, Search, ArrowUpDown, Database, FileText, X, CheckCircle2, AlertCircle } from 'lucide-react';

export interface DocumentRecord {
  filename: string;
  file_hash?: string;
  created_at?: string;
  status?: 'processing' | 'indexed' | 'failed';
  size?: number;
}

export function KnowledgeBaseView({
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
                  {document.status === 'processing' ? <Loader2 size={10} className="animate-spin" /> : document.status === 'failed' ? <AlertCircle size={10} /> : <CheckCircle2 size={10} />} {document.status === 'processing' ? 'Indexing' : document.status === 'failed' ? 'Failed' : 'Indexed'}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
