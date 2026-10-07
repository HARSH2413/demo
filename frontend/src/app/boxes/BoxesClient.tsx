"use client";

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Loader2, Plus, X, AlertCircle } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import DomainSelect from '@/components/boxes/DomainSelect';

interface Box {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  document_count?: number;
}

interface BoxesResponse {
  data: Box[];
}

interface SingleBoxResponse {
  data: Box;
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 5) return 'Good night';
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  if (h < 21) return 'Good evening';
  return 'Good night';
}

export default function BoxesClient({ userName = '' }: { userName?: string }) {
  const router = useRouter();
  const [greeting, setGreeting] = useState('');
  useEffect(() => { setGreeting(getGreeting()); }, []);
  const [boxes, setBoxes] = useState<Box[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Create Box Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newBoxName, setNewBoxName] = useState('');
  const [newBoxDescription, setNewBoxDescription] = useState('');
  const [newBoxDomain, setNewBoxDomain] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const fetchBoxes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiFetch<BoxesResponse>('/api/v1/boxes/');
      setBoxes(res.data || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load boxes.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBoxes();
  }, [fetchBoxes]);

  // Listen for create-box event from ShellLayout sidebar
  useEffect(() => {
    const handler = () => setShowCreateModal(true);
    window.addEventListener('docintel:create-box', handler);
    if (new URLSearchParams(window.location.search).get('new') === '1') {
      setShowCreateModal(true);
      window.history.replaceState(null, '', '/boxes');
    }
    return () => window.removeEventListener('docintel:create-box', handler);
  }, []);

  const handleCreateBox = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBoxName.trim() || !newBoxDomain || isCreating) return;

    try {
      setIsCreating(true);
      setError(null);
      
      // Map human-readable domain to backend enum
      let backendDomain = "general";
      const d = newBoxDomain.toLowerCase();
      if (d.includes('finance')) backendDomain = 'finance';
      else if (d.includes('legal')) backendDomain = 'legal';
      else if (d.includes('human')) backendDomain = 'human_resources';
      else if (d.includes('engineering')) backendDomain = 'engineering';
      else if (d.includes('sales')) backendDomain = 'sales';
      else if (d.includes('marketing')) backendDomain = 'marketing';
      else if (d.includes('operations')) backendDomain = 'operations';
      else if (d.includes('compliance')) backendDomain = 'compliance';

      const body: Record<string, string> = { name: newBoxName.trim(), domain: backendDomain };
      if (newBoxDescription.trim()) body.description = newBoxDescription.trim();
      const res = await apiFetch<SingleBoxResponse>('/api/v1/boxes/', {
        method: 'POST',
        body: JSON.stringify(body)
      });
      setBoxes([res.data, ...boxes]);
      setNewBoxName('');
      setNewBoxDescription('');
      setNewBoxDomain('');
      setShowCreateModal(false);
      router.push(`/boxes/${res.data.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create box.");
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteBox = async (boxId: string, boxName: string) => {
    if (!window.confirm(`Delete box "${boxName}"? This cannot be undone.`)) return;
    try {
      await apiFetch(`/api/v1/boxes/${boxId}`, { method: 'DELETE' });
      setBoxes(boxes.filter(b => b.id !== boxId));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete box.");
    }
  };

  const filteredBoxes = boxes.filter(box =>
    box.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (box.description || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const timeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    if (hours < 1) return 'Just now';
    if (hours < 24) return `Updated ${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `Updated ${days}d ago`;
    return `Updated ${new Date(dateStr).toLocaleDateString()}`;
  };

  return (
    <>
      {/* Main Dashboard Content — matches Stitch docintel_minimal_dashboard_light */}
      <div className="flex-1 px-6 md:px-10 py-8 md:py-12 max-w-5xl w-full mx-auto">
        {/* Welcome Header */}
        <section className="mb-10 md:mb-12">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 font-headline mb-2 min-h-[2rem]">
            {greeting ? `${greeting}${userName ? `, ${userName}` : ''}` : '\u00A0'}
          </h1>
          <p className="text-sm text-slate-500 font-normal">
            Select a Box to start querying or create a new workspace.
          </p>
        </section>

        {/* Search & Create Row */}
        <section className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 mb-8">
          <div className="relative flex-1 max-w-md">
            <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              className="w-full bg-white border border-slate-200 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:ring-1 focus:ring-indigo-600 focus:border-indigo-600 focus:outline-none transition-all shadow-sm"
              placeholder="Search boxes..."
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm transition-colors duration-150 shrink-0 shadow-sm"
          >
            <Plus size={16} />
            <span>Create Box</span>
          </button>
        </section>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg flex items-center gap-3 text-sm">
            <AlertCircle size={18} />
            <span className="font-medium">{error}</span>
          </div>
        )}

        {/* Filter Tabs */}
        <section className="flex items-center gap-6 mb-6 border-b border-slate-200 pb-3">
          <button className="text-xs font-semibold text-indigo-600 transition-colors relative py-1">
            All Boxes
            <span className="absolute bottom-[-13px] left-0 right-0 h-0.5 bg-indigo-600 rounded-full" />
          </button>
          <button className="text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors py-1">
            Recent
          </button>
        </section>

        {/* Boxes Grid */}
        {loading ? (
          <div className="flex items-center justify-center p-20">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
          </div>
        ) : filteredBoxes.length === 0 ? (
          <div className="text-center p-16 border-2 border-dashed border-slate-200 rounded-lg bg-white text-slate-500">
            <div className="w-12 h-12 mx-auto mb-4 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center">
              <svg className="w-6 h-6 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>
            </div>
            <h2 className="text-base font-semibold text-slate-700 mb-1 font-headline">
              {boxes.length ? 'No boxes match your search.' : 'No Boxes Yet'}
            </h2>
            <p className="text-sm text-slate-500">
              {boxes.length ? 'Try a different search term.' : 'Create your first Box to start querying your documents.'}
            </p>
          </div>
        ) : (
          <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredBoxes.map(box => (
              <Link
                key={box.id}
                href={`/boxes/${box.id}`}
                className="group p-5 rounded-lg bg-white border border-slate-200 hover:border-slate-300 hover:shadow-sm transition-all duration-150 flex flex-col justify-between h-44 cursor-pointer relative"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h2 className="text-base font-semibold text-slate-900 tracking-tight group-hover:text-indigo-600 transition-colors line-clamp-1 font-headline">
                      {box.name}
                    </h2>
                    <span className="text-slate-400 opacity-0 group-hover:opacity-100 group-hover:text-indigo-600 transition-opacity shrink-0">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 17L17 7M17 7H7M17 7V17" /></svg>
                    </span>
                  </div>
                  {box.description && (
                    <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">
                      {box.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center justify-between text-xs text-slate-500 pt-3 border-t border-slate-100">
                  {box.document_count !== undefined && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[11px] font-medium">
                      {box.document_count} documents
                    </span>
                  )}
                  <span className="text-slate-400 text-[11px]">
                    {timeAgo(box.created_at)}
                  </span>
                </div>
                {/* Delete button — appears on hover */}
                <button
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleDeleteBox(box.id, box.name); }}
                  className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-600 p-1 rounded-lg hover:bg-red-50 transition-all z-10"
                  title="Delete Box"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                </button>
              </Link>
            ))}
          </section>
        )}
      </div>

      {/* Create Box Modal — matches Stitch docintel_create_box_modal_personal_user */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0f172a]/30 backdrop-blur-[3px]">
          <div className="w-full max-w-[560px] bg-white rounded-2xl border border-slate-200 shadow-2xl overflow-hidden flex flex-col">
            {/* Header */}
            <div className="px-6 pt-5 pb-4 border-b border-slate-100 flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-indigo-600 inline-block" />
                  <h2 className="text-lg font-semibold text-slate-900 tracking-tight font-headline">Create New Box</h2>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Set up a personal workspace for your documents and grounded AI analysis.
                </p>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-900 rounded-lg p-1.5 hover:bg-slate-100 transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Body */}
            <form onSubmit={handleCreateBox} className="px-6 py-5 space-y-5 overflow-y-auto max-h-[calc(85vh-130px)]">
              {/* Box Name */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-900 tracking-tight flex items-center gap-1" htmlFor="box-name">
                    Box Name <span className="text-red-500 font-medium">*</span>
                  </label>
                  <span className="text-[10px] text-slate-400 font-mono">{newBoxName.length} / 64</span>
                </div>
                <input
                  autoFocus
                  className="w-full bg-white border border-slate-300 rounded-lg px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/15 transition-all"
                  id="box-name"
                  placeholder="e.g., Q4 Acquisition Due Diligence"
                  type="text"
                  maxLength={64}
                  value={newBoxName}
                  onChange={e => setNewBoxName(e.target.value)}
                  required
                />
                <p className="text-[11px] text-slate-500">A clear, descriptive name for your workspace.</p>
              </div>

              {/* Domain */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-900 tracking-tight flex items-center gap-1" htmlFor="box-domain">
                  What is this Box about? <span className="text-red-500 font-medium">*</span>
                </label>
                <DomainSelect value={newBoxDomain} onChange={setNewBoxDomain} />
                <p className="text-[11px] text-slate-500">Helps the AI tailor answers to your field.</p>
              </div>

              {/* Description */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-900 tracking-tight" htmlFor="box-desc">
                  Description <span className="text-slate-400 font-normal">(Optional)</span>
                </label>
                <textarea
                  className="w-full bg-white border border-slate-300 rounded-lg px-3.5 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/15 transition-all resize-none"
                  id="box-desc"
                  placeholder="Briefly describe the purpose of this collection or types of documents to be uploaded..."
                  rows={3}
                  value={newBoxDescription}
                  onChange={e => setNewBoxDescription(e.target.value)}
                />
              </div>

              {/* Privacy section */}
              <div className="space-y-2">
                <div>
                  <label className="text-xs font-semibold text-slate-900 tracking-tight block">Workspace Privacy</label>
                  <span className="text-[11px] text-slate-500">Manage privacy settings for your personal workspace.</span>
                </div>
                <label className="flex items-start gap-3 p-3 rounded-lg border border-indigo-200 bg-indigo-50/40 cursor-pointer">
                  <input type="radio" name="privacy" value="private" defaultChecked className="mt-0.5 text-indigo-600 focus:ring-indigo-600/30 border-slate-300" />
                  <div className="h-7 w-7 rounded bg-indigo-100 flex items-center justify-center shrink-0 text-indigo-600 mt-0.5">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-semibold text-slate-900">Private Workspace</span>
                      <span className="text-[9px] px-1.5 py-0.5 bg-indigo-600 text-white rounded font-semibold">DEFAULT</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5 leading-normal">
                      Only accessible by you. Documents and chat history remain strictly private.
                    </p>
                  </div>
                </label>
              </div>

              {/* Info notice */}
              <div className="flex items-start gap-2.5 p-3 rounded-lg bg-slate-50 border border-slate-200">
                <svg className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z" /></svg>
                <p className="text-[11px] text-slate-600 leading-relaxed">
                  <strong className="font-semibold text-indigo-600">Local isolation active:</strong> Your uploaded documents are processed securely and never used to train public AI models.
                </p>
              </div>
            </form>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-slate-100 bg-white flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 rounded-lg text-xs font-medium text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                onClick={handleCreateBox}
                disabled={isCreating || !newBoxName.trim() || !newBoxDomain}
                className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-50"
              >
                {isCreating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                <span>Create Box</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
