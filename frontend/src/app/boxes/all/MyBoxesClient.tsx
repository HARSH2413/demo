"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  AlertCircle, Briefcase, Building2, FileText, FlaskConical, Folder, GraduationCap, Hammer,
  Heart, Headphones, Home, Landmark, LayoutGrid, List, Loader2, MessageSquare, Megaphone,
  MoreVertical, Plus, Scale, Search, ShoppingCart, Star, Stethoscope, Trash2, Users, Wrench, Cpu,
  Factory, Radio, Wallet, User as UserIcon,
} from 'lucide-react';
import { apiFetch } from '@/lib/api';

interface Box {
  id: string;
  name: string;
  description?: string;
  domain?: string;
  created_at: string;
  updated_at?: string;
  document_count?: number;
}

type Tab = 'all' | 'recent' | 'favorites';

const DOMAIN_ICONS: Record<string, React.ElementType> = {
  'Business & Management': Briefcase,
  'Finance & Accounting': Wallet,
  'Legal & Compliance': Scale,
  'Human Resources': Users,
  'Sales & Marketing': Megaphone,
  'Technology & IT': Cpu,
  'Engineering': Wrench,
  'Healthcare & Medical': Stethoscope,
  'Education & Training': GraduationCap,
  'Research & Science': FlaskConical,
  'Government & Public Sector': Landmark,
  'Real Estate & Property': Home,
  'Manufacturing & Operations': Factory,
  'Construction & Infrastructure': Hammer,
  'Media & Communications': Radio,
  'Retail & E-commerce': ShoppingCart,
  'Customer Support & Service': Headphones,
  'Nonprofit & Organizations': Heart,
  'Personal / General Documents': UserIcon,
  'Government': Building2,
};

const FAV_KEY = 'docintel:favorite-boxes';
const RECENT_DAYS = 7;

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return mins <= 1 ? 'Just now' : `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function MyBoxesClient() {
  const router = useRouter();
  const [boxes, setBoxes] = useState<Box[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState<Tab>('all');
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [favorites, setFavorites] = useState<string[]>([]);
  const [menuOpen, setMenuOpen] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const fetchBoxes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiFetch<{ data: Box[] }>('/api/v1/boxes/');
      setBoxes(res.data || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load boxes.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchBoxes(); }, [fetchBoxes]);

  useEffect(() => {
    try { setFavorites(JSON.parse(localStorage.getItem(FAV_KEY) || '[]')); } catch { /* ignore */ }
    const v = localStorage.getItem('docintel:boxes-view');
    if (v === 'list' || v === 'grid') setView(v);
  }, []);

  // Sidebar "New Box" → open create modal on dashboard
  const openCreate = useCallback(() => router.push('/boxes?new=1'), [router]);
  useEffect(() => {
    window.addEventListener('docintel:create-box', openCreate);
    return () => window.removeEventListener('docintel:create-box', openCreate);
  }, [openCreate]);

  useEffect(() => {
    if (!menuOpen) return;
    const close = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(null);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [menuOpen]);

  const toggleFavorite = (id: string) => {
    setFavorites(prev => {
      const next = prev.includes(id) ? prev.filter(f => f !== id) : [...prev, id];
      localStorage.setItem(FAV_KEY, JSON.stringify(next));
      return next;
    });
  };

  const changeView = (v: 'grid' | 'list') => {
    setView(v);
    localStorage.setItem('docintel:boxes-view', v);
  };

  const handleDelete = async (box: Box) => {
    setMenuOpen(null);
    if (!window.confirm(`Delete box "${box.name}"? This cannot be undone.`)) return;
    try {
      await apiFetch(`/api/v1/boxes/${box.id}`, { method: 'DELETE' });
      setBoxes(b => b.filter(x => x.id !== box.id));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete box.');
    }
  };

  const visible = useMemo(() => {
    const q = query.toLowerCase();
    let list = boxes.filter(b =>
      b.name.toLowerCase().includes(q) ||
      (b.description || '').toLowerCase().includes(q) ||
      (b.domain || '').toLowerCase().includes(q)
    );
    if (tab === 'favorites') list = list.filter(b => favorites.includes(b.id));
    if (tab === 'recent') {
      const cutoff = Date.now() - RECENT_DAYS * 86400000;
      list = list
        .filter(b => new Date(b.updated_at || b.created_at).getTime() >= cutoff)
        .sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime());
    }
    return list;
  }, [boxes, query, tab, favorites]);

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: 'all', label: 'All Boxes', count: boxes.length },
    { key: 'recent', label: 'Recent' },
    { key: 'favorites', label: 'Favorites', count: favorites.filter(f => boxes.some(b => b.id === f)).length },
  ];

  const renderMenu = (box: Box) => menuOpen === box.id && (
    <div ref={menuRef} className="absolute right-0 top-8 z-20 w-44 bg-white border border-slate-200 rounded-lg shadow-lg py-1 text-sm">
      <button onClick={() => { toggleFavorite(box.id); setMenuOpen(null); }} className="w-full flex items-center gap-2 px-3 py-2 text-slate-700 hover:bg-slate-50">
        <Star size={14} className={favorites.includes(box.id) ? 'fill-amber-400 text-amber-400' : ''} />
        {favorites.includes(box.id) ? 'Remove favorite' : 'Add to favorites'}
      </button>
      <Link href={`/boxes/${box.id}`} className="w-full flex items-center gap-2 px-3 py-2 text-slate-700 hover:bg-slate-50">
        <FileText size={14} /> Manage documents
      </Link>
      <div className="my-1 border-t border-slate-100" />
      <button onClick={() => handleDelete(box)} className="w-full flex items-center gap-2 px-3 py-2 text-red-600 hover:bg-red-50">
        <Trash2 size={14} /> Delete box
      </button>
    </div>
  );

  const DomainIcon = ({ domain, className }: { domain?: string; className?: string }) => {
    const Icon = (domain && DOMAIN_ICONS[domain]) || Folder;
    return <Icon size={20} className={className} />;
  };

  return (
    <div className="flex-1 px-6 md:px-10 py-8 md:py-10 max-w-6xl w-full mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 font-headline">My Boxes</h1>
          <p className="text-sm text-slate-500 mt-1">Organize and access your document workspaces.</p>
        </div>
        <button
          id="my-boxes-new"
          onClick={openCreate}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium shadow-sm transition-all active:scale-[0.99] shrink-0"
        >
          <Plus size={16} /> New Box
        </button>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-3">
        <nav className="flex items-center gap-1">
          {tabs.map(t => (
            <button
              key={t.key}
              id={`my-boxes-tab-${t.key}`}
              onClick={() => setTab(t.key)}
              className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${tab === t.key ? 'bg-indigo-50 text-indigo-600' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'}`}
            >
              {t.label}
              {t.count !== undefined && t.count > 0 && (
                <span className={`text-[11px] ${tab === t.key ? 'text-indigo-400' : 'text-slate-400'}`}>{t.count}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-72">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              id="my-boxes-search"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Filter boxes..."
              className="w-full pl-9 pr-3 py-1.5 text-sm bg-white rounded-lg border border-slate-200 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 transition-all shadow-sm"
            />
          </div>
          <div className="flex items-center bg-slate-50 p-0.5 rounded-lg border border-slate-200 shrink-0">
            <button onClick={() => changeView('grid')} title="Grid view" className={`p-1.5 rounded transition-colors ${view === 'grid' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-400 hover:text-slate-700'}`}>
              <LayoutGrid size={16} />
            </button>
            <button onClick={() => changeView('list')} title="List view" className={`p-1.5 rounded transition-colors ${view === 'list' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-400 hover:text-slate-700'}`}>
              <List size={16} />
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-24 text-slate-400">
          <Loader2 className="animate-spin" size={24} />
        </div>
      ) : visible.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center border border-dashed border-slate-200 rounded-xl bg-white">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600 mb-3">
            {tab === 'favorites' ? <Star size={22} /> : <Folder size={22} />}
          </div>
          <h2 className="text-sm font-semibold text-slate-900">
            {query ? 'No boxes match your search' : tab === 'favorites' ? 'No favorites yet' : tab === 'recent' ? 'No recent activity' : 'No boxes yet'}
          </h2>
          <p className="text-xs text-slate-500 mt-1 max-w-xs">
            {tab === 'favorites' ? 'Star a box from its menu to pin it here.' : 'Create a box to start organizing your documents.'}
          </p>
          {tab === 'all' && !query && (
            <button onClick={openCreate} className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium">
              <Plus size={14} /> Create Box
            </button>
          )}
        </div>
      ) : view === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {visible.map(box => {
            const fav = favorites.includes(box.id);
            return (
              <article
                key={box.id}
                className="group relative flex flex-col justify-between bg-white rounded-xl border border-slate-200 hover:border-indigo-200 hover:shadow-[0_4px_16px_-2px_rgba(15,23,42,0.06)] transition-all duration-200 p-5"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                      <DomainIcon domain={box.domain} />
                    </div>
                    <div className="relative flex items-center gap-0.5">
                      <button onClick={() => toggleFavorite(box.id)} title={fav ? 'Remove favorite' : 'Add to favorites'} className="p-1 rounded-lg text-slate-300 hover:text-amber-400 hover:bg-slate-50 transition-colors">
                        <Star size={16} className={fav ? 'fill-amber-400 text-amber-400' : ''} />
                      </button>
                      <button onClick={() => setMenuOpen(menuOpen === box.id ? null : box.id)} title="Options" className="p-1 rounded-lg text-slate-400 hover:text-slate-900 hover:bg-slate-50 transition-colors">
                        <MoreVertical size={18} />
                      </button>
                      {renderMenu(box)}
                    </div>
                  </div>
                  <Link href={`/boxes/${box.id}`}>
                    <h2 className="text-base font-semibold text-slate-900 tracking-tight group-hover:text-indigo-600 transition-colors line-clamp-1">{box.name}</h2>
                  </Link>
                  <p className="text-sm text-slate-500 mt-1.5 line-clamp-2 leading-relaxed min-h-[2.75rem]">
                    {box.description || 'No description provided.'}
                  </p>
                  {box.domain && (
                    <div className="flex items-center gap-2 mt-3">
                      <span className="px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-600">{box.domain}</span>
                    </div>
                  )}
                </div>
                <div className="mt-5 pt-3.5 border-t border-slate-100 flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <FileText size={14} className="text-slate-400" />
                    <span>{box.document_count ?? 0} docs</span>
                    <span className="text-slate-300">•</span>
                    <span>{timeAgo(box.updated_at || box.created_at)}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Link href={`/boxes/${box.id}`} className="px-2.5 py-1 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-medium transition-colors">Docs</Link>
                    <Link href={`/boxes/${box.id}?view=chat`} className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium transition-colors">
                      <MessageSquare size={12} /> Chat
                    </Link>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100">
          {visible.map(box => {
            const fav = favorites.includes(box.id);
            return (
              <div key={box.id} className="group relative flex items-center gap-4 px-5 py-3.5 hover:bg-slate-50/60 transition-colors">
                <div className="w-9 h-9 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600 shrink-0">
                  <DomainIcon domain={box.domain} className="w-[18px] h-[18px]" />
                </div>
                <Link href={`/boxes/${box.id}`} className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-slate-900 truncate group-hover:text-indigo-600 transition-colors">{box.name}</div>
                  <div className="text-xs text-slate-500 truncate">{box.description || 'No description provided.'}</div>
                </Link>
                {box.domain && <span className="hidden md:inline px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-600 shrink-0">{box.domain}</span>}
                <span className="hidden sm:inline text-xs text-slate-500 w-16 text-right shrink-0">{box.document_count ?? 0} docs</span>
                <span className="hidden lg:inline text-xs text-slate-400 w-20 text-right shrink-0">{timeAgo(box.updated_at || box.created_at)}</span>
                <div className="relative flex items-center gap-1 shrink-0">
                  <button onClick={() => toggleFavorite(box.id)} className="p-1 rounded-lg text-slate-300 hover:text-amber-400">
                    <Star size={15} className={fav ? 'fill-amber-400 text-amber-400' : ''} />
                  </button>
                  <Link href={`/boxes/${box.id}?view=chat`} className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium">
                    <MessageSquare size={12} /> Chat
                  </Link>
                  <button onClick={() => setMenuOpen(menuOpen === box.id ? null : box.id)} className="p-1 rounded-lg text-slate-400 hover:text-slate-900 hover:bg-slate-100">
                    <MoreVertical size={16} />
                  </button>
                  {renderMenu(box)}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Footer */}
      {!loading && boxes.length > 0 && (
        <footer className="pt-4 flex items-center justify-between text-xs text-slate-400 border-t border-slate-200">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-600" />
            Showing {visible.length} of {boxes.length} workspace{boxes.length === 1 ? '' : 's'}
          </div>
        </footer>
      )}
    </div>
  );
}
